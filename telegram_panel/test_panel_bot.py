"""Tests for cs_panel_bot.py. Run:  python test_panel_bot.py
A fake Telegram server and a fake Moonraker run on localhost; the real bot code talks to
them. The windows fed to the bot are produced by the real macros through ../sim."""
import json, os, sys, threading, time
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

TG = {"calls": [], "updates": [], "next_id": 100, "uid": 1}
MR = {"store": [], "scripts": [], "estop": 0, "sim": None, "t": 1000.0}
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
                TG["calls"].append((method, body))
                if method == "sendMessage":
                    TG["next_id"] += 1
                    res = {"message_id": TG["next_id"]}
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
                "webhooks": {"state": "ready"}, "extruder": dict(st["extruder"]), "heater_bed": {"temperature": 79.6, "target": 80.0},
                "gcode_macro COLOR_SWAP": dict(st["gcode_macro COLOR_SWAP"]),
                "gcode_macro _COLOR_SWAP_CFG": dict(st["gcode_macro _COLOR_SWAP_CFG"])}}})
        else:
            self.reply({"error": "?"}, 404)

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/printer/gcode/script":
            script = unquote(parse_qs(u.query)["script"][0])
            with LOCK:
                MR["scripts"].append(script)
            err = run_gcode(script)
            if err:
                self.reply({"error": {"code": 400, "message": err}}, 400)
            else:
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
    raise AssertionError("no button %r in %s" % (label, [x["text"] for x in buttons(b)]))


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
cfg = {"token": "111:AAA", "chat_id": "777", "moonraker": serve(MRH), "api": serve(TGH), "title": "FLSUN V400", "poll": 0.05, "long_poll": 1}
bot = B.Bot(cfg)
bot.start()
check("start: hello with the Panel key, then the panel", wait(lambda: sum(1 for m, b in TG["calls"] if m == "sendMessage") >= 2)
      and any("keyboard" in (b.get("reply_markup") or {}) for m, b in TG["calls"] if m == "sendMessage"))
time.sleep(0.3)
check("start: an old window on the console is not replayed", not any("OLD WINDOW" in b.get("text", "") for m, b in TG["calls"]))
p = last("sendMessage")
check("panel idle: status, HOME, Settings, Emergency stop, no Pause", "State: <b>standby</b>" in p["text"] and "Mode: <b>HOME</b>" in p["text"]
      and [x["text"] for x in buttons(p)] == ["Refresh", "I am HOME - tap when leaving", "Settings", "Emergency stop"], [x["text"] for x in buttons(p)])

# ---------------------------------------------------------------- security
n = len(TG["calls"])
text_msg("hello", chat=999); tap("m:estop", chat=999); tap("w:1:0", chat=999)
time.sleep(0.6)
check("another chat: ignored, nothing sent to the printer", MR["estop"] == 0 and not MR["scripts"]
      and all(m == "answerCallbackQuery" for m, b in TG["calls"][n:]), TG["calls"][n:])

# ---------------------------------------------------------------- settings window mirrored
tap(find(p, "Settings"))
check("Settings: the printer gets COLOR_SWAP_SETTINGS", wait(lambda: "COLOR_SWAP_SETTINGS" in MR["scripts"]))
check("Settings: the window arrives as a message with buttons", wait(lambda: last_window()[1] is not None and "Color swap settings" in last_window()[1]["text"]))
m, w = last_window()
labels = [x["text"] for x in buttons(w)]
check("Settings window: same buttons as on the printer", "I am HOME - tap when you leave" in labels and "Purge amount: NORMAL" in labels
      and "Factory reset..." in labels and "Close" in labels and m == "sendMessage", labels)
win_id = TG["next_id"]
tap(find(w, "Purge amount"), msg_id=win_id)
check("tap Purge amount: printer runs it, the SAME message is edited to HIGH",
      wait(lambda: "_CS_PURGE_LEVEL" in MR["scripts"] and last_window()[0] == "editMessageText"
           and "Purge amount: HIGH" in [x["text"] for x in buttons(last_window()[1])] and last_window()[1]["message_id"] == win_id), last_window())
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

# ---------------------------------------------------------------- a real swap, answered from the phone
sim.pstate, sim.target, sim.pos, sim.e = "printing", 240.0, [30.0, 20.0, 3.2], -2.0
text_msg("Panel")
wait(lambda: "State: <b>printing</b>" in last("sendMessage")["text"])
p = last("sendMessage")
check("panel printing: file, progress, Pause and Cancel", "Done: <b>34%</b>" in p["text"] and "test.gcode" in p["text"]
      and {"Pause", "Cancel print"} <= set(x["text"] for x in buttons(p)), p["text"])
before = TG["next_id"]
err = run_gcode("COLOR_SWAP SLOT=2 MATERIAL=PLA OLD_MATERIAL=PETG TEMP=215 OLD_TEMP=240 RETRACT=2 PURGE=43")
check("swap starts (AWAY: filament stays in)", err is None and sim.vars["COLOR_SWAP"]["state"] == 1 and sim.vars["COLOR_SWAP"]["unloaded"] == 0, err)
check("swap window arrives as a NEW message (the phone rings)", wait(lambda: last_window()[0] == "sendMessage" and "Color swap 1" in last_window()[1]["text"]
      and TG["next_id"] > before), last_window())
