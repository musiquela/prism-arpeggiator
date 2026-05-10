# SPDX-License-Identifier: MIT
"""
MIDI Arpeggiator - Phase 3: Full Features
ESP32-S3 Reverse TFT Feather + MIDI FeatherWing

Controls:
- D0: Cycle pattern (normal) / decrease selected param (edit mode)
- D1: Tap tempo (normal) / long press enter/exit edit mode / short press cycle param (edit mode)
- D2: Cycle octaves (normal) / increase selected param (edit mode)

Connect synth MIDI OUT → FeatherWing MIDI IN
Connect FeatherWing MIDI OUT → synth MIDI IN
"""

import board
# Immediately blank display to prevent REPL flash during imports
board.DISPLAY.root_group = None

import busio
import digitalio
import displayio
import terminalio
import time
import supervisor
from adafruit_display_text import label
from adafruit_display_shapes.rect import Rect
import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

# Import our modules
from note_buffer import NoteBuffer
from arpeggiator import Arpeggiator
from scales import SCALE_NAMES

# --- Display Setup ---
display = board.DISPLAY

# Boot splash screen
boot_splash = displayio.Group()
display.root_group = boot_splash

boot_bg = displayio.Bitmap(240, 135, 1)
boot_pal = displayio.Palette(1)
boot_pal[0] = 0x000000
boot_splash.append(displayio.TileGrid(boot_bg, pixel_shader=boot_pal))

title_label = label.Label(terminalio.FONT, text="David Wingo's", color=0x888888, scale=2)
title_label.anchor_point = (0.5, 0.5)
title_label.anchored_position = (120, 55)
boot_splash.append(title_label)

subtitle_label = label.Label(terminalio.FONT, text="Arpeggiator", color=0xFFFFFF, scale=3)
subtitle_label.anchor_point = (0.5, 0.5)
subtitle_label.anchored_position = (120, 85)
boot_splash.append(subtitle_label)

# Show splash briefly
time.sleep(1.5)

# Main UI
splash = displayio.Group()
display.root_group = splash

# Background
bg = displayio.Bitmap(240, 135, 1)
pal = displayio.Palette(1)
pal[0] = 0x000000
splash.append(displayio.TileGrid(bg, pixel_shader=pal))

# Battery - top right (scale=2) - added to display later once readings stabilize
batt_label = label.Label(terminalio.FONT, text="", color=0x888888, scale=2)
batt_label.x = 175
batt_label.y = 12
batt_label_shown = False

# Parameter labels (dim) and values (bright) - each on own line
# BPM - line 1
bpm_lbl = label.Label(terminalio.FONT, text="BPM", color=0x666666, scale=2)
bpm_lbl.x = 5
bpm_lbl.y = 22
splash.append(bpm_lbl)

bpm_label = label.Label(terminalio.FONT, text="120", color=0xFFFFFF, scale=2)
bpm_label.x = 55
bpm_label.y = 22
splash.append(bpm_label)

# Pattern - line 2
pat_lbl = label.Label(terminalio.FONT, text="PAT", color=0x666666, scale=2)
pat_lbl.x = 5
pat_lbl.y = 44
splash.append(pat_lbl)

pattern_label = label.Label(terminalio.FONT, text="UP", color=0x00FF88, scale=2)
pattern_label.x = 55
pattern_label.y = 44
splash.append(pattern_label)

# Division - line 3
div_lbl = label.Label(terminalio.FONT, text="DIV", color=0x666666, scale=2)
div_lbl.x = 5
div_lbl.y = 66
splash.append(div_lbl)

div_label = label.Label(terminalio.FONT, text="1/8", color=0x00FFFF, scale=2)
div_label.x = 55
div_label.y = 66
splash.append(div_label)

# Octave - line 4
oct_lbl = label.Label(terminalio.FONT, text="OCT", color=0x666666, scale=2)
oct_lbl.x = 5
oct_lbl.y = 88
splash.append(oct_lbl)

