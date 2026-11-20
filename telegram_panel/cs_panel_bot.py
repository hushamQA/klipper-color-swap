#!/usr/bin/env python3
"""COLOR_SWAP Telegram panel - a control panel with buttons, no typing.

Runs on the printer next to Moonraker. Python 3.7+, standard library only.

  * Everything here is for controlling the printer from FAR AWAY. Buttons that need
    somebody standing at the printer (Unload, Load + purge, Purge, Re-home, material
    presets, Printer setup) are never shown.
  * A fixed bar of keys sits at the bottom of the chat (Status, Pause, Resume,
    Home / Away, Settings, Cancel print, STOP). It never scrolls away.
  * The control panel is ONE message: pinned, updating itself, and brought back to the
    bottom of the chat by any key. It shows the printer status and has buttons for
    Refresh, Pause / Resume / Cancel, Heaters off, HOME / AWAY, Settings and
    Emergency stop.
  * A waiting color swap gets its own card: what is waiting, and what can be done from
    here - Keep the current color and continue, Wait for me, Cancel print. When the
    swap needs hands (the old filament is out, or it ran out) the card says so.
  * Settings opens the settings window in the chat with the same buttons as on the
    printer (minus Printer setup). Windows opened AT the printer are not sent here.
  * A print with color swaps starts: one message says the mode (HOME / AWAY) with a
    button to change it - AWAY only helps if it is set BEFORE a swap starts.
  * A button is only offered while it can still do something (HOME / AWAY is not offered
    for a swap whose old filament is already out).
  * Only ONE chat may use the bot (chat_id). Everybody else is ignored.
  * There is no way to type G-code: buttons only.

Token and chat id: [bot] in cs_telegram.conf, or - when that file has none - the
tgram://TOKEN/CHAT_ID line of the Moonraker notifier that already sends the alerts.
"""
import configparser
import html
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = "1.5"
# The fixed bar of keys at the bottom of the chat (Telegram's "reply keyboard"). It takes
# the place of the phone keyboard and stays there however many messages arrive, so the
# controls never scroll away. KEYBOARD_VER changes when the layout does, so it is re-sent.
KEYBOARD_VER = 3
KEYBOARD = {"keyboard": [[{"text": "📊 Status"}, {"text": "⏸ Pause"}, {"text": "▶️ Resume"}],
                         [{"text": "🏠 Home / Away"}, {"text": "⚙️ Settings"}],
                         [{"text": "⛔ Cancel print"}, {"text": "🛑 STOP"}]],
            "resize_keyboard": True, "is_persistent": True}
# what each key (or typed word) means: a panel action, or "status" = just show the panel
KEYS = {"status": "status", "panel": "status", "/panel": "status", "/start": "status",
        "pause": "pause", "resume": "resume", "home / away": "mode", "settings": "settings",
        "cancel print": "cancel", "stop": "estop"}
DEFAULT_STATE = "~/cs-telegram-panel/state.json"
# The commands a settings window is made of. A window with any other button is not a
# settings window and is never shown in the chat.
SETTINGS_CMDS = {"COLOR_SWAP_SETTINGS", "_CS_SET_EDIT", "_CS_SET_ADJ", "_CS_SET_MODE", "_CS_PURGE_LEVEL",
                 "_CS_SET_RESET", "_CS_SET_CLOSE", "COLOR_SWAP_CHECK"}
# Settings buttons that only make sense at the printer (install-time values, the install
# check that answers on the console): left out of the chat.
AT_PRINTER_ONLY = ("COLOR_SWAP_SETTINGS V=setup", "COLOR_SWAP_CHECK")
DEFAULT_CONF = "~/printer_data/config/cs_telegram.conf"
MOONRAKER_CONF = "~/printer_data/config/moonraker.conf"


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def load_config(path=DEFAULT_CONF, moonraker_conf=MOONRAKER_CONF):
    cfg = {"token": "", "chat_id": "", "moonraker": "http://127.0.0.1:7125",
           "api": "https://api.telegram.org", "title": "3D printer", "poll": 1.0}
    cp = configparser.ConfigParser()
    try:
        cp.read(os.path.expanduser(path), encoding="utf-8")
    except configparser.Error as e:
        log("config error:", e)
    if cp.has_section("bot"):
        for k in ("token", "chat_id", "moonraker", "api", "title"):
            v = cp.get("bot", k, fallback="").strip()
            if v and v not in ("BOT_TOKEN", "CHAT_ID"):
                cfg[k] = v
    if not cfg["token"] or not cfg["chat_id"]:
        try:
            text = open(os.path.expanduser(moonraker_conf), encoding="utf-8").read()
            m = re.search(r"^\s*url:\s*tgram://([^/\s]+)/([^/\s?]+)", text, re.M)
            if m and m.group(1) != "BOT_TOKEN":
                cfg["token"] = cfg["token"] or m.group(1)
                cfg["chat_id"] = cfg["chat_id"] or m.group(2)
        except OSError:
            pass
    # the notifier (apprise) also accepts the token written as "bot123456:ABC..."
    cfg["token"] = re.sub(r"^bot(?=\d+:)", "", cfg["token"], flags=re.I)
    return cfg


def esc(s):
    return html.escape(str(s), quote=False)


def key_of(text):
    """A key of the bar, without its emoji: "⏸ Pause" -> "pause"."""
    return re.sub(r"[^\w /]+", "", text or "").strip().lower()


def bar(pct, n=10):
    """A progress bar of n blocks: ▰▰▰▱▱▱▱▱▱▱"""
    full = int(round(max(0.0, min(100.0, pct)) / 100.0 * n))
    return "▰" * full + "▱" * (n - full)


