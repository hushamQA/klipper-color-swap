"""COLOR_SWAP macro tests. Run:  python run_tests.py   (needs: pip install jinja2)
Renders color_swap.cfg and macros.cfg the way Klipper does and runs the macros against a
fake printer (delta, cartesian, corexy). Nothing touches the real printer."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sim import Sim, Raise

BASE = os.path.dirname(HERE)
CS = os.path.join(BASE, "color_swap.cfg")
V400 = os.path.join(BASE, "macros.cfg")
if not os.path.exists(V400):          # package / repository layout
    V400 = os.path.join(BASE, "FLSUN_V400", "macros.cfg")
GEN = os.path.join(HERE, "generic_macros.cfg")

SWAP = "COLOR_SWAP SLOT=2 MATERIAL=PLA OLD_MATERIAL=PETG TEMP=215 OLD_TEMP=240 RETRACT=2 PURGE=43.155"
# Same material type, only the color changes: the only swap AWAY continues by itself (v6.5).
SAME = "COLOR_SWAP SLOT=2 MATERIAL=PETG OLD_MATERIAL=PETG TEMP=235 OLD_TEMP=240 RETRACT=2 PURGE=43.155"
results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond), extra))
    print(("PASS " if cond else "FAIL ") + name + (("  -> " + str(extra)) if extra and not cond else ""))


def start(kin="delta", macros=V400, x=30.0, y=20.0, z=3.2, layer=5, home=True):
    s = Sim([macros, CS], kin=kin)
    s.fire("_CS_BOOT")
    if home:                          # the factory mode is AWAY; most tests check HOME steps
        set_cfg(s, "auto_continue_min", 0)
    s.pstate, s.target, s.layer = "printing", 240.0, layer
    s.pos = [x, y, z]
    s.e = 0.0
    s.minz = 1e9
    s.e = -2.0          # the slicer retracted RETRACT before the toolchange
    return s


def cs(s):
    return s.vars["COLOR_SWAP"]


def set_cfg(s, k, v):
    s.vars["_COLOR_SWAP_CFG"][k] = v


for kin, macros in (("delta", V400), ("cartesian", GEN), ("corexy", GEN)):
    tag = "[%s] " % kin
    # ---------- 1. normal swap ----------
    s = start(kin, macros)
    z0 = s.pos[2]
    s.cmd(SWAP)
    check(tag + "swap: state 1, unloaded, paused", cs(s)["state"] == 1 and cs(s)["unloaded"] == 1 and s.paused)
    exp_py = -140.0 if kin == "delta" else 12.0
    exp_px = 0.0 if kin == "delta" else 117.5
    check(tag + "park point", abs(s.pos[0] - exp_px) < 0.01 and abs(s.pos[1] - exp_py) < 0.01 and s.pos[2] >= 60, s.pos)
    check(tag + "purge total 43+15 (PETG->PLA, main PETG)", abs(cs(s)["purge_total"] - 58.155) < 0.01, cs(s)["purge_total"])
    check(tag + "main material", cs(s)["main_material"] == "PETG")
    check(tag + "tick armed + idle timeout raised", s.timers.get("_CS_TICK") == 10 and any("SET_IDLE_TIMEOUT TIMEOUT=28800" in l for l in s.log))
    labels = [b for t, b in s.prompt()]
    check(tag + "prompt 1 has Load + purge and material buttons", any("Load + purge|_CS_LOAD" in b for b in labels) and any("ABS 250C" in b for b in labels), labels)
    s.fire("_CS_SWAP_CHECKPOINT")
    check(tag + "swap checkpoint saved with main", s.saved.get("cs_resume", {}).get("main") == "PETG" and s.saved["cs_resume"]["kind"] == "swap", s.saved.get("cs_resume"))
    # RESUME while unloaded must be refused when the hook is there
    if macros == V400:
        try:
            s.cmd("RESUME")
            check(tag + "raw RESUME refused while unloaded", False)
        except Raise:
            check(tag + "raw RESUME refused while unloaded", s.paused)
    s.filament = False
    s.cmd("_CS_LOAD")
    check(tag + "load refused: sensor empty", cs(s)["state"] == 1 and cs(s)["view"] == "nofil")
    s.filament = True
    e_before = s.e
    s.cmd("_CS_LOAD")
    check(tag + "loaded: state 2, hold 2", cs(s)["state"] == 2 and cs(s)["hold"] == 2.0)
    check(tag + "purged counter", abs(cs(s)["purged"] - (58.155 + 8)) < 0.01, cs(s)["purged"])
    s.cmd("_CS_PURGE_MORE MM=30")
    s.cmd("_CS_CONFIRM")
    check(tag + "confirm view", cs(s)["view"] == "confirm")
    e_loaded = s.e
    s.cmd("_CS_CONTINUE")
    check(tag + "continued: printing, state 0", s.pstate == "printing" and cs(s)["state"] == 0 and not s.paused)
    # nozzle full = filament at 0 relative to the loaded-and-held point + hold; after
    # continue the slicer still has to push RETRACT (2): so e must be reprime - 2 above "held+hold"
    net = s.e - (e_loaded + 2.0)     # relative to nozzle-full
    check(tag + "filament accounting: slicer push of 2 mm fills exactly (+1.5 reprime)", abs(net - (1.5 - 2.0)) < 1e-6, net)
    check(tag + "back at the paused point", abs(s.pos[0] - 30) < 1e-6 and abs(s.pos[2] - z0) < 1e-6, s.pos)
    check(tag + "never below the paused Z", s.minz >= z0 - 1e-9, s.minz)
    check(tag + "sensor back on, motors released, idle timeout restored",
          any("SET_FILAMENT_SENSOR SENSOR=filament_sensor ENABLE=1" in l for l in s.log)
          and any("SET_TMC_CURRENT STEPPER=stepper_a HOLDCURRENT=0.5" in l for l in s.log)
          and any("SET_IDLE_TIMEOUT TIMEOUT=1800" in l for l in s.log))
    check(tag + "stats: 1 swap", cs(s)["swaps"] == 1 and cs(s)["cur_material"] == "PLA")

    # ---------- 2. back to main: +60 ----------
    s.e = -2.0
    s.target = 215.0
    s.cmd("COLOR_SWAP SLOT=1 MATERIAL=PETG OLD_MATERIAL=PLA TEMP=240 OLD_TEMP=215 RETRACT=2 PURGE=25")
    check(tag + "back to main purge 25+15+60", abs(cs(s)["purge_total"] - 100) < 0.01 and cs(s)["to_main"] == 1, cs(s)["purge_total"])
    s.cmd("_CS_CANCEL_MENU")
    s.cmd("_CS_CANCEL_PRINT UNLOAD=0")
    check(tag + "cancel: state 0, cancelled", cs(s)["state"] == 0 and s.pstate == "cancelled")

    # ---------- 3. auto continue ----------
    s = start(kin, macros)
    set_cfg(s, "auto_continue_min", 5)
    z0 = s.pos[2]
    s.cmd(SAME)
    check(tag + "auto-continue: not unloaded, Unload button", cs(s)["unloaded"] == 0 and any("Unload|_CS_UNLOAD" in b for t, b in s.prompt()), s.prompt())
    check(tag + "auto-continue: no unload moves", not any(l.startswith("G1 E-13") for l in s.log))
    e_paused = s.e
    s.tick(29)
    check(tag + "auto-continue: still waiting at 4:50", cs(s)["state"] == 1)
    s.tick(1)
    check(tag + "auto-continue: resumed with old color at 5:00", s.pstate == "printing" and cs(s)["state"] == 0 and cs(s)["cur_material"] == "PETG" and cs(s)["swaps"] == 0)
    check(tag + "auto-continue: reheated to old temp", s.target == 240.0, s.target)
    # before pause: e=-2 (slicer). continue must leave it at -2 + reprime
    check(tag + "auto-continue: accounting (-2 + 1.5)", abs(s.e - (-2.0 + 1.5)) < 1e-6, s.e)
    check(tag + "auto-continue: never below paused Z", s.minz >= z0 - 1e-9, s.minz)

    # ---------- 4. auto continue cancelled by a touch, manual unload, standby ----------
    s = start(kin, macros)
    set_cfg(s, "auto_continue_min", 5)
    s.cmd(SWAP)
    s.cmd("CS_WAIT")
    s.tick(40)
    check(tag + "CS_WAIT holds the swap", cs(s)["state"] == 1 and s.paused)
    check(tag + "standby after 5 min idle", cs(s)["standby"] == 1 and s.target == 170.0, (cs(s)["standby"], s.target))
    s.cmd("_CS_UNLOAD")
    check(tag + "manual unload reheats + unloaded", cs(s)["unloaded"] == 1 and s.target == 240.0 and cs(s)["standby"] == 0)
    s.cmd("_CS_LOAD")
    s.tick(31)
    check(tag + "standby again in state 2", cs(s)["standby"] == 1 and s.target == 170.0)
    s.cmd("_CS_CONFIRM")
    check(tag + "Continue after standby wakes (reheat + purge), no confirm yet", cs(s)["standby"] == 0 and cs(s)["view"] == "" and s.target == 215.0 and cs(s)["state"] == 2)
    s.tick(6 * 61)
    check(tag + "nozzle off after 60 min, still paused, bed untouched", cs(s)["standby"] == 2 and s.target == 0.0 and s.paused and not any(l.startswith("M140 S0") for l in s.log))
    check(tag + "reminders sent", sum("still waiting" in l for l in s.log if l.startswith("SET_GCODE_VARIABLE MACRO=_CS_ALERT")) >= 5)
    s.cmd("_CS_CONFIRM")
    s.cmd("_CS_CONFIRM")
    s.cmd("_CS_CONTINUE")
    check(tag + "continues after heater-off wait", s.pstate == "printing" and s.target == 215.0)

    # ---------- 5. keep color by button ----------
    s = start(kin, macros)
    set_cfg(s, "auto_unload", 0)
    s.cmd(SWAP)
    check(tag + "auto_unload 0: filament stays", cs(s)["unloaded"] == 0)
    s.cmd("_CS_KEEP")
    check(tag + "keep question", cs(s)["view"] == "keep")
    s.cmd("_CS_KEEP_GO")
    check(tag + "keep: printing with PETG", s.pstate == "printing" and cs(s)["cur_material"] == "PETG")

    # ---------- 6. layer-1 wipe line ----------
    s = start(kin, macros, x=10 if kin == "delta" else 110, y=10 if kin == "delta" else 120, z=0.6, layer=1)
    if kin != "delta":
        s.objects = [{"name": "a", "polygon": [[90, 90], [140, 90], [140, 140], [90, 140]]}]
    s.cmd(SWAP)
    s.cmd("_CS_LOAD")
    s.cmd("_CS_CONFIRM")
    s.cmd("_CS_CONTINUE")
    drew = any((l.startswith("G3 ") if kin == "delta" else (l.startswith("G1 X225") and "E8" in l)) for l in s.log)
    check(tag + "layer-1 wipe line drawn", drew and cs(s)["wipe_count"] == 1, [l for l in s.log if l.startswith("G3") or "Wipe" in l or "wipe" in l])
    check(tag + "wipe line lowest Z is wipe_z 0.3", abs(s.minz - 0.3) < 1e-9, s.minz)

    # ---------- 7. runout through M600 (already paused by the sensor) ----------
    if macros == V400:
        s = start(kin, macros)
        s.e = 0.0
        cs(s)["cur_material"] = "PETG"; cs(s)["cur_slot"] = 1; cs(s)["job_file"] = "test.gcode"; cs(s)["job_dur"] = 50
        s.cmd("PAUSE")           # what Klipper does at a runout, then runout_gcode:
        s.cmd("M600")
        check(tag + "runout: swap window, state 1, runout flag", cs(s)["state"] == 1 and cs(s)["runout"] == 1 and cs(s)["purge_total"] == 25, cs(s))
        s.cmd("_CS_LOAD")
        s.cmd("_CS_CONFIRM"); s.cmd("_CS_CONTINUE")
        # no slicer retract: after RESUME (pushes 1) nozzle must be full + reprime
        check(tag + "runout: continues, swaps not counted", s.pstate == "printing" and cs(s)["swaps"] == 0)

    # ---------- 8. hookless cancel is cleaned up by the tick ----------
    s = start(kin, macros)
    s.cmd(SWAP)
    s.paused, s.pstate = False, "cancelled"
    s.tick(1)
    check(tag + "tick resets after an outside cancel", cs(s)["state"] == 0 and "_CS_TICK" not in s.timers or s.timers.get("_CS_TICK") == 0)

    # ---------- 9. power loss: resume restores the main filament ----------
    s = start(kin, macros)
    s.cmd(SWAP); s.fire("_CS_SWAP_CHECKPOINT")
    saved = dict(s.saved)
    s2 = Sim([macros, CS], kin=kin)          # restart: every macro variable is wiped
    s2.saved = saved
    s2.fire("_CS_BOOT")
    s2.homed = "" if kin == "delta" else "xyz"
    s2.fire("_CS_BOOT_CHECK")
    check(tag + "boot: resume window offered", any("Resume saved print" in b for t, b in s2.prompt()), s2.prompt())
    s2.cmd("_CS_RS_PREP")
    check(tag + "resume prep: step 1", s2.vars["RESUME_SAVED_PRINT"]["step"] == 1, s2.log[-5:])
    s2.cmd("_CS_RS_UNLOAD"); s2.cmd("_CS_RS_LOAD"); s2.cmd("_CS_RS_CONFIRM"); s2.cmd("_CS_RS_GO")
    c2 = s2.vars["COLOR_SWAP"]
    check(tag + "resume: main filament, slot, job restored", c2["main_material"] == "PETG" and c2["cur_material"] == "PLA" and c2["cur_slot"] == 2 and c2["job_file"] == "test.gcode" and c2["swaps"] == 1, c2)
    s2.pstate, s2.target, s2.duration = "printing", 215.0, 5.0
    s2.fire("_CS_AUTOSAVE")
    check(tag + "resume: autosave does not see a new job", s2.vars["COLOR_SWAP"]["main_material"] == "PETG")
    s2.e = -2.0
    s2.cmd("COLOR_SWAP SLOT=1 MATERIAL=PETG OLD_MATERIAL=PLA TEMP=240 OLD_TEMP=215 RETRACT=2 PURGE=25")
    check(tag + "resume: next swap back to main gets +60", abs(s2.vars["COLOR_SWAP"]["purge_total"] - 100) < 0.01, s2.vars["COLOR_SWAP"]["purge_total"])

    # ---------- 10a. the factory mode is AWAY, 5 min (version 6.3) ----------
    sd = start(kin, macros, home=False)
    check(tag + "factory mode: AWAY, 5 min", sd.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 5 and sd.vars["_COLOR_SWAP_CFG"]["away_min"] == 5)
    sd.cmd(SAME)
    labels = [b for t, b in sd.prompt()]
    check(tag + "factory mode: the old filament stays in, Unload by hand or Keep", cs(sd)["unloaded"] == 0 and any(b.startswith("Unload|") for b in labels)
          and any(b.startswith("Keep current color|") for b in labels), labels)
    sd.tick(29)
    check(tag + "factory mode: still waiting before 5 min", sd.paused and cs(sd)["state"] == 1)
    sd.tick(2)
    check(tag + "factory mode: after 5 min the print goes on with the same color", sd.pstate == "printing" and not sd.paused and cs(sd)["state"] == 0
          and cs(sd)["cur_material"] == "PETG" and cs(sd)["swaps"] == 0)

    sv_ = Sim([macros, CS], kin=kin); sv_.saved = {"cs_set": {"away_min": 1}}; sv_.fire("_CS_BOOT")
    check(tag + "boot: saved away time 1 + factory AWAY = waits 1 min, as the window says", sv_.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 1, sv_.vars["_COLOR_SWAP_CFG"]["auto_continue_min"])
    sv_ = Sim([macros, CS], kin=kin); sv_.saved = {"cs_set": {"away_min": 7, "auto_continue_min": 0}}; sv_.fire("_CS_BOOT")
    check(tag + "boot: saved HOME stays HOME", sv_.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 0)

    # ---------- 10. settings window (simplified, version 6.1) ----------
    s = Sim([macros, CS], kin=kin)
    s.fire("_CS_BOOT")
    set_cfg(s, "auto_continue_min", 0)
    c = s.vars["_COLOR_SWAP_CFG"]
    ngroups = len(s.vars["_CS_SCHEMA"]["groups"])
    s.cmd("COLOR_SWAP_SETTINGS")
    first = [b for t, b in s.prompt() if t == "prompt_button"]
    check(tag + "settings: first window has 7 buttons, HOME, NORMAL", len(first) == 7 and "I am HOME" in first[0] and "Purge amount: NORMAL" in first[2], first)
    check(tag + "settings: purge level detected at boot", cs(s)["purge_level"] == "normal")
    # HOME / AWAY
    s.cmd("_CS_SET_MODE")
    check(tag + "settings: AWAY sets auto continue to away_min", c["auto_continue_min"] == 5 and any("I am AWAY" in b for t, b in s.prompt()), s.prompt())
    s.cmd("_CS_SET_EDIT K=away_min G=-1")
    s.cmd("_CS_SET_ADJ K=away_min D=10 G=-1 P=0 E=1")
    check(tag + "settings: away time follows while AWAY", c["away_min"] == 15 and c["auto_continue_min"] == 15)
    s.cmd("_CS_SET_MODE")
    check(tag + "settings: HOME sets auto continue 0, keeps away time", c["auto_continue_min"] == 0 and c["away_min"] == 15)
    s.cmd("_CS_SET_ADJ K=away_min D=-10 G=-1 P=0 E=1")
    check(tag + "settings: away time change while HOME does not arm it", c["auto_continue_min"] == 0 and c["away_min"] == 5)
    # purge level
    s.cmd("_CS_PURGE_LEVEL")
    six = lambda: (c["purge_default"], c["purge_to_main_extra"], c["purge_material_change"], c["purge_btn1"], c["purge_btn2"], c["purge_btn3"])
    check(tag + "settings: HIGH", cs(s)["purge_level"] == "high" and six() == (90, 110, 25, 25, 55, 110), six())
    s.cmd("_CS_PURGE_LEVEL")
    check(tag + "settings: LOW", cs(s)["purge_level"] == "low" and six() == (30, 35, 10, 10, 20, 35), six())
    s.cmd("_CS_SET_ADJ K=purge_btn2 D=5 G=5 P=0 E=1")
    check(tag + "settings: a hand change shows CUSTOM", cs(s)["purge_level"] == "custom")
    s.cmd("COLOR_SWAP_SETTINGS")
    check(tag + "settings: CUSTOM on the button", any("Purge amount: CUSTOM" in b for t, b in s.prompt()))
    s.cmd("_CS_PURGE_LEVEL")
    check(tag + "settings: from CUSTOM back to NORMAL", cs(s)["purge_level"] == "normal" and six() == (50, 60, 15, 15, 30, 60), six())
    # lists
    s.cmd("COLOR_SWAP_SETTINGS V=adv")
    adv = [b for t, b in s.prompt() if t == "prompt_button"]
    s.cmd("COLOR_SWAP_SETTINGS V=setup")
    setup = [b for t, b in s.prompt() if t == "prompt_button"]
    check(tag + "settings: 6 advanced groups, 3 setup groups + Check install", len(adv) == 6 and len(setup) == 3 and any("Check install" in b for t, b in s.prompt()), (adv, setup))
    # every numeric setting reachable; hidden ones are exactly the ones that do not apply
    set_cfg(s, "flick", 1)
    s.settings["output_pin beeper"] = {}         # a printer with a buzzer shows the beep lines
    seen = set()
    for pa in (1, 0):                 # park X / Y only show with the automatic park point OFF
        set_cfg(s, "park_auto", pa)
        for g in range(ngroups):
            for p_ in range(4):
                s.log.clear()
                s.cmd("COLOR_SWAP_SETTINGS G=%d P=%d" % (g, p_))
                pr = s.prompt()
                if not any("Tap a line" in b for t, b in pr):
                    continue
                for t, b in pr:
                    if t == "prompt_button" and " K=" in b:
                        seen.add(b.split(" K=")[1].split()[0])
                        assert len(b.split("|")[0]) <= 48, b
    set_cfg(s, "flick", 0); set_cfg(s, "park_auto", 1)
    del s.settings["output_pin beeper"]
    scalars = set(k for k, v in c.items() if isinstance(v, (int, float)))
    hidden = {"away_min", "auto_continue_min"} | ({"wipe_len", "resume_trust_z"} if kin == "delta" else set())
    check(tag + "settings: every numeric setting is reachable", scalars - seen == hidden and not (seen - scalars), (sorted(scalars - seen), sorted(seen - scalars)))
    s.cmd("COLOR_SWAP_SETTINGS G=7 P=1")
    check(tag + "settings: flick details hidden while flick is off", not any("flick_mm" in b for t, b in s.prompt()))
    for k in sorted(scalars):
        s.cmd("_CS_SET_EDIT K=%s G=0 P=0" % k)
    s.cmd("_CS_SET_EDIT K=reprime_mm G=5 P=2")
    check(tag + "settings: edit window explains the number", any(t == "prompt_text" and "Raise to 2 or 3" in b and "This is the file default" in b for t, b in s.prompt()), s.prompt())
    s.cmd("_CS_SET_ADJ K=purge_to_main_extra D=5 G=5 P=0 E=1")
    check(tag + "settings: changed value offers the file default", any("Back to the file default (60)" in b for t, b in s.prompt()), s.prompt())
    s.cmd("_CS_SET_ADJ K=auto_unload T=1 G=3 P=0")
    check(tag + "settings: star on a changed line", any(b.startswith("* Pull old filament out (HOME only): OFF") for t, b in s.prompt()), s.prompt())
    s.cmd("COLOR_SWAP_SETTINGS V=adv")
    check(tag + "settings: group shows how many changed", any("Swap (1 changed)" in b for t, b in s.prompt()) and any("Purge details (1 changed)" in b for t, b in s.prompt()), s.prompt())
    s.cmd("_CS_SET_ADJ K=reprime_mm D=-0.5 G=5 P=2 E=1")
    s.cmd("_CS_SET_ADJ K=park_lift D=-1000 G=9 P=0 E=1")
    check(tag + "settings: applied + clamped", c["purge_to_main_extra"] == 65 and c["auto_unload"] == 0 and c["reprime_mm"] == 1.0 and c["park_lift"] == 1, (c["purge_to_main_extra"], c["auto_unload"], c["reprime_mm"], c["park_lift"]))
    sv = s.saved.get("cs_set")
    check(tag + "settings: saved", sv["purge_to_main_extra"] == 65 and sv["auto_unload"] == 0 and sv["reprime_mm"] == 1.0 and sv["park_lift"] == 1 and sv["away_min"] == 5, sv)
    s3 = Sim([macros, CS], kin=kin); s3.saved = dict(s.saved); s3.fire("_CS_BOOT")
    check(tag + "settings: loaded after restart", s3.vars["_COLOR_SWAP_CFG"]["purge_to_main_extra"] == 65 and s3.vars["_COLOR_SWAP_CFG"]["auto_unload"] == 0 and s3.vars["COLOR_SWAP"]["purge_level"] == "custom")
    s3.cmd("_CS_SET_RESET"); s3.cmd("_CS_SET_RESET GO=1")
    check(tag + "settings: reset all", s3.vars["_COLOR_SWAP_CFG"]["purge_to_main_extra"] == 60 and s3.saved["cs_set"] == {"auto_continue_min": 0} and s3.vars["_COLOR_SWAP_CFG"]["auto_unload"] == 1 and s3.vars["COLOR_SWAP"]["purge_level"] == "normal")
    check(tag + "factory reset: asked first, button on the first window", any("Factory reset..." in b for t, b in s3.prompt()) and any("Factory reset done" in l for l in s3.log))
    s3.cmd("COLOR_SWAP_FACTORY_RESET")
    check(tag + "factory reset macro asks before doing it", any("Yes, factory reset" in b for t, b in s3.prompt()))
    s3.cmd("COLOR_SWAP_SET NAME=reprime_mm VALUE=2.5"); s3.cmd("COLOR_SWAP_SET NAME=park_lift VALUE=9999"); s3.cmd("COLOR_SWAP_SET"); s3.cmd("COLOR_SWAP_SET NAME=nonsense VALUE=1")
    check(tag + "COLOR_SWAP_SET types a value, clamps it, saves it", s3.vars["_COLOR_SWAP_CFG"]["reprime_mm"] == 2.5 and s3.vars["_COLOR_SWAP_CFG"]["park_lift"] == 100 and s3.saved["cs_set"] == {"auto_continue_min": 0, "reprime_mm": 2.5, "park_lift": 100}, s3.saved["cs_set"])
    s3.cmd("_CS_SET_RESET GO=1")
    # settings can be opened and changed while printing and while a swap waits
    sp = start(kin, macros)
    sp.cmd("COLOR_SWAP_SETTINGS"); sp.cmd("_CS_SET_ADJ K=reprime_mm D=0.5 G=5 P=2 E=1"); sp.cmd("_CS_SET_CLOSE")
    moved = [l for l in sp.log if l.startswith(("G1", "G0", "G28", "M104", "M109", "PAUSE"))]
    check(tag + "settings while printing: applied, nothing moves", sp.vars["_COLOR_SWAP_CFG"]["reprime_mm"] == 2.0 and not moved and sp.pstate == "printing", moved)
    sp.cmd(SWAP); sp.cmd("COLOR_SWAP_SETTINGS"); sp.cmd("_CS_PURGE_LEVEL"); sp.cmd("_CS_SET_CLOSE")
    check(tag + "settings during a swap: close brings the swap window back", any("Load + purge|_CS_LOAD" in b for t, b in sp.prompt()) and sp.vars["COLOR_SWAP"]["state"] == 1, sp.prompt())
    s3.cmd("_CS_SET_CLOSE")
    s3.cmd("COLOR_SWAP_CHECK")
    check(tag + "install check runs", any("installation check" in l for l in s3.log), s3.log[-14:])
    check(tag + "install check: wipe line ready, trust Z not claimed", any("Layer-1 wipe line: ready" in l for l in s3.log) and not any("trusted Z is ON" in l for l in s3.log))
    if kin != "delta":
        s4 = Sim([macros, CS], kin=kin); s4.fire("_CS_BOOT"); s4.homed = ""
        s4.saved = {"cs_resume": {"kind": "auto", "file": "test.gcode", "pos": 1, "layer": 3, "total": 9, "x": 100, "y": 100, "z": 1.0, "e": 0, "abse": 0, "temp": 215, "ptemp": 215, "bed": 60, "fan": 0.5, "retract": 0, "slot": 1, "mat": "PLA", "main": "PLA", "wc": 0, "sw": 0, "pg": 0, "offz": 0, "sf": 1, "ef": 1, "pa": 0.03, "st": 0.04, "mesh": "default", "excl": []}}
        s4.vars["_COLOR_SWAP_CFG"]["resume_trust_z"] = 1
        s4.cmd("_CS_RS_PREP")
        check(tag + "trust Z refused while enable_force_move is off", s4.vars["RESUME_SAVED_PRINT"]["step"] == 0 and not any(l.startswith("SET_KINEMATIC_POSITION") for l in s4.log))
        s4.settings["force_move"] = {"enable_force_move": True}
        s4.cmd("_CS_RS_PREP")
        check(tag + "trust Z works with enable_force_move on", s4.vars["RESUME_SAVED_PRINT"]["step"] == 1 and any(l.startswith("SET_KINEMATIC_POSITION Z=1.0") for l in s4.log))
    # ---------- 10b. the buttons as drawn (version 6.3) ----------
    # Press what the edit window SHOWS, not a typed command: "- 1" must lower the value.
    sb = Sim([macros, CS], kin=kin); sb.fire("_CS_BOOT")
    cb = sb.vars["_COLOR_SWAP_CFG"]
    schema = {it[0]: it for gr in sb.vars["_CS_SCHEMA"]["groups"] for it in gr[2]}
    def press(label):
        btn = [b for t, b in sb.prompt() if t == "prompt_button" and b.split("|")[0] == label]
        assert btn, (label, sb.prompt())
        sb.cmd(btn[0].split("|")[1])
    wrong = []
    for k, it in schema.items():
        if it[2] == 0 or k == "auto_continue_min":
            continue
        step = it[2]
        lbl = lambda x: str(int(x)) if x == int(x) else str(round(x, 3))
        sb.cmd("_CS_SET_EDIT K=%s G=-1" % k)
        v0 = float(cb[k])
        press("+ " + lbl(step)); v1 = float(cb[k])
        press("- " + lbl(step)); v2 = float(cb[k])
        press("- " + lbl(step * 10)); v3 = float(cb[k])
        press("+ " + lbl(step * 10)); v4 = float(cb[k])
        lo, hi = float(it[3]), float(it[4])
        ok = (v1 >= v0 or v0 >= hi) and v2 <= v1 and v3 <= v2 and v4 >= v3 and (v3 < v2 or v2 <= lo or k.startswith("temp_") or k == "purge_max")
        if not ok:
            wrong.append((k, v0, v1, v2, v3, v4))
        sb.cmd("_CS_SET_ADJ K=%s V=%s Q=1" % (k, v0))
    check(tag + "settings: the drawn - buttons lower and + buttons raise every number", not wrong, wrong)
    sb.cmd("_CS_SET_EDIT K=away_min G=-1"); press("- 1")
    check(tag + "settings: away time 5 - 1 = 4 (the reported bug)", cb["away_min"] == 4, cb["away_min"])
    sb.cmd("_CS_SET_ADJ K=away_min V=5 Q=1")
    # purge limits never cross
    sb.cmd("COLOR_SWAP_SET NAME=purge_min VALUE=400")
    sb.cmd("COLOR_SWAP_SET NAME=purge_max VALUE=20")
    check(tag + "settings: purge min never above purge max", cb["purge_min"] == 250 and cb["purge_max"] == 250, (cb["purge_min"], cb["purge_max"]))
    sb.cmd("_CS_SET_RESET GO=1")
    # a material temperature is 0 or at least min_temp
    sb.cmd("COLOR_SWAP_SET NAME=temp_pla VALUE=100")
    t_down = cb["temp_pla"]
    sb.cmd("_CS_SET_EDIT K=temp_pla G=-1"); press("+ 5")
    check(tag + "settings: material temp below min_temp goes to 0, + from 0 jumps to min_temp", t_down == 0 and cb["temp_pla"] == 170, (t_down, cb["temp_pla"]))
    sb.cmd("_CS_SET_RESET GO=1")
    # lines that do nothing are hidden
    def group_lines(name):
        gi = [i for i, gr in enumerate(sb.vars["_CS_SCHEMA"]["groups"]) if gr[0] == name][0]
        out = []
        for p_ in range(3):
            sb.cmd("COLOR_SWAP_SETTINGS G=%d P=%d" % (gi, p_))
            out += [b.split(" K=")[1].split()[0] for t, b in sb.prompt() if t == "prompt_button" and " K=" in b]
        return set(out)
    a_nopin = group_lines("Alerts")
    check(tag + "settings: no buzzer pin = no buzzer lines (they would do nothing)", not ({"beep", "beep_count", "beep_ms"} & a_nopin) and "remind_min" in a_nopin, a_nopin)
    sb.settings["output_pin beeper"] = {}
    a1 = group_lines("Alerts"); set_cfg(sb, "beep", 0); set_cfg(sb, "notify", 0); a0 = group_lines("Alerts")
    check(tag + "settings: beep and reminder details hidden while those are OFF", {"beep_count", "beep_ms", "remind_min"} <= a1 and not ({"beep_count", "beep_ms", "remind_min"} & a0), (a1, a0))
    sw = group_lines("Swap"); sb.vars["COLOR_SWAP"]["sensor_obj"] = ""; sw0 = group_lines("Swap")
    check(tag + "settings: sensor lines only with a filament sensor", {"load_check_sensor", "runout_swap"} <= sw and not ({"load_check_sensor", "runout_swap"} & sw0), (sw, sw0))
    sb.vars["COLOR_SWAP"]["sensor_obj"] = "filament_switch_sensor filament_sensor"
    p1 = group_lines("Park point"); set_cfg(sb, "park_auto", 0); p0 = group_lines("Park point")
    check(tag + "settings: automatic park shows the edge, manual park shows X / Y", "park_edge" in p1 and "park_x" not in p1 and "park_x" in p0 and "park_edge" not in p0, (p1, p0))
    w1 = group_lines("First layer line"); set_cfg(sb, "first_layer_wipe", 0); w0 = group_lines("First layer line")
    check(tag + "settings: start line details hidden while the line is OFF", "wipe_z" in w1 and w0 == {"first_layer_wipe", "flick"}, (w1, w0))
    # factory reset keeps HOME / AWAY
    sr = Sim([macros, CS], kin=kin); sr.fire("_CS_BOOT")
    sr.cmd("COLOR_SWAP_SET NAME=away_min VALUE=9"); sr.cmd("COLOR_SWAP_SET NAME=reprime_mm VALUE=3")
    sr.cmd("_CS_SET_RESET GO=1")
    rc = sr.vars["_COLOR_SWAP_CFG"]
    check(tag + "factory reset keeps AWAY (with the factory away time)", rc["auto_continue_min"] == 5 and rc["away_min"] == 5 and rc["reprime_mm"] == 1.5 and sr.saved["cs_set"] == {"auto_continue_min": 5}, (rc["auto_continue_min"], rc["away_min"], sr.saved.get("cs_set")))
    sr2 = Sim([macros, CS], kin=kin); sr2.saved = dict(sr.saved); sr2.fire("_CS_BOOT")
    check(tag + "factory reset: AWAY still on after a restart", sr2.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 5)
    sr.cmd("_CS_SET_MODE"); sr.cmd("_CS_SET_RESET GO=1")
    check(tag + "factory reset keeps HOME (although the factory mode is AWAY)", rc["auto_continue_min"] == 0 and sr.saved["cs_set"] == {"auto_continue_min": 0}, sr.saved.get("cs_set"))
    sr3 = Sim([macros, CS], kin=kin); sr3.saved = dict(sr.saved); sr3.fire("_CS_BOOT")
    check(tag + "factory reset: HOME still on after a restart", sr3.vars["_COLOR_SWAP_CFG"]["auto_continue_min"] == 0)
    # HOME / AWAY in the settings window during a swap that already needs hands
    sx = start(kin, macros); sx.cmd(SWAP); sx.cmd("COLOR_SWAP_SETTINGS")
    pr = sx.prompt()
    check(tag + "settings during an unloaded swap: HOME / AWAY says it is for the NEXT swaps", any(b.startswith("Next swaps: I am HOME") for t, b in pr)
          and any(t == "prompt_text" and "already out" in b for t, b in pr), pr[:3])
    sy = start(kin, macros); set_cfg(sy, "auto_unload", 0); sy.cmd(SAME); sy.cmd("COLOR_SWAP_SETTINGS")
    check(tag + "settings during a swap with the filament still in: AWAY still helps this swap", any(b.startswith("I am HOME") for t, b in sy.prompt()), sy.prompt()[:3])
    sy.cmd("_CS_SET_MODE"); sy.tick(31)
    check(tag + "AWAY set during that swap: it goes on by itself", sy.pstate == "printing")
    # AWAY: the nozzle stays hot until the print goes on by itself
    sa = start(kin, macros)
    sa.cmd("_CS_SET_MODE"); set_cfg(sa, "away_min", 10); set_cfg(sa, "auto_continue_min", 10)
    sa.cmd(SAME)
    sa.tick(40)
    check(tag + "AWAY: no cool-down before the print goes on by itself", cs(sa)["standby"] == 0 and not any("nozzle cooled" in l for l in sa.log), [l for l in sa.log if "cooled" in l])
    sa.tick(25)
    check(tag + "AWAY: continues after 10 min with a hot nozzle", sa.pstate == "printing")
    sh = start(kin, macros); sh.cmd(SWAP); sh.tick(35)
    check(tag + "HOME: the nozzle still cools after 5 min", cs(sh)["standby"] == 1)

    # AWAY really arms the swap
    s = start(kin, macros)
    s.cmd("_CS_SET_MODE")
    s.cmd(SAME)
    check(tag + "AWAY mode: the next swap keeps the filament in", cs(s)["unloaded"] == 0)
    s.tick(30)
    check(tag + "AWAY mode: continues by itself after 5 min", s.pstate == "printing")

    # ---------- 10b. AWAY never goes on with the wrong MATERIAL (v6.5) ----------
    sm = start(kin, macros, home=False)
    sm.cmd(SWAP)                                   # PETG -> PLA
    txt = [b for t, b in sm.prompt() if t == "prompt_text"]
    check(tag + "material change: old filament stays in, window says it waits", cs(sm)["unloaded"] == 0
          and any("material changes (PETG to PLA)" in b for b in txt) and not any("more min" in b for b in txt), txt)
    check(tag + "material change: phone message says it will not continue", any("will NOT continue by itself" in l for l in sm.log), [l for l in sm.log if "_CS_ALERT" in l][:2])
    sm.tick(6 * 30)
    check(tag + "material change: still waiting after 30 min", sm.paused and cs(sm)["state"] == 1 and sm.pstate != "printing")
    rem_ = [l for l in sm.log if "still waiting" in l]
    check(tag + "material change: the reminder says press Unload and names the change, not 'insert'", rem_ and all("press Unload (material changes PETG to PLA)" in l and "insert" not in l for l in rem_), rem_[:1])
    check(tag + "material change: the nozzle cools to standby while it waits", cs(sm)["standby"] == 1 and sm.target == 170.0, (cs(sm)["standby"], sm.target))
    sm.cmd("CS_STATUS")
    check(tag + "material change: CS_STATUS says why it waits", any("material changes (PETG to PLA), waiting for you" in l for l in sm.log))
    sm.cmd("_CS_KEEP")
    check(tag + "material change: Keep warns which material the part gets", any(t == "prompt_text" and "WARNING: the slicer wants PLA" in b for t, b in sm.prompt()), sm.prompt())
    sm.cmd("_CS_KEEP_GO")
    check(tag + "material change: Keep on purpose still goes on with the old filament", sm.pstate == "printing" and cs(sm)["cur_material"] == "PETG")
    sr_ = start(kin, macros, home=False)
    sr_.cmd("COLOR_SWAP SLOT=2 MATERIAL=PLA TEMP=215 OLD_TEMP=215 RETRACT=2 PURGE=40")     # no OLD_MATERIAL from the slicer
    sr_.tick(31)
    check(tag + "unknown old material: AWAY goes on as before", sr_.pstate == "printing")

    # ---------- 11. remote + telegram keyboard ----------
    s = start(kin, macros)
    set_cfg(s, "tg_bot", 1); set_cfg(s, "auto_continue_min", 5)
    s.cmd(SWAP)
    s.fire("_CS_ALERT_SEND"); s.fire("_CS_TG_SEND"); s.fire("_CS_BEEP_RUN")
    check(tag + "telegram keyboard sent", any(l.startswith("RESPOND PREFIX=tgcustom_keyboard") and "CS_KEEP" in l for l in s.log), [l for l in s.log if "PREFIX" in l])
    check(tag + "notifier called", any(l.startswith("REMOTE notify") for l in s.log))
    for c_ in ("CS_STATUS", "CS_WAIT", "CS_UNLOAD", "CS_LOAD", "CS_PURGE", "CS_STATUS", "CS_CONTINUE", "CS_STATUS", "TEST_ALERT"):
        s.cmd(c_)
    check(tag + "remote: unload, load, purge, continue", s.pstate == "printing" and cs(s)["swaps"] == 1)
    s = start(kin, macros); set_cfg(s, "auto_unload", 0); s.cmd(SWAP); s.cmd("CS_KEEP")
    check(tag + "remote: CS_KEEP", s.pstate == "printing")
    s = start(kin, macros); s.cmd(SWAP); s.cmd("CS_CANCEL")
    check(tag + "remote: CS_CANCEL", s.pstate == "cancelled" and cs(s)["state"] == 0)

    # ---------- 12. bowden lengths are split ----------
    s = start(kin, macros)
    set_cfg(s, "unload_mm", 700); set_cfg(s, "load_mm", 700); set_cfg(s, "purge_pulse_mm", 0)
    s.cmd(SWAP); s.cmd("_CS_LOAD")
    check(tag + "bowden 700 mm split into <= 50 mm moves", cs(s)["state"] == 2)

    # ---------- 13. re-home during a swap ----------
    s = start(kin, macros)
    s.cmd(SWAP); s.cmd("_CS_REHOME")
    check(tag + "rehome returns to the park point", abs(s.pos[1] - exp_py) < 0.01 and s.pos[2] >= 13, s.pos)

    # ---------- 14. new job detection without hooks ----------
    s = start(kin, macros)
    s.cmd(SWAP); s.cmd("_CS_LOAD"); s.cmd("_CS_CONFIRM"); s.cmd("_CS_CONTINUE")
    s.pstate = "complete"; s.fire("_CS_AUTOSAVE")
    check(tag + "complete: checkpoint cleared, summary", cs(s)["done"] == 1 and s.saved.get("cs_resume") in (0, None) and any("Color swaps in this print: 1" in l for l in s.log))
    s.pstate, s.duration, s.e, s.target = "printing", 3.0, -2.0, 215.0
    s.cmd("COLOR_SWAP SLOT=2 MATERIAL=PETG OLD_MATERIAL=PLA TEMP=240 OLD_TEMP=215 RETRACT=2")
    check(tag + "same file printed again: new job, main = PLA, default purge 50+15", cs(s)["main_material"] == "PLA" and cs(s)["done"] == 0 and abs(cs(s)["purge_total"] - 65) < 0.01, (cs(s)["main_material"], cs(s)["purge_total"]))

    # ---------- 15. v6.4: no KlipperScreen popup on top of an open window ----------
    # A popup ("echo:" or "!!" line) that opens while a swap window is shown hides the
    # window behind the normal screen and holds every touch until the window closes
    # (seen on the printer 2026-11-15, -19 and -20). Windows must come AFTER messages.
    def popups_over_window(sim):
        bad_, open_ = [], False
        for l in sim.log:
            if "action:prompt_show" in l:
                open_ = True
            elif "action:prompt_end" in l:
                open_ = False
            elif open_ and l.startswith("RESPOND") and "PREFIX=" not in l and "TYPE=command" not in l:
                bad_.append(l)
        return bad_
    flows = []
    s = start(kin, macros); s.cmd(SWAP); s.fire("_CS_SWAP_CHECKPOINT") if "_CS_SWAP_CHECKPOINT" in s.timers else None
    for c_ in ("_CS_SET_MATERIAL MATERIAL=PETG", "_CS_UNLOAD", "_CS_CONTINUE", "_CS_LOAD", "_CS_PURGE_MORE MM=15", "_CS_REHOME",
               "COLOR_SWAP_SETTINGS", "_CS_SET_ADJ K=reprime_mm D=0.5 G=5 P=2 E=1", "_CS_SET_CLOSE", "CS_STATUS", "_CS_CONFIRM", "_CS_BACK"):
        s.cmd(c_)
    s.tick(40)
    flows.append(s)
    s = start(kin, macros, home=False); s.cmd(SWAP); s.fire("_CS_SWAP_CHECKPOINT"); s.cmd("CS_WAIT"); s.tick(70)
    flows.append(s)
    s = start(kin, macros, home=False); s.cmd(SAME); s.fire("_CS_SWAP_CHECKPOINT"); s.tick(31)
    flows.append(s)
    bad_lines = sum((popups_over_window(f) for f in flows), [])
    check(tag + "no popup message while a swap window is open", not bad_lines, bad_lines[:5])
    s = start(kin, macros); s.cmd(SWAP)
    try:
        s.cmd("RESUME")
    except Raise:
        pass
    if kin == "delta":             # only RESUME macros with the _COLOR_SWAP_ON_RESUME hook refuse
      check(tag + "RESUME refused: the window comes back AFTER the error", s.timers.get("_CS_REPROMPT") == 0.5 and not popups_over_window(s))
      s.fire("_CS_REPROMPT")
      check(tag + "RESUME refused: reprompt shows the swap window", any("Load + purge|_CS_LOAD" in b for t, b in s.prompt()))

    # ---------- 16. v6.4: never wait for the nozzle to cool down ----------
    s = start(kin, macros)        # PETG 240 -> PLA 215 (cooler)
    s.cmd(SWAP); s.cmd("_CS_LOAD"); s.cmd("_CS_PURGE_MORE MM=15"); s.cmd("_CS_CONFIRM"); s.cmd("_CS_CONTINUE")
    waits = [l for l in s.log if l.startswith("TEMPERATURE_WAIT")]
    check(tag + "no wait for a cool-down (no MAXIMUM), heating still waited for", waits and not any("MAXIMUM" in l for l in waits) and s.pstate == "printing", waits)
    check(tag + "cooler filament: target drops at once, settle push kept", any(l == "M104 S215.0" for l in s.log) and not any("M106 S255" in l for l in s.log), [l for l in s.log if l.startswith(("M104", "M106"))])
    s = start(kin, macros, home=False); s.target = 215.0   # AWAY, PLA 215 -> PETG 240 (hotter)
    s.cmd("COLOR_SWAP SLOT=1 MATERIAL=PETG OLD_MATERIAL=PLA TEMP=240 OLD_TEMP=215 RETRACT=2 PURGE=40")
    check(tag + "AWAY: no preheat to the new filament while it may keep the old one", s.target == 215.0 and cs(s)["unloaded"] == 0, s.target)
    s.cmd("_CS_UNLOAD")
    check(tag + "AWAY: Unload starts heating for the new filament", s.target == 240.0 and cs(s)["unloaded"] == 1, s.target)
    s = start(kin, macros, home=False); s.target = 215.0
    s.cmd("COLOR_SWAP SLOT=1 MATERIAL=PETG OLD_MATERIAL=PLA TEMP=240 OLD_TEMP=215 RETRACT=2 PURGE=40")
    s.cmd("_CS_CANCEL_MENU"); s.cmd("_CS_CANCEL_PRINT UNLOAD=1")
    check(tag + "cancel + unload: heats for the filament IN the nozzle (215), not the next (240)",
          any(l.startswith("TEMPERATURE_WAIT") and "MINIMUM=212" in l for l in s.log) and not any("MINIMUM=237" in l for l in s.log),
          [l for l in s.log if l.startswith("TEMPERATURE_WAIT")])

    # ---------- 17. v6.4: phone messages carry their kind ----------
    s = start(kin, macros); s.cmd(SWAP); s.fire("_CS_ALERT_SEND")
    check(tag + "alert reaches the notifier as KIND|text", any(l.startswith("REMOTE notify") and "swap|Color swap" in l for l in s.log), [l for l in s.log if l.startswith("REMOTE")])

# ---------- 18. v6.4 START_PRINT (V400 macros): no settle waits ----------
s = Sim([V400, CS], kin="delta"); s.fire("_CS_BOOT")
s.cmd("START_PRINT BED_TEMP=80 EXTRUDER_TEMP=250 MESH=0")
check("[delta] START_PRINT: bed wait ends 3 C below, nozzle 3 C below, no M190 / M109",
      "TEMPERATURE_WAIT SENSOR=heater_bed MINIMUM=77.0" in s.log and "TEMPERATURE_WAIT SENSOR=extruder MINIMUM=247.0" in s.log
      and not any(l.startswith(("M190", "M109")) for l in s.log), [l for l in s.log if "WAIT" in l or l.startswith(("M1",))])
s.target = 250.0
s.cmd("UNLOAD_FILAMENT TEMP=220")
check("[delta] UNLOAD_FILAMENT: hotter nozzle unloads at once (target kept, no M109)",
      s.target == 250.0 and not any(l.startswith("M109") for l in s.log), s.target)

# ---------- 19. v6.4: the KlipperScreen Unload / Load buttons go through a waiting swap ----------
s = start("delta", V400, home=False); s.cmd(SWAP)
s.cmd("UNLOAD_FILAMENT")
check("[delta] UNLOAD_FILAMENT during a swap = the swap's Unload (it knows the filament is out)",
      cs(s)["unloaded"] == 1 and cs(s)["state"] == 1 and any("Load + purge|_CS_LOAD" in b for t, b in s.prompt()))
s.cmd("LOAD_FILAMENT")
check("[delta] LOAD_FILAMENT during a swap = the swap's Load + purge", cs(s)["state"] == 2)
s.cmd("UNLOAD_FILAMENT")
check("[delta] UNLOAD_FILAMENT after the purge only shows the swap window", cs(s)["state"] == 2 and any("_CS_CONFIRM" in b for t, b in s.prompt()))
# ---------- 20. v6.4: with the Telegram panel the notifier stays quiet ----------
s = start("delta", V400); set_cfg(s, "tg_panel", 1); s.cmd(SWAP); s.fire("_CS_ALERT_SEND")
check("[delta] tg_panel 1: no notifier call, console line for the panel",
      not any(l.startswith("REMOTE notify") for l in s.log) and any('MSG="cs_alert swap|' in l for l in s.log))

# ---------- 21. v6.4: continue from where a cancelled print stopped ----------
s = start("delta", V400)
s.fire("_CS_AUTOSAVE")
check("[delta] autosave point at 12345", (s.saved.get("cs_resume") or {}).get("pos") == 12345, s.saved.get("cs_resume"))
s.fpos = 20000; s.pos = [12.0, -8.0, 4.4]
s.cmd("CANCEL_PRINT")
sp = s.saved.get("cs_stop") or {}
check("[delta] cancel while printing: stop point with the print temperature (taken before the heaters go off)",
      sp.get("pos") == 20000 and sp.get("kind") == "stop" and sp.get("temp") == 240.0 and abs(sp.get("z", 0) - 4.4) < 1e-6, sp)
check("[delta] cancel keeps the older save point too", (s.saved.get("cs_resume") or {}).get("pos") == 12345)
s.cmd("RESUME_SAVED_PRINT")
lbl = [b_ for t, b_ in s.prompt()]
check("[delta] resume window offers: from where it stopped / from the save point",
      any("From where it stopped" in b_ and "_CS_RS_USE_STOP" in b_ for b_ in lbl) and any("Start from the save point|_CS_RS_PREP" in b_ for b_ in lbl), lbl)
s.cmd("_CS_RS_USE_STOP")
check("[delta] chosen: the stop point becomes the resume point, no second choice left",
      s.saved["cs_resume"].get("pos") == 20000 and s.saved["cs_stop"] == 0 and not any("_CS_RS_USE_STOP" in b_ for t, b_ in s.prompt()))
s.cmd("_CS_RS_PREP"); s.cmd("_CS_RS_UNLOAD"); s.cmd("_CS_RS_LOAD"); s.cmd("_CS_RS_CONFIRM"); s.cmd("_CS_RS_GO")
check("[delta] the file continues at the stop position (M26 S20000), at Z 4.4 with no lift", "M26 S20000" in s.log and any(l.startswith("G1 Z4.4 ") for l in s.log), [l for l in s.log if l.startswith(("M26", "G1 Z"))][-3:])
s = start("delta", V400); s.cmd(SWAP); s.fpos = 30000; s.cmd("CANCEL_PRINT")
check("[delta] cancel during a swap: no stop point (the swap point is the place)", not isinstance(s.saved.get("cs_stop"), dict))
s = start("delta", V400); s.fpos = 500; s.cmd("CANCEL_PRINT"); s.pstate = "standby"
s.cmd("RESUME_SAVED_PRINT")
check("[delta] a stop point alone is offered as the resume point", any("where it was cancelled" in b_ for t, b_ in s.prompt()), s.prompt())
s.pstate = "printing"; s.cmd("START_PRINT BED_TEMP=80 EXTRUDER_TEMP=250 MESH=0")
check("[delta] a new print forgets the stop point", s.saved.get("cs_stop") == 0)

bad = [r for r in results if not r[1]]
print("\n%d checks, %d failed" % (len(results), len(bad)))
for r in bad:
    print("  FAILED:", r[0], r[2])