oct_label = label.Label(terminalio.FONT, text="1", color=0xFFFF00, scale=2)
oct_label.x = 55
oct_label.y = 88
splash.append(oct_label)

# Scale - line 5
scl_lbl = label.Label(terminalio.FONT, text="SCL", color=0x666666, scale=2)
scl_lbl.x = 5
scl_lbl.y = 110
splash.append(scl_lbl)

scale_label = label.Label(terminalio.FONT, text="OFF", color=0xFF88FF, scale=2)
scale_label.x = 55
scale_label.y = 110
splash.append(scale_label)


# --- MIDI Setup ---
uart = busio.UART(board.TX, board.RX, baudrate=31250, timeout=0.001)
midi = adafruit_midi.MIDI(midi_in=uart, midi_out=uart, in_channel=None, out_channel=0)

# --- Battery Monitor ---
# The MAX17048 uses Maxim's ModelGauge algorithm which tracks battery state over time.
# Simply read cell_percent directly - do NOT use quick_start on boot or custom voltage
# calculations, as these interfere with the algorithm's learned model.
try:
    import adafruit_max1704x
    i2c = board.I2C()
    battery = adafruit_max1704x.MAX17048(i2c)
    has_battery = True

    # Wake from hibernation if needed (hibernation saves power but reduces update rate)
    if battery.hibernating:
        battery.wake()

    print(f"MAX17048: {battery.cell_voltage:.2f}V, {battery.cell_percent:.1f}%")

except Exception as e:
    print(f"Battery monitor not found: {e}")
    has_battery = False

# --- Components ---
note_buffer = NoteBuffer()
arp = Arpeggiator()

# --- Button Setup ---
btn_d0 = digitalio.DigitalInOut(board.D0)
btn_d0.switch_to_input(pull=digitalio.Pull.UP)

btn_d1 = digitalio.DigitalInOut(board.D1)
btn_d1.switch_to_input(pull=digitalio.Pull.DOWN)

btn_d2 = digitalio.DigitalInOut(board.D2)
btn_d2.switch_to_input(pull=digitalio.Pull.DOWN)

# --- State ---
last_btn_time = {"d0": 0, "d1": 0, "d2": 0}
tap_times = []  # For tap tempo
pattern_index = 0
division_index = 1  # Start at 1/8
scale_index = 0
last_display_update = 0
last_batt_update = -2.0  # Trigger first battery read immediately

# Edit mode state - simplified to single edit mode
edit_mode = False  # True when in edit mode
edit_param = 0  # 0=BPM, 1=Pattern, 2=Division, 3=Octave, 4=Scale
NUM_PARAMS = 5  # BPM, Pattern, Division, Octave, Scale
d1_press_time = 0
d1_was_pressed = False
d1_long_press_handled = False  # Prevents repeat triggers while held
blink_state = True
last_blink = 0

# Division list for cycling
DIVISIONS = ["1/4", "1/8", "1/8T", "1/16", "1/16T"]

# Original colors for each parameter
PARAM_COLORS = {
    "BPM": 0xFFFFFF,
    "PAT": 0x00FF88,
    "DIV": 0x00FFFF,
    "OCT": 0xFFFF00,
    "SCL": 0xFF88FF,
}

# Battery state
batt_pct = 0
batt_reads = 0  # Count successful reads before showing
usb_connected = False

print("Arpeggiator Ready")
print("Hold notes on your MIDI controller")
print("Long press D1 for edit mode")

