**English** | [العربية](%D9%84%D9%88%D8%AD%D8%A9-Telegram)

`telegram_panel/` is a small bot that runs on the printer and turns the chat into a control panel. Nothing is typed: every action is a button.

**It is for controlling the printer from far away.** Anything that needs somebody standing at the printer — Unload, Load + purge, Purge, Re-home, the material buttons, Printer setup — is deliberately **not** in the chat.

<table><tr>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_6_keyboard.png" width="620" alt="Telegram"><br><sub>The key bar (always at the bottom)</sub></td>
</tr></table>

<table><tr>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_2_panel_next_swap.png" width="360" alt="Telegram"><br><sub>The control panel while printing, with the next swap (1.8)</sub></td>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_1_print_start.png" width="360" alt="Telegram"><br><sub>Print start message (1.7) and the warning 10 min before a swap (1.8)</sub></td>
</tr></table>

| In the chat | What it is |
|---|---|
| **The key bar** (always at the bottom, in place of the phone keyboard) | **Status**, **Pause**, **Resume**, **Home / Away**, **Photo**, **Settings**, **Cancel print**, **STOP**. It stays there however many messages arrive, so the controls never scroll away. A key only acts when it makes sense (Pause does nothing while idle); Cancel print and STOP only ask, the Yes / No is on the panel |
| The control panel | **One** message, pinned to the top of the chat, that updates itself (every minute while printing). Any key brings it down to the bottom, right above the keys, and removes the old copy and the key press, so the chat stays clean. State, file, progress, layer, time left, temperatures, the waiting swap, HOME / AWAY. Buttons: **Refresh**, **Photo** and **Video** (with a camera), **Pause / Resume**, **Cancel print**, **Heaters off** (idle with a heater on), **I am HOME / AWAY**, **Settings**, **Timelapse ON / OFF** and **Last timelapse** (with moonraker-timelapse), **Emergency stop** |
| Print start message | Only for a print with color swaps (Moonraker counts them in the file). It lists the filaments used (with grams), warns when the material type changes (those swaps wait for you, also in AWAY), says the mode and has **I am HOME - tap when leaving** / **I am AWAY** and **Settings** — the moment to choose, before the first swap. Its buttons go away once a swap starts |
| The color swap card | Sent by itself when a swap starts (the phone rings) and kept up to date. It says what is waiting and offers only what works from far away |
| Next swap (1.8) | While printing the panel shows **🔜 Next swap: Filament 2 PLA at layer 42 · about 16 min**, and `warn_min` (10) minutes before each swap one message **🔔 Color swap in about 10 min** says what will happen there |
| Camera (1.9) | With a camera on the printer, **📷 Photo** (key, panel and swap card) sends a picture of the printer. A picture also comes by itself right under the swap card when a swap starts, when the purge is ready (**is the color right?** — check it from far away), on a runout, and when a print ends (complete, error, cancelled). The camera is found by itself (the first webcam in Moonraker); `camera:` in `cs_telegram.conf` takes a snapshot URL, or `off`. No camera, or unplugged: no Photo button, nothing else changes. The automatic pictures follow **Alerts → Phone messages** |
| Video and timelapse (1.9) | **🎥 Video** records 10 s of the live camera on the printer (ffmpeg, one core, lowest priority: 640 wide, about 1.5 MB) and sends it to watch in the chat. A live stream that keeps running is not possible in a Telegram bot. With moonraker-timelapse the panel shows **🎬 Timelapse: ON / OFF** (one tap switches it), the video of a **complete** print comes to the chat by itself once Moonraker has made it (`timelapse_video: off` in `cs_telegram.conf` stops that), and **🎞 Last timelapse** sends the newest video again. Telegram takes at most 50 MB from a bot: a bigger video stays in Mainsail → Timelapse |
| Settings | The settings window of [Part 5](Settings-Window) with the same buttons, updated in place (without Printer setup and Check install) |

**What the color swap card offers**

| Situation | Buttons |
|---|---|
| Old filament still in the nozzle (AWAY, or auto unload off) | **Keep the current color and continue**, **Wait for me - do not continue** (while the countdown runs; never for a change of material, which already waits), **Cancel print** |
| Old filament already out (or being pulled out in HOME), or new one loaded and waiting for the color check | **Cancel print** only — the card says somebody has to be at the printer, and that AWAY must be set before a swap |
| Filament ran out | **Cancel print** only |

<table><tr>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_3_swap_card_away.png" width="300" alt="Telegram"><br><sub>AWAY, only the color changes: counts down</sub></td>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_4_swap_card_material.png" width="300" alt="Telegram"><br><sub>AWAY, the material changes: waits for you</sub></td>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_5_keep_warning.png" width="300" alt="Telegram"><br><sub>Keep asks first and warns</sub></td>
</tr></table>

<table><tr>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_7_purge_photo.png" width="300" alt="Telegram"><br><sub>The purge is ready: the card, then a photo to check the color</sub></td>
<td align="center" valign="top"><img src="https://raw.githubusercontent.com/hushamQA/klipper-swappilot/main/screenshots/telegram_8_video.png" width="300" alt="Telegram"><br><sub>🎥 Video: 10 s of the live camera</sub></td>
</tr></table>

- Keep, Cancel print and Emergency stop ask a second time.
- When the swap ends the card closes itself and says how: continued with which filament, or cancelled.
- Windows opened **at** the printer (its own swap window, settings, resume) are not sent to the chat.
- Only your chat can use it; any other chat is ignored. There is no way to send G-code.
- 1.4: a button only shows while it can still do something. During a swap that needs hands the panel has no HOME / AWAY button (and the Home / Away key does nothing). When Klipper is shut down (after an emergency stop) the panel offers only **Restart Klipper** (asks first).
- 1.4: Klipper runs no command while it heats. A tap then is not lost: the panel says **switching to AWAY - waiting for the printer**, and it runs as soon as the heating ends, before any swap.
- 1.4 fix: in 1.3 Telegram's own "pinned a message" note was read as a key press, which sent and pinned a new panel every 2 seconds until Telegram blocked the bot for hours. Such notes are now ignored, and a "too many requests" answer is waited out.
- It uses the bot you already have for the alerts (the `tgram://` line in `moonraker.conf`) — no new token.
- Python standard library only, one file, one service of the normal user (`cs-telegram-panel`). No sudo, no password.
- What it does is written to `cs_telegram_panel.log` (Mainsail → Machine → logs).

**Install** (once, over SSH, printer idle): copy the `telegram_panel` folder to the printer and run `bash install.sh`. To remove: `bash install.sh remove`. Restart it: `systemctl --user restart cs-telegram-panel`.

Leave **Alerts → Telegram answer buttons** OFF with this panel: that switch is for the other bot (`telegram_bot.txt`, moonraker-telegram-bot), which is an alternative, not an addition.

> Version 1.9 (camera) is installed on the FLSUN V400 (2026-11-23): the service runs, the new key bar was sent, and on the printer the panel found the USB camera through Moonraker, took a real picture and showed the Photo button. On the printer a real 10 s video was made (640x360, 1.4 MB, 10.7 s) and the panel showed Photo, Video and Timelapse: ON. Checked against a fake Telegram server and the simulated printer (163 checks). The automatic pictures and the timelapse video have not yet been seen during a real print.
>
> Version 1.8 is installed on the FLSUN V400 (2026-11-21): the service runs and the pinned panel was refreshed. The new parts were checked against a fake Telegram server and the simulated printer (114 checks: `python telegram_panel/test_panel_bot.py`), and the file scan on a real 5 MB print file on the printer itself (1.5 s). The early warning has not yet been seen during a real print.