# Phone messages from the macros arrive as console lines "// cs_alert KIND|text".
# The kinds a swap card already shows (it updates itself) are not sent again.
CARD_KINDS = {"swap", "runout", "purge", "auto", "keep", "go", "cancel", "wait", "status"}
ALERTS = {"remind": ("🟡", "⏰", "Color swap still waiting"),
          "off": ("🔵", "🧊", "Nozzle heater switched off"),
          "saved": ("🟣", "💾", "Unfinished print saved"),
          "resume": ("🔵", "♻️", "Resume ready"),
          "test": ("⚪", "🔔", "Test message"),
          "info": ("⚪", "🔔", "Printer message")}

# printer state -> colored mark on the panel
STATE_MARK = {"printing": "🟢", "paused": "🟡", "standby": "⚪", "complete": "✅", "cancelled": "⛔", "error": "🔴"}


def hms(sec):
    sec = int(max(sec or 0, 0))
    return "%dh%02dm" % (sec // 3600, sec % 3600 // 60) if sec >= 3600 else "%dm" % (sec // 60)


class Bot:
    def __init__(self, cfg):
        self.cfg = cfg
        self.chat = str(cfg["chat_id"])
        self.stop = threading.Event()
        self.lock = threading.RLock()
        self.offset = 0
        # the mirrored printer window
        self.building = None          # prompt being received
        self.window = None            # prompt shown: {"title","text","rows","cmds"}
        self.win_msg = None           # Telegram message id of the window
        self.win_seq = 0
        self.close_at = 0             # time a prompt_end arrived with nothing after it yet
        self.mark = None              # (time, count) of the last console line handled
        self.panel_msg = None
        self.confirm = None           # ("cancel" | "estop", time)
        # Only the settings window is mirrored, and only while it was opened from here.
        self.settings_until = 0
        # the color swap card (what can be done about a waiting swap from far away)
        self.swap_msg = None
        self.swap_on = False
        self.swap_confirm = None      # ("keep" | "cancel", time)
        self.swap_dirty = False
        self.swap_shown = None        # last text + buttons sent, to skip identical edits
        self.status_at = 0
        self.panel_shown = None
        self.kb_ver = 0
        self.panel_at = 0
        self.printing = False
        self.mute_until = 0           # Telegram said "too many requests": quiet until then
        self.pending = None           # a mode / settings tap waiting for a busy printer
        self.job_file = None          # the print the start message was sent for
        self.job_seen = False
        self.start_msg = None
        self.start_info = None        # {"file", "swaps"}
        self.tg_panel_set = False     # tg_panel was switched on once (state.json)
        self.notify_on = True

    # ------------------------------------------------------------ network
    def tg(self, method, timeout=35, **params):
        if time.time() < self.mute_until:
            return None
        url = "%s/bot%s/%s" % (self.cfg["api"], self.cfg["token"], method)
        data = json.dumps(params).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read().decode())
                return out.get("result") if out.get("ok") else None
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            if "not modified" in body:       # the message already shows exactly this
                return True
            if e.code == 429:                # flood limit: stay quiet as long as Telegram asks
                m = re.search(r'"retry_after":\s*(\d+)', body)
                self.mute_until = time.time() + (int(m.group(1)) if m else 30)
            log("telegram", method, e.code, body)
            return None
        except Exception as e:           # network down, timeout...
            log("telegram", method, "failed:", type(e).__name__)
            return None

    def mr(self, path, post=False, timeout=10):
        req = urllib.request.Request(self.cfg["moonraker"] + path, data=b"" if post else None,
                                     method="POST" if post else "GET")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode()).get("result")

    def gcode(self, script, done=None):
        """Send one command to the printer. A long one (Load + purge) keeps running after
        the HTTP call times out, so it is sent from its own thread and never blocks.
        Klipper runs nothing while it heats (M109 / M190), so a command can wait minutes."""
        def run():
            try:
                self._gcode(script)
            finally:
                if done:
                    done()
        threading.Thread(target=run, daemon=True).start()

    def _gcode(self, script):
        try:
            self.mr("/printer/gcode/script?script=" + urllib.parse.quote(script), post=True, timeout=600)
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")
            try:
                msg = json.loads(msg)["error"]["message"]
            except Exception:
                pass
            self.say("⚠️ <b>The printer refused that</b>\n<code>%s</code>" % esc(str(msg)[:300]))
        except Exception as e:
            log("gcode", script, "->", type(e).__name__)

    def say(self, text, markup=None):
        p = {"chat_id": self.chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
        if markup is not None:
            p["reply_markup"] = markup
        return self.tg("sendMessage", **p)

    def edit(self, msg_id, text, markup=None):
        p = {"chat_id": self.chat, "message_id": msg_id, "text": text, "parse_mode": "HTML",
             "disable_web_page_preview": True, "reply_markup": markup or {"inline_keyboard": []}}
        return self.tg("editMessageText", **p)

    # ------------------------------------------------------------ the control panel
    def status(self):
        q = ("/printer/objects/query?print_stats&display_status&virtual_sdcard&pause_resume&webhooks"
             "&extruder=temperature,target&heater_bed=temperature,target"
             "&gcode_macro%20COLOR_SWAP=state,unloaded,slot,material,old_material,cur_material,runout,waited,idle_s,touched,swaps,standby"
             "&gcode_macro%20_COLOR_SWAP_CFG=auto_continue_min,away_min,auto_unload,notify,tg_panel")
        try:
            return self.mr(q)["status"]
        except Exception as e:
            log("status failed:", type(e).__name__)
            return None

    @staticmethod
    def needs_hands(st):
        """A swap waits that nobody far away can finish: the old filament is out (or being
        pulled out right now), it ran out, or the new one is loaded and must be checked.
        HOME / AWAY cannot help such a swap any more."""
        cs = st.get("gcode_macro COLOR_SWAP") or {}
        cc = st.get("gcode_macro _COLOR_SWAP_CFG") or {}
        state = int(cs.get("state", 0) or 0)
        if not state:
            return False
        unloading = state == 1 and not cs.get("unloaded") and not cs.get("runout") \
            and int(cc.get("auto_unload", 1) or 0) == 1 and float(cc.get("auto_continue_min", 0) or 0) <= 0
        return bool(cs.get("unloaded") or cs.get("runout") or state == 2 or unloading)

    def busy_note(self):
        """A mode / settings tap that the printer has not run yet (it is heating)."""
        p = self.pending
        if not p or time.time() - p["t"] < 3:
            return ""
        if p["what"] == "mode":
            return ("<i>Switching to %s: waiting for the printer. It is heating (or busy) and Klipper takes no "
                    "command until that ends. Your tap runs right after - before any color swap.</i>" % ("AWAY" if p["away"] else "HOME"))
        return "<i>Opening the settings: waiting for the printer (heating or busy). The window comes as soon as that ends.</i>"

    def slow(self, what, script, away=None):
        """Send a mode / settings command; if the printer is busy the panel says so."""
        p = {"what": what, "away": away, "t": time.time()}
        self.pending = p

        def done():
            if self.pending is p:
                self.pending = None
                if time.time() - p["t"] >= 3:
                    self.show_panel()
                    self.refresh_start()

        def later():
            if self.pending is p:
                self.show_panel()
                self.refresh_start()
        threading.Timer(3.5, later).start()
        self.gcode(script, done=done)

    def panel(self, st=None):
        st = st if st is not None else self.status()
        title = "🖨 <b>%s</b>" % esc(self.cfg["title"])
        if not st:
            return title + "\n\n🔴 The printer does not answer (Klipper or Moonraker is down).", \
                {"inline_keyboard": [[{"text": "🔄 Refresh", "callback_data": "m:refresh"}]]}
        ps = st.get("print_stats", {})
        state = ps.get("state", "?")
        paused = st.get("pause_resume", {}).get("is_paused", False)
        ex, bed = st.get("extruder", {}), st.get("heater_bed", {})
        cs = st.get("gcode_macro COLOR_SWAP") or {}
        cc = st.get("gcode_macro _COLOR_SWAP_CFG") or {}
        klippy = st.get("webhooks", {}).get("state", "ready")
        lines = [title, ""]
        if klippy != "ready":
            lines.append("🔴 Klipper: <b>%s</b> - nothing runs until Klipper is restarted." % esc(klippy))
            kb = [[{"text": "🔄 Refresh", "callback_data": "m:refresh"}]]
            if self.confirm and self.confirm[0] == "restart" and time.time() - self.confirm[1] < 30:
                lines += ["", "❓ <b>Really restart Klipper?</b> The print, if one was running, cannot go on."]
                return "\n".join(lines), {"inline_keyboard": [[{"text": "✅ Yes, restart Klipper", "callback_data": "m:yes_restart"},
                                                                {"text": "↩️ No, go back", "callback_data": "m:no"}]]}
            self.confirm = None
            if klippy in ("shutdown", "error"):
                kb.append([{"text": "🔁 Restart Klipper", "callback_data": "m:restart"}])
            return "\n".join(lines), {"inline_keyboard": kb}
        shown = "paused" if paused else state
        lines.append("%s State: <b>%s</b>" % (STATE_MARK.get(shown, "⚪"), esc(shown)))
        if state in ("printing", "paused") and ps.get("filename"):
            prog = (st.get("display_status", {}).get("progress") or st.get("virtual_sdcard", {}).get("progress") or 0) * 100
            info = ps.get("info") or {}
            layer = (" · layer %s/%s" % (info.get("current_layer"), info.get("total_layer"))
                     if info.get("total_layer") else "")
            lines.append("📄 File: %s" % esc(ps["filename"]))
            lines.append("📈 Done: <b>%d%%</b> %s%s" % (round(prog), bar(prog), layer))
            dur = ps.get("print_duration") or 0
            left = (" · about %s left" % hms(dur / prog * (100 - prog))) if prog >= 2 else ""
            lines.append("⏱ Printing for %s%s" % (hms(dur), left))
        lines.append("🌡 Nozzle <b>%d</b> / %d°C   🛏 Bed <b>%d</b> / %d°C" % (
            round(ex.get("temperature", 0)), round(ex.get("target", 0)),
            round(bed.get("temperature", 0)), round(bed.get("target", 0))))
        swap = int(cs.get("state", 0) or 0)
        if swap:
            what = "filament runout" if cs.get("runout") else "color swap to filament %s %s" % (cs.get("slot", ""), cs.get("material", ""))
            step = ("old filament still in" if not cs.get("unloaded") else "waiting for the new filament") if swap == 1 else "loaded - check the purge"
            lines.append("")
            lines.append("%s <b>Waiting: %s</b>\n      %s · ⏳ %d min" % ("🧵" if cs.get("runout") else "🎨", esc(what.strip()), step,
                                                                 int(cs.get("waited", 0) or 0) // 60))
        away = float(cc.get("auto_continue_min", 0) or 0) > 0
        hands = self.needs_hands(st)
        pend = self.pending if self.pending and self.pending["what"] == "mode" else None
        if cc:
            lines.append("")
            if pend and pend["away"] != away:
                lines.append("🔁 Mode: <b>%s</b>, switching to <b>%s</b>" % ("AWAY" if away else "HOME", "AWAY" if pend["away"] else "HOME"))
            else:
                lines.append("✈️ Mode: <b>AWAY</b> - a swap keeps the old filament in, waits %d min, then the print goes on with that color" % cc.get("auto_continue_min", 0)
                             if away else "🏠 Mode: <b>HOME</b> - every color swap waits for you, the old filament is pulled out at once")
            if hands:
                lines.append("🙋 HOME / AWAY cannot help this swap: somebody has to be at the printer. It applies from the next swap.")
        note = self.busy_note()
        if note:
            lines += ["", note]
        kb = [[{"text": "🔄 Refresh", "callback_data": "m:refresh"}]]
        if self.confirm and time.time() - self.confirm[1] < 30:
            word = {"cancel": "cancel the print", "estop": "EMERGENCY STOP"}.get(self.confirm[0], "do that")
            lines += ["", "❓ <b>Really %s?</b>" % word]
            kb = [[{"text": "✅ Yes, %s" % word, "callback_data": "m:yes_" + self.confirm[0]},
                   {"text": "↩️ No, go back", "callback_data": "m:no"}]]
            return "\n".join(lines), {"inline_keyboard": kb}
        self.confirm = None
        if state == "printing" and not paused:
            kb.append([{"text": "⏸ Pause", "callback_data": "m:pause"}, {"text": "⛔ Cancel print", "callback_data": "m:cancel"}])
        elif paused or state == "paused":
            row = [] if swap else [{"text": "▶️ Resume", "callback_data": "m:resume"}]
            kb.append(row + [{"text": "⛔ Cancel print", "callback_data": "m:cancel"}])
        if swap:
            kb.append([{"text": "🎨 Color swap - what can I do?", "callback_data": "m:swap"}])
        if state not in ("printing", "paused") and not paused and (ex.get("target", 0) or bed.get("target", 0)):
            kb.append([{"text": "❄️ Heaters off", "callback_data": "m:heat_off"}])
        if cc:
            row = [] if hands else [{"text": "✈️ I am AWAY - tap when home" if (pend["away"] if pend else away) else "🏠 I am HOME - tap when leaving",
                                     "callback_data": "m:mode"}]
            kb.append(row + [{"text": "⚙️ Settings", "callback_data": "m:settings"}])
        kb.append([{"text": "🛑 Emergency stop", "callback_data": "m:estop"}])
        return "\n".join(lines), {"inline_keyboard": kb}

    def load_state(self):
        try:
            d = json.load(open(os.path.expanduser(self.cfg.get("state", DEFAULT_STATE)), encoding="utf-8"))
            self.panel_msg = d.get("panel_msg")
            self.kb_ver = d.get("kb_ver", 0)
            self.tg_panel_set = d.get("tg_panel_set", False)
        except (OSError, ValueError):
            pass

    def save_state(self):
        try:
            json.dump({"panel_msg": self.panel_msg, "kb_ver": getattr(self, "kb_ver", 0),
                       "tg_panel_set": self.tg_panel_set}, open(os.path.expanduser(self.cfg.get("state", DEFAULT_STATE)), "w", encoding="utf-8"))
        except OSError as e:
            log("could not save the state:", e)

    def show_panel(self, new=False):
        """There is ONE panel message. It is pinned to the top of the chat and edited in
        place. new=True (the Panel key) moves it to the bottom of the chat: the old one
        is deleted, the new one is pinned."""
        text, kb = self.panel()
        with self.lock:
            self.panel_at = time.time()
            if self.panel_msg and not new:
                if (text, kb) == self.panel_shown or self.edit(self.panel_msg, text, kb):
                    self.panel_shown = (text, kb)
                    return
            r = self.say(text, kb)
            if not r:                    # no network: keep the old one, try again later
                return
            old, self.panel_msg, self.panel_shown = self.panel_msg, r["message_id"], (text, kb)
            if old and old != self.panel_msg:
                self.tg("deleteMessage", chat_id=self.chat, message_id=old)
            self.tg("pinChatMessage", chat_id=self.chat, message_id=self.panel_msg, disable_notification=True)
            self.save_state()
            log("panel sent and pinned")

    def panel_action(self, what):
        st = self.status() or {}
        cc = st.get("gcode_macro _COLOR_SWAP_CFG") or {}
        note = ""
        if what == "pause":
            self.gcode("PAUSE"); note = "Pausing"
        elif what == "resume":
            self.gcode("RESUME"); note = "Resuming"
        elif what in ("cancel", "estop", "restart"):
            self.confirm = (what, time.time())
        elif what == "yes_restart":
            self.confirm = None
            try:
                self.mr("/printer/firmware_restart", post=True)
            except Exception:
                pass
            note = "Restarting Klipper"
            time.sleep(2.0)
        elif what == "yes_cancel":
            self.confirm = None; self.gcode("CANCEL_PRINT"); note = "Cancelling the print"
        elif what == "yes_estop":
            self.confirm = None
            try:
                self.mr("/printer/emergency_stop", post=True)
            except Exception:
                pass
            note = "Emergency stop sent"
        elif what == "no":
            self.confirm = None
        elif what == "swap":
            self.swap_card(st, new=True); note = "Color swap"
        elif what == "heat_off":
            self.gcode("TURN_OFF_HEATERS"); note = "Heaters off"
            time.sleep(0.8)
        elif what == "settings":
            self.settings_until = time.time() + 900      # mirror the settings window for this visit
            self.slow("settings", "COLOR_SWAP_SETTINGS"); note = "Opening the settings"
        elif what == "mode" and cc and self.needs_hands(st):
            note = "Too late for this swap - somebody has to be at the printer. Set AWAY before the next one."
        elif what == "mode" and cc:
            pend = self.pending if self.pending and self.pending["what"] == "mode" else None
            away = pend["away"] if pend else float(cc.get("auto_continue_min", 0) or 0) > 0
            val = 0 if away else max(float(cc.get("away_min", 5) or 5), 1)
            # quiet change: nothing opens on the printer screen
            self.slow("mode", "_CS_SET_ADJ K=auto_continue_min V=%g Q=1" % val, away=not away)
            note = "Mode: HOME" if away else "Mode: AWAY"
            time.sleep(0.8)
        if what in ("pause", "resume", "yes_cancel"):
            time.sleep(1.0)
        return note

    # ------------------------------------------------------------ the mirrored window
    def feed(self, line):
        """One console line from the printer. Windows arrive as '// action:prompt_...'."""
        m = re.match(r"^(?://\s*)?action:prompt_(\w+)\s?(.*)$", line.strip())
        if not m:
            return
        kind, arg = m.group(1), m.group(2).strip()
        self.swap_dirty = True      # a window changed on the printer: look at the swap again
        if kind == "begin":
            self.building = {"title": arg, "text": "", "rows": [], "group": None, "footer": []}
        elif kind == "end":
            self.building = None
            if self.window is not None:
                self.close_at = time.time()
        elif self.building is None:
            return
        elif kind == "text":
            self.building["text"] = arg
        elif kind == "button_group_start":
            self.building["group"] = []
        elif kind == "button_group_end":
            if self.building["group"]:
                self.building["rows"].append(self.building["group"])
            self.building["group"] = None
        elif kind in ("button", "footer_button"):
            parts = arg.split("|")
            label = parts[0].strip()
            cmd = (parts[1].strip() if len(parts) > 1 and parts[1].strip() else label)
            btn = (label, cmd)
            if kind == "footer_button":
                self.building["footer"].append(btn)
            elif self.building["group"] is not None:
                self.building["group"].append(btn)
            else:
                self.building["rows"].append([btn])
        elif kind == "show":
            b = self.building
            every = [btn for row in b["rows"] for btn in row] + b["footer"]
            # Mirrored: the settings window, while it was opened from this chat. NOT
            # mirrored: the color swap and resume windows - their buttons (Unload, Load +
            # purge, Purge, Re-home...) are for somebody standing at the printer. What can
            # be done about a swap from far away is on the color swap card instead.
            is_settings = bool(every) and all(c.split(" ")[0] in SETTINGS_CMDS for _, c in every)
            if not (is_settings and time.time() < self.settings_until):
                if self.window is not None:
                    self.close_at = time.time() - 2
                return
            self.settings_until = time.time() + 900
            rows = []
            for row in b["rows"] + ([b["footer"]] if b["footer"] else []):
                row = [btn for btn in row if not any(btn[1].startswith(x) for x in AT_PRINTER_ONLY)]
                # long labels do not fit four in a row on a phone
                width = 2 if any(len(lbl) > 16 for lbl, _ in row) else 3
                for i in range(0, len(row), width):
                    rows.append(row[i:i + width])
            self.window = {"title": b["title"], "text": b["text"], "rows": rows}
            self.close_at = 0
            self.render_window()

    def render_window(self):
        w = self.window
        self.win_seq += 1
        cmds, kb = [], []
        for row in w["rows"]:
            line = []
            for label, cmd in row:
                line.append({"text": label[:60], "callback_data": "w:%d:%d" % (self.win_seq, len(cmds))})
                cmds.append((label, cmd))
            kb.append(line)
        w["cmds"] = cmds
        text = "⚙️ <b>%s</b>" % esc(w["title"]) + ("\n\n" + esc(w["text"]) if w["text"] else "")
        if not cmds:
            text += "\n\n⏳ <i>Working - no buttons until it is done.</i>"
        markup = {"inline_keyboard": kb}
        if self.win_msg and self.edit(self.win_msg, text, markup):
            log("window updated:", w["title"], "- %d buttons" % len(cmds))
            return
        r = self.say(text, markup)
        self.win_msg = r["message_id"] if r else None
        log("window sent:" if r else "window NOT sent:", w["title"], "- %d buttons" % len(cmds))

    def close_window(self):
        w, self.window, self.close_at = self.window, None, 0
        if w and self.win_msg:
            self.edit(self.win_msg, "⚙️ <b>%s</b>\n\n✔️ <i>Closed.</i>" % esc(w["title"]))
        if w:
            log("window closed:", w["title"])
        self.win_msg = None      # the next window is a new message, so the phone rings
        self.settings_until = 0

    # ------------------------------------------------------------ the color swap card
    def swap_view(self, st):
        """Text and buttons for a waiting swap: only what makes sense from far away."""
        cs = st.get("gcode_macro COLOR_SWAP") or {}
        cc = st.get("gcode_macro _COLOR_SWAP_CFG") or {}
        state, unloaded, runout = int(cs.get("state", 0) or 0), bool(cs.get("unloaded")), bool(cs.get("runout"))
        mins = int(cs.get("waited", 0) or 0) // 60
        new = ("filament %s %s" % (cs.get("slot") or "", cs.get("material") or "")).strip()
        ac = float(cc.get("auto_continue_min", 0) or 0) * 60
        armed = ac > 0 and not cs.get("touched") and state == 1 and not unloaded and not runout
        unloading = state == 1 and not unloaded and not runout and int(cc.get("auto_unload", 1) or 0) == 1 and ac <= 0
        can_keep = state == 1 and not unloaded and not runout and not unloading
        if runout:
            head = "🟠 🧵 Filament ran out"
            body = "🙋 The print is paused. Somebody at the printer has to load filament. From here you can only cancel."
        elif unloading:
            head = "🟡 🎨 Color swap to %s" % new
            body = ("🏠 Mode HOME: the printer is pulling the old filament out. Somebody at the printer has to insert the new one. "
                    "From here you can only cancel.\n\n💡 Next time you leave, tap AWAY before the swap: the old filament then stays in "
                    "and the print can go on with it.")
        elif state == 1 and not unloaded:
            head = "🟡 🎨 Color swap to %s" % new
            body = "🧵 The old filament (%s) is still in the nozzle, so the print can go on with it." % (cs.get("old_material") or "current color")
            if armed:
                left = max(int((ac - float(cs.get("idle_s", 0) or 0)) / 60 + 0.999), 0)
                body += "\n\n⏩ Nobody answers: in about <b>%d min</b> the print continues by itself with the current color." % left
            else:
                body += "\n\n✋ The printer is waiting. It will not continue by itself."
        elif state == 1:
            head = "🟡 🎨 Color swap to %s" % new
            body = ("🙋 The old filament is already out. Somebody at the printer has to insert the new one. From here you can only cancel."
                    "\n\n💡 AWAY helps only when it is set before a swap starts: the old filament then stays in.")
        else:
            head = "🔵 🧪 Color swap to %s" % new
            body = "🙋 The new filament is loaded. Somebody at the printer has to check the color and press Continue."
        text = "<b>%s</b>\n⏳ Waiting %d min · 🌡 Nozzle %d°C\n\n%s" % (esc(head), mins, round(st.get("extruder", {}).get("temperature", 0)), body)
        if cs.get("standby"):
            text += "\n\n🧊 The nozzle has cooled down to wait. The bed and the motors stay on."
        kb = []
        c = self.swap_confirm
        if c and time.time() - c[1] < 30 and (c[0] != "keep" or can_keep):
            q = "Continue the print now with the current color?" if c[0] == "keep" else "Really cancel the print?"
            text += "\n\n❓ <b>%s</b>" % q
            kb.append([{"text": "✅ Yes, continue" if c[0] == "keep" else "⛔ Yes, cancel the print", "callback_data": "s:yes_" + c[0]},
                       {"text": "↩️ No, go back", "callback_data": "s:no"}])
            return text, {"inline_keyboard": kb}
        self.swap_confirm = None
        if can_keep:
            kb.append([{"text": "▶️ Keep the current color and continue", "callback_data": "s:keep"}])
        if armed:
            kb.append([{"text": "✋ Wait for me - do not continue", "callback_data": "s:wait"}])
        kb.append([{"text": "⛔ Cancel print", "callback_data": "s:cancel"}, {"text": "🔄 Refresh", "callback_data": "s:refresh"}])
        return text, {"inline_keyboard": kb}

    def swap_card(self, st=None, new=False):
        st = st if st is not None else self.status()
        if not st:
            return
        with self.lock:
            cs = st.get("gcode_macro COLOR_SWAP") or {}
            active = int(cs.get("state", 0) or 0) > 0
            if not active:
                if self.swap_on and self.swap_msg:
                    ps = st.get("print_stats", {}).get("state", "")
                    end = ("The print continues with %s." % (cs.get("cur_material") or "the loaded filament")) if ps == "printing" \
                        else "The print was cancelled." if ps == "cancelled" else "The swap is over (printer: %s)." % ps
                    mark = "🟢 ✅" if ps == "printing" else "🔴 ⛔" if ps == "cancelled" else "⚪ ✔️"
                    self.edit(self.swap_msg, "%s <b>Color swap finished</b>\n\n%s" % (mark, esc(end)))
                    log("swap card closed:", end)
                self.swap_on, self.swap_msg, self.swap_shown, self.swap_confirm = False, None, None, None
                return
            text, kb = self.swap_view(st)
            if not self.swap_on:
                new = True                      # a new swap: a new message, so the phone rings
            self.swap_on = True
            if (text, kb) == self.swap_shown and not new:
                return
            if self.swap_msg and not new and self.edit(self.swap_msg, text, kb):
                self.swap_shown = (text, kb)
                return
            r = self.say(text, kb)
            self.swap_msg = r["message_id"] if r else None
            self.swap_shown = (text, kb)
            log("swap card sent:" if r else "swap card NOT sent:", re.sub(r"<[^>]+>", "", text.split("\n")[0]))

    def swap_action(self, what):
        note = ""
        if what in ("keep", "cancel"):
            self.swap_confirm = (what, time.time())
        elif what == "no":
            self.swap_confirm = None
        elif what == "yes_keep":
            self.swap_confirm = None; self.gcode("CS_KEEP"); note = "Continuing with the current color"
        elif what == "yes_cancel":
            self.swap_confirm = None; self.gcode("CANCEL_PRINT"); note = "Cancelling the print"
        elif what == "wait":
            self.gcode("_CS_TOUCH"); note = "The printer waits for you"
        if what in ("yes_keep", "yes_cancel", "wait"):
            time.sleep(1.2)
        self.swap_shown = None
        return note

    # ------------------------------------------------------------ phone messages from the macros
    def alert(self, line):
        """'// cs_alert KIND|text' from _CS_ALERT. Swap stages are on the swap card already."""
        m = re.match(r"^(?://\s*)?cs_alert\s+(\w+)\|(.*)$", line.strip())
        if not m or not self.notify_on:
            return
        kind, text = m.group(1).lower(), m.group(2).strip()
        if kind in CARD_KINDS:
            self.swap_dirty = True
            return
        mark, icon, head = ALERTS.get(kind, ALERTS["info"])
        self.say("%s %s <b>%s</b>\n%s\n🖨 <i>%s</i>" % (mark, icon, head, esc(text), esc(self.cfg["title"])))
        log("alert sent:", kind)

    def claim_alerts(self, st):
        """Once per install: tell the macros that this panel sends the messages
        (tg_panel 1), so the Moonraker notifier stops sending the same ones. Only while
        the printer is idle; the user can switch it back in the settings."""
        cc = st.get("gcode_macro _COLOR_SWAP_CFG") or {}
        self.notify_on = int(cc.get("notify", 1) or 0) == 1
        if self.tg_panel_set or "tg_panel" not in cc:
            return
        if int(cc.get("tg_panel") or 0) == 1:
            self.tg_panel_set = True
            self.save_state()
            return
        if st.get("print_stats", {}).get("state") in ("printing", "paused"):
            return
        self.tg_panel_set = True
        self.save_state()
        self.gcode("_CS_SET_ADJ K=tg_panel V=1 Q=1")
        log("tg_panel switched on: the panel sends the swap messages")

    # ------------------------------------------------------------ the print start message
    def watch_job(self, st):
        """A print with color swaps has started: say the mode now, while AWAY can still help."""
        ps = st.get("print_stats", {})
        state, fn = ps.get("state", ""), ps.get("filename") or ""
        if not self.job_seen:                 # the bot (re)started: not a new print
            self.job_seen = True
            self.job_file = fn if state in ("printing", "paused") else None
            return
        if state not in ("printing", "paused"):
            self.job_file = None
            return
        if not fn or fn == self.job_file:
            return
        self.job_file = fn
        swaps = None
        try:
            meta = self.mr("/server/files/metadata?filename=" + urllib.parse.quote(fn)) or {}
            swaps = meta.get("filament_change_count")
            if swaps is None and meta.get("filament_colors") is not None:
                swaps = 1 if len(set(meta["filament_colors"])) > 1 else 0
        except Exception:
            pass
        if swaps == 0:
            return                            # one color: HOME / AWAY does not matter
        self.start_info = {"file": fn, "swaps": swaps}
        self.start_msg = None
        text, kb = self.start_view(st)
        r = self.say(text, kb)
        self.start_msg = r["message_id"] if r else None
        log("print start message:", fn, swaps)

    def start_view(self, st):
        cc = st.get("gcode_macro _COLOR_SWAP_CFG") or {}
        cs = st.get("gcode_macro COLOR_SWAP") or {}
        info = self.start_info or {}
        away = float(cc.get("auto_continue_min", 0) or 0) > 0
        pend = self.pending if self.pending and self.pending["what"] == "mode" else None
        target = pend["away"] if pend else away
        n = info.get("swaps")
        lines = ["🚀 <b>Print started</b>", "📄 " + esc(info.get("file", ""))]
        if n:
            lines.append("🎨 Color swaps in this file: %d" % n)
        lines.append("")
        if target:
            lines.append("✈️ Mode: <b>AWAY</b> - a swap keeps the old filament in, waits %d min, then the print goes on with that color."
                         % max(float(cc.get("auto_continue_min", 0) or 0), float(cc.get("away_min", 5) or 5)))
        else:
            lines.append("🏠 Mode: <b>HOME</b> - every swap waits for you and the old filament is pulled out at once.")
        started = info.get("swap") or int(cs.get("state", 0) or 0) > 0
        if started:
            lines.append("<i>🎨 A color swap has started: change the mode on the panel for the next swaps.</i>")
            return "\n".join(lines), {"inline_keyboard": []}
        if not target:
            lines.append("💡 Leaving? Tap AWAY now - it must be set before the first swap.")
        note = self.busy_note()
        if note:
            lines += ["", note]
        kb = [[{"text": "✈️ I am AWAY - tap when home" if target else "🏠 I am HOME - tap when leaving", "callback_data": "p:mode"},
               {"text": "⚙️ Settings", "callback_data": "p:settings"}]]
        return "\n".join(lines), {"inline_keyboard": kb}

    def refresh_start(self, st=None):
        if not self.start_msg:
            return
        st = st if st is not None else self.status()
        if st:
            text, kb = self.start_view(st)
            self.edit(self.start_msg, text, kb)
            if not kb["inline_keyboard"]:
                self.start_msg = None          # done: the buttons are gone for good

    # ------------------------------------------------------------ loops
    def poll_printer(self):
        try:
            store = self.mr("/server/gcode_store?count=150", timeout=8)["gcode_store"]
        except Exception:
            return
        if self.mark is None:                     # first run: do not replay old windows
            self.mark = (store[-1]["time"], sum(1 for m in store if m["time"] == store[-1]["time"])) if store else (0, 0)
            return
        t0, n0 = self.mark
        new, same = [], 0
        for m in store:
            if m["time"] > t0:
                new.append(m)
            elif m["time"] == t0:
                same += 1
                if same > n0:
                    new.append(m)
        if new:
            last = new[-1]["time"]
            self.mark = (last, sum(1 for m in store if m["time"] == last))
            with self.lock:
                for m in new:
                    if "action:prompt_" in m.get("message", ""):
                        for line in m["message"].split("\n"):
                            self.feed(line)
                    elif "cs_alert " in m.get("message", ""):
                        for line in m["message"].split("\n"):
                            self.alert(line)
        with self.lock:
            if self.close_at and time.time() - self.close_at > 1.5:
                self.close_window()
        # the swap card: at once when a window changed on the printer, else every few seconds
        every = 5 if self.swap_on else float(self.cfg.get("status_every", 10))
        if self.swap_dirty or time.time() - self.status_at >= every:
            self.swap_dirty, self.status_at = False, time.time()
            st = self.status()
            if st:
                self.printing = st.get("print_stats", {}).get("state") in ("printing", "paused")
                self.claim_alerts(st)
                self.watch_job(st)
                self.swap_card(st)
                if self.swap_on and self.start_info:
                    self.start_info["swap"] = True     # this print had its first swap
                if self.start_msg and (self.swap_on or not self.printing):
                    self.refresh_start(st)
        # the pinned panel keeps itself up to date: every minute while printing or while
        # a swap waits, every five minutes otherwise
        if self.panel_msg and time.time() - self.panel_at >= float(
                self.cfg.get("panel_busy", 60) if (self.printing or self.swap_on) else self.cfg.get("panel_idle", 300)):
            self.show_panel()

    def printer_loop(self):
        while not self.stop.is_set():
            try:
                self.poll_printer()
            except Exception as e:
                log("printer loop:", type(e).__name__, e)
            self.stop.wait(float(self.cfg.get("poll", 1.0)))

    def handle(self, upd):
        cb = upd.get("callback_query")
        msg = upd.get("message")
        chat = str(((cb or {}).get("message") or msg or {}).get("chat", {}).get("id", ""))
        if chat != self.chat:
            if cb:
                self.tg("answerCallbackQuery", callback_query_id=cb["id"], text="Not allowed.")
            log("ignored a message from another chat")
            return
        if msg and (not msg.get("text") or (msg.get("from") or {}).get("is_bot")):
            # "... pinned a message" and other service notes: not a key press. Answering it
            # with a new pinned panel made another such note - an endless loop (v1.3).
            return
        if msg:
            # A key of the fixed bar at the bottom of the chat (or any typed text).
            key = KEYS.get(key_of(msg.get("text")), "status")
            log("key:", key)
            # keep the chat clean: the key press itself is removed
            if msg.get("message_id"):
                self.tg("deleteMessage", chat_id=self.chat, message_id=msg["message_id"])
            if key != "status":
                st = self.status() or {}
                state = st.get("print_stats", {}).get("state", "")
                paused = st.get("pause_resume", {}).get("is_paused", False)
                swap = int((st.get("gcode_macro COLOR_SWAP") or {}).get("state", 0) or 0)
                ready = st.get("webhooks", {}).get("state", "ready") == "ready"
                # a key only does something when it makes sense right now
                if not ready:
                    key = "status"                # Klipper is down: the panel offers the restart
                elif key == "pause" and not (state == "printing" and not paused):
                    key = "status"
                elif key == "resume" and not ((paused or state == "paused") and not swap):
                    key = "status"
                elif key == "cancel" and state not in ("printing", "paused"):
                    key = "status"
            if key != "status":
                self.panel_action(key)       # cancel and stop only ask here; Yes / No is on the panel
            # the panel always lands at the bottom, right above the keys
            self.show_panel(new=True)
            return
        if not cb:
            return
        data = cb.get("data", "")
        note = ""
        if data.startswith("w:"):
            _, seq, idx = data.split(":")
            with self.lock:
                ok = self.window is not None and int(seq) == self.win_seq and int(idx) < len(self.window.get("cmds", []))
                btn = self.window["cmds"][int(idx)] if ok else None
            if btn:
                log("button:", btn[0])
                self.gcode(btn[1])
                note = btn[0]
            else:
                note = "That window is no longer open."
                mid = cb.get("message", {}).get("message_id")
                if mid and mid != self.win_msg:
                    self.tg("editMessageReplyMarkup", chat_id=self.chat, message_id=mid, reply_markup={"inline_keyboard": []})
            self.tg("answerCallbackQuery", callback_query_id=cb["id"], text=note[:190])
        elif data.startswith("s:"):
            log("swap button:", data[2:])
            self.swap_msg = cb.get("message", {}).get("message_id") or self.swap_msg
            note = self.swap_action(data[2:])
            self.tg("answerCallbackQuery", callback_query_id=cb["id"], text=(note or "Updated")[:190])
            self.swap_card()
        elif data.startswith("p:"):
            log("start message button:", data[2:])
            self.start_msg = cb.get("message", {}).get("message_id") or self.start_msg
            note = self.panel_action(data[2:]) if data[2:] in ("mode", "settings") else ""
            self.tg("answerCallbackQuery", callback_query_id=cb["id"], text=(note or "Updated")[:190])
            self.refresh_start()
            self.show_panel()
        elif data.startswith("m:"):
            self.panel_msg = cb.get("message", {}).get("message_id") or self.panel_msg
            log("panel button:", data[2:])
            note = self.panel_action(data[2:])
            self.tg("answerCallbackQuery", callback_query_id=cb["id"], text=(note or "Updated")[:190])
            self.show_panel()

    def telegram_loop(self):
        while not self.stop.is_set():
            ups = self.get_updates()
            if ups is None:
                self.stop.wait(3)
                continue
            for u in ups:
                self.offset = u["update_id"] + 1
                try:
                    self.handle(u)
                except Exception as e:
                    log("update failed:", type(e).__name__, e)

    def get_updates(self):
        lp = int(self.cfg.get("long_poll", 25))
        url = "%s/bot%s/getUpdates" % (self.cfg["api"], self.cfg["token"])
        data = json.dumps({"offset": self.offset, "timeout": lp, "allowed_updates": ["message", "callback_query"]}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=lp + 10) as r:
                out = json.loads(r.read().decode())
                return out.get("result", []) if out.get("ok") else None
        except Exception as e:
            log("getUpdates failed:", type(e).__name__)
            return None

    def hello(self):
        """Say hello with the Panel key. Right after the printer is switched on the
        network may not be up yet, so this is tried again for a few minutes."""
        for attempt in range(int(self.cfg.get("hello_tries", 30))):
            self.tg("setMyCommands", commands=[{"command": "panel", "description": "Open the control panel"}])
            if self.panel_msg and getattr(self, "kb_ver", 0) == KEYBOARD_VER:
                # not the first start: no new message, the pinned panel is just refreshed
                st = self.status()
                text, kb = self.panel(st)
                if self.edit(self.panel_msg, text, kb):
                    self.panel_shown, self.panel_at = (text, kb), time.time()
                    log("online - pinned panel refreshed")
                    return
            r = self.say("🖨 <b>%s</b> - control panel is online ✅ (v%s)\n⌨️ The keys at the bottom of this chat stay there: "
                         "<b>📊 Status</b> brings the panel down to the bottom." % (esc(self.cfg["title"]), VERSION), KEYBOARD)
            if r is not None:
                self.kb_ver = KEYBOARD_VER
                log("online - hello message and the key bar sent")
                self.show_panel(new=True)
                return
            if attempt == 0:
                log("could not send the hello message yet (no network, or wrong token / chat id) - trying again")
            if self.stop.wait(float(self.cfg.get("hello_wait", 10))):
                return
        log("gave up on the hello message - check the token and chat id")

    def start(self):
        self.load_state()
        threading.Thread(target=self.hello, daemon=True).start()
        threading.Thread(target=self.printer_loop, daemon=True).start()
        threading.Thread(target=self.telegram_loop, daemon=True).start()


def main():
    conf = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONF
    cfg = load_config(conf)
    if not cfg["token"] or not cfg["chat_id"]:
        log("No bot token / chat id. Put them in", conf, "under [bot], or set up the Moonraker notifier first.")
        sys.exit(1)
    log("COLOR_SWAP Telegram panel", VERSION, "- moonraker", cfg["moonraker"])
    bot = Bot(cfg)
    bot.start()
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        bot.stop.set()


if __name__ == "__main__":
    main()
