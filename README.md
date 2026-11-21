**English** | [العربية](README.ar.md)

# Multi-color printing on a single-extruder printer — any Klipper printer (version 6.5)

**One** print file. Whenever the print needs a new color, the printer pauses on its own and a window appears on the screen.
You swap the filament, press a button, and the print continues.

Installation: [`INSTALL.md`](INSTALL.md)

> 🎬 **Tutorial video (2 minutes, Arabic):** [`video/COLOR_SWAP_tutorial_AR_v2.mp4`](video/COLOR_SWAP_tutorial_AR_v2.mp4)
> Recorded on **version 2**: the idea is the same, but the windows have changed since (Continue is on the left, purge buttons 15 / 30 / 60 mm, and version 6 added the settings window). This file is the correct reference.

## What's new in version 6.5 (2026-11-21) — AWAY never prints the wrong material

> Installed on the FLSUN V400 on 2026-11-21, printer idle: Klipper ready with no warnings, Telegram panel 1.8 online, the printer files match this package byte for byte. Simulator: 402 checks; Telegram panel 1.8: 114 checks. The 1.8 file scan was run on a real 5 MB print file: 6 swaps found with their layers and minutes.

| What was wrong | Now |
|---|---|
| AWAY went on after 5 min with the old filament even when the slicer asked for another **material** (for example PETG part → PLA support interface). The part looked fine but was wrong: the support welded to it, or a TPU / PETG section was printed in PLA. | A swap that changes the material type (`OLD_MATERIAL` ≠ `MATERIAL` from the slicer) **always waits for you**, in AWAY too. The old filament stays in, so **Keep** / `CS_KEEP` can still go on with it on purpose (the Keep window warns which material that part gets). The nozzle cools to standby while it waits. A swap that only changes the color goes on by itself as before. |
| The window, `CS_STATUS`, the phone message and the Telegram card said "continues by itself" for every swap | They say **the material changes (PETG to PLA): this swap waits for you**, and the Telegram card has no "Wait for me" button for that swap (it already waits) |
| You found out about a material change only when the swap stopped | 🆕 Telegram panel 1.7: the **print start message** lists the filaments the file really uses (`🧵 Filaments: 1 PETG (19.5 g) · 2 PLA (1.3 g)`) and, when their material types differ, warns at once: **Material change in this print (PETG / PLA): those swaps always wait for somebody at the printer, also in AWAY** |
| A swap came with no notice: you could not plan to be at the printer | 🆕 Telegram panel 1.8: the panel reads the print file once (in the background) and shows **🔜 Next swap: Filament 2 PLA at layer 42 (in 5 layers) · about 16 min** (plus **✋ material change** when it is one), or **No more color swaps**. **10 min before each swap** one message: **🔔 Color swap in about 10 min**, with what will happen there (AWAY goes on by itself / the material change waits / HOME waits). The minutes come from the slicer's time marks (`M73 R`), corrected by how fast this print really goes. Change the 10 with `warn_min:` in `cs_telegram.conf` (0 = off) |

## Version 6.4 (2026-11-20) — no frozen screen, less waiting

> Installed on the FLSUN V400 on 2026-11-20, printer idle. Simulator: 375 checks; Telegram panel 1.5: 88 checks. The touch freeze was found in the KlipperScreen log of three swaps (2026-11-15, -19, -20) and reproduced with a test window on the printer.

