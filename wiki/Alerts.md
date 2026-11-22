**English** | [العربية](%D8%A7%D9%84%D8%AA%D9%86%D8%A8%D9%8A%D9%87%D8%A7%D8%AA)

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

## Turning on phone messages — Telegram (10 minutes, once)

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

## Buzzer on the board

Needs a part fitted inside the printer. The macro is ready: it beeps 3 times at the same stages,
**and never beeps while actually printing** (so it leaves no mark on the part).

| Item | Details |
|---|---|
| Part | **Active buzzer module** with three pins (VCC, GND, I/O), works on 3.3–5V, e.g. KY-012 |
| Board | A modified version of the MKS Robin Nano v2.1; its connectors differ from the original. No published pin can be trusted |
| Needed before fitting | A clear photo of the mainboard to choose a safe free pin |
| After fitting | Add an `[output_pin beeper]` section in `printer.cfg` with the right pin, then `TEST_ALERT` |
