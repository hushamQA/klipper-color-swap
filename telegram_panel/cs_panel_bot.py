#!/usr/bin/env python3
"""COLOR_SWAP Telegram panel - a control panel with buttons, no typing.

Runs on the printer next to Moonraker. Python 3.7+, standard library only.

  * Any message (or the "Panel" key) shows the control panel: printer status and
    buttons for Refresh, Pause / Resume / Cancel, HOME / AWAY, Settings, the waiting
    color swap, and Emergency stop.
  * Every window the printer opens (the color swap windows and the whole settings
    window) is mirrored into the chat as a message with the same buttons. A tap on a
    button does exactly what a tap on the printer screen does.
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

VERSION = "1.0"
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

    # ------------------------------------------------------------ network
    def tg(self, method, timeout=35, **params):
        url = "%s/bot%s/%s" % (self.cfg["api"], self.cfg["token"], method)
        data = json.dumps(params).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read().decode())
                return out.get("result") if out.get("ok") else None
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            if "not modified" not in body:
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

    def gcode(self, script):
        """Send one command to the printer. A long one (Load + purge) keeps running after
        the HTTP call times out, so it is sent from its own thread and never blocks."""
        def run():
            try:
                self.mr("/printer/gcode/script?script=" + urllib.parse.quote(script), post=True, timeout=600)
            except urllib.error.HTTPError as e:
                msg = e.read().decode("utf-8", "replace")
                try:
                    msg = json.loads(msg)["error"]["message"]
                except Exception:
                    pass
                self.say("<b>The printer refused that</b>\n" + esc(str(msg)[:300]))
            except Exception as e:
                log("gcode", script, "->", type(e).__name__)
        threading.Thread(target=run, daemon=True).start()

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
             "&gcode_macro%20COLOR_SWAP=state,unloaded,slot,material,runout,waited,swaps"
             "&gcode_macro%20_COLOR_SWAP_CFG=auto_continue_min,away_min")
        try:
            return self.mr(q)["status"]
        except Exception as e:
            log("status failed:", type(e).__name__)
            return None

    def panel(self, st=None):
        st = st if st is not None else self.status()
        title = "<b>%s</b>" % esc(self.cfg["title"])
        if not st:
            return title + "\n\nThe printer does not answer (Klipper or Moonraker is down).", \
                {"inline_keyboard": [[{"text": "Refresh", "callback_data": "m:refresh"}]]}
        ps = st.get("print_stats", {})
        state = ps.get("state", "?")
        paused = st.get("pause_resume", {}).get("is_paused", False)
        ex, bed = st.get("extruder", {}), st.get("heater_bed", {})
        cs = st.get("gcode_macro COLOR_SWAP") or {}
        cc = st.get("gcode_macro _COLOR_SWAP_CFG") or {}
        klippy = st.get("webhooks", {}).get("state", "ready")
        lines = [title, ""]
        if klippy != "ready":
            lines.append("Klipper: <b>%s</b>" % esc(klippy))
        lines.append("State: <b>%s</b>" % esc("paused" if paused else state))
        if state in ("printing", "paused") and ps.get("filename"):
            prog = (st.get("display_status", {}).get("progress") or st.get("virtual_sdcard", {}).get("progress") or 0) * 100
            info = ps.get("info") or {}
            layer = (" - layer %s of %s" % (info.get("current_layer"), info.get("total_layer"))
                     if info.get("total_layer") else "")
            lines.append("File: %s" % esc(ps["filename"]))
            lines.append("Done: <b>%d%%</b>%s" % (round(prog), layer))
            dur = ps.get("print_duration") or 0
            left = (" - about %s left" % hms(dur / prog * (100 - prog))) if prog >= 2 else ""
            lines.append("Printing for %s%s" % (hms(dur), left))
        lines.append("Nozzle %d / %d C   Bed %d / %d C" % (round(ex.get("temperature", 0)), round(ex.get("target", 0)),
                                                     round(bed.get("temperature", 0)), round(bed.get("target", 0))))
        swap = int(cs.get("state", 0) or 0)
        if swap:
            what = "filament runout" if cs.get("runout") else "color swap to filament %s %s" % (cs.get("slot", ""), cs.get("material", ""))
            step = ("old filament still in" if not cs.get("unloaded") else "waiting for the new filament") if swap == 1 else "loaded - check the purge"
            lines.append("")
            lines.append("<b>Waiting: %s</b> (%s, %d min)" % (esc(what.strip()), step, int(cs.get("waited", 0) or 0) // 60))
        away = float(cc.get("auto_continue_min", 0) or 0) > 0
        if cc:
            lines.append("")
            lines.append("Mode: <b>AWAY</b> - a swap waits %d min, then the print goes on with the color it has" % cc.get("auto_continue_min", 0)
                         if away else "Mode: <b>HOME</b> - every color swap waits for you")
        kb = [[{"text": "Refresh", "callback_data": "m:refresh"}]]
        if self.confirm and time.time() - self.confirm[1] < 30:
            word = "cancel the print" if self.confirm[0] == "cancel" else "EMERGENCY STOP"
            lines += ["", "<b>Really %s?</b>" % word]
            kb = [[{"text": "Yes, %s" % word, "callback_data": "m:yes_" + self.confirm[0]},
                   {"text": "No, go back", "callback_data": "m:no"}]]
            return "\n".join(lines), {"inline_keyboard": kb}
        self.confirm = None
        if state == "printing" and not paused:
            kb.append([{"text": "Pause", "callback_data": "m:pause"}, {"text": "Cancel print", "callback_data": "m:cancel"}])
        elif paused or state == "paused":
            row = [] if swap else [{"text": "Resume", "callback_data": "m:resume"}]
            kb.append(row + [{"text": "Cancel print", "callback_data": "m:cancel"}])
        if swap:
            kb.append([{"text": "Open the color swap window", "callback_data": "m:swap"}])
        if cc:
            kb.append([{"text": "I am AWAY - tap when home" if away else "I am HOME - tap when leaving", "callback_data": "m:mode"},
                       {"text": "Settings", "callback_data": "m:settings"}])
        kb.append([{"text": "Emergency stop", "callback_data": "m:estop"}])
        return "\n".join(lines), {"inline_keyboard": kb}

    def show_panel(self, new=False):
        text, kb = self.panel()
        with self.lock:
            if self.panel_msg and not new and self.edit(self.panel_msg, text, kb):
                return
            r = self.say(text, kb)
            self.panel_msg = r["message_id"] if r else None

    def panel_action(self, what):
        st = self.status() or {}
        cc = st.get("gcode_macro _COLOR_SWAP_CFG") or {}
        note = ""
        if what == "pause":
            self.gcode("PAUSE"); note = "Pausing"
        elif what == "resume":
            self.gcode("RESUME"); note = "Resuming"
        elif what in ("cancel", "estop"):
            self.confirm = (what, time.time())
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
            self.gcode("COLOR_SWAP_PROMPT"); note = "Opening the color swap window"
        elif what == "settings":
            self.gcode("COLOR_SWAP_SETTINGS"); note = "Opening the settings"
        elif what == "mode" and cc:
            away = float(cc.get("auto_continue_min", 0) or 0) > 0
            val = 0 if away else max(float(cc.get("away_min", 5) or 5), 1)
            # quiet change: nothing opens on the printer screen
            self.gcode("_CS_SET_ADJ K=auto_continue_min V=%g Q=1" % val)
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
            rows = []
            for row in b["rows"] + ([b["footer"]] if b["footer"] else []):
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
        text = "<b>%s</b>" % esc(w["title"]) + ("\n\n" + esc(w["text"]) if w["text"] else "")
        if not cmds:
            text += "\n\n<i>Working - no buttons until it is done.</i>"
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
            self.edit(self.win_msg, "<b>%s</b>\n\n<i>Closed.</i>" % esc(w["title"]))
        if w:
            log("window closed:", w["title"])
        self.win_msg = None      # the next window is a new message, so the phone rings

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
        with self.lock:
            if self.close_at and time.time() - self.close_at > 1.5:
                self.close_window()

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
        if msg:
            log("panel asked for")
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

    def start(self):
        self.tg("setMyCommands", commands=[{"command": "panel", "description": "Open the control panel"}])
        r = self.say("<b>%s</b> - control panel is online (v%s).\nTap <b>Panel</b> below at any time." % (esc(self.cfg["title"]), VERSION),
                     {"keyboard": [[{"text": "Panel"}]], "resize_keyboard": True, "is_persistent": True})
        log("could not send the hello message - check the token and chat id" if r is None else "online - hello message sent")
        self.show_panel(new=True)
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
