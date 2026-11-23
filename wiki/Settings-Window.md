**English** | [العربية](%D9%86%D8%A7%D9%81%D8%B0%D8%A9-%D8%A7%D9%84%D8%A5%D8%B9%D8%AF%D8%A7%D8%AF%D8%A7%D8%AA)

**KlipperScreen**: home screen → **Color swap settings** (also in the print menu). **Mainsail**: the macro `COLOR_SWAP_SETTINGS`.
Every change applies at once (no restart) and is kept in `variables.cfg`.

## The first window — what you change from print to print

<table><tr>
<td align="center"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/klipperscreen_07_settings.png" width="460" alt="KlipperScreen"><br><sub>KlipperScreen (scroll for the rest)</sub></td>
<td align="center"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/mainsail_07_settings.png" width="300" alt="Mainsail"><br><sub>Mainsail — the whole window</sub></td>
</tr></table>

| Button | What it does |
|---|---|
| **I am HOME / I am AWAY** | One tap. HOME: every swap waits for you and the old filament is pulled out at once. AWAY: the old filament stays in, a swap waits the away time, then the print goes on with that color — except when the material type changes: that swap always waits for you. **Set AWAY before the swap starts** — once the filament is out, only somebody at the printer can finish the swap |
| **Away: continue by itself after N min** | The away time (5 min, at most 60). The nozzle stays hot meanwhile. Changing it while HOME does not switch AWAY on |
| **Purge amount: LOW / NORMAL / HIGH** | One tap moves six values together: the default purge, both extras and the three purge buttons. NORMAL = the values in the file, LOW = 0.6×, HIGH = 1.8×. If you change one of the six by hand it says **CUSTOM**; the next tap goes back to NORMAL |
| **Material temperatures** | PLA, PETG, ABS, ASA, TPU. 0 hides a button |
| **Alerts** | Phone message, reminder interval, Telegram answer buttons, buzzer |
| **Advanced...** | Fine tuning — see below |
| **Printer setup...** | What is set once at install time, plus **Check install** |

Footer: **Factory reset...** and **Close** (a waiting color swap window comes back).

| Purge amount | Default | Back to main | Material change | Buttons |
|---|---|---|---|---|
| LOW | 30 | 10 | 10 | 10 / 20 / 35 |
| NORMAL | 50 | 20 | 15 | 15 / 30 / 60 |
| HIGH | 90 | 35 | 25 | 25 / 55 / 110 |

## Factory reset

**Factory reset...** (red, bottom of the first window) asks once, then puts **every** color swap setting back to the value written in `color_swap.cfg` and empties the saved changes. **HOME / AWAY is kept**, and so is a saved resume point. In Mainsail it is also a macro button: `COLOR_SWAP_FACTORY_RESET`.

## The same window in Mainsail — before and during a print

Mainsail shows exactly the same windows as KlipperScreen (it draws the same prompt).

| Where | How |
|---|---|
| Dashboard → **Macros** | Button **COLOR SWAP SETTINGS**. It is there in every state: idle, printing, paused |
| Console | Type `COLOR_SWAP_SETTINGS` |
| Type one value | `COLOR_SWAP_SET NAME=reprime_mm VALUE=2` — `COLOR_SWAP_SET` alone lists every name with its value |

- **While printing**: a change only writes a number and saves it — nothing moves and nothing heats. It counts from the next color swap on.
- **While a swap is waiting**: open the settings, change what you need, **Close** — the swap window comes back. A change to the purge amount made before **Load + purge** is used by that very swap.
- KlipperScreen and Mainsail show the same window at the same time; a tap on either one answers both.
- Closed the window with the **×**? Press the button again.

## Inside a group

- A line that ends in **ON / OFF** switches when you tap it.
- A line with a number opens a small window: its title is the name and the value, the text says **what the number does and when to raise or lower it**, and the buttons are **− 10× / − / + / + 10×**. **Back to the file default** appears only after you changed it. **Done** goes back.
- **A star** in front of a line = you changed it. The Advanced and Printer setup lists show **(2 changed)** next to a group.
- Settings that do nothing are not shown: the straight-line length and "trust Z" on a delta; the buzzer without a buzzer pin; the sensor options without a filament sensor; the details of a switch that is OFF (beeps, reminders, cool-down, purge pulses, start line, shake); park X / Y while the park point is automatic, the edge distance while it is manual.
- Values that must fit together are kept together: purge min never above purge max; a material temperature is 0 or at least the "never move filament below" temperature.

## Advanced

<table><tr>
<td align="center"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/klipperscreen_08_settings_advanced.png" width="460" alt="KlipperScreen"><br><sub>KlipperScreen</sub></td>
<td align="center"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/mainsail_08_settings_advanced.png" width="300" alt="Mainsail"><br><sub>Mainsail</sub></td>
</tr></table>

| Group | What is in it |
|---|---|
| Swap | Pull the old filament out by itself, refuse loading without filament, runout window, speed back to the print, heat band |
| Long waits | Cool the nozzle after / down to, purge after reheating, nozzle heater off after, everything off after, hold the head firmly |
| Purge details | All 14 purge numbers one by one, including **Fresh push before you cut** (`refill_mm`) |
| Unload and load feel | Tip forming, slow end of loading, loading speed, speed for TPU |
| First layer line | The layer-1 start line and the strand shake |
| Power cut resume | Save interval, offer to resume at start-up, stop height |

## Printer setup

| Group | What is in it |
|---|---|
| Park point | Automatic or your own X / Y, distance from the front limit, lift, lowest height |
| Filament path | Length pulled out, length pushed in (bowden: the tube length) |
| This printer | What RESUME pushes by itself, lowest temperature for moving filament, trust Z after a power cut (not on a delta) |

Four names are still edited in the file, at the end of `_COLOR_SWAP_CFG`: `notify_name`, `beeper_pin`, `sensor` ("auto"), `hold_steppers` ([] = automatic).
