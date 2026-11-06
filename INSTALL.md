**English** | [العربية](INSTALL.ar.md)

# Installing the COLOR_SWAP macro — on any Klipper printer

Version 5 — 2026-11-06 — for the FLSUN V400 (Klipper v0.13, Mainsail v2.19, KlipperScreen, OrcaSlicer 2.4.2)

## Contents

| File | What to do with it |
|---|---|
| `color_swap.cfg` | **The macro itself** — upload it on every printer |
| `FLSUN_V400/macros.cfg` and `FLSUN_V400/KlipperScreen.conf` | Ready-made files for the FLSUN V400 only (they contain the hook lines and the Color swap and Resume saved buttons) |
| `orca_change_filament_gcode.txt` | OrcaSlicer line for the color swap |
| `moonraker_notifier.txt` | 🆕 Phone messages section (Telegram), pasted at the end of `moonraker.conf` |
| `orca_before_layer_change_gcode.txt` | 🆕 OrcaSlicer line for save points (resume after a power cut) |
| `README.md` / `README.ar.md` | Step-by-step usage (English / Arabic) |
| `INSTALL.md` / `INSTALL.ar.md` | This file (English / Arabic) |
| `test/` | Test model: a plate + the letter T |
| `ROLLBACK_v4/` | 🆕 The printer's files before version 5 (to go back) |
| `SHA256SUMS.txt` | Checksum of every file — to confirm a file is intact after uploading |

The `ROLLBACK_v4/` files were copied from the printer itself (the working version 4). The version 5 files match what was uploaded to the printer on 2026-11-06.

---

## Case 1 — FLSUN V400 printer (10 minutes)

1. Open **Mainsail** → **Machine** (config files).
2. Make a backup: download `macros.cfg` and `printer.cfg` to your computer.
3. Upload `color_swap.cfg`.
4. Upload `FLSUN_V400/macros.cfg` in place of the existing `macros.cfg`.
   > If the `macros.cfg` on your printer is different (you edited it yourself), do not upload it — follow steps 2 and 3 of Case 2 instead.
5. Open `printer.cfg` and add this line directly **below** `[include macros.cfg]`:
   ```
   [include color_swap.cfg]
   ```
6. Upload `KlipperScreen.conf` in place of the existing one (it adds the **Color swap** button to the print menu), then restart KlipperScreen.
7. 🆕 Open `moonraker.conf` and paste the content of `moonraker_notifier.txt` at its **end** (do not replace the whole file).
   Then replace `BOT_TOKEN` and `CHAT_ID` (steps in [`README.md`](README.md), Part 4).
8. Make sure the printer is **not printing**, then press **Save & Restart**.
9. **Test:** type in the Console:
   ```
   COLOR_SWAP
   ```
   The correct reply: `COLOR_SWAP only works during a print.` → the install worked, and nothing moved.

---

## Case 2 — another Klipper printer (20 minutes)

### Before you start: make sure `printer.cfg` has these sections

```
[pause_resume]
[respond]
[exclude_object]
[gcode_arcs]
```

Any section that is missing → add it as is (one line per section).

### Steps

1. Upload `color_swap.cfg` and add `[include color_swap.cfg]` to `printer.cfg`.
2. **`RESUME` macro:** add this line as the **first line** inside `gcode:`:
   ```
   _COLOR_SWAP_ON_RESUME
   ```
3. **`CANCEL_PRINT` macro:** add this line **before** `CANCEL_PRINT_BASE`:
   ```
   _COLOR_SWAP_RESET
   ```
   **Start macro (`START_PRINT` or `PRINT_START`):** add at its beginning:
   ```
   _CS_CLEAR_CHECKPOINT
   ```
   **End macro (`END_PRINT` or `PRINT_END`):** add at its end (stops the autosave after the print finishes):
   ```
   _CS_CLEAR_CHECKPOINT DONE=1
   ```
   > If your start macro ends with a filament retraction (`G1 E-…`) after the prime line: delete it.
   > Orca only retracts and restores what it retracted itself, so the skirt starts short and broken.
   > Resuming after a stop (`RESUME_SAVED_PRINT`) needs `[save_variables]` in `printer.cfg`,
   > and works on **delta printers only** (their Home moves up). On other printers Home moves down onto the part, so the macro refuses.
   Example:
   ```
   [gcode_macro RESUME]
   rename_existing: RESUME_BASE
   gcode:
     _COLOR_SWAP_ON_RESUME
     ...rest of the macro unchanged...
   ```
   > Recommended: if your `RESUME` pushes filament (`G1 E…`) before `RESUME_BASE`, skip that push after a swap
   > and add `VELOCITY=250` to `RESUME_BASE` — see `RESUME` in `FLSUN_V400/macros.cfg` as an example.
   > If `RESUME` and `CANCEL_PRINT` come from `mainsail.cfg` or `fluidd.cfg` (which are not edited),
   > copy the macro into your own macros file first, then add the line.
4. Open `color_swap.cfg` and edit the `[gcode_macro _COLOR_SWAP_CFG]` section:

   | Variable | What to set |
   |---|---|
   | `park_x / park_y` | The purge spot: above the bed edge, away from the part |
   | `sensor` | The name of the filament sensor in `printer.cfg` (no sensor is fine) |

   **Example for a 235×235 mm square bed** (coordinates from 0 to 235):
   ```
   variable_park_x: 117.5
   variable_park_y: 10
   ```
5. **Save & Restart**, then test as in step 9 of Case 1.

> The macro calls your printer's existing `PAUSE` to lift the head and move it away.
> Make sure your `PAUSE` really lifts the head before the first print.

---

## OrcaSlicer setup (once per printer profile)

1. **Printer settings** → search for **Manual filament change** → ✔.
2. **Printer settings** → search for **Change filament G-code** → paste the content of `orca_change_filament_gcode.txt`:
   ```
   {if layer_num >= 0}COLOR_SWAP SLOT={next_extruder + 1} MATERIAL={filament_type[next_extruder]} OLD_MATERIAL={filament_type[previous_extruder]} TEMP={new_filament_temp} OLD_TEMP={old_filament_temp} RETRACT={new_retract_length_toolchange} PURGE={flush_length}{endif}
   ```
3. **Process** → search for **Prime tower** → turn **Enable** off.
4. **Bed temperature**: search for `bed temperature` and choose **By First filament**.
5. 🆕 **Printer settings** → **Machine G-code** → **Before layer change G-code** → add at its end (keep what is there):
   ```
   _CS_CHECKPOINT LAYER={layer_num + 1} TOTAL={total_layer_count} SLOT={current_extruder + 1} MATERIAL={filament_type[current_extruder]}
   ```
   > Error when slicing? Delete `SLOT=…` and `MATERIAL=…` and keep the rest.
6. Save both profiles.

---

## Going back to version 4 (FLSUN V400)

1. Upload the two files from `ROLLBACK_v4/` in place of the existing ones: `color_swap.cfg` and `macros.cfg`.
2. Make sure the printer is **not printing**, then press **Save & Restart**.
3. Orca needs no change.

---

## Removing the macro (back to the previous state)

1. Delete the line `[include color_swap.cfg]` from `printer.cfg`.
2. Delete the lines `_COLOR_SWAP_ON_RESUME`, `_COLOR_SWAP_RESET` and `_CS_CLEAR_CHECKPOINT`, and the `_CS_CHECKPOINT` line from Orca.
3. **Save & Restart**.
