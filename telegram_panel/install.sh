#!/bin/bash
# Install the COLOR_SWAP Telegram control panel on the printer.
# Run it ON the printer, as the normal user (pi). No sudo and no password needed:
# it is installed as a service of that user.
#   bash install.sh           install or update, then start
#   bash install.sh remove    stop and remove (the settings file and the log are kept)
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="$HOME/cs-telegram-panel"
CONF="$HOME/printer_data/config/cs_telegram.conf"
UNITDIR="$HOME/.config/systemd/user"
UNIT=cs-telegram-panel.service
LOG="$HOME/printer_data/logs/cs_telegram_panel.log"

if [ "$1" = "remove" ]; then
  systemctl --user disable --now "$UNIT" 2>/dev/null || true
  rm -f "$UNITDIR/$UNIT"
  systemctl --user daemon-reload
  rm -rf "$DEST"
  echo "Removed. $CONF and $LOG were kept."
  exit 0
fi

python3 -c 'import sys; assert sys.version_info >= (3, 7), "Python 3.7 or newer is needed"'
mkdir -p "$DEST" "$UNITDIR"
cp "$SRC/cs_panel_bot.py" "$DEST/"
python3 -m py_compile "$DEST/cs_panel_bot.py"
[ -f "$CONF" ] || cp "$SRC/cs_telegram.conf" "$CONF"
cp "$SRC/$UNIT" "$UNITDIR/$UNIT"
# start at boot even when nobody is logged in
loginctl enable-linger "$USER" 2>/dev/null || echo "Note: could not enable start-at-boot (loginctl enable-linger). Run: sudo loginctl enable-linger $USER"
systemctl --user daemon-reload
systemctl --user enable "$UNIT" >/dev/null 2>&1
systemctl --user restart "$UNIT"
sleep 6
echo "service: $(systemctl --user is-active "$UNIT")"
tail -5 "$LOG" 2>/dev/null || true
echo
echo "Open the chat with your bot in Telegram: a message with the Panel key should be there."
echo "Log: $LOG   Restart: systemctl --user restart $UNIT"