| What was wrong | Now |
|---|---|
| During a swap the KlipperScreen screen sometimes froze: the swap window vanished behind the normal screen and no button worked until auto continue closed the window 5 min later. Cause: a message popup (e.g. "Resume point saved…") opened on top of the open swap window; KlipperScreen puts it on the screen behind the window, where it holds the touches. | Messages sent while a window is open go to the console only (`// …`). An error first closes the window, shows, and the window comes back on top. A simulator test checks every swap flow for this. |
| A swap to a cooler filament waited 30–40 s for the nozzle to cool (load step, and again before continuing). Auto continue to the old color waited 40 s too. | Only heating is waited for. A hotter nozzle unloads, loads, purges and continues at once and reaches the lower temperature by itself. |
| AWAY: the nozzle was heated to the next filament at once, so a swap that ended with the old color printed it too hot. | AWAY keeps the old filament's temperature until you press Unload. |
| KlipperScreen's own Unload / Load buttons (the panel behind the swap window) bypassed the swap, which then still thought the old filament was in. | During a swap, `UNLOAD_FILAMENT` / `LOAD_FILAMENT` run the swap's own Unload / Load + purge, or show the swap window. |
| Cancel + unload heated to the NEXT filament's temperature. | It heats for the filament that is in the nozzle. |
| Every swap sent two almost identical, plain phone messages. | Messages have a colored mark, an emoji and a bold heading. With the Telegram panel installed the panel sends them (one updating card per swap) and the notifier stays quiet for them (`tg_panel`, set by the panel itself). |
| A cancelled print could only continue from the last save point (a swap or the 1-minute save); the lines printed after it came out twice, on top of the part. | `CANCEL_PRINT` keeps where the print really stopped (`_CS_STOP_POINT`, first line of CANCEL_PRINT). **Resume saved** then offers **From where it stopped (no double lines)** or **Start from the save point**. |
| A message popup from anything else (not only this macro) could still freeze KlipperScreen behind a window. | Optional `klipperscreen_popup_fix.sh`: one line in KlipperScreen makes its popups non-modal (installed on the V400). |
| On a pause KlipperScreen opened its Extrude panel behind the swap window. | `auto_open_extrude: False` in `[main]` of KlipperScreen.conf (in `FLSUN_V400/KlipperScreen.conf`; a note in `KlipperScreen_color_swap.conf`). |
| The Telegram swap card showed only the nozzle. | It also shows the bed temperature and the layer with a progress bar. |
| FLSUN V400 `START_PRINT`: M190 / M109 waited until the temperature SETTLED; the last 3 °C of the bed took 30–40 s while the screen already showed 79–80 °C. | It starts when the bed is within 3 °C (`BED_BAND=`) and the nozzle within 3 °C. |

**Update the `[notifier phone]` section** in `moonraker.conf` from `moonraker_notifier.txt` (keep your url line), or phone messages show as `swap|Color swap …`.

## What's new in version 6.3 (2026-11-15) — settings reviewed

> Installed on the FLSUN V400 on 2026-11-15, printer idle. On the printer, the − buttons now send a negative step, and the Alerts page hides the buzzer lines (this V400 has no buzzer pin). Simulator: 337 checks; Telegram panel 1.4: 84 checks.

| What was wrong | Now |
|---|---|
| The factory mode was HOME: a print started by somebody else stopped at the first swap with the filament pulled out | **The factory mode is AWAY, 5 min**: the old filament stays in, and after 5 min with no button the print goes on with the same color. Tap **I am HOME** when you want full control |
| **Every − button raised the value** (Jinja read `{-x}` as "trim spaces", not as a minus) | − lowers, + raises. The tests now press the buttons as drawn |
| **Factory reset switched AWAY back to HOME** — the next swap pulled the filament out | Factory reset keeps HOME / AWAY: where you are is not a setting |
| AWAY: the nozzle cooled down before the print went on by itself | While AWAY is counting down the nozzle stays hot. The away time is at most 60 min |
| Purge "never less than" could be set above "never more than" | The two never cross |
| A material temperature of e.g. 100 °C — a swap below `min_temp` is refused | 0 (button hidden) or at least `min_temp` |
| Lines that do nothing were shown | Hidden: buzzer lines without a buzzer pin, sensor options without a sensor, beep / reminder / cool-down / pulse / start line details while their switch is OFF, park X / Y while the park point is automatic (and the edge while it is manual) |
| During a swap whose filament is already out, HOME / AWAY looked like it could still save the print | The window says it is for the **next** swaps (button **Next swaps: I am HOME...**) |
| "Pull old filament out by itself" — not clear it is HOME only | Renamed **Pull old filament out (HOME only)**. AWAY never pulls it out: Unload is by hand, and when the time runs out the print goes on with the same color |

## What's new in version 6 (2026-11-11)

> Version 6.2 is installed on the FLSUN V400 (2026-11-12): the config loads, and every settings window was opened and used on the printer. **A real color swap has not been printed with it yet** — do the first one on the small test model and stay next to the printer.

