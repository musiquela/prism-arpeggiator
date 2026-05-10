# boot.py - Prism MIDI Arpeggiator
# Runs before code.py to configure USB

import board
import supervisor
import usb_hid
import usb_midi

# Disable terminal/REPL display completely - display stays blank until code.py
board.DISPLAY.root_group = None
supervisor.status_bar.display = False

# Set USB device identification
supervisor.set_usb_identification(
    manufacturer="Prism",
    product="Prism MIDI Arpeggiator"
)

# ESP32-S3 has limited USB endpoints
# Must disable HID to enable MIDI
usb_hid.disable()

usb_midi.enable()