# --- Helper Functions ---
def update_param_display(blink):
    """Update display with current parameter values, applying blink in edit mode."""
    # BPM
    bpm_label.text = str(arp.bpm)
    if edit_mode and edit_param == 0:
        bpm_label.color = PARAM_COLORS["BPM"] if blink else 0x000000
    else:
        bpm_label.color = PARAM_COLORS["BPM"]

    # Pattern
    pattern_label.text = arp.pattern.upper()
    if edit_mode and edit_param == 1:
        pattern_label.color = PARAM_COLORS["PAT"] if blink else 0x000000
    else:
        pattern_label.color = PARAM_COLORS["PAT"]

    # Division
    div_label.text = arp.division
    if edit_mode and edit_param == 2:
        div_label.color = PARAM_COLORS["DIV"] if blink else 0x000000
    else:
        div_label.color = PARAM_COLORS["DIV"]

    # Octave
    oct_label.text = str(arp.octaves)
    if edit_mode and edit_param == 3:
        oct_label.color = PARAM_COLORS["OCT"] if blink else 0x000000
    else:
        oct_label.color = PARAM_COLORS["OCT"]

    # Scale
    scale_label.text = arp.scale
    if edit_mode and edit_param == 4:
        scale_label.color = PARAM_COLORS["SCL"] if blink else 0x000000
    else:
        scale_label.color = PARAM_COLORS["SCL"]

def adjust_param(direction):
    """Adjust the currently selected parameter."""
    global pattern_index, division_index, scale_index

    if edit_param == 0:  # BPM
        new_bpm = arp.bpm + direction
        arp.set_bpm(new_bpm)
    elif edit_param == 1:  # Pattern
        pattern_index = (pattern_index + direction) % len(Arpeggiator.PATTERNS)
        arp.set_pattern(Arpeggiator.PATTERNS[pattern_index])
        arp.build_sequence(note_buffer.notes_in_order if arp.pattern == "order" else note_buffer.notes)
    elif edit_param == 2:  # Division
        division_index = (division_index + direction) % len(DIVISIONS)
        arp.set_division(DIVISIONS[division_index])
    elif edit_param == 3:  # Octave
        new_oct = arp.octaves + direction
        if new_oct < 1:
            new_oct = 4
        elif new_oct > 4:
            new_oct = 1
        arp.set_octaves(new_oct)
        arp.build_sequence(note_buffer.notes_in_order if arp.pattern == "order" else note_buffer.notes)
    elif edit_param == 4:  # Scale
        scale_index = (scale_index + direction) % len(SCALE_NAMES)
        arp.set_scale(SCALE_NAMES[scale_index])
        arp.build_sequence(note_buffer.notes_in_order if arp.pattern == "order" else note_buffer.notes)