| Problem | Fix |
|---|---|
| Changing a setting meant editing the file and restarting | **Settings window on the screen**: KlipperScreen → **Color swap settings**. Every number, with − / + buttons, kept after a restart (Part 5) |
| The macro only fitted the FLSUN V400 | **Any printer**: park point, wipe line, sensor and motors are worked out from the printer itself. `COLOR_SWAP_CHECK` shows what it found |
| The old filament was always pulled out at once | `auto_unload` can be switched **off**: the window then opens with an **Unload** button and a **Keep current color** button |
| Nobody home at a swap = the print waits | `auto_continue_min`: no button for N minutes → **the print goes on with the current color** (Part 6; since 6.5 never when the material type changes) |
| After one hour of waiting the motors switched off and the print was lost | The nozzle cools to standby after 5 min and switches off after 60 min, but **the bed and the motors stay on** for 8 hours. Any button reheats |
| One phone message, easy to miss | A reminder every 10 minutes while a swap waits |
| No way to answer from outside | **Remote commands** `CS_STATUS`, `CS_KEEP`, `CS_WAIT`, `CS_CONTINUE`, … and Telegram buttons through moonraker-telegram-bot (Part 6) |
| A runout used the old plain M600 | Runout and M600 open **the same window** for the same filament (tip forming, Load + purge, alerts) |
| Load + purge with no filament inserted purged air | The filament sensor is checked first; **Load anyway** overrides |
| Only PLA and PETG buttons | Five presets: PLA, PETG, ABS, ASA, TPU. TPU is loaded and purged at half speed |
| A power cut lost the print's main filament, so the +60 mm purge went to the wrong swap | The main filament, the filament in the nozzle and the counters are **saved in the resume point** |
| Bowden printers: a 700 mm load is refused by Klipper | Long moves are split into pieces under `max_extrude_only_distance` |
| No numbers | The window title counts the swaps; the end of the print reports swaps, purged filament and waiting time |

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

**To change the amounts:** **Color swap settings → Purge amount** (LOW / NORMAL / HIGH), or one number at a time under **Advanced → Purge details** (Part 5). No restart is needed.

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

## 🆕 Part 5 — The settings window

**KlipperScreen**: home screen → **Color swap settings** (also in the print menu). **Mainsail**: the macro `COLOR_SWAP_SETTINGS`.
Every change applies at once (no restart) and is kept in `variables.cfg`.

### The first window — what you change from print to print

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
| LOW | 30 | 35 | 10 | 10 / 20 / 35 |
| NORMAL | 50 | 60 | 15 | 15 / 30 / 60 |
| HIGH | 90 | 110 | 25 | 25 / 55 / 110 |

### Factory reset

**Factory reset...** (red, bottom of the first window) asks once, then puts **every** color swap setting back to the value written in `color_swap.cfg` and empties the saved changes. **HOME / AWAY is kept**, and so is a saved resume point. In Mainsail it is also a macro button: `COLOR_SWAP_FACTORY_RESET`.

### The same window in Mainsail — before and during a print

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

### Inside a group

- A line that ends in **ON / OFF** switches when you tap it.
- A line with a number opens a small window: its title is the name and the value, the text says **what the number does and when to raise or lower it**, and the buttons are **− 10× / − / + / + 10×**. **Back to the file default** appears only after you changed it. **Done** goes back.
- **A star** in front of a line = you changed it. The Advanced and Printer setup lists show **(2 changed)** next to a group.
- Settings that do nothing are not shown: the straight-line length and "trust Z" on a delta; the buzzer without a buzzer pin; the sensor options without a filament sensor; the details of a switch that is OFF (beeps, reminders, cool-down, purge pulses, start line, shake); park X / Y while the park point is automatic, the edge distance while it is manual.
- Values that must fit together are kept together: purge min never above purge max; a material temperature is 0 or at least the "never move filament below" temperature.

### Advanced

| Group | What is in it |
|---|---|
| Swap | Pull the old filament out by itself, refuse loading without filament, runout window, speed back to the print, heat band |
| Long waits | Cool the nozzle after / down to, purge after reheating, nozzle heater off after, everything off after, hold the head firmly |
| Purge details | All 13 purge numbers one by one |
| Unload and load feel | Tip forming, slow end of loading, loading speed, speed for TPU |
| First layer line | The layer-1 start line and the strand shake |
| Power cut resume | Save interval, offer to resume at start-up, stop height |

