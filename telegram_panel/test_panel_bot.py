"""Tests for cs_panel_bot.py. Run:  python test_panel_bot.py
A fake Telegram server and a fake Moonraker run on localhost; the real bot code talks to
them. The windows fed to the bot are produced by the real macros through ../sim."""
import json, os, re, sys, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "sim"))
import cs_panel_bot as B
from sim import Sim

BASE = os.path.join(HERE, "..")
MACROS = os.path.join(BASE, "macros.cfg")
if not os.path.exists(MACROS):
    MACROS = os.path.join(BASE, "FLSUN_V400", "macros.cfg")
CS = os.path.join(BASE, "color_swap.cfg")

TG = {"calls": [], "updates": [], "next_id": 100, "uid": 1, "flood": 0}
MR = {"store": [], "scripts": [], "estop": 0, "sim": None, "t": 1000.0, "klippy": "ready", "delay": 0.0,
      "meta": {}, "restart": 0}
LOCK = threading.RLock()


def console(msg):
    with LOCK:
        MR["t"] += 0.01
        MR["store"].append({"message": msg, "time": MR["t"], "type": "response"})


def run_gcode(script):
    """Run a command on the simulated printer and put its window lines on the console."""
    s = MR["sim"]
    n = len(s.log)
    try:
        s.cmd(script)
    except Exception as e:
        return str(e)
    for l in s.log[n:]:
        if l.startswith("RESPOND TYPE=command MSG="):
            console("// " + l.split('MSG="', 1)[1].rsplit('"', 1)[0])
    return None


class TGH(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        method = self.path.rsplit("/", 1)[1]
        res = True
        if method == "getUpdates":
            end = time.time() + 0.3
            while time.time() < end:
                with LOCK:
                    ups = [u for u in TG["updates"] if u["update_id"] >= body.get("offset", 0)]
                if ups:
                    break
                time.sleep(0.02)
            res = ups
        else:
            with LOCK:
                if TG["flood"] > 0 and method != "answerCallbackQuery":
                    TG["flood"] -= 1
                    TG["calls"].append(("429:" + method, body))
                    out = json.dumps({"ok": False, "error_code": 429, "description": "Too Many Requests: retry after 1",
                                      "parameters": {"retry_after": 1}}).encode()
                    self.send_response(429); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)
                    return
                TG["calls"].append((method, body))
                if method == "sendMessage":
                    TG["next_id"] += 1
                    res = {"message_id": TG["next_id"]}
                if method == "pinChatMessage":
                    # real Telegram: a service message "... pinned a message" arrives as an update
                    TG["uid"] += 1
                    TG["updates"].append({"update_id": TG["uid"], "message": {"message_id": 90000 + TG["uid"], "chat": {"id": 777},
                                          "from": {"id": 111, "is_bot": True}, "pinned_message": {"message_id": body["message_id"]}}})
        out = json.dumps({"ok": True, "result": res}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)


