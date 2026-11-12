"""Tiny Klipper macro simulator: parses the cfg files the way Klipper does, renders
every gcode_macro with Klipper's Jinja settings and runs them against a fake printer."""
import ast, configparser, json, re, shlex, sys, copy
import jinja2


class Raise(Exception):
    pass


def read_cfg(paths):
    text = ""
    for p in paths:
        lines = open(p, encoding="utf-8").read().split("\n")
        out = []
        for line in lines:
            pos = line.find("#")
            if pos >= 0:
                line = line[:pos]
            out.append(line)
        text += "\n".join(out) + "\n"
    cp = configparser.RawConfigParser(strict=False, inline_comment_prefixes=(";", "#"))
    cp.read_string(text)
    return cp


class Sim:
    def __init__(self, paths, kin="delta", settings_extra=None):
        self.cp = read_cfg(paths)
        self.env = jinja2.Environment("{%", "%}", "{", "}", extensions=["jinja2.ext.do"])
        self.macros, self.vars, self.delayed = {}, {}, {}
        self.settings = {}
        for sec in self.cp.sections():
            low = sec.lower()
            self.settings[low] = {k: v for k, v in self.cp.items(sec)}
            if sec.startswith("gcode_macro "):
                name = sec.split(None, 1)[1].upper()
                try:
                    self.macros[name] = self.env.from_string(self.cp.get(sec, "gcode"))
                except Exception as e:
                    raise SystemExit("TEMPLATE ERROR in %s line %s: %s" % (name, getattr(e, "lineno", "?"), e))
                v = {}
                for opt in self.cp.options(sec):
                    if opt.startswith("variable_"):
                        lit = ast.literal_eval(self.cp.get(sec, opt))
                        json.dumps(lit)
                        v[opt[9:]] = lit
                self.vars[name] = v
            elif sec.startswith("delayed_gcode "):
                name = sec.split(None, 1)[1].upper()
                self.delayed[name] = self.env.from_string(self.cp.get(sec, "gcode"))
        self.kin = kin
        self.log = []          # every non-macro command, in order
        self.timers = {}
        self.e = 0.0           # net extruder position
        self.pos = [0.0, 0.0, 10.0]
        self.minz = 1e9
        self.absolute = True
        self.rel_e = True
        self.saved = {}
        self.paused = False
        self.pstate = "standby"
        self.target = 0.0
        self.depth = 0
        if kin == "delta":
            self.lo, self.hi, self.cone = (-152.0, -152.0, -5.0), (152.0, 152.0, 418.0), 368.0
            pr = {"kinematics": "delta", "print_radius": 152.0}
        else:
            self.lo, self.hi, self.cone = (0.0, 0.0, 0.0), (235.0, 235.0, 250.0), None
            pr = {"kinematics": kin}
        self.settings["printer"] = pr
        self.settings.setdefault("extruder", {})["max_extrude_only_distance"] = 50.0
        self.settings["idle_timeout"] = {"timeout": 1800.0}
        for k in ("tmc2209 stepper_a", "tmc2209 stepper_b", "tmc2209 stepper_c", "tmc2209 extruder"):
            self.settings[k] = {"run_current": 1.5, "hold_current": 0.5}
        self.settings["filament_switch_sensor filament_sensor"] = {}
        # as on the real printer: exclude_object has no options so Klipper leaves it out of
        # settings, and force_move is always listed with its switch off
        for k in ("pause_resume", "respond", "save_variables", "virtual_sdcard", "gcode_arcs"):
            self.settings.setdefault(k, {})
        self.settings["force_move"] = {"enable_force_move": False}
        if settings_extra:
            self.settings.update(settings_extra)
        self.filament = True
        self.objects = [{"name": "a", "polygon": [[-20, -20], [20, -20], [20, 20], [-20, 20]]}]
        self.filename = "test.gcode"
        self.duration = 100.0
        self.layer = 5
        self.homed = "xyz"

    # ---- fake printer status ----
    def status(self):
        th = {"position": D(x=self.pos[0], y=self.pos[1], z=self.pos[2]),
              "axis_minimum": D(x=self.lo[0], y=self.lo[1], z=self.lo[2]),
              "axis_maximum": D(x=self.hi[0], y=self.hi[1], z=self.hi[2]),
              "homed_axes": self.homed}
        if self.cone is not None:
            th["cone_start_z"] = self.cone
        st = {
            "toolhead": D(**th),
            "configfile": D(settings=self.settings),
            "print_stats": D(state=self.pstate, filename=self.filename, print_duration=self.duration,
                             info=D(current_layer=self.layer, total_layer=40)),
            "pause_resume": D(is_paused=self.paused),
            "extruder": D(target=self.target, temperature=self.target, can_extrude=self.target >= 170,
                          pressure_advance=0.03, smooth_time=0.04),
            "heater_bed": D(target=60.0),
            "fan": D(speed=0.8),
            "gcode_move": D(gcode_position=D(x=self.pos[0], y=self.pos[1], z=self.pos[2], e=self.e),
                            absolute_extrude=not self.rel_e, homing_origin=D(z=0.0),
                            speed_factor=1.0, extrude_factor=1.0),
            "virtual_sdcard": D(is_active=self.pstate == "printing", file_position=12345),
            "save_variables": D(variables=self.saved),
            "exclude_object": D(objects=self.objects, excluded_objects=[]),
            "bed_mesh": D(profile_name="default", profiles={"default": {}}),
            "idle_timeout": D(state="Printing"),
            "filament_switch_sensor filament_sensor": D(filament_detected=self.filament, enabled=True),
        }
        for name, v in self.vars.items():
            st["gcode_macro " + name] = D(**copy.deepcopy(v))
        return D(**st)

    def ctx(self, params, name=None):
        def raise_error(msg):
            raise Raise(msg)

        def respond_info(msg):
            self.log.append("// " + msg)
            return ""

        def remote(method, **kw):
            self.log.append("REMOTE %s %s" % (method, kw))
            return ""
        c = {"printer": self.status(), "params": params, "rawparams": "",
             "action_raise_error": raise_error, "action_respond_info": respond_info,
             "action_call_remote_method": remote}
        if name:
            c.update(copy.deepcopy(self.vars[name]))
        return c

    # ---- gcode execution ----
    def run(self, script):
        for line in script.split("\n"):
            line = line.split("#")[0].split(";")[0].strip()   # Klipper strips comments
            if line:
                self.cmd(line)

    def cmd(self, line):
        parts = line.split(None, 1)
        name = parts[0].upper()
        rest = parts[1] if len(parts) > 1 else ""
        params = {}
        if re.match(r"^[A-Z_][A-Z0-9_]*$", name) and not re.match(r"^[GM]\d+$", name) or name in self.macros:
            try:
                for a in shlex.split(rest):
                    if "=" not in a:
                        raise ValueError("bad arg %r in %r" % (a, line))
                    k, v = a.split("=", 1)
                    params[k.upper()] = v
            except ValueError as e:
                if name not in ("M23",):
                    raise Raise("PARSE %s: %s" % (line, e))
        if name in self.macros:
            # Klipper refuses a macro that is already running ("called recursively")
            self.stack = getattr(self, "stack", [])
            if name in self.stack:
                raise Raise("Macro %s called recursively (stack %s)" % (name, self.stack))
            self.stack.append(name)
            try:
                out = self.macros[name].render(self.ctx(params, name))
                self.run(out)
            finally:
                self.stack.pop()
            return
        self.builtin(name, rest, params, line)

    def builtin(self, name, rest, params, line):
        self.log.append(line)
        if name == "SET_GCODE_VARIABLE":
            m = params["MACRO"].upper()
            assert m in self.vars, "unknown macro " + m
            assert params["VARIABLE"] in self.vars[m], "unknown variable %s.%s" % (m, params["VARIABLE"])
            lit = ast.literal_eval(params["VALUE"])
            json.dumps(lit)
            self.vars[m][params["VARIABLE"]] = lit
        elif name == "SAVE_VARIABLE":
            self.saved[params["VARIABLE"]] = ast.literal_eval(params["VALUE"])
        elif name == "UPDATE_DELAYED_GCODE":
            assert params["ID"].upper() in self.delayed, "unknown delayed " + params["ID"]
            self.timers[params["ID"].upper()] = float(params["DURATION"])
        elif name in ("G1", "G0", "G3"):
            w = dict((a[0].upper(), float(a[1:])) for a in rest.split())
            if "E" in w:
                assert abs(w["E"]) <= 50.0001, "extrude move too long: " + line
                self.e = self.e + w["E"] if self.rel_e else w["E"]
            for i, ax in enumerate("XYZ"):
                if ax in w:
                    self.pos[i] = w[ax] if self.absolute else self.pos[i] + w[ax]
            assert self.lo[0] - 1e-6 <= self.pos[0] <= self.hi[0] + 1e-6, "X out of range: " + line
            assert self.lo[1] - 1e-6 <= self.pos[1] <= self.hi[1] + 1e-6, "Y out of range: " + line
            if self.kin == "delta":
                assert (self.pos[0] ** 2 + self.pos[1] ** 2) ** 0.5 <= 152.001, "outside radius: " + line
            self.minz = min(self.minz, self.pos[2])
        elif name == "G90":
            self.absolute = True
        elif name == "G91":
            self.absolute = False
        elif name == "M83":
            self.rel_e = True
        elif name == "M82":
            self.rel_e = False
        elif name == "G28":
            self.homed = "xyz"
            if self.kin == "delta":
                self.pos = [0.0, 0.0, self.hi[2]]
        elif name in ("M104", "M109"):
            self.target = float(rest.strip()[1:])
        elif name == "PAUSE_BASE":
            self.paused, self.pstate = True, "paused"
            self.pause_pos = (list(self.pos), self.e)
        elif name == "RESUME_BASE":
            assert self.paused
            self.paused, self.pstate = False, "printing"
            self.pos = list(self.pause_pos[0])
        elif name == "CANCEL_PRINT_BASE":
            self.paused, self.pstate = False, "cancelled"
        elif name in ("RESPOND", "TEMPERATURE_WAIT", "SET_IDLE_TIMEOUT", "SET_TMC_CURRENT", "SET_FILAMENT_SENSOR",
                      "M106", "M107", "M140", "M190", "M400", "G4", "G92", "G21", "M23", "M24", "M26", "M220", "M221",
                      "SET_PRESSURE_ADVANCE", "SET_GCODE_OFFSET", "_SET_GCODE_OFFSET", "BED_MESH_PROFILE", "BED_MESH_CLEAR",
                      "SET_PRINT_STATS_INFO", "SET_PIN", "SDCARD_RESET_FILE", "EXCLUDE_OBJECT", "SET_KINEMATIC_POSITION",
                      "NEOPIXEL_GREEN", "SAVE_GCODE_STATE", "RESTORE_GCODE_STATE", "BED_MESH_CALIBRATE"):
            pass
        else:
            raise Raise("UNKNOWN COMMAND: " + line)

    def fire(self, timer):
        timer = timer.upper()
        self.timers.pop(timer, None)
        self.run(self.delayed[timer].render(self.ctx({})))

    def tick(self, n=1):
        for _ in range(n):
            if self.timers.get("_CS_TICK", 0) > 0:
                self.fire("_CS_TICK")

    def prompt(self):
        """Buttons of the last prompt shown."""
        out, started = [], False
        for l in reversed(self.log):
            if "action:prompt_show" in l:
                started = True
                continue
            if started:
                if "action:prompt_end" in l:
                    break
                m = re.search(r'MSG="action:(prompt_\w+) ?(.*)"', l)
                if m:
                    out.append((m.group(1), m.group(2)))
        return list(reversed(out))


class D(dict):
    """dict with attribute access, like Klipper's status objects in Jinja."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
    def __getattr__(self, k):
        try:
            return self[k]
        except KeyError:
            raise AttributeError(k)