### Printer setup

| Group | What is in it |
|---|---|
| Park point | Automatic or your own X / Y, distance from the front limit, lift, lowest height |
| Filament path | Length pulled out, length pushed in (bowden: the tube length) |
| This printer | What RESUME pushes by itself, lowest temperature for moving filament, trust Z after a power cut (not on a delta) |

Four names are still edited in the file, at the end of `_COLOR_SWAP_CFG`: `notify_name`, `beeper_pin`, `sensor` ("auto"), `hold_steppers` ([] = automatic).

---

## 🆕 Part 6 — Away from the printer

### Auto continue with the current color

**AWAY is the factory mode** (since 6.3), with 5 min: whoever starts a print, a swap that only changes the color goes on by itself. A swap that changes the material type always waits for somebody (6.5). **Color swap settings → I am AWAY** — one tap switches to **HOME** when you want every swap to wait for you. The waiting time is the button below it (5 min).

| What happens at a swap | |
|---|---|
| The head parks. The old filament **stays in** (it is what the print may continue with) | Window: **Unload** / **Keep current color** |
| You press anything | Auto continue is off for this swap; it now waits for you |
| Nobody presses anything for 5 minutes | The print continues **with the current color**, and a message goes to the phone |
| 🆕 6.5: the slicer's MATERIAL differs from the old one (PETG → PLA) | **No countdown**: the swap waits for you like HOME, the nozzle cools to standby. **Keep** still goes on with the old filament if you choose it |

- The rest of the file prints in the "wrong" color until the next swap. Nothing else is lost.
- Only a swap between filaments of the same material type continues by itself; the macro checks `MATERIAL` / `OLD_MATERIAL` from the slicer line. Without `OLD_MATERIAL` (an old slicer line) it cannot tell and continues as before.
- Tap **I am AWAY** to switch to HOME: every swap waits for you, and the old filament is pulled out at once. Tap **I am HOME** to go back to AWAY.
- At start-up AWAY always waits the away time the window shows.

### What a long wait does (nothing here loses the print)

| After | What happens | To go on |
|---|---|---|
| 5 min with no button (`standby_min`) | Nozzle cools to 170 °C | Any button reheats. **Continue...** purges 10 mm first and asks you to cut the strand |
| 60 min (`nozzle_off_min`) | Nozzle heater off. **Bed and motors stay on** | The same |
| 8 hours (`wait_max_min`) | Klipper switches everything off | `RESUME_SAVED_PRINT` (Part 3) |
| every 10 min (`remind_min`) | A phone message | — |

### Remote commands

Plain commands that need no window. Send them from anything that reaches the printer: Mainsail over a VPN, Mobileraker, OctoApp, or Telegram.

| Command | What it does |
|---|---|
| `CS_STATUS` | Where the swap stands, the nozzle temperature, and which commands fit now. The answer also goes to the phone |
| `CS_WAIT` | "I am coming": auto continue is off for this swap |
| `CS_KEEP` | No swap: continue now with the color in the nozzle |
| `CS_UNLOAD` / `CS_LOAD` | Pull the old filament out / load and purge the one somebody inserted |
| `CS_PURGE` | Purge 30 mm more (`CS_PURGE MM=60`) |
| `CS_CONTINUE` | The swap is done: continue the print. Nobody cuts the strand — look at the camera first |
| `CS_CANCEL` | Cancel the print |

### Telegram control panel (buttons, no typing)

`telegram_panel/` is a small bot that runs on the printer and turns the chat into a control panel. Nothing is typed: every action is a button.

**It is for controlling the printer from far away.** Anything that needs somebody standing at the printer — Unload, Load + purge, Purge, Re-home, the material buttons, Printer setup — is deliberately **not** in the chat.

