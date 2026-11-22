**English** | [العربية](%D8%A7%D9%84%D8%A3%D9%85%D8%A7%D9%86)

**No.** All the swap moves:

| Move | Direction |
|---|---|
| Pause (`PAUSE`) | Up first (at least 10 mm above the layer, and not lower than Z 60), then forward |
| Load, purge, flick | Filament only, or left/right — no Z move |
| Return (`RESUME`) | One line to the point where Orca paused = the layer + Orca's lift (0.5 mm). Every point on the line is above the model |
| **Re-home** and **Start** when resuming | `G28`: the towers go up to the switches at the top — away from the bed. Then straight down from the **center** to the purge height (at least 10 mm above the part), then to the edge |
| **Continue print** when resuming | Sideways at the purge height (above the part), then straight down to the saved point: swap point = the layer + 0.5 mm, layer point = top of the last layer + 0.5 mm |

Verified by simulating the macro (6 cases): lowest Z = the Z at the pause for a swap, and the saved Z + 0.5 when resuming from a layer.

## Waiting

A waiting swap no longer loses the print after an hour — see [Part 6](Away-Mode). The nozzle cools, then switches off; the bed and the motors stay on for `wait_max_min` (8 hours). Do not pull the filament by hand once the nozzle is cold: press **Unload again**, it heats first.
