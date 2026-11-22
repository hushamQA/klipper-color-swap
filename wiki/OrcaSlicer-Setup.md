**English** | [العربية](%D8%A5%D8%B9%D8%AF%D8%A7%D8%AF-OrcaSlicer)

> Type each setting's name into the **search box** in the settings. If it does not appear, turn on **Advanced**.

1. **Printer settings** → **Change filament G-code** → clear it and paste this line exactly (one line):
   ```
   {if layer_num >= 0}COLOR_SWAP SLOT={next_extruder + 1} MATERIAL={filament_type[next_extruder]} OLD_MATERIAL={filament_type[previous_extruder]} TEMP={new_filament_temp} OLD_TEMP={old_filament_temp} RETRACT={new_retract_length_toolchange} PURGE={flush_length}{endif}
   ```
2. **Bed temperature** → search for `bed temperature` → choose **By First filament** (instead of **By Highest Temp**).
   The bed then stays at the temperature of the first filament for the whole print. The macro itself never changes the bed temperature.
3. **Save points (for power cuts)** → **Printer settings** → **Machine G-code** → **Before layer change G-code** →
   add this line **at the end** (keep the existing lines):
   ```
   _CS_CHECKPOINT LAYER={layer_num + 1} TOTAL={total_layer_count} SLOT={current_extruder + 1} MATERIAL={filament_type[current_extruder]}
   ```
   The full content is in `orca_before_layer_change_gcode.txt`. It can be added to any printer profile, even for single-color prints.
   > If Orca shows an error when slicing because of this line: delete the `SLOT=…` and `MATERIAL=…` parts and keep the rest.
4. Save the printer profile and the process profile.

The other settings stay as in version 2: **Manual filament change** ✔, **Prime tower** off,
**Exclude objects** ✔ and **Label objects** ✔.

## Purge amount

The **Flushing volumes** button in the Filament panel (above the filaments) shows the table. Orca computes the amount from the two colors.
The macro takes it and applies:

| Rule | Value |
|---|---|
| Minimum | 25 mm (≈ 60 mm³) |
| Maximum | 250 mm |
| Added when the **type** changes (PLA ↔ PETG) | +15 mm |
| Added when **going back to the main filament** (e.g. PLA supports → PETG) | +20 mm (60 before 6.6) |
| No number from Orca | 50 mm (the Marlin default, ≈ 120 mm³ like Prusa) |

Example: PLA → PETG (back to the main filament) = 25 + 15 + 20 = **60 mm**, in 3 pulses of 20 mm each.

The "main filament" is the one the print **started** with (the old filament at the first swap), not a fixed type.
If a print starts with PLA, the +20 is added when going back to PLA.

**To change the amounts:** **Color swap settings → Purge amount** (LOW / NORMAL / HIGH), or one number at a time under **Advanced → Purge details** ([Part 5](Settings-Window)). No restart is needed.

> For comparison: Bambu users report about 800 mm³ (≈ 330 mm) for a PLA → PETG change. If the layer is still brittle after the change, raise the number to 120–200.