| In the chat | What it is |
|---|---|
| **The key bar** (always at the bottom, in place of the phone keyboard) | **Status**, **Pause**, **Resume**, **Home / Away**, **Settings**, **Cancel print**, **STOP**. It stays there however many messages arrive, so the controls never scroll away. A key only acts when it makes sense (Pause does nothing while idle); Cancel print and STOP only ask, the Yes / No is on the panel |
| The control panel | **One** message, pinned to the top of the chat, that updates itself (every minute while printing). Any key brings it down to the bottom, right above the keys, and removes the old copy and the key press, so the chat stays clean. State, file, progress, layer, time left, temperatures, the waiting swap, HOME / AWAY. Buttons: **Refresh**, **Pause / Resume**, **Cancel print**, **Heaters off** (idle with a heater on), **I am HOME / AWAY**, **Settings**, **Emergency stop** |
| 🆕 Print start message | Only for a print with color swaps (Moonraker counts them in the file). It lists the filaments used (with grams), warns when the material type changes (those swaps wait for you, also in AWAY), says the mode and has **I am HOME - tap when leaving** / **I am AWAY** and **Settings** — the moment to choose, before the first swap. Its buttons go away once a swap starts |
| The color swap card | Sent by itself when a swap starts (the phone rings) and kept up to date. It says what is waiting and offers only what works from far away |
| 🆕 Next swap (1.8) | While printing the panel shows **🔜 Next swap: Filament 2 PLA at layer 42 · about 16 min**, and `warn_min` (10) minutes before each swap one message **🔔 Color swap in about 10 min** says what will happen there |
| Settings | The settings window of Part 5 with the same buttons, updated in place (without Printer setup and Check install) |

**What the color swap card offers**

| Situation | Buttons |
|---|---|
| Old filament still in the nozzle (AWAY, or auto unload off) | **Keep the current color and continue**, **Wait for me - do not continue** (while the countdown runs; never for a change of material, which already waits), **Cancel print** |
| Old filament already out (or being pulled out in HOME), or new one loaded and waiting for the color check | **Cancel print** only — the card says somebody has to be at the printer, and that AWAY must be set before a swap |
| Filament ran out | **Cancel print** only |

- Keep, Cancel print and Emergency stop ask a second time.
- When the swap ends the card closes itself and says how: continued with which filament, or cancelled.
- Windows opened **at** the printer (its own swap window, settings, resume) are not sent to the chat.
- Only your chat can use it; any other chat is ignored. There is no way to send G-code.
- 🆕 1.4: a button only shows while it can still do something. During a swap that needs hands the panel has no HOME / AWAY button (and the Home / Away key does nothing). When Klipper is shut down (after an emergency stop) the panel offers only **Restart Klipper** (asks first).
- 🆕 1.4: Klipper runs no command while it heats. A tap then is not lost: the panel says **switching to AWAY - waiting for the printer**, and it runs as soon as the heating ends, before any swap.
- 🆕 1.4 fix: in 1.3 Telegram's own "pinned a message" note was read as a key press, which sent and pinned a new panel every 2 seconds until Telegram blocked the bot for hours. Such notes are now ignored, and a "too many requests" answer is waited out.
- It uses the bot you already have for the alerts (the `tgram://` line in `moonraker.conf`) — no new token.
- Python standard library only, one file, one service of the normal user (`cs-telegram-panel`). No sudo, no password.
- What it does is written to `cs_telegram_panel.log` (Mainsail → Machine → logs).

**Install** (once, over SSH, printer idle): copy the `telegram_panel` folder to the printer and run `bash install.sh`. To remove: `bash install.sh remove`. Restart it: `systemctl --user restart cs-telegram-panel`.

Leave **Alerts → Telegram answer buttons** OFF with this panel: that switch is for the other bot (`telegram_bot.txt`, moonraker-telegram-bot), which is an alternative, not an addition.

> Version 1.8 is installed on the FLSUN V400 (2026-11-21): the service runs and the pinned panel was refreshed. The new parts were checked against a fake Telegram server and the simulated printer (114 checks: `python telegram_panel/test_panel_bot.py`), and the file scan on a real 5 MB print file on the printer itself (1.5 s). The early warning has not yet been seen during a real print.

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

### Waiting

A waiting swap no longer loses the print after an hour — see Part 6. The nozzle cools, then switches off; the bed and the motors stay on for `wait_max_min` (8 hours). Do not pull the filament by hand once the nozzle is cold: press **Unload again**, it heats first.

---

## Technical details

### Files

