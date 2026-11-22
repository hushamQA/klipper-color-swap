**English** | [العربية](%D8%AA%D9%81%D8%A7%D8%B5%D9%8A%D9%84-%D8%AA%D9%82%D9%86%D9%8A%D8%A9)

## Files

| File | Contents |
|---|---|
| `color_swap.cfg` | The macro, windows, settings window, waiting clock, head lock, save points, resume, alerts and remote commands |
| `FLSUN_V400/macros.cfg` | `RESUME` (returns fast after a swap), `M600` (opens the swap window), `CANCEL_PRINT`, `UNLOAD_FILAMENT`/`LOAD_FILAMENT` with forced heating, and `START_PRINT`/`END_PRINT` that delete the save point |
| `FLSUN_V400/KlipperScreen.conf` | **Color swap** button in the print menu, and **Resume saved** button on the home screen |
| `orca_change_filament_gcode.txt` | Orca line for the color swap |
| `orca_before_layer_change_gcode.txt` | Orca line for save points |
| `moonraker_notifier.txt` | Telegram section to paste at the end of `moonraker.conf` |
| `KlipperScreen_color_swap.conf` | The KlipperScreen buttons for other printers |
| `telegram_panel/` | Telegram control panel with buttons (bot, service, installer, tests) |
| `telegram_bot.txt` | The alternative: moonraker-telegram-bot |
| `sim/` | Tests: `python sim/run_tests.py` renders the macros the way Klipper does and runs 418 checks on a fake delta, Cartesian and CoreXY printer. Needs `pip install jinja2`. Nothing touches a real printer |
| `klipperscreen_popup_fix.sh` | Optional one-line KlipperScreen fix: message popups no longer hold the touches (see version 6.4) |
| `ROLLBACK_v5.1/` | Version 5.1 files, to go back |

The save point is a single variable `cs_resume` in `variables.cfg` on the printer. The settings changed on the screen are `cs_set` in the same file.

## Filament accounting (no gap and no blob on resume)

| Stage | Filament |
|---|---|
| Before the swap | Orca retracts `RETRACT` (2 mm), and `PAUSE` retracts 1 mm |
| Unload | Push 3 mm + what was retracted → fast pull 13 mm → the rest in the same pull, no stop (6.6) |
| After the purge | Retract `hold` = the larger of `RETRACT` and 1 mm |
| Continue... | Push `hold` + 5 (`refill_mm`) → pull `hold` back. You cut this strand |
| Yes, continue print | Push `hold` + 1.5 → retract `RETRACT` + 1 (`pause_retract_mm`) → `RESUME` pushes its 1 mm |
| Start of printing | Orca pushes `RETRACT` → the nozzle is exactly full |

## Settings

All of them are in the settings window ([Part 5](Settings-Window)), where each one explains itself. The names in the file and their defaults:

| Setting | Default | Meaning |
|---|---|---|
| `park_auto / park_edge` | 1 / 12 | Automatic park point, mm inside the front limit |
| `park_x / park_y` | 0 / -140 | Manual park point (`park_auto` 0) |
| `park_lift / park_min_z` | 10 / 60 | Lift above the model, lowest park height |
| `auto_unload` | 1 | Pull the old filament out at once (0 = Unload button) |
| `auto_continue_min` | 5 (AWAY) | Minutes with no button before the print goes on with the current color (never when the material type changes). 0 = HOME. Set by the HOME / AWAY button |
| `away_min` | 5 | The away time the AWAY button uses |
| `load_check_sensor` | 1 | Refuse Load + purge when the sensor sees no filament |
| `runout_swap` | 1 | Runout / M600 use the swap window |
| `pause_retract_mm` | 1 | What the printer's own PAUSE retracts and RESUME pushes |
| `resume_speed / heat_band` | 250 / 3 | Return speed mm/s, temperature band |
| `min_temp` | 170 | Nothing is loaded or unloaded below this |
| `standby_min / standby_temp / standby_purge_mm` | 5 / 170 / 10 | Nozzle standby while waiting |
| `nozzle_off_min / wait_max_min` | 60 / 480 | Nozzle off; everything off |
| `remind_min` | 10 | Phone reminder interval |
| `hold_boost` | 1 | Head lock while waiting |
| `unload_mm / unload_purge_mm / unload_snap_mm / unload_dwell_ms` | 40 / 3 / 13 / 0 | Unload and tip forming (0 = one pull, no stop) |
| `load_mm / load_slow_mm / load_speed` | 40 / 15 / 600 | Load (last 15 mm slow) |
| `flex_speed_pct` | 50 | TPU / TPE / FLEX speed, percent |
| `purge_min / purge_max / purge_default` | 25 / 250 / 50 | Purge limits |
| `purge_material_change / purge_to_main_extra` | 15 / 20 | Extras |
| `purge_speed / purge_pulse_mm / purge_pulse_retract` | 180 / 20 / 2 | 3 mm/s, pulsed purge |
| `purge_btn1 / purge_btn2 / purge_btn3` | 15 / 30 / 60 | The purge buttons |
| `settle_mm / refill_mm / reprime_mm` | 8 / 5 / 1.5 | Settle after cooling, fresh push on Continue... (you cut it), nozzle fill on Yes |
| `temp_pla / temp_petg / temp_abs / temp_asa / temp_tpu` | 215 / 240 / 250 / 255 / 225 | Material presets |
| `first_layer_wipe / first_layer_max_z` | 1 / 0.75 | Layer-1 wipe line |
| `wipe_edge / wipe_len` | 7 / 80 | Line distance from the limit, length (not delta) |
| `wipe_step / wipe_z / wipe_e_per_mm / wipe_speed / wipe_margin` | 1.2 / 0.3 / 0.1 / 1200 / 10 | Line details |
| `flick / flick_mm / flick_cool_ms` | 0 / 8 / 1500 | Side flick |
| `autosave_s / boot_prompt / resume_lift` | 60 / 1 / 0.5 | Power-loss resume |
| `resume_trust_z` | 0 | Not delta: home X/Y only and trust Z |
| `notify / tg_bot / beep` | 1 / 0 / 1 | Phone messages, Telegram bot buttons, buzzer |
| `beep_count / beep_ms` | 3 / 150 | Buzzer |

## Verified

- Version 6.3 on the FLSUN V400 (2026-11-15, printer idle): the away time window sends `D=-1.0` / `D=-10.0` for − 1 / − 10 (6.2 sent `D=1.0`); the Alerts page shows no buzzer lines (no buzzer pin), the Swap page keeps the sensor lines (sensor found).
- `PURGE` arrives from Orca: in a sliced file the values were `PURGE=43.155` and `PURGE=22.4506`.
- Bed temperature in the COLOR_SWAP profile = `by_first_filament`.
- Orca accepts the `_CS_CHECKPOINT` line: a file sliced on 2026-11-05 has 44 lines with correct filament numbers (layer 36: `SLOT=2 MATERIAL=PLA`).
- Version 4 installed on the printer on 2026-11-05: no warnings, calibration unchanged, the `RESUME_SAVED_PRINT` window appears.
- Telegram messages reach the phone (`TEST_ALERT`, 2026-11-06).

- Version 6, in a simulator that renders the macros with Klipper's own template settings and runs them (2026-11-11): 262 checks on a delta, a Cartesian and a CoreXY machine — swap, back-to-main purge, auto continue, standby and heater-off, keep color, layer-1 wipe line, runout, cancel, power-loss resume, settings window (every numeric setting is on the screen), remote commands, bowden lengths. Lowest Z = the Z at the pause (0.3 for the layer-1 line), and the filament accounting comes out exact.

- Version 6.2 on the FLSUN V400 itself (2026-11-12, printer idle, nothing moved): Klipper loads the config with no warnings; `COLOR_SWAP_CHECK` finds the delta limits, park point X0 Y-140, the filament sensor, the three tower motors and the hook lines; all 111 settings windows open without an error; HOME / AWAY, the away time, purge LOW / NORMAL / HIGH / CUSTOM, an ON / OFF switch, `COLOR_SWAP_SET` and Factory reset each changed and saved the right values; the window shows in Mainsail with the **COLOR SWAP SETTINGS** button on the dashboard.

## Not verified yet

- **A real color swap with version 6** — the swap, auto continue, standby, runout and resume paths ran in the simulator only.
- Opening the settings window in Mainsail **during** a real print (tested with the printer idle, and in the simulator while printing).
- The Telegram bot button message (`tgcustom_keyboard`) and the non-delta "trust Z" resume.
- The Re-home button and a full resume on a real print (simulation only).
