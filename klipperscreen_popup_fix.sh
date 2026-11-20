#!/bin/sh
# COLOR_SWAP v6.4 - optional KlipperScreen fix (any printer). Run on the printer as the
# user KlipperScreen runs as:   sh klipperscreen_popup_fix.sh
#
# KlipperScreen shows "echo:" messages in a MODAL popover. A modal popover grabs every
# touch. When it opens while a prompt window (the color swap window) is on the screen it
# sits behind that window: the window vanishes and nothing responds until the window is
# closed. color_swap.cfg sends no such message while its windows are open; this one-line
# change makes the popovers non-modal, so a message from anything else cannot freeze it.
# A backup is kept next to the file. A KlipperScreen update may undo it: run it again.
set -e
F="${1:-$HOME/KlipperScreen/screen.py}"
[ -f "$F" ] || { echo "Not found: $F (pass the path of KlipperScreen/screen.py)"; exit 1; }
if grep -q "relative_to=self.base_panel.titlebar, modal=False" "$F"; then
  echo "Already fixed: $F"; exit 0
fi
grep -q "popup = Gtk.Popover(relative_to=self.base_panel.titlebar,$" "$F" || {
  echo "This KlipperScreen version has a different popup line - nothing changed."; exit 1; }
cp -n "$F" "$F.bak-popup"
sed -i 's/popup = Gtk.Popover(relative_to=self.base_panel.titlebar,$/popup = Gtk.Popover(relative_to=self.base_panel.titlebar, modal=False,/' "$F"
echo "Fixed: $F (backup: $F.bak-popup). Restart KlipperScreen while the printer is idle."
