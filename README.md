**English** | [العربية](README.ar.md)

# Multi-color printing on a single-extruder printer — FLSUN V400 (version 5)

**One** print file. Whenever the print needs a new color, the printer pauses on its own and a window appears on the screen.
You swap the filament, press a button, and the print continues.

> 🎬 **Tutorial video (2 minutes, Arabic):** [`video/COLOR_SWAP_tutorial_AR_v2.mp4`](video/COLOR_SWAP_tutorial_AR_v2.mp4)
> Recorded on **version 2**: the install steps are the same, but some buttons have changed (Continue is now on the left, and the purge buttons are now 15 / 30 / 60 mm). This file is the correct reference.

Installation: [`INSTALL.md`](INSTALL.md)

## What's new in version 5 (2026-11-06)

| Problem | Fix |
|---|---|
| No resume after a power cut unless the Orca line was added | **Autosave every minute** from Klipper itself, for every print and every profile. When the printer is switched on after a power cut, **the resume window opens on its own** |
| The head flick after a swap is not needed | **Removed** (`flick: 0`) |
| A second tap where Load + purge was pressed Continue print by mistake | While work runs, the window has **no buttons**. Continue is now on the **left** and asks a second time. The Load + purge spot is now a **Purge** button only |
| The skirt is broken at the start | `START_PRINT` retracted 1 mm after the prime line and nothing restored it. **The retraction is removed**. The skirt itself is **turned off** in the Orca profile `0.20mm FLSun V400 -COLOR_SWAP` (`Skirt loops = 0`); add it yourself when you need it |
| Going back to the main filament after the support filament needed +60 mm by hand | **+60 mm automatically** (`purge_to_main_extra`), and the purge runs in **pulses** that sweep out the old filament |
| The new color starts badly on the first layer (small letters) | **First layer only**: a short wipe line on the bed edge after every swap |

## What's new in version 4 (2026-11-05)

| Problem | Fix |
|---|---|
| A light push while inserting filament moves the head, and it loses its position | During a swap the motors hold the head at full print current (1.5 A instead of 0.5 A = three times the force) |
| The head moved anyway | **Head moved? Re-home** button in the swap window: the head goes **up** (Home), then back to the purge spot. Continue returns to exactly the right point |
| No way to resume a print that was cancelled at a filament change | A save point at every color swap + a **Resume saved** button |
| Power cut | A save point at the start of every layer, stored on the printer's disk (survives a power cut) |

## What's new in version 3 (2026-11-05)

| Problem in version 2 | Fix in version 3 |
|---|---|
| The wipe line lowered the head to Z 0.3 next to the model → collision risk | **Wipe line removed**. The head never goes below the height of the layer where it paused |
| Many moves after the purge before printing | After Continue: a tiny purge + a side flick + return **in one straight, fast move** |
| The new color starts with broken lines | The nozzle is primed right before returning, the return is fast (250 mm/s instead of 50), and `RESUME` no longer pushes 1 mm at the purge spot |
| Purge failed when mixing PETG and PLA | The purge runs at the **higher** temperature (so the old plastic melts), then cools, then a short purge at the new temperature |
| Loading pushed fast into the nozzle | The last 15 mm of the load are slow (3 mm/s) |
| Delay after pressing Load + purge | Heating starts **before** the old filament is unloaded. `M109` (waits until the temperature settles within ±1°C, 10–40 s extra) is replaced with a wait that ends as soon as the temperature is within ±3°C |
| Purge amount too large | The amount comes from **Orca's Flushing volumes table** based on the colors (usually 25–42 mm instead of 100) |
| No cancel | A **Cancel...** button in every window, with the option to unload the filament while hot |
| Closing the window = no way to reopen it | A **Color swap** button in KlipperScreen's print menu, or the `COLOR_SWAP_PROMPT` macro in Mainsail |
| Clogs from pulling cold filament | Every unload **waits for the nozzle to heat**. `UNLOAD_FILAMENT` is fixed (it used to pull while cooling) |

---

## Part 1 — OrcaSlicer setup (once)

> Type each setting's name into the **search box** in the settings. If it does not appear, turn on **Advanced**.