m, w = last_window(); sw_id = TG["next_id"]
check("swap window: Keep current color, Unload, Cancel", {"Keep current color", "Unload", "Cancel..."} <= set(x["text"] for x in buttons(w)), [x["text"] for x in buttons(w)])
text_msg("Panel")
wait(lambda: "Waiting: color swap to filament 2 PLA" in last("sendMessage")["text"])
p = last("sendMessage")
check("panel during a swap: says what waits, offers the window, no Resume", "old filament still in" in p["text"]
      and "Open the color swap window" in [x["text"] for x in buttons(p)] and "Resume" not in [x["text"] for x in buttons(p)], p["text"])
tap(find(w, "Keep current color"), msg_id=sw_id)
wait(lambda: "keep the color?" in last_window()[1]["text"])
m, w = last_window()
tap(find(w, "Yes, keep and continue"), msg_id=sw_id)
check("Keep current color from the phone: the print goes on", wait(lambda: sim.pstate == "printing" and sim.vars["COLOR_SWAP"]["state"] == 0))
check("after the swap the window message is closed", wait(lambda: "Closed" in last_window()[1]["text"], 5))

# ---------------------------------------------------------------- full swap with a busy window
run_gcode("_CS_SET_ADJ K=auto_continue_min V=0 Q=1")
sim.e = -2.0
run_gcode("COLOR_SWAP SLOT=2 MATERIAL=PLA OLD_MATERIAL=PETG TEMP=215 OLD_TEMP=240 RETRACT=2 PURGE=43")
wait(lambda: "Load + purge" in [x["text"] for x in buttons(last_window()[1])])
m, w = last_window(); sw_id = TG["next_id"]
tap(find(w, "Load + purge"), msg_id=sw_id)
check("Load + purge from the phone: check-the-purge window follows", wait(lambda: "check the purge" in last_window()[1]["text"]))
check("a busy window (no buttons) was shown in between", any("Working - no buttons" in b.get("text", "") for m, b in TG["calls"]))
m, w = last_window()
tap(find(w, "Continue..."), msg_id=sw_id)
wait(lambda: "continue?" in last_window()[1]["text"])
m, w = last_window()
tap(find(w, "Yes, continue print"), msg_id=sw_id)
check("Continue from the phone: printing with the new color", wait(lambda: sim.pstate == "printing" and sim.vars["COLOR_SWAP"]["cur_material"] == "PLA"))

# ---------------------------------------------------------------- refused command is reported
sim.e = -2.0
run_gcode("COLOR_SWAP SLOT=1 MATERIAL=PETG OLD_MATERIAL=PLA TEMP=240 OLD_TEMP=215 RETRACT=2 PURGE=30")
text_msg("Panel"); wait(lambda: "Waiting:" in last("sendMessage")["text"])
n = len(TG["calls"])
bot.gcode("RESUME")
check("RESUME with no filament loaded: the refusal reaches the chat", wait(lambda: any(m == "sendMessage" and "refused" in b["text"] and "not loaded" in b["text"] for m, b in TG["calls"][n:])), TG["calls"][n:])

# ---------------------------------------------------------------- cancel and emergency stop need a second tap
p = last("sendMessage") if "Waiting:" in last("sendMessage")["text"] else None
text_msg("Panel"); time.sleep(0.5)
p = [b for m, b in TG["calls"] if m == "sendMessage" and "Emergency stop" in str(b.get("reply_markup"))][-1]; pid = TG["next_id"]
n = len(MR["scripts"])
tap(find(p, "Cancel print"), msg_id=pid)
check("Cancel print: asks first, nothing sent yet", wait(lambda: any(m == "editMessageText" and "Really cancel the print?" in b["text"] for m, b in TG["calls"]))
      and "CANCEL_PRINT" not in MR["scripts"][n:])
q = [b for m, b in TG["calls"] if m == "editMessageText" and "Really cancel" in b["text"]][-1]
tap(find(q, "No, go back"), msg_id=pid); time.sleep(0.5)
check("No: still printing / paused, not cancelled", sim.pstate != "cancelled")
tap("m:estop", msg_id=pid)
wait(lambda: any(m == "editMessageText" and "Really EMERGENCY STOP?" in b["text"] for m, b in TG["calls"]))
check("Emergency stop: asks first", MR["estop"] == 0)
tap("m:yes_estop", msg_id=pid)
check("Emergency stop: sent after the second tap", wait(lambda: MR["estop"] == 1))
tap("m:cancel", msg_id=pid); time.sleep(0.4); tap("m:yes_cancel", msg_id=pid)
check("Cancel print: done after the second tap", wait(lambda: sim.pstate == "cancelled" and sim.vars["COLOR_SWAP"]["state"] == 0))

bot.stop.set()
bad = [r for r in results if not r[1]]
print("\n%d checks, %d failed" % (len(results), len(bad)))
sys.exit(1 if bad else 0)
