**English** | [العربية](%D8%A7%D8%B3%D8%AA%D9%83%D9%85%D8%A7%D9%84-%D8%B7%D8%A8%D8%A7%D8%B9%D8%A9-%D9%85%D8%AA%D9%88%D9%82%D9%81%D8%A9)

Works after: a **cancel** at a color swap, a **moved head** followed by a cancel, or a **power cut**.

## Before you start — check with your eyes

| Condition | Why |
|---|---|
| The part is still stuck to the bed and has not moved | The print continues on top of it at the same coordinates |
| The nozzle is not touching the part | After a power cut the head may drop. Lift it gently by hand (the motors are off) |
| The file is still on the printer with the same name | The printer continues from the same file |

## Steps (10–15 minutes, mostly heating)

1. **After a power cut:** switch the printer on and wait one minute; the window opens **on its own**.
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

## Where are the points saved?

| When | Where it resumes from |
|---|---|
| **Every minute while printing** (automatic, every profile) | About the same line: less than a minute is lost |
| Start of every layer (the Orca line in [Part 1](OrcaSlicer-Setup), step 3: now optional) | The start of the layer |
| At every color swap (automatic) | Right after the swap, in the new color |
| Start of a new print / successful end of a print | The point is deleted |
| Print cancelled | The point **stays** (so you can resume later) |

## Limits you should know

- **Whatever was printed in the last minute before the stop is printed a second time on top of itself.** A small mark in one spot.
- **The once-a-minute save point can fall during a retraction:** the first line after resuming may come out with a small blob (0.8 mm of extra filament). No risk to the part.
- **After a power cut the bed cools down.** The part may come loose. Do not continue if it moved.
- **A file in a subfolder, or with quotes in its name → no save points.** Upload files to the root folder.
- **Height above 368 mm → no resume** (there is no room to purge beside the part up there).
- If the power is cut **while** a save point is being written (a fraction of a second), Klipper may refuse to start with the message `Unable to parse existing variable file`.
  Fix: Mainsail → **Machine** → open `variables.cfg` → delete the line that starts with `cs_resume` → **Save & Restart**.

## Cancelling

Press **Cancel...**:

| When | Buttons |
|---|---|
| Before loading | **Cancel print** — the old filament is out of the nozzle, you can pull it by hand |
| After loading | **Cancel print** — the filament stays in the nozzle. **Do not pull it while cold**; use `UNLOAD_FILAMENT` later (it heats first) |
|  | **Unload hot + cancel** — unloads the filament while hot, then cancels |
|  | **Back to the swap** — go back |