1. **Printer settings** → **Change filament G-code** → clear it and paste this line exactly (one line):
   ```
   {if layer_num >= 0}COLOR_SWAP SLOT={next_extruder + 1} MATERIAL={filament_type[next_extruder]} OLD_MATERIAL={filament_type[previous_extruder]} TEMP={new_filament_temp} OLD_TEMP={old_filament_temp} RETRACT={new_retract_length_toolchange} PURGE={flush_length}{endif}
   ```
2. **Bed temperature** → search for `bed temperature` → choose **By First filament** (instead of **By Highest Temp**).
   The bed then stays at the temperature of the first filament for the whole print. The macro itself never changes the bed temperature.
3. **🆕 Save points (for power cuts)** → **Printer settings** → **Machine G-code** → **Before layer change G-code** →
   add this line **at the end** (keep the existing lines):
   ```
   _CS_CHECKPOINT LAYER={layer_num + 1} TOTAL={total_layer_count} SLOT={current_extruder + 1} MATERIAL={filament_type[current_extruder]}
   ```
   The full content is in `orca_before_layer_change_gcode.txt`. It can be added to any printer profile, even for single-color prints.
   > If Orca shows an error when slicing because of this line: delete the `SLOT=…` and `MATERIAL=…` parts and keep the rest.
4. Save the printer profile and the process profile.

The other settings stay as in version 2: **Manual filament change** ✔, **Prime tower** off,
**Exclude objects** ✔ and **Label objects** ✔.

### Purge amount

The **Flushing volumes** button in the Filament panel (above the filaments) shows the table. Orca computes the amount from the two colors.
The macro takes it and applies:

| Rule | Value |
|---|---|
| Minimum | 25 mm (≈ 60 mm³) |
| Maximum | 250 mm |
| Added when the **type** changes (PLA ↔ PETG) | +15 mm |
| 🆕 Added when **going back to the main filament** (e.g. PLA supports → PETG) | +60 mm |
| No number from Orca | 50 mm (the Marlin default, ≈ 120 mm³ like Prusa) |

Example: PLA → PETG (back to the main filament) = 25 + 15 + 60 = **100 mm**, in 5 pulses of 20 mm each.

The "main filament" is the one the print **started** with (the old filament at the first swap), not a fixed type.
If a print starts with PLA, the +60 is added when going back to PLA.

**🆕 To change the +60 by hand:** `color_swap.cfg` → line 87:
```
variable_purge_to_main_extra: 60
```
Change the number → Save & Restart. (Line 81 `purge_material_change` = the amount added when the type changes; line 94 `purge_pulse_mm` = pulse size, 0 = no pulses.)

> For comparison: Bambu users report about 800 mm³ (≈ 330 mm) for a PLA → PETG change. If the layer is still brittle after the change, raise the number to 120–200.

---

## Part 2 — During the print

The printer lifts the head **up first**, then moves to the front edge and unloads the old filament while hot.

### Window 1: "Color swap - load filament 2"

1. Pull out the old filament.
2. Insert the new filament.
3. Press **Load + purge**.

| Other button | When |
|---|---|
| **PLA 215C** / **PETG 240C** | The new filament is a different type from the one in the file |
| **Unload again** | The old filament did not come out |
| **Cancel...** | You want to cancel the print |

### Window 2: "Color swap - check the purge"

> 🆕 While loading and purging, a window **with no buttons** appears ("please wait"). Wait until it closes.

4. Look at the filament coming out: is the color mixed? Press **Purge +15**, **+30** or **+60** (or the **Purge +30mm** button at the bottom right).
5. **Cut** the strand at the nozzle with tweezers. Do not pull it hard (pulling empties the nozzle, and the lines start broken).
6. Press **Continue...** (bottom **left**) → then **Yes, continue print**. What happens next:
   1. A tiny purge (1.5 mm) to fill the nozzle.
   2. 🆕 **First layer only:** a short wipe line (a 10 cm arc) on the front-right edge of the bed, at 0.3 mm height.
      Each swap on the first layer draws its line 1.2 mm further in. It is skipped, with the reason shown, if the model is closer than 10 mm to the line.
   3. Return in one straight, fast move to the print position.

