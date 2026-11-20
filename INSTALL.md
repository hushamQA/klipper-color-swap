**English** | [العربية](INSTALL.ar.md)

# Installing the COLOR_SWAP macro — on any Klipper printer

Version 6.3 — 2026-11-15 — written on a FLSUN V400 (Klipper v0.13, Mainsail v2.19, KlipperScreen, OrcaSlicer 2.4.2).
Delta, Cartesian, CoreXY and bed-slinger printers use the same `color_swap.cfg`.

> **Status of version 6.3:** installed on the FLSUN V400 on 2026-11-15 (config loads; the − buttons and the hidden lines checked on the printer), and run in a simulator (337 checks on a delta, a Cartesian and a CoreXY machine). Telegram panel 1.4: 84 checks.
> A **real color swap has not been printed with it yet**. Do the first swap on a small test model (`test/`) and stay next to the printer.
> The files in this package are byte-for-byte the ones on the printer.

## Contents

| File | What to do with it |
|---|---|
| `color_swap.cfg` | **The macro itself** — upload it on every printer |
| `FLSUN_V400/macros.cfg` and `FLSUN_V400/KlipperScreen.conf` | Ready-made files for the FLSUN V400 only |
| 🆕 `KlipperScreen_color_swap.conf` | The four KlipperScreen buttons, to paste into your own `KlipperScreen.conf` (other printers) |
| `orca_change_filament_gcode.txt` | OrcaSlicer line for the color swap |
| `orca_before_layer_change_gcode.txt` | OrcaSlicer line for save points (optional) |
| `moonraker_notifier.txt` | Phone messages (Telegram), pasted at the end of `moonraker.conf` |
| 🆕 `telegram_bot.txt` | Remote control from Telegram: install steps, `telegram.conf` and the command list |
| `README.md` / `README.ar.md` | Step-by-step usage (English / Arabic) |
| `INSTALL.md` / `INSTALL.ar.md` | This file (English / Arabic) |
| `test/` | Test model: a plate + the letter T |
| `ROLLBACK_v5.1/` | 🆕 The files of version 5.1 (to go back) |
| `SHA256SUMS.txt` | Checksum of every file |

---

## Case 1 — FLSUN V400 printer (10 minutes)

1. Open **Mainsail** → **Machine** (config files).
2. Make a backup: download `color_swap.cfg`, `macros.cfg`, `KlipperScreen.conf` and `printer.cfg` to your computer.
3. Upload `color_swap.cfg` in place of the existing one.
4. Upload `FLSUN_V400/macros.cfg` in place of the existing `macros.cfg`.
   > Both files must be changed **together**: version 6 expects `RESUME` to push its 1 mm (version 5 skipped it).
   > If your `macros.cfg` is your own, see "Updating from version 5" below instead.
5. `printer.cfg` must have `[include color_swap.cfg]` directly **below** `[include macros.cfg]` (already there if version 5 was installed).
6. Upload `FLSUN_V400/KlipperScreen.conf` in place of the existing one (it adds the **Color swap settings** button), then restart KlipperScreen.
7. Phone messages: `moonraker_notifier.txt` as before (nothing to change if version 5.1 already sends messages).
8. Make sure the printer is **not printing**, then press **Save & Restart**.
9. **Test** — type in the Console:
   ```
   COLOR_SWAP_CHECK
   ```
   It lists the printer limits, the park point, the sensor and the motors it found, and anything that is missing. Nothing moves.
   Then `COLOR_SWAP` must answer `COLOR_SWAP only works during a print.`

### Updating from version 5 with your own macros.cfg

Only two places changed in `macros.cfg`:

- **`RESUME`**: delete these three lines (the swap now retracts 1 mm more instead, so the push must stay):
  ```
  {% if swap %}
  {% set e = 0 %}
  {% endif %}
  ```
- **`M600`** (optional, for the runout window): see `M600` in `FLSUN_V400/macros.cfg` — the block that starts with `COLOR_SWAP RUNOUT=1`.

---

## Case 2 — another Klipper printer (15 minutes)

### 1. Sections in `printer.cfg`

```
[pause_resume]
[respond]
[virtual_sdcard]      (already there on every Mainsail / Fluidd install)
[save_variables]
filename: ~/printer_data/config/variables.cfg
[exclude_object]      (for the layer-1 wipe line)
[gcode_arcs]          (deltas only, for the layer-1 wipe line)
```

Add the ones you do not have.

### 2. Upload and include

Upload `color_swap.cfg` and add `[include color_swap.cfg]` to `printer.cfg`, **after** the include of your own macros (or `mainsail.cfg`).

### 3. Nothing to edit in the file

Version 6 works the printer out by itself:

| What | How |
|---|---|
| Park point | Bed centre in X (delta: 0), `park_edge` (12 mm) inside the front Y limit |
| Layer-1 wipe line | Delta: an arc inside the front-right limit. Others: a straight line along the front limit |
| Filament sensor | The first `[filament_switch_sensor]` / `[filament_motion_sensor]` found |
| Head lock | Every `stepper_*` that has a TMC `hold_current` |
| Long (bowden) loads | Split into pieces shorter than `max_extrude_only_distance` |