# --- Main Loop ---
while True:
    now = time.monotonic()

    # --- Read MIDI Input ---
    msg = midi.receive()
    if msg is not None:
        if isinstance(msg, NoteOn) and msg.velocity > 0:
            note_buffer.note_on(msg.note, msg.velocity)
            arp.build_sequence(note_buffer.notes_in_order if arp.pattern == "order" else note_buffer.notes)
        elif isinstance(msg, NoteOff) or (isinstance(msg, NoteOn) and msg.velocity == 0):
            note_buffer.note_off(msg.note)
            arp.build_sequence(note_buffer.notes_in_order if arp.pattern == "order" else note_buffer.notes)

    # --- Read Buttons ---
    d0 = not btn_d0.value
    d1 = btn_d1.value
    d2 = btn_d2.value

    # --- D1: Long press detection for edit mode ---
    if d1:
        if not d1_was_pressed:
            # Button just pressed
            d1_press_time = now
            d1_was_pressed = True
            d1_long_press_handled = False
        elif not d1_long_press_handled and (now - d1_press_time > 1.0):
            # Long press threshold reached while button still held
            if edit_mode:
                # Exit edit mode
                edit_mode = False
            else:
                # Enter edit mode
                edit_mode = True
                edit_param = 0
            d1_long_press_handled = True  # Don't trigger again until button released
    else:
        if d1_was_pressed:
            # Button released
            if not d1_long_press_handled:
                # Was a short press (< 1 second)
                if edit_mode:
                    # In edit mode: cycle to next parameter
                    edit_param = (edit_param + 1) % NUM_PARAMS
                else:
                    # Normal mode: tap tempo
                    if now - last_btn_time["d1"] > 0.15:
                        tap_times.append(now)
                        if len(tap_times) > 4:
                            tap_times.pop(0)
                        if len(tap_times) >= 2:
                            intervals = [tap_times[i+1] - tap_times[i] for i in range(len(tap_times)-1)]
                            avg_interval = sum(intervals) / len(intervals)
                            if avg_interval > 0:
                                new_bpm = int(60.0 / avg_interval)
                                arp.set_bpm(new_bpm)
                        last_btn_time["d1"] = now
        d1_was_pressed = False

    # --- D0 and D2 behavior ---
    if edit_mode:
        # Edit mode: D0/D2 adjust the selected parameter's value
        if d0 and (now - last_btn_time["d0"] > 0.15):
            adjust_param(-1)
            last_btn_time["d0"] = now

        if d2 and (now - last_btn_time["d2"] > 0.15):
            adjust_param(1)
            last_btn_time["d2"] = now
    else:
        # Normal mode
        # D0: Cycle pattern
        if d0 and (now - last_btn_time["d0"] > 0.25):
            pattern_index = (pattern_index + 1) % len(Arpeggiator.PATTERNS)
            arp.set_pattern(Arpeggiator.PATTERNS[pattern_index])
            arp.build_sequence(note_buffer.notes_in_order if arp.pattern == "order" else note_buffer.notes)
            last_btn_time["d0"] = now

        # D2: Cycle octaves
        if d2 and (now - last_btn_time["d2"] > 0.25):
            new_oct = (arp.octaves % 4) + 1
            arp.set_octaves(new_oct)
            arp.build_sequence(note_buffer.notes_in_order if arp.pattern == "order" else note_buffer.notes)
            last_btn_time["d2"] = now

    # Clear tap tempo if no tap for 2 seconds
    if tap_times and (now - tap_times[-1] > 2.0):
        tap_times.clear()

    # --- Arpeggiator Tick ---
    note_on, note_off = arp.tick(now)

    # Send MIDI
    if note_off is not None:
        midi.send(NoteOff(note_off, 0))
    if note_on is not None:
        midi.send(NoteOn(note_on, 100))

    # --- Update Blink State ---
    blink_interval = 0.25  # Consistent blink rate in edit mode
    if now - last_blink > blink_interval:
        blink_state = not blink_state
        last_blink = now

    # --- Read Battery (every 1 second, or 2 seconds after stabilized) ---
    # Use cell_percent directly from the MAX17048 - it handles all the complexity
    # of LiPo discharge curves and charging via its ModelGauge algorithm
    batt_interval = 1.0 if batt_reads < 2 else 2.0
    if now - last_batt_update > batt_interval:
        usb_connected = supervisor.runtime.usb_connected
        if has_battery:
            try:
                reading = battery.cell_percent
                # Only count as valid if reading is reasonable (not 0 or garbage)
                if 0 < reading <= 100:
                    batt_pct = reading
                    batt_reads += 1
            except:
                pass
        last_batt_update = now

    # --- Update Display (10 Hz) ---
    if now - last_display_update > 0.1:
        update_param_display(blink_state)

        # Update battery display - wait for 2 valid reads to stabilize
        if has_battery and batt_reads >= 2:
            # Add label to display on first valid reading
            if not batt_label_shown:
                splash.append(batt_label)
                batt_label_shown = True

            # Clamp percentage to 0-100 range for display
            pct = max(0, min(100, int(batt_pct)))

            # Show percentage with + indicator when USB connected
            if usb_connected:
                batt_label.text = f"{pct}%+"
            else:
                batt_label.text = f"{pct}%"

            # Color: green when good, grey when moderate, orange/red when low
            if pct <= 5:
                batt_label.color = 0xFF0000 if blink_state else 0x000000  # Blink red
            elif pct <= 10:
                batt_label.color = 0xFF8800  # Orange
            elif pct > 50:
                batt_label.color = 0x00FF00  # Green
            else:
                batt_label.color = 0x888888  # Grey

        last_display_update = now

    time.sleep(0.002)  # 2ms loop for tight MIDI timing