| Bottom buttons (version 5) | Left | Middle | Right |
|---|---|---|---|
| Window 1 | Cancel... | Unload again | **Load + purge** |
| Window 2 | **Continue...** (asks a second time) | Cancel... | Purge +30mm |
| The question | Back | — | **Yes, continue print** |

Two taps in a row on the same spot never continue the print.

### I closed the window

- **KlipperScreen**: print screen → **Menu** → **Color swap**.
- **Mainsail**: the **COLOR_SWAP_PROMPT** macro button.

### 🆕 The head moved while I was inserting the filament

1. Press **Head moved? Re-home** (it is in both windows).
2. The head goes all the way up, then comes down from the **center** to the purge height, then moves to the front edge.
3. Finish the swap as usual. **Continue print** returns to the correct point.

> Tip: hold the extruder body with your other hand while you push the filament.

---

## 🆕 Part 3 — Resuming a stopped print

Works after: a **cancel** at a color swap, a **moved head** followed by a cancel, or a **power cut**.

### Before you start — check with your eyes

| Condition | Why |
|---|---|
| The part is still stuck to the bed and has not moved | The print continues on top of it at the same coordinates |
| The nozzle is not touching the part | After a power cut the head may drop. Lift it gently by hand (the motors are off) |
| The file is still on the printer with the same name | The printer continues from the same file |

### Steps (10–15 minutes, mostly heating)

1. 🆕 **After a power cut:** switch the printer on and wait one minute; the window opens **on its own**.
   In the other cases: **KlipperScreen** → home screen → **Resume saved** (or in **Mainsail**: the **RESUME_SAVED_PRINT** macro).
2. A window shows the file name, the layer and the Z height. Press **Start**.
   - The printer heats the bed, goes **up** (Home), then comes down from the center to the front edge, and heats the nozzle.
3. A **Resume - filament N** window appears:
   - The right filament is loaded? → **Purge +15mm** until it comes out clean.
   - A different filament, or none? → **Unload** → insert the right filament → **Load + purge**.
4. **Cut** the strand at the nozzle with tweezers.
5. Press **Continue...** (bottom left) → **Yes, continue print**. The head moves **above** the part to the saved point, then goes straight down, then continues the file.

| Other button | What it does |
|---|---|
| **Delete point** | Deletes the save point |
| **Cancel resume** (in step 3) | Turns the heaters off and lifts the head. The point stays saved |

### Where are the points saved?

| When | Where it resumes from |
|---|---|
| 🆕 **Every minute while printing** (automatic, every profile) | About the same line: less than a minute is lost |
| Start of every layer (the Orca line in Part 1, step 3: now optional) | The start of the layer |
| At every color swap (automatic) | Right after the swap, in the new color |
| Start of a new print / successful end of a print | The point is deleted |
| Print cancelled | The point **stays** (so you can resume later) |

### Limits you should know

- **Whatever was printed in the last minute before the stop is printed a second time on top of itself.** A small mark in one spot.
- 🆕 **The once-a-minute save point can fall during a retraction:** the first line after resuming may come out with a small blob (0.8 mm of extra filament). No risk to the part.
- **After a power cut the bed cools down.** The part may come loose. Do not continue if it moved.
- **A file in a subfolder, or with quotes in its name → no save points.** Upload files to the root folder.
- **Height above 368 mm → no resume** (there is no room to purge beside the part up there).
- If the power is cut **while** a save point is being written (a fraction of a second), Klipper may refuse to start with the message `Unable to parse existing variable file`.
  Fix: Mainsail → **Machine** → open `variables.cfg` → delete the line that starts with `cs_resume` → **Save & Restart**.

### Cancelling

Press **Cancel...**:

| When | Buttons |
|---|---|
| Before loading | **Cancel print** — the old filament is out of the nozzle, you can pull it by hand |
| After loading | **Cancel print** — the filament stays in the nozzle. **Do not pull it while cold**; use `UNLOAD_FILAMENT` later (it heats first) |
|  | **Unload hot + cancel** — unloads the filament while hot, then cancels |
|  | **Back to the swap** — go back |

---

## 🆕 Part 4 — Alerts (phone + buzzer)

A message arrives at every stage that needs you:

| When | Message |
|---|---|
| Color swap: the old filament is out | `Color swap: insert filament 2 PLA, then press Load + purge` |
| Purge finished | `Purge done: check the color, cut the strand, then Continue` |
| Resume ready | `Resume ready: ...` |
| Printer switched on with an unfinished print saved | `Printer started with an unfinished print saved ...` |
| Filament runout / M600 | `Filament runout or M600: printer paused ...` |
| Print finished / error / cancelled | `Print complete: file name` (from Moonraker) |

The messages are sent from a separate timer: if sending fails (no internet, for example) **the print is not affected**.

### Turning on phone messages — Telegram (10 minutes, once)

1. In Telegram search for **@BotFather** → `/newbot` → choose a name, then a username that ends in `bot` → copy the **token** (numbers, then `:`, then letters).
2. Open your new bot → **Start** → send it any message (a bot cannot start a chat with you).
3. In a browser open `https://api.telegram.org/bot<TOKEN>/getUpdates` (the word `bot` directly followed by the token, no space or `/`).
   Find `"chat":{"id":` → the number after it is your **CHAT_ID**. If `"result":[]` is empty, send the bot another message and refresh.
4. Mainsail → **Machine** → `moonraker.conf` → end of the file → replace `BOT_TOKEN` and `CHAT_ID`:
   ```
   url: tgram://BOT_TOKEN/CHAT_ID
   ```
   → make sure the printer is **not printing** → **Save & Restart**.
5. Type in the Console: `TEST_ALERT` → a test message arrives.

> The token is a secret: do not share it. Lost it? @BotFather → `/mybots` → your bot → **API Token**. To stop the messages: `variable_notify_name: ""` in `color_swap.cfg`.

### Buzzer on the board

Needs a part fitted inside the printer. The macro is ready: it beeps 3 times at the same stages,
**and never beeps while actually printing** (so it leaves no mark on the part).

| Item | Details |
|---|---|
| Part | **Active buzzer module** with three pins (VCC, GND, I/O), works on 3.3–5V, e.g. KY-012 |
| Board | A modified version of the MKS Robin Nano v2.1; its connectors differ from the original. No published pin can be trusted |
| Needed before fitting | A clear photo of the mainboard to choose a safe free pin |
| After fitting | Add an `[output_pin beeper]` section in `printer.cfg` with the right pin, then `TEST_ALERT` |

---

## Safety: does the head go below the layer height?

**No.** All the swap moves:

| Move | Direction |
|---|---|
| Pause (`PAUSE`) | Up first (at least 10 mm above the layer, and not lower than Z 60), then forward |
| Load, purge, flick | Filament only, or left/right — no Z move |
| Return (`RESUME`) | One line to the point where Orca paused = the layer + Orca's lift (0.5 mm). Every point on the line is above the model |
| 🆕 **Re-home** and **Start** when resuming | `G28`: the towers go up to the switches at the top — away from the bed. Then straight down from the **center** to the purge height (at least 10 mm above the part), then to the edge |
| 🆕 **Continue print** when resuming | Sideways at the purge height (above the part), then straight down to the saved point: swap point = the layer + 0.5 mm, layer point = top of the last layer + 0.5 mm |

Verified by simulating the macro (6 cases): lowest Z = the Z at the pause for a swap, and the saved Z + 0.5 when resuming from a layer.

### ⚠ Warning

**Do not leave the printer paused for more than an hour.** After that Klipper turns off the motors and heaters,
the printer loses the head position, and the print cannot be finished. And do not pull the filament after that while it is cold.

---

## Technical details

### Files

| File | Contents |
|---|---|
| `color_swap.cfg` | The macro, windows and settings, head lock, save points and resume |
| `FLSUN_V400/macros.cfg` | `RESUME` (skips the 1 mm push and returns fast after a swap), `CANCEL_PRINT`, `UNLOAD_FILAMENT`/`LOAD_FILAMENT` with forced heating, and `START_PRINT`/`END_PRINT` that delete the save point |
| `FLSUN_V400/KlipperScreen.conf` | **Color swap** button in the print menu, and 🆕 **Resume saved** button on the home screen |
| `orca_change_filament_gcode.txt` | Orca line for the color swap |
| 🆕 `orca_before_layer_change_gcode.txt` | Orca line for save points |
| `moonraker_notifier.txt` | Telegram section to paste at the end of `moonraker.conf` |
| `ROLLBACK_v4/` | Version 4 files, to go back |