| File | Contents |
|---|---|
| `color_swap.cfg` | The macro, windows, settings window, waiting clock, head lock, save points, resume, alerts and remote commands |
| `FLSUN_V400/macros.cfg` | `RESUME` (returns fast after a swap), `M600` (opens the swap window), `CANCEL_PRINT`, `UNLOAD_FILAMENT`/`LOAD_FILAMENT` with forced heating, and `START_PRINT`/`END_PRINT` that delete the save point |
| `FLSUN_V400/KlipperScreen.conf` | **Color swap** button in the print menu, and 🆕 **Resume saved** button on the home screen |
| `orca_change_filament_gcode.txt` | Orca line for the color swap |
| 🆕 `orca_before_layer_change_gcode.txt` | Orca line for save points |
| `moonraker_notifier.txt` | Telegram section to paste at the end of `moonraker.conf` |
| 🆕 `KlipperScreen_color_swap.conf` | The KlipperScreen buttons for other printers |
| 🆕 `telegram_panel/` | Telegram control panel with buttons (bot, service, installer, tests) |
| 🆕 `telegram_bot.txt` | The alternative: moonraker-telegram-bot |
| 🆕 `sim/` | Tests: `python sim/run_tests.py` renders the macros the way Klipper does and runs 402 checks on a fake delta, Cartesian and CoreXY printer. Needs `pip install jinja2`. Nothing touches a real printer |
| 🆕 `klipperscreen_popup_fix.sh` | Optional one-line KlipperScreen fix: message popups no longer hold the touches (see version 6.4) |
| `ROLLBACK_v5.1/` | Version 5.1 files, to go back |

The save point is a single variable `cs_resume` in `variables.cfg` on the printer. 🆕 The settings changed on the screen are `cs_set` in the same file.

### Filament accounting (no gap and no blob on resume)

