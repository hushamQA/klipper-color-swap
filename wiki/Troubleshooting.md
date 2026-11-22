**English** | [العربية](%D8%AD%D9%84-%D8%A7%D9%84%D9%85%D8%B4%D8%A7%D9%83%D9%84)

Each problem: what you see, why it happens, what to change. Every setting named here is in **Color swap settings** on the printer screen (no file editing) — see [The settings window](Settings-Window).

## The new color starts with an empty stretch

**You see:** after a swap the head draws part of the layer with nothing coming out, then the color appears. On layer 1 the wipe arc starts only from its middle.

**Why:** after the purge the nozzle keeps oozing while you look at the color and cut the strand, so it goes back to the part half empty. This is a known effect of manual filament changes ([Prusa forum](https://forum.prusa3d.com/forum/prusaslicer/pause-for-filament-chanage-behavior/), [Prusa-Firmware #2502](https://github.com/prusa3d/Prusa-Firmware/issues/2502)).

**Fix (version 6.6):** **Continue...** pushes `refill_mm` (5 mm) of fresh plastic, and you cut **that** strand in the next window, right before **Yes, continue print**. Still a gap? **Advanced → Purge details → Fresh push before you cut**: raise it to 7 or 8. A blob at the start instead? Lower **Refill the nozzle on Continue** (`reprime_mm`).

## The purge is too long or too short

**Too long** (wasted filament, long waits): **Purge amount → LOW**, or one number at a time in **Advanced → Purge details**. Going back to the main filament adds `purge_to_main_extra` (20 mm since 6.6, 60 before).
**Too short** (mixed color, brittle layer after a PLA ↔ PETG change): **Purge +15 / +30 / +60** during the swap, or **Purge amount → HIGH**.
The base amount comes from Orca's **Flushing volumes** table — see [OrcaSlicer setup](OrcaSlicer-Setup).

## The old filament is hard to pull out

Since 6.6 the unload is **one pull with no stop** (`unload_dwell_ms` 0). A stop in the middle lets the filament cool in the hot end. If it still sticks: check the temperature of the old filament (the unload waits for it), and **Unload again** — it heats first. Never pull by hand once the nozzle is cold.

## AWAY did not continue by itself

That swap **changes the material** (PLA → PETG...): since 6.5 such a swap always waits for a person, also in AWAY. The window and the Telegram card say so. **Keep current color** still goes on with the old filament on purpose. See [Away from the printer](Away-Mode).

## I closed the swap window

KlipperScreen: print screen → **Menu** → **Color swap**. Mainsail: the **COLOR_SWAP_PROMPT** macro button. Remote: `CS_STATUS`.

## The head moved while I was inserting the filament

Press **Head moved? Re-home** in the swap window — see [During the print](During-the-Print).

## KlipperScreen freezes during a swap

A message popup opened on top of the swap window and holds the touches. Install the optional one-line fix `klipperscreen_popup_fix.sh` — see [Installation](Installation).

## The Telegram panel does not answer

On the printer: `systemctl --user restart cs-telegram-panel`. What it did is in `cs_telegram_panel.log` (Mainsail → Machine → logs). See [Telegram control panel](Telegram-Panel).

## The print does not continue after a power cut

`RESUME_SAVED_PRINT` (or **Resume saved** on the home screen) — see [Resume a stopped print](Resume-a-Stopped-Print).