The save point is a single variable `cs_resume` in `variables.cfg` on the printer.

### Filament accounting (no gap and no blob on resume)

| Stage | Filament |
|---|---|
| Before the swap | Orca retracts `RETRACT` (2 mm), and `PAUSE` retracts 1 mm |
| Unload | Push 3 mm + what was retracted → fast pull 13 mm → wait 3 s → pull the rest (Marlin's method to form a clean tip) |
| After the purge | Retract `hold` = the larger of `RETRACT` and 1 mm |
| Continue | Push `hold` + 1.5 → retract exactly `RETRACT` |
| Start of printing | Orca pushes `RETRACT` → the nozzle is exactly full |

### Settings — in `_COLOR_SWAP_CFG`

| Variable | Default | Meaning |
|---|---|---|
| `park_x / park_y / park_lift / park_min_z` | 0 / -140 / 10 / 60 | Purge spot and height |
| `unload_mm / unload_purge_mm / unload_dwell_ms` | 40 / 3 / 3000 | Unload |
| `load_mm / load_slow_mm` | 40 / 15 | Load (last 15 mm slow) |
| `purge_min / purge_max / purge_default` | 25 / 250 / 50 | Purge amount limits |
| `purge_material_change` | 15 | Added when the type changes |
| 🆕 `purge_to_main_extra` | 60 | Added when going back to the main filament (line 87) |
| 🆕 `purge_pulse_mm / purge_pulse_retract` | 20 / 2 | Pulsed purge (0 = one continuous purge) |
| `purge_speed` | 180 | 3 mm/s |
| `purge_buttons` | [15, 30, 60] | Extra purge buttons |
| `settle_mm` | 8 | Purge at the new temperature when cooling (PETG → PLA) |
| `reprime_mm` | 1.5 | Nozzle fill at Continue. Raise to 2–3 if the start is still weak |
| `flick / flick_mm` | **0** / 8 | Side flick (0 = off, the default in version 5) |
| `resume_speed` | 250 | Return speed, mm/s |
| `heat_band` | 3 | The wait ends when the temperature is within ± this number |
| `temp_pla / temp_petg` | 215 / 240 | Button temperatures |
| `wait_timeout` | 3600 | Seconds before the motors are turned off |
| 🆕 `hold_boost` | 1 | Head lock while waiting (0 = off) |
| 🆕 `hold_steppers` | stepper_a/b/c | Motors that are locked |
| `resume_lift` | 0.5 | Stop height above the layer point before continuing the file |
| 🆕 `autosave_s` | 60 | Save the resume point every this many seconds (0 = off) |
| 🆕 `boot_prompt` | 1 | Open the resume window on its own after the printer starts |
| 🆕 `first_layer_wipe` | 1 | Wipe line on the first layer only (0 = off) |
| 🆕 `wipe_radius / wipe_step / wipe_z / wipe_margin` | 145 / 1.2 / 0.3 / 10 | Wipe line position, height, and safe distance from the model |
| 🆕 `notify_name` | phone | Moonraker notifier name for phone messages ("" = off) |

### Verified

- `PURGE` arrives from Orca: in a sliced file the values were `PURGE=43.155` and `PURGE=22.4506`.
- Bed temperature in the COLOR_SWAP profile = `by_first_filament`.
- Orca accepts the `_CS_CHECKPOINT` line: a file sliced on 2026-11-05 has 44 lines with correct filament numbers (layer 36: `SLOT=2 MATERIAL=PLA`).
- Version 4 installed on the printer on 2026-11-05: no warnings, calibration unchanged, the `RESUME_SAVED_PRINT` window appears.
- Telegram messages reach the phone (`TEST_ALERT`, 2026-11-06).

### Not verified yet

- The Re-home button and a full resume on a real print (tested in simulation only).

## License

MIT — see [`LICENSE`](LICENSE). Use and modify it freely, with credit.