| Stage | Filament |
|---|---|
| Before the swap | Orca retracts `RETRACT` (2 mm), and `PAUSE` retracts 1 mm |
| Unload | Push 3 mm + what was retracted → fast pull 13 mm → wait 3 s → pull the rest (Marlin's method to form a clean tip) |
| After the purge | Retract `hold` = the larger of `RETRACT` and 1 mm |
| Continue | Push `hold` + 1.5 → retract `RETRACT` + 1 (`pause_retract_mm`) → `RESUME` pushes its 1 mm |
| Start of printing | Orca pushes `RETRACT` → the nozzle is exactly full |

### Settings

All of them are in the settings window (Part 5), where each one explains itself. The names in the file and their defaults:

| Setting | Default | Meaning |
|---|---|---|
| `park_auto / park_edge` | 1 / 12 | Automatic park point, mm inside the front limit |
| `park_x / park_y` | 0 / -140 | Manual park point (`park_auto` 0) |
| `park_lift / park_min_z` | 10 / 60 | Lift above the model, lowest park height |
| 🆕 `auto_unload` | 1 | Pull the old filament out at once (0 = Unload button) |
| 🆕 `auto_continue_min` | 5 (AWAY) | Minutes with no button before the print goes on with the current color (never when the material type changes). 0 = HOME. Set by the HOME / AWAY button |
| 🆕 `away_min` | 5 | The away time the AWAY button uses |
| 🆕 `load_check_sensor` | 1 | Refuse Load + purge when the sensor sees no filament |
| 🆕 `runout_swap` | 1 | Runout / M600 use the swap window |
| 🆕 `pause_retract_mm` | 1 | What the printer's own PAUSE retracts and RESUME pushes |
| `resume_speed / heat_band` | 250 / 3 | Return speed mm/s, temperature band |
| 🆕 `min_temp` | 170 | Nothing is loaded or unloaded below this |
| 🆕 `standby_min / standby_temp / standby_purge_mm` | 5 / 170 / 10 | Nozzle standby while waiting |
| 🆕 `nozzle_off_min / wait_max_min` | 60 / 480 | Nozzle off; everything off |
| 🆕 `remind_min` | 10 | Phone reminder interval |
| `hold_boost` | 1 | Head lock while waiting |
| `unload_mm / unload_purge_mm / unload_snap_mm / unload_dwell_ms` | 40 / 3 / 13 / 3000 | Unload and tip forming |
| `load_mm / load_slow_mm / load_speed` | 40 / 15 / 600 | Load (last 15 mm slow) |
| 🆕 `flex_speed_pct` | 50 | TPU / TPE / FLEX speed, percent |
| `purge_min / purge_max / purge_default` | 25 / 250 / 50 | Purge limits |
| `purge_material_change / purge_to_main_extra` | 15 / 60 | Extras |
| `purge_speed / purge_pulse_mm / purge_pulse_retract` | 180 / 20 / 2 | 3 mm/s, pulsed purge |
| `purge_btn1 / purge_btn2 / purge_btn3` | 15 / 30 / 60 | The purge buttons |
| `settle_mm / reprime_mm` | 8 / 1.5 | Settle after cooling, nozzle fill at Continue |
| `temp_pla / temp_petg / temp_abs / temp_asa / temp_tpu` | 215 / 240 / 250 / 255 / 225 | Material presets |
| `first_layer_wipe / first_layer_max_z` | 1 / 0.75 | Layer-1 wipe line |
| 🆕 `wipe_edge / wipe_len` | 7 / 80 | Line distance from the limit, length (not delta) |
| `wipe_step / wipe_z / wipe_e_per_mm / wipe_speed / wipe_margin` | 1.2 / 0.3 / 0.1 / 1200 / 10 | Line details |
| `flick / flick_mm / flick_cool_ms` | 0 / 8 / 1500 | Side flick |
| `autosave_s / boot_prompt / resume_lift` | 60 / 1 / 0.5 | Power-loss resume |
| 🆕 `resume_trust_z` | 0 | Not delta: home X/Y only and trust Z |
| 🆕 `notify / tg_bot / beep` | 1 / 0 / 1 | Phone messages, Telegram bot buttons, buzzer |
| `beep_count / beep_ms` | 3 / 150 | Buzzer |

### Verified

- 🆕 Version 6.3 on the FLSUN V400 (2026-11-15, printer idle): the away time window sends `D=-1.0` / `D=-10.0` for − 1 / − 10 (6.2 sent `D=1.0`); the Alerts page shows no buzzer lines (no buzzer pin), the Swap page keeps the sensor lines (sensor found).
- `PURGE` arrives from Orca: in a sliced file the values were `PURGE=43.155` and `PURGE=22.4506`.
- Bed temperature in the COLOR_SWAP profile = `by_first_filament`.
- Orca accepts the `_CS_CHECKPOINT` line: a file sliced on 2026-11-05 has 44 lines with correct filament numbers (layer 36: `SLOT=2 MATERIAL=PLA`).
- Version 4 installed on the printer on 2026-11-05: no warnings, calibration unchanged, the `RESUME_SAVED_PRINT` window appears.
- Telegram messages reach the phone (`TEST_ALERT`, 2026-11-06).

- 🆕 Version 6, in a simulator that renders the macros with Klipper's own template settings and runs them (2026-11-11): 262 checks on a delta, a Cartesian and a CoreXY machine — swap, back-to-main purge, auto continue, standby and heater-off, keep color, layer-1 wipe line, runout, cancel, power-loss resume, settings window (every numeric setting is on the screen), remote commands, bowden lengths. Lowest Z = the Z at the pause (0.3 for the layer-1 line), and the filament accounting comes out exact.

- 🆕 Version 6.2 on the FLSUN V400 itself (2026-11-12, printer idle, nothing moved): Klipper loads the config with no warnings; `COLOR_SWAP_CHECK` finds the delta limits, park point X0 Y-140, the filament sensor, the three tower motors and the hook lines; all 111 settings windows open without an error; HOME / AWAY, the away time, purge LOW / NORMAL / HIGH / CUSTOM, an ON / OFF switch, `COLOR_SWAP_SET` and Factory reset each changed and saved the right values; the window shows in Mainsail with the **COLOR SWAP SETTINGS** button on the dashboard.

### Not verified yet

- **A real color swap with version 6** — the swap, auto continue, standby, runout and resume paths ran in the simulator only.
- Opening the settings window in Mainsail **during** a real print (tested with the printer idle, and in the simulator while printing).
- The Telegram bot button message (`tgcustom_keyboard`) and the non-delta "trust Z" resume.
- The Re-home button and a full resume on a real print (simulation only).

## License

MIT — see [`LICENSE`](LICENSE). Use and modify it freely, with credit.