class MRH(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, obj, code=200):
        out = json.dumps(obj).encode()
        self.send_response(code); self.send_header("Content-Length", str(len(out))); self.end_headers(); self.wfile.write(out)

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/server/gcode_store":
            with LOCK:
                self.reply({"result": {"gcode_store": list(MR["store"][-150:])}})
        elif u.path == "/printer/objects/query":
            s = MR["sim"]
            st = s.status()
            self.reply({"result": {"status": {
                "print_stats": dict(st["print_stats"]), "display_status": {"progress": 0.34},
                "virtual_sdcard": {"progress": 0.34}, "pause_resume": dict(st["pause_resume"]),
                "webhooks": {"state": MR["klippy"]}, "extruder": dict(st["extruder"]), "heater_bed": {"temperature": 79.6, "target": 80.0 if s.target else 0.0},
                "gcode_macro COLOR_SWAP": dict(st["gcode_macro COLOR_SWAP"]),
                "gcode_macro _COLOR_SWAP_CFG": dict(st["gcode_macro _COLOR_SWAP_CFG"])}}})
        elif u.path == "/server/files/metadata":
            fn = unquote(parse_qs(u.query)["filename"][0])
            if fn in MR["meta"]:
                self.reply({"result": MR["meta"][fn]})
            else:
                self.reply({"error": {"message": "no metadata"}}, 404)
        else:
            self.reply({"error": "?"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/printer/gcode/script":
            script = unquote(parse_qs(u.query)["script"][0])
            if MR["delay"]:
                time.sleep(MR["delay"])       # Klipper is heating: the command waits
            with LOCK:
                MR["scripts"].append(script)
            err = run_gcode(script)
            if err:
                self.reply({"error": {"code": 400, "message": err}}, 400)
            else:
                self.reply({"result": "ok"})
        elif u.path == "/printer/firmware_restart":
            MR["restart"] += 1
            self.reply({"result": "ok"})
        elif u.path == "/printer/emergency_stop":
            MR["estop"] += 1
            self.reply({"result": "ok"})
        else:
            self.reply({"error": "?"}, 404)


def serve(handler):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return "http://127.0.0.1:%d" % srv.server_address[1]


results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (("  -> " + str(extra)[:400]) if not cond else ""))


def wait(pred, sec=4.0):
    end = time.time() + sec
    while time.time() < end:
        with LOCK:
            if pred():
                return True
        time.sleep(0.03)
    return False


def last(method=None):
    with LOCK:
        for m, b in reversed(TG["calls"]):
            if method is None or m == method:
                return b
    return None


def last_window():
    """The newest message that looks like a mirrored window (has w: buttons or 'Working')."""
    with LOCK:
        for m, b in reversed(TG["calls"]):
            if m in ("sendMessage", "editMessageText"):
                kb = (b.get("reply_markup") or {}).get("inline_keyboard")
                if kb is not None and (any(x["callback_data"].startswith("w:") for r in kb for x in r) or "Working" in b["text"] or "Closed" in b["text"]):
                    return m, b
    return None, None


def last_card():
    """The newest color swap card (its buttons start with s:, or it says finished)."""
    with LOCK:
        for m, b in reversed(TG["calls"]):
            if m in ("sendMessage", "editMessageText"):
                kb = (b.get("reply_markup") or {}).get("inline_keyboard") or []
                if any(x["callback_data"].startswith("s:") for r in kb for x in r) or "Color swap finished" in b.get("text", ""):
                    return m, b
    return None, None


def plain(t):
    """A label without its leading emoji (v1.5 labels start with one)."""
    return re.sub(r"^[^\w(]+", "", t or "")


def buttons(b):
    return [x for r in (b.get("reply_markup") or {}).get("inline_keyboard", []) for x in r]


def tap(b_or_data, chat=777, msg_id=None):
    data = b_or_data if isinstance(b_or_data, str) else b_or_data["callback_data"]
    with LOCK:
        TG["uid"] += 1
        TG["updates"].append({"update_id": TG["uid"], "callback_query": {"id": str(TG["uid"]), "data": data,
                              "message": {"message_id": msg_id or TG["next_id"], "chat": {"id": chat}}}})


def text_msg(text, chat=777):
    with LOCK:
        TG["uid"] += 1
        TG["updates"].append({"update_id": TG["uid"], "message": {"message_id": 1, "text": text, "chat": {"id": chat}}})


def find(b, label):
    for x in buttons(b):
        if label in x["text"]:
            return x
    raise AssertionError("no button %r in %s" % (label, [plain(x["text"]) for x in buttons(b)]))


# ---------------------------------------------------------------- config
import tempfile
d = tempfile.mkdtemp()
open(os.path.join(d, "moonraker.conf"), "w").write("[notifier phone]\nurl: tgram://111:AAA/777\n")
c = B.load_config(os.path.join(d, "none.conf"), os.path.join(d, "moonraker.conf"))
check("config: token and chat id taken from the Moonraker notifier", c["token"] == "111:AAA" and c["chat_id"] == "777", c)
open(os.path.join(d, "cs.conf"), "w").write("[bot]\ntoken: 222:BBB\nchat_id: 888\ntitle: My V400\n")
c = B.load_config(os.path.join(d, "cs.conf"), os.path.join(d, "moonraker.conf"))
check("config: cs_telegram.conf wins", c["token"] == "222:BBB" and c["chat_id"] == "888" and c["title"] == "My V400", c)
open(os.path.join(d, "ph.conf"), "w").write("[bot]\ntoken: BOT_TOKEN\nchat_id: CHAT_ID\n")
c = B.load_config(os.path.join(d, "ph.conf"), os.path.join(d, "nothing"))
check("config: placeholders are not a token", c["token"] == "" and c["chat_id"] == "")

open(os.path.join(d, "moonraker.conf"), "w").write("[notifier phone]\nurl: tgram://bot111:AAA/777\n")
c = B.load_config(os.path.join(d, "none.conf"), os.path.join(d, "moonraker.conf"))
check("config: a token written as bot111:AAA (apprise style) loses the bot prefix", c["token"] == "111:AAA", c["token"])

# ---------------------------------------------------------------- start
sim = Sim([MACROS, CS], kin="delta")
sim.fire("_CS_BOOT")
MR["sim"] = sim
console("// old line"); console("// action:prompt_begin OLD WINDOW"); console("// action:prompt_show")
cfg = {"token": "111:AAA", "chat_id": "777", "moonraker": serve(MRH), "api": serve(TGH), "title": "FLSUN V400", "poll": 0.05, "long_poll": 1, "status_every": 0.3,
       "state": os.path.join(d, "state.json"), "panel_busy": 1000, "panel_idle": 1000, "hello_wait": 0.2}
bot = B.Bot(cfg)
bot.start()
check("start: hello with the Panel key, then the panel", wait(lambda: sum(1 for m, b in TG["calls"] if m == "sendMessage") >= 2)
      and any("keyboard" in (b.get("reply_markup") or {}) for m, b in TG["calls"] if m == "sendMessage"))
time.sleep(0.3)
first_panel = TG["next_id"]
check("start: the panel is pinned, silently", wait(lambda: any(m == "pinChatMessage" and b["message_id"] == first_panel and b.get("disable_notification") for m, b in TG["calls"])), TG["calls"][-3:])
check("start: the panel message id is remembered on disk", json.load(open(cfg["state"]))["panel_msg"] == first_panel)
n = len(TG["calls"])
text_msg("Panel")
check("Panel key: the typed message and the old panel are deleted, a new panel is sent and pinned",
      wait(lambda: {1, first_panel} <= set(b["message_id"] for m, b in TG["calls"][n:] if m == "deleteMessage")
           and any(m == "pinChatMessage" and b["message_id"] == TG["next_id"] and b["message_id"] != first_panel for m, b in TG["calls"][n:])), TG["calls"][n:])
check("start: an old window on the console is not replayed", not any("OLD WINDOW" in b.get("text", "") for m, b in TG["calls"]))
p = last("sendMessage")
check("panel idle, factory mode AWAY: status, AWAY, Settings, Emergency stop, no Pause", "State: <b>standby</b>" in p["text"] and "Mode: <b>AWAY</b>" in p["text"]
      and [plain(x["text"]) for x in buttons(p)] == ["Refresh", "I am AWAY - tap when home", "Settings", "Emergency stop"], [plain(x["text"]) for x in buttons(p)])
run_gcode("_CS_SET_ADJ K=auto_continue_min V=0 Q=1")      # the tests below start from HOME
time.sleep(0.3)
text_msg("Panel")
wait(lambda: "Mode: <b>HOME</b>" in last("sendMessage")["text"])
wait(lambda: last("pinChatMessage")["message_id"] == TG["next_id"]); time.sleep(0.4)
p = last("sendMessage")

# ---------------------------------------------------------------- v1.5: the panel sends the phone messages
check("panel claims the phone messages once (tg_panel 1) while the printer is idle",
      wait(lambda: MR["scripts"].count("_CS_SET_ADJ K=tg_panel V=1 Q=1") == 1), MR["scripts"])
MR["scripts"].clear()
n = len(TG["calls"])
with LOCK:
    MR["store"].append({"message": "// cs_alert remind|Color swap still waiting (10 min) - insert the filament", "time": MR["t"] + 1, "type": "response"})
    MR["store"].append({"message": "// cs_alert swap|Color swap to filament 2 PLA is waiting", "time": MR["t"] + 1, "type": "response"})
    MR["t"] += 1
check("alert: a reminder becomes a formatted message", wait(lambda: any(m == "sendMessage" and "⏰ <b>Color swap still waiting</b>" in b["text"]
      and "insert the filament" in b["text"] for m, b in TG["calls"][n:])), TG["calls"][n:])
time.sleep(0.5)
check("alert: a swap stage is left to the swap card (no second message)",
      not any(m == "sendMessage" and "is waiting" in b["text"] for m, b in TG["calls"][n:]), TG["calls"][n:])

# ---------------------------------------------------------------- security
n = len(TG["calls"])
text_msg("hello", chat=999); tap("m:estop", chat=999); tap("w:1:0", chat=999)
time.sleep(0.6)
check("another chat: ignored, nothing sent to the printer", MR["estop"] == 0 and not MR["scripts"]
      and all(m == "answerCallbackQuery" for m, b in TG["calls"][n:]), TG["calls"][n:])

# ---------------------------------------------------------------- windows opened at the printer stay there
n = len(TG["calls"])
run_gcode("COLOR_SWAP_SETTINGS"); run_gcode("COLOR_SWAP_SETTINGS V=adv"); run_gcode("_CS_SET_CLOSE"); run_gcode("RESUME_SAVED_PRINT"); run_gcode("_CS_PROMPT_CLOSE")
time.sleep(0.8)
check("settings / resume windows opened at the printer are NOT sent to the chat", not [b for m, b in TG["calls"][n:] if m in ("sendMessage", "editMessageText")], TG["calls"][n:])

# ---------------------------------------------------------------- settings window mirrored
tap(find(p, "Settings"))
check("Settings: the printer gets COLOR_SWAP_SETTINGS", wait(lambda: "COLOR_SWAP_SETTINGS" in MR["scripts"]))
check("Settings: the window arrives as a message with buttons", wait(lambda: last_window()[1] is not None and "Color swap settings" in last_window()[1]["text"]))
m, w = last_window()
labels = [plain(x["text"]) for x in buttons(w)]
check("Settings window: the everyday buttons, without Printer setup", "I am HOME - tap when you leave" in labels and "Purge amount: NORMAL" in labels
      and "Factory reset..." in labels and "Close" in labels and "Advanced..." in labels and "Printer setup..." not in labels and m == "sendMessage", labels)
win_id = TG["next_id"]
tap(find(w, "Purge amount"), msg_id=win_id)
check("tap Purge amount: printer runs it, the SAME message is edited to HIGH",
      wait(lambda: "_CS_PURGE_LEVEL" in MR["scripts"] and last_window()[0] == "editMessageText"
           and "Purge amount: HIGH" in [plain(x["text"]) for x in buttons(last_window()[1])] and last_window()[1]["message_id"] == win_id), last_window())
check("the simulated printer really changed", sim.vars["_COLOR_SWAP_CFG"]["purge_to_main_extra"] == 110)
old_btn = find(w, "Advanced")          # a button of the PREVIOUS render
n = len(MR["scripts"])
tap(old_btn, msg_id=win_id)
time.sleep(0.5)
check("a button from an older render is refused", len(MR["scripts"]) == n and "no longer open" in (last("answerCallbackQuery") or {}).get("text", ""))
m, w = last_window()
tap(find(w, "Advanced"), msg_id=win_id)
wait(lambda: "Fine tuning" in last_window()[1]["text"])
m, w = last_window()
tap(find(w, "Purge details"), msg_id=win_id)
wait(lambda: "Purge details" in last_window()[1]["text"])
m, w = last_window()
tap(find(w, "Extra purge back to main"), msg_id=win_id)
check("number window: explains itself, has + and - buttons", wait(lambda: "Raise it if that layer is brittle" in last_window()[1]["text"]
      and any(x["text"] == "+ 5" for x in buttons(last_window()[1]))), last_window())
m, w = last_window()
check("rows are at most 3 wide and labels are intact", all(len(r) <= 3 for r in w["reply_markup"]["inline_keyboard"]))
tap(find(w, "+ 5"), msg_id=win_id)
check("+ 5 applied on the printer", wait(lambda: sim.vars["_COLOR_SWAP_CFG"]["purge_to_main_extra"] == 115))
run_gcode("_CS_SET_RESET GO=1"); run_gcode("_CS_SET_CLOSE")
check("Close on the printer: the message loses its buttons", wait(lambda: "Closed" in last_window()[1]["text"] and not buttons(last_window()[1]), 5))

# ---------------------------------------------------------------- mode from the panel
text_msg("Panel")
wait(lambda: "Mode: <b>HOME</b>" in last("sendMessage")["text"])
p = last("sendMessage"); pid = TG["next_id"]
n = len(TG["calls"])
tap(find(p, "I am HOME"), msg_id=pid)
check("panel HOME -> AWAY: quiet setting change, panel edited", wait(lambda: sim.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 5
      and any(m == "editMessageText" and "Mode: <b>AWAY</b>" in b["text"] for m, b in TG["calls"][n:])), TG["calls"][n:])
check("mode change opened no window", not any("Color swap settings" in b.get("text", "") for m, b in TG["calls"][n:]))

# ---------------------------------------------------------------- a swap while AWAY: the remote card
sim.pstate, sim.target, sim.pos, sim.e = "printing", 240.0, [30.0, 20.0, 3.2], -2.0
text_msg("Panel")
wait(lambda: "State: <b>printing</b>" in last("sendMessage")["text"])
p = last("sendMessage")
check("panel printing: file, progress, Pause and Cancel", "Done: <b>34%</b>" in p["text"] and "test.gcode" in p["text"]
      and {"Pause", "Cancel print"} <= set(plain(x["text"]) for x in buttons(p)), p["text"])
before = TG["next_id"]
err = run_gcode("COLOR_SWAP SLOT=2 MATERIAL=PLA OLD_MATERIAL=PETG TEMP=215 OLD_TEMP=240 RETRACT=2 PURGE=43")
check("swap starts (AWAY: filament stays in)", err is None and sim.vars["COLOR_SWAP"]["state"] == 1 and sim.vars["COLOR_SWAP"]["unloaded"] == 0, err)
check("swap card arrives as a NEW message (the phone rings)", wait(lambda: last_card()[0] == "sendMessage" and "Color swap to filament 2 PLA" in last_card()[1]["text"]
      and TG["next_id"] > before), last_card())
m, c = last_card(); card_id = TG["next_id"]
labels = [plain(x["text"]) for x in buttons(c)]
check("card AWAY: Keep, Wait for me, Cancel, Refresh - and says it continues by itself",
      labels == ["Keep the current color and continue", "Wait for me - do not continue", "Cancel print", "Refresh"]
      and "continues by itself" in c["text"] and "still in the nozzle" in c["text"], (labels, c["text"]))
allsent = [x["text"] for mm, bb in TG["calls"] for x in buttons(bb) if mm in ("sendMessage", "editMessageText")]
banned = {"Unload", "Unload again", "Load + purge", "Load anyway", "Head moved? Re-home", "PLA 215C", "PETG 240C", "Continue...",
          "Keep current color", "Printer setup...", "Check install"}
check("no at-the-printer button ever reached the chat (Unload, Load + purge, Purge +, Re-home, material, Printer setup)",
      not (banned & set(allsent)) and not any(t.startswith("Purge +") for t in allsent), sorted(banned & set(allsent)))
check("the printer's own swap window was not mirrored", last_window()[1] is None or "Color swap 1" not in last_window()[1]["text"])
text_msg("Panel")
wait(lambda: "Waiting: color swap to filament 2 PLA" in last("sendMessage")["text"])
p = last("sendMessage")
check("panel during a swap: says what waits, no Resume, a button to the card", "old filament still in" in p["text"]
      and "Color swap - what can I do?" in [plain(x["text"]) for x in buttons(p)] and "Resume" not in [plain(x["text"]) for x in buttons(p)], p["text"])
# Wait for me
tap(find(c, "Wait for me"), msg_id=card_id)
check("Wait for me: auto continue is off, the card says it waits", wait(lambda: sim.vars["COLOR_SWAP"]["touched"] == 1
      and "will not continue by itself" in last_card()[1]["text"] and "Wait for me" not in [plain(x["text"]) for x in buttons(last_card()[1])]), last_card())
n = len(MR["scripts"])
check("Wait for me did not open or change anything else", MR["scripts"][n - 1] == "_CS_TOUCH")
# Keep: asks first
m, c = last_card()
tap(find(c, "Keep the current color"), msg_id=card_id)
check("Keep: asks first", wait(lambda: "Continue the print now with the current color?" in last_card()[1]["text"]) and sim.pstate != "printing")
m, c = last_card()
tap(find(c, "No, go back"), msg_id=card_id)
wait(lambda: "Keep the current color and continue" in [plain(x["text"]) for x in buttons(last_card()[1])])
m, c = last_card()
tap(find(c, "Keep the current color"), msg_id=card_id)
wait(lambda: "Yes, continue" in [plain(x["text"]) for x in buttons(last_card()[1])])
m, c = last_card()
tap(find(c, "Yes, continue"), msg_id=card_id)
check("Keep confirmed: the print goes on with the old color", wait(lambda: sim.pstate == "printing" and sim.vars["COLOR_SWAP"]["state"] == 0
      and sim.vars["COLOR_SWAP"]["cur_material"] == "PETG"))
check("the card closes itself: finished, no buttons", wait(lambda: last_card()[0] == "editMessageText" and "Color swap finished" in last_card()[1]["text"]
      and "continues with PETG" in last_card()[1]["text"] and not buttons(last_card()[1]), 6), last_card())

# ---------------------------------------------------------------- a swap while HOME: nothing to do from far away but cancel
run_gcode("_CS_SET_ADJ K=auto_continue_min V=0 Q=1")
sim.e = -2.0
run_gcode("COLOR_SWAP SLOT=2 MATERIAL=PLA OLD_MATERIAL=PETG TEMP=215 OLD_TEMP=240 RETRACT=2 PURGE=43")
check("HOME swap (filament already out): card says somebody must be there", wait(lambda: last_card()[0] == "sendMessage" and "already out" in last_card()[1]["text"]), last_card())
m, c = last_card(); card_id = TG["next_id"]
check("HOME swap card: only Cancel print and Refresh", [plain(x["text"]) for x in buttons(c)] == ["Cancel print", "Refresh"], [plain(x["text"]) for x in buttons(c)])
run_gcode("_CS_LOAD")          # somebody at the printer loads the filament
check("after loading at the printer the card follows: check the color there", wait(lambda: "loaded" in last_card()[1]["text"] and "press Continue" in last_card()[1]["text"]
      and [plain(x["text"]) for x in buttons(last_card()[1])] == ["Cancel print", "Refresh"], 6), last_card())
run_gcode("_CS_CONFIRM"); run_gcode("_CS_CONTINUE")
check("after Continue at the printer the card closes", wait(lambda: "Color swap finished" in last_card()[1]["text"] and "continues with PLA" in last_card()[1]["text"], 6), last_card())

# ---------------------------------------------------------------- runout
sim.e = 0.0
run_gcode("PAUSE"); run_gcode("M600")
check("runout card: only cancel is possible", wait(lambda: last_card()[0] == "sendMessage" and "Filament ran out" in last_card()[1]["text"]
      and [plain(x["text"]) for x in buttons(last_card()[1])] == ["Cancel print", "Refresh"], 6), last_card())
m, c = last_card(); card_id = TG["next_id"]

# ---------------------------------------------------------------- refused command is reported
n = len(TG["calls"])
bot.gcode("RESUME")
check("RESUME with no filament loaded: the refusal reaches the chat", wait(lambda: any(m == "sendMessage" and "refused" in b["text"] and "not loaded" in b["text"] for m, b in TG["calls"][n:])), TG["calls"][n:])

# ---------------------------------------------------------------- cancel from the card needs a second tap
tap(find(c, "Cancel print"), msg_id=card_id)
check("card Cancel print: asks first", wait(lambda: "Really cancel the print?" in last_card()[1]["text"]) and sim.pstate != "cancelled")
m, c = last_card()
tap(find(c, "Yes, cancel the print"), msg_id=card_id)
check("card Cancel confirmed: cancelled, swap cleared, card closed", wait(lambda: sim.pstate == "cancelled" and sim.vars["COLOR_SWAP"]["state"] == 0
      and "Color swap finished" in last_card()[1]["text"] and "cancelled" in last_card()[1]["text"], 6), last_card())

# ---------------------------------------------------------------- panel: heaters off, cancel and emergency stop
sim.target = 215.0
text_msg("Panel"); wait(lambda: "State: <b>cancelled</b>" in last("sendMessage")["text"])
p = last("sendMessage"); pid = TG["next_id"]
check("idle with a hot nozzle: Heaters off is offered", "Heaters off" in [plain(x["text"]) for x in buttons(p)], [plain(x["text"]) for x in buttons(p)])
sim.macros["TURN_OFF_HEATERS"] = sim.env.from_string("M104 S0"); sim.vars["TURN_OFF_HEATERS"] = {}
tap(find(p, "Heaters off"), msg_id=pid)
check("Heaters off: sent, and the button goes away", wait(lambda: sim.target == 0.0 and any(m == "editMessageText" and b.get("message_id") == pid
      and "Heaters off" not in [plain(x["text"]) for x in buttons(b)] for m, b in TG["calls"][-4:])), TG["calls"][-3:])
sim.pstate, sim.target = "printing", 240.0
text_msg("Panel"); wait(lambda: "State: <b>printing</b>" in last("sendMessage")["text"])
p = last("sendMessage"); pid = TG["next_id"]
n = len(MR["scripts"])
tap(find(p, "Cancel print"), msg_id=pid)
check("panel Cancel print: asks first, nothing sent yet", wait(lambda: any(m == "editMessageText" and "Really cancel the print?" in b["text"] and b.get("message_id") == pid for m, b in TG["calls"]))
      and "CANCEL_PRINT" not in MR["scripts"][n:])
q = [b for m, b in TG["calls"] if m == "editMessageText" and "Really cancel" in b["text"] and b.get("message_id") == pid][-1]
tap(find(q, "No, go back"), msg_id=pid); time.sleep(0.5)
check("No: still printing", sim.pstate == "printing")
tap("m:estop", msg_id=pid)
wait(lambda: any(m == "editMessageText" and "Really EMERGENCY STOP?" in b["text"] for m, b in TG["calls"]))
check("Emergency stop: asks first", MR["estop"] == 0)
tap("m:yes_estop", msg_id=pid)
check("Emergency stop: sent after the second tap", wait(lambda: MR["estop"] == 1))
tap("m:cancel", msg_id=pid); time.sleep(0.4); tap("m:yes_cancel", msg_id=pid)
check("panel Cancel print: done after the second tap", wait(lambda: sim.pstate == "cancelled"))

# ---------------------------------------------------------------- the fixed bar of keys at the bottom of the chat
hello = [b for m, b in TG["calls"] if m == "sendMessage" and "keyboard" in (b.get("reply_markup") or {})][0]
keys = [k["text"] for row in hello["reply_markup"]["keyboard"] for k in row]
raw_keys = keys
keys = [plain(k) for k in raw_keys]
check("key bar: Status, Pause, Resume, Home / Away, Settings, Cancel print, STOP - persistent",
      keys == ["Status", "Pause", "Resume", "Home / Away", "Settings", "Cancel print", "STOP"] and hello["reply_markup"].get("is_persistent"), keys)
check("every key is understood by the bot (with its emoji, and typed without)", all(B.key_of(k) in B.KEYS for k in raw_keys) and all(B.key_of(k) in B.KEYS for k in keys))
sim.pstate, sim.target, sim.paused = "cancelled", 0.0, False
n, ns = len(TG["calls"]), len(MR["scripts"])
text_msg("Pause"); text_msg("Resume"); text_msg("Cancel print")
check("idle: Pause, Resume and Cancel print keys do nothing but show the panel",
      wait(lambda: sum(1 for m, b in TG["calls"][n:] if m == "sendMessage") >= 3) and MR["scripts"][ns:] == []
      and not any("Really" in b.get("text", "") for m, b in TG["calls"][n:]), (MR["scripts"][ns:], TG["calls"][n:]))
check("each key press is deleted from the chat", sum(1 for m, b in TG["calls"][n:] if m == "deleteMessage") >= 3)
sim.pstate, sim.target = "printing", 240.0
ns = len(MR["scripts"])
text_msg("Pause")
check("printing: the Pause key pauses, and the panel comes to the bottom", wait(lambda: MR["scripts"][ns:] == ["PAUSE"] and sim.paused
      and "State: <b>paused</b>" in last("sendMessage")["text"]), (MR["scripts"][ns:], last("sendMessage")["text"]))
text_msg("Resume")
check("paused: the Resume key resumes", wait(lambda: "RESUME" in MR["scripts"][ns:] and not sim.paused and sim.pstate == "printing"), MR["scripts"][ns:])
n = len(TG["calls"])
text_msg("Home / Away")
check("Home / Away key switches the mode", wait(lambda: sim.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 5 and "Mode: <b>AWAY</b>" in last("sendMessage")["text"]), last("sendMessage")["text"])
text_msg("Home / Away")
wait(lambda: sim.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 0)
e0 = MR["estop"]
text_msg("STOP")
check("STOP key: only asks - Yes / No on the panel, nothing sent", wait(lambda: "Really EMERGENCY STOP?" in last("sendMessage")["text"]
      and [plain(x["text"]) for x in buttons(last("sendMessage"))] == ["Yes, EMERGENCY STOP", "No, go back"]) and MR["estop"] == e0, last("sendMessage"))
tap(find(last("sendMessage"), "No, go back"), msg_id=TG["next_id"]); time.sleep(0.5)
ns = len(MR["scripts"])
text_msg("Cancel print")
check("Cancel print key while printing: only asks", wait(lambda: "Really cancel the print?" in last("sendMessage")["text"]) and "CANCEL_PRINT" not in MR["scripts"][ns:])
tap(find(last("sendMessage"), "No, go back"), msg_id=TG["next_id"]); time.sleep(0.5)
text_msg("Settings")
check("Settings key opens the settings window in the chat", wait(lambda: last_window()[1] is not None and "Color swap settings" in last_window()[1]["text"]
      and buttons(last_window()[1])), last_window())
run_gcode("_CS_SET_CLOSE"); time.sleep(2.2)
text_msg("whatever I type")
check("any other text just shows the panel", wait(lambda: "State: <b>printing</b>" in last("sendMessage")["text"]))

# ---------------------------------------------------------------- v1.4: the pin notice is not a key press
n = len(TG["calls"])
text_msg("Status")
time.sleep(2.0)
sent = [m for m, b in TG["calls"][n:] if m == "sendMessage"]
check("the 'pinned a message' notice does not start a loop (v1.3 sent a new panel every 2 s)", len(sent) == 1, len(sent))

# ---------------------------------------------------------------- v1.4: Telegram says too many requests
with LOCK:
    TG["flood"] = 1
n = len(TG["calls"])
text_msg("Status")
time.sleep(0.6)
quiet = [m for m, b in TG["calls"][n:] if not m.startswith("429") and m != "answerCallbackQuery"]
check("429: the bot stays quiet until retry_after has passed", any(m.startswith("429") for m, b in TG["calls"][n:]) and not quiet, TG["calls"][n:])
time.sleep(0.8)
text_msg("Status")
check("429: after the wait it works again", wait(lambda: any(m == "sendMessage" for m, b in TG["calls"][n:])))

# ---------------------------------------------------------------- v1.4: HOME / AWAY only while it can help
run_gcode("_CS_SET_ADJ K=auto_continue_min V=0 Q=1")
sim.pstate, sim.target, sim.paused, sim.e = "printing", 240.0, False, -2.0
run_gcode("COLOR_SWAP SLOT=2 MATERIAL=PLA OLD_MATERIAL=PETG TEMP=215 OLD_TEMP=240 RETRACT=2 PURGE=43")
text_msg("Status")
wait(lambda: "Waiting: color swap" in last("sendMessage")["text"])
p = last("sendMessage")
labels = [plain(x["text"]) for x in buttons(p)]
check("panel, HOME swap with the filament out: no HOME / AWAY button, says it cannot help this swap",
      not any("I am" in l for l in labels) and "Settings" in labels and "cannot help this swap" in p["text"], (labels, p["text"]))
ns = len(MR["scripts"])
text_msg("Home / Away"); time.sleep(0.8)
check("Home / Away key during that swap changes nothing", sim.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 0 and not MR["scripts"][ns:], MR["scripts"][ns:])
fake = {"gcode_macro COLOR_SWAP": {"state": 1, "unloaded": 0, "runout": 0, "slot": 2, "material": "PLA", "old_material": "PETG", "waited": 3},
        "gcode_macro _COLOR_SWAP_CFG": {"auto_continue_min": 0, "away_min": 5, "auto_unload": 1}, "extruder": {"temperature": 240}}
text, kb = bot.swap_view(fake)
check("card while the printer is still pulling the filament out (HOME): no Keep button", "pulling the old filament out" in text
      and [plain(x["text"]) for r in kb["inline_keyboard"] for x in r] == ["Cancel print", "Refresh"], (text, kb))
fake["gcode_macro _COLOR_SWAP_CFG"]["auto_unload"] = 0
text, kb = bot.swap_view(fake)
check("HOME with auto unload OFF: the filament stays in, Keep is offered", "Keep the current color and continue" in [plain(x["text"]) for r in kb["inline_keyboard"] for x in r])
check("needs_hands: unloaded / loading / runout yes, filament still in (auto unload off) no",
      bot.needs_hands({"gcode_macro COLOR_SWAP": {"state": 1, "unloaded": 1}}) and bot.needs_hands({"gcode_macro COLOR_SWAP": {"state": 2}})
      and not bot.needs_hands(fake) and not bot.needs_hands({"gcode_macro COLOR_SWAP": {"state": 0}}))
run_gcode("CANCEL_PRINT")
wait(lambda: sim.vars["COLOR_SWAP"]["state"] == 0)

# ---------------------------------------------------------------- v1.4: a tap while the printer heats
sim.pstate, sim.target, sim.paused = "standby", 0.0, False
text_msg("Status"); wait(lambda: "State: <b>standby</b>" in last("sendMessage")["text"])
p = last("sendMessage"); pid = TG["next_id"]
MR["delay"] = 5.0
n = len(TG["calls"])
tap(find(p, "I am HOME"), msg_id=pid)
check("busy printer: the panel says the switch to AWAY waits for the heating, button already shows AWAY",
      wait(lambda: any(m == "editMessageText" and "switching to <b>AWAY</b>" in b["text"] and "heating" in b["text"]
                       and "I am AWAY - tap when home" in [plain(x["text"]) for x in buttons(b)] for m, b in TG["calls"][n:]), 6), TG["calls"][n:])
check("busy printer: once the heating ends the mode is applied and the note goes", wait(lambda: sim.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 5
      and any(m == "editMessageText" and "Mode: <b>AWAY</b>" in b["text"] and "heating" not in b["text"] for m, b in TG["calls"][n:]), 8))
MR["delay"] = 0.0
run_gcode("_CS_SET_ADJ K=auto_continue_min V=0 Q=1")

# ---------------------------------------------------------------- v1.4: the print start message
MR["meta"]["multi.gcode"] = {"filament_change_count": 3, "filament_colors": ["#111111", "#222222"]}
MR["meta"]["single.gcode"] = {"filament_change_count": 0, "filament_colors": ["#111111"]}
sim.filename, sim.pstate, sim.target = "single.gcode", "printing", 240.0
time.sleep(1.0)
check("one-color print: no start message", not any(m == "sendMessage" and "single.gcode" in b["text"] for m, b in TG["calls"]))
sim.pstate = "complete"; time.sleep(0.6)
n = len(TG["calls"])
sim.filename, sim.pstate = "multi.gcode", "printing"
check("print with color swaps: a start message with the mode and the AWAY button",
      wait(lambda: any(m == "sendMessage" and "Print started" in b["text"] and "Color swaps in this file: 3" in b["text"]
                       and "Mode: <b>HOME</b>" in b["text"] and "before the first swap" in b["text"] for m, b in TG["calls"][n:])), TG["calls"][n:])
sm = [b for m, b in TG["calls"][n:] if m == "sendMessage" and "Print started" in b["text"]][0]
tap(find(sm, "I am HOME"), msg_id=bot.start_msg)
check("start message: AWAY tapped before the swap - applied, the message shows AWAY", wait(lambda: sim.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 5
      and any(m == "editMessageText" and "Print started" in b["text"] and "Mode: <b>AWAY</b>" in b["text"] for m, b in TG["calls"][n:])))
sim.e = -2.0
run_gcode("COLOR_SWAP SLOT=2 MATERIAL=PLA OLD_MATERIAL=PETG TEMP=215 OLD_TEMP=240 RETRACT=2 PURGE=43")
check("AWAY set from the start message: the swap keeps the filament in", sim.vars["COLOR_SWAP"]["unloaded"] == 0)
check("once a swap starts the start message loses its buttons", wait(lambda: any(m == "editMessageText" and "Print started" in b["text"]
      and "A color swap has started" in b["text"] and not buttons(b) for m, b in TG["calls"][n:]), 6))
run_gcode("CANCEL_PRINT"); run_gcode("_CS_SET_ADJ K=auto_continue_min V=0 Q=1")
wait(lambda: sim.vars["COLOR_SWAP"]["state"] == 0)

# ---------------------------------------------------------------- v1.4: Klipper shut down (after an emergency stop)
sim.pstate, sim.target = "standby", 0.0
MR["klippy"] = "shutdown"
text_msg("Status")
wait(lambda: "Klipper: <b>shutdown</b>" in last("sendMessage")["text"])
p = last("sendMessage"); pid = TG["next_id"]
check("Klipper shut down: only Refresh and Restart Klipper (nothing else can work)", [plain(x["text"]) for x in buttons(p)] == ["Refresh", "Restart Klipper"], [plain(x["text"]) for x in buttons(p)])
ns = len(MR["scripts"])
text_msg("Settings"); time.sleep(0.6)
check("Klipper shut down: keys send nothing", not MR["scripts"][ns:])
tap(find(p, "Restart Klipper"), msg_id=pid)
wait(lambda: any(m == "editMessageText" and "Really restart Klipper?" in b["text"] for m, b in TG["calls"]))
check("Restart Klipper: asks first", MR["restart"] == 0)
tap("m:yes_restart", msg_id=pid)
check("Restart Klipper: sent after the second tap", wait(lambda: MR["restart"] == 1, 5))
MR["klippy"] = "ready"

# ---------------------------------------------------------------- one pinned panel that survives a restart and updates itself
bot.stop.set()
time.sleep(1.5)
pinned = json.load(open(cfg["state"]))["panel_msg"]
sim.pstate, sim.target = "standby", 0.0
with LOCK:
    TG["updates"].clear()      # real Telegram does not replay updates that were already taken
n = len(TG["calls"])
cfg2 = dict(cfg, panel_idle=0.4, panel_busy=0.4)
bot2 = B.Bot(cfg2)
bot2.start()
check("restart: the pinned panel is edited in place - no hello, no new message, no new pin",
      wait(lambda: any(m == "editMessageText" and b["message_id"] == pinned and "State: <b>standby</b>" in b["text"] for m, b in TG["calls"][n:]))
      and not any(m in ("sendMessage", "pinChatMessage") for m, b in TG["calls"][n:]), TG["calls"][n:])
n = len(TG["calls"])
sim.pstate, sim.target = "printing", 240.0
check("the pinned panel updates by itself when the printer changes",
      wait(lambda: any(m == "editMessageText" and b["message_id"] == pinned and "State: <b>printing</b>" in b["text"] for m, b in TG["calls"][n:]), 5)
      and not any(m == "sendMessage" for m, b in TG["calls"][n:]), TG["calls"][n:])
time.sleep(1.2)
n = len(TG["calls"])
time.sleep(1.2)
check("nothing is sent while nothing changes", not [m for m, b in TG["calls"][n:] if m in ("editMessageText", "sendMessage")], TG["calls"][n:])
bot2.stop.set()

bad = [r for r in results if not r[1]]
print("\n%d checks, %d failed" % (len(results), len(bad)))
sys.exit(1 if bad else 0)