Everything else is changed on the screen: **Color swap settings** (step 6), or the macro `COLOR_SWAP_SETTINGS` in Mainsail.
For a bowden printer set **Printer setup → Filament path → Length pulled out / Length pushed in** to your tube length.

### 4. One value to check: what your RESUME pushes

The macro calls **your** `PAUSE` and **your** `RESUME`. Mainsail's and Fluidd's retract 1 mm at pause and push 1 mm at resume.
The setting **Printer setup → This printer → What RESUME pushes by itself** (`pause_retract_mm`, default 1) must be that number. Set it to 0 if your `RESUME` pushes nothing.

### 5. Hook lines (recommended, not required)

Without them the macro still works: it notices a cancel within 10 seconds and a new or finished print within a minute.
With them it is stricter (a `RESUME` pressed with no filament loaded is refused):

| Macro | Add | Where |
|---|---|---|
| `RESUME` | `_COLOR_SWAP_ON_RESUME` | first line of `gcode:` |
| `CANCEL_PRINT` | `_COLOR_SWAP_RESET` | before `CANCEL_PRINT_BASE` |
| `START_PRINT` / `PRINT_START` | `_CS_CLEAR_CHECKPOINT` | first line |
| `END_PRINT` / `PRINT_END` | `_CS_CLEAR_CHECKPOINT DONE=1` | last line |
| filament sensor | `runout_gcode: COLOR_SWAP_RUNOUT` | in the sensor section (runout opens the swap window) |

> If `RESUME` and `CANCEL_PRINT` come from `mainsail.cfg` / `fluidd.cfg` (not editable), copy the macro into your own file first.

### 6. KlipperScreen buttons

Open your `KlipperScreen.conf`, paste the content of `KlipperScreen_color_swap.conf` **above** the line
`#~# --- Do not edit below this line...`, and restart KlipperScreen.

### 7. Save & Restart, then check

```
COLOR_SWAP_CHECK
```

Read every line: the park point must be over the bed edge and away from where you print; "Missing sections" must say none.

### Not a delta? Read this about resuming after a power cut

`RESUME_SAVED_PRINT` must find the head position without touching the part.
A delta homes upward, so it always works. On other printers homing Z comes **down onto the part**, so:

| Situation | Result |
|---|---|
| The motors are still on (cancel at a swap, no restart) | Works: no homing at all |
| After a power cut or restart | Refused — unless **Printer setup → This printer → After a power cut trust Z** is on and `printer.cfg` has `[force_move]` with `enable_force_move: True`. Then only X and Y are homed and Z is taken as unchanged. Use it only if your bed or gantry really does not move without power. **Untested.** |

---

## OrcaSlicer setup (once per printer profile)

1. **Printer settings** → search for **Manual filament change** → ✔.
2. **Printer settings** → search for **Change filament G-code** → paste the content of `orca_change_filament_gcode.txt`:
   ```
   {if layer_num >= 0}COLOR_SWAP SLOT={next_extruder + 1} MATERIAL={filament_type[next_extruder]} OLD_MATERIAL={filament_type[previous_extruder]} TEMP={new_filament_temp} OLD_TEMP={old_filament_temp} RETRACT={new_retract_length_toolchange} PURGE={flush_length}{endif}
   ```
3. **Process** → search for **Prime tower** → turn **Enable** off.
4. **Bed temperature**: search for `bed temperature` and choose **By First filament**.
5. Optional (version 6 saves a point every minute by itself): **Printer settings** → **Machine G-code** → **Before layer change G-code** → add at its end:
   ```
   _CS_CHECKPOINT LAYER={layer_num + 1} TOTAL={total_layer_count} SLOT={current_extruder + 1} MATERIAL={filament_type[current_extruder]}
   ```
6. Save both profiles.

---

## Remote control (optional)

Follow `telegram_bot.txt`, then switch on **Color swap settings → Alerts → Telegram answer buttons**.

---

## Going back to version 5.1 (FLSUN V400)

1. Upload the files from `ROLLBACK_v5.1/` in place of the existing ones: `color_swap.cfg`, `macros.cfg`, `KlipperScreen.conf`.
2. Make sure the printer is **not printing**, then press **Save & Restart**.
3. Orca needs no change. The saved settings (`cs_set` in `variables.cfg`) are simply ignored by version 5.1.

---

## Removing the macro

1. Delete the line `[include color_swap.cfg]` from `printer.cfg`.
2. Delete the hook lines (`_COLOR_SWAP_ON_RESUME`, `_COLOR_SWAP_RESET`, `_CS_CLEAR_CHECKPOINT`, `COLOR_SWAP_RUNOUT`), the `COLOR_SWAP RUNOUT=1` block in `M600`, and the Orca lines.
3. **Save & Restart**.
