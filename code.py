# SPDX-License-Identifier: MIT
"""
MIDI Arpeggiator - Phase 3: Full Features
ESP32-S3 Reverse TFT Feather + MIDI FeatherWing

Controls:
- D0: Decrease selected param (edit mode only) / wake display
- D1: Tap tempo (normal) / long press enter/exit edit mode / short press cycle param (edit mode)
- D2: Increase selected param (edit mode only) / wake display
- D0+D2 (hold 2s): Enter deep sleep mode (preserves settings)
- Auto-sleep: After 15 min of no MIDI/button activity
- Any button: Wake from deep sleep

Connect synth MIDI OUT → FeatherWing MIDI IN
Connect FeatherWing MIDI OUT → synth MIDI IN
"""

import board
# Immediately blank display to prevent REPL flash during imports
board.DISPLAY.root_group = None

# Check if waking from deep sleep (must check before any display ops)
waking_from_sleep = False
try:
    import alarm as _alarm_check
    waking_from_sleep = _alarm_check.wake_alarm is not None
except ImportError:
    pass

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

# Deep sleep support - graceful fallback if unavailable
try:
    import alarm
    from alarm.pin import PinAlarm
    DEEP_SLEEP_AVAILABLE = True
except ImportError:
    DEEP_SLEEP_AVAILABLE = False
    alarm = None

# Import our modules
from note_buffer import NoteBuffer
from arpeggiator import Arpeggiator
from scales import SCALE_NAMES

# --- Display Setup ---
display = board.DISPLAY

# Set initial brightness for manual control
display.brightness = 1.0

# Boot splash screen - different for cold boot vs wake from sleep
boot_splash = displayio.Group()
display.root_group = boot_splash

boot_bg = displayio.Bitmap(240, 135, 1)
boot_pal = displayio.Palette(1)
boot_pal[0] = 0x000000
boot_splash.append(displayio.TileGrid(boot_bg, pixel_shader=boot_pal))

if waking_from_sleep:
    # Brief wake indicator
    wake_label = label.Label(terminalio.FONT, text="Waking...", color=0x00FF88, scale=2)
    wake_label.anchor_point = (0.5, 0.5)
    wake_label.anchored_position = (120, 67)
    boot_splash.append(wake_label)
    time.sleep(0.3)
else:
    # Full boot splash
    title_label = label.Label(terminalio.FONT, text="David Wingo's", color=0x888888, scale=2)
    title_label.anchor_point = (0.5, 0.5)
    title_label.anchored_position = (120, 55)
    boot_splash.append(title_label)

    subtitle_label = label.Label(terminalio.FONT, text="Arpeggiator", color=0xFFFFFF, scale=3)
    subtitle_label.anchor_point = (0.5, 0.5)
    subtitle_label.anchored_position = (120, 85)
    boot_splash.append(subtitle_label)

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
# The adafruit_max1704x library constructor calls reset(), which erases the MAX17048's
# ModelGauge learned model. After reset, the chip falls back to raw voltage-based
# estimation which is inaccurate under load. We compensate by:
# 1. Waiting for system stabilization after boot (see Battery Stabilization section)
# 2. Calling quick_start to trigger SOC recalibration from stable voltage
# 3. Using voltage-based sanity checks during the first 4 reads
try:
    import adafruit_max1704x
    i2c = board.I2C()
    battery = adafruit_max1704x.MAX17048(i2c)
    has_battery = True

    # Wake from hibernation if needed (hibernation saves power but reduces update rate)
    if battery.hibernating:
        battery.wake()

except Exception:
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
last_voltage = 0.0  # Track voltage for USB edge detection
usb_connected = True  # Assume USB on boot, detect transitions via voltage

# Display sleep state
last_activity_time = time.monotonic()  # Initialize to boot time
display_dimmed = False
SLEEP_TIMEOUT = 10.0  # Seconds before dimming
DIM_BRIGHTNESS = 0.1  # 10% brightness
FULL_BRIGHTNESS = 1.0  # 100% brightness

# Deep sleep settings
DEEP_SLEEP_TIMEOUT = 900.0  # 15 minutes of no MIDI activity
DEEP_SLEEP_HOLD_TIME = 2.0  # Seconds to hold D0+D2 for manual sleep

# Deep sleep combo detection (D0 + D2 simultaneous long-press)
d0d2_combo_start = 0
d0d2_combo_active = False

# Countdown display (full-screen centered) for sleep combo
countdown_splash = displayio.Group()
countdown_bg = displayio.Bitmap(240, 135, 1)
countdown_pal = displayio.Palette(1)
countdown_pal[0] = 0x000000
countdown_splash.append(displayio.TileGrid(countdown_bg, pixel_shader=countdown_pal))
countdown_label = label.Label(terminalio.FONT, text="", color=0xFF8800, scale=3)
countdown_label.anchor_point = (0.5, 0.5)
countdown_label.anchored_position = (120, 67)
countdown_splash.append(countdown_label)

# MIDI activity tracking for auto-sleep
last_midi_activity = time.monotonic()


def voltage_to_percent_estimate(voltage):
    """Approximate percentage from voltage (fallback when ModelGauge unstable).

    Used during stabilization to reject wildly wrong readings from the
    MAX17048 after its ModelGauge model is reset by the library constructor.
    """
    if voltage >= 4.15:
        return 100
    elif voltage >= 4.0:
        return 85
    elif voltage >= 3.85:
        return 65
    elif voltage >= 3.75:
        return 45
    elif voltage >= 3.65:
        return 25
    elif voltage >= 3.5:
        return 10
    else:
        return 5


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

# --- Deep Sleep Functions ---
def save_state_to_sleep_memory():
    """Save arpeggiator state to sleep memory for restoration on wake."""
    if not DEEP_SLEEP_AVAILABLE:
        return
    # Layout: [magic, bpm, pattern_index, division_index, octaves, scale_index]
    alarm.sleep_memory[0] = 0xAB  # Magic byte to validate data
    alarm.sleep_memory[1] = arp.bpm
    alarm.sleep_memory[2] = pattern_index
    alarm.sleep_memory[3] = division_index
    alarm.sleep_memory[4] = arp.octaves
    alarm.sleep_memory[5] = scale_index

def restore_state_from_sleep_memory():
    """Restore arpeggiator state from sleep memory after wake."""
    global pattern_index, division_index, scale_index
    if not DEEP_SLEEP_AVAILABLE:
        return
    # Check magic byte
    if alarm.sleep_memory[0] != 0xAB:
        return  # Invalid data, use defaults
    # Restore state
    arp.set_bpm(alarm.sleep_memory[1])
    pattern_index = alarm.sleep_memory[2]
    if pattern_index < len(Arpeggiator.PATTERNS):
        arp.set_pattern(Arpeggiator.PATTERNS[pattern_index])
    division_index = alarm.sleep_memory[3]
    if division_index < len(DIVISIONS):
        arp.set_division(DIVISIONS[division_index])
    arp.set_octaves(alarm.sleep_memory[4])
    scale_index = alarm.sleep_memory[5]
    if scale_index < len(SCALE_NAMES):
        arp.set_scale(SCALE_NAMES[scale_index])

def show_sleep_message():
    """Display sleep message briefly, then blank screen before deep sleep."""
    sleep_splash = displayio.Group()
    display.root_group = sleep_splash

    # Black background
    sleep_bg = displayio.Bitmap(240, 135, 1)
    sleep_pal = displayio.Palette(1)
    sleep_pal[0] = 0x000000
    sleep_splash.append(displayio.TileGrid(sleep_bg, pixel_shader=sleep_pal))

    # "SLEEP" in orange, centered
    sleep_label = label.Label(terminalio.FONT, text="SLEEP", color=0xFF8800, scale=3)
    sleep_label.anchor_point = (0.5, 0.5)
    sleep_label.anchored_position = (120, 67)
    sleep_splash.append(sleep_label)

    time.sleep(0.5)

    # Blank the screen before deep sleep so "Waking..." is first thing seen on wake
    sleep_label.color = 0x000000

def enter_deep_sleep():
    """Save state and enter deep sleep until button press."""
    if not DEEP_SLEEP_AVAILABLE:
        return

    # Save state for restoration
    save_state_to_sleep_memory()

    # Show sleep message
    show_sleep_message()

    # Wait for all buttons to be released before sleeping
    while (not btn_d0.value) or btn_d1.value or btn_d2.value:
        time.sleep(0.01)
    time.sleep(0.1)  # Extra debounce delay

    # Release display to free memory and stop rendering
    display.root_group = None

    # Deinit UART (MIDI) to release TX/RX pins
    uart.deinit()

    # Deinit I2C (battery monitor) to release I2C bus
    if has_battery:
        i2c.deinit()

    # Disable TFT power for minimal power consumption
    tft_power = digitalio.DigitalInOut(board.TFT_I2C_POWER)
    tft_power.switch_to_output(value=False)

    # Disable NeoPixel power
    neopixel_power = digitalio.DigitalInOut(board.NEOPIXEL_POWER)
    neopixel_power.switch_to_output(value=False)

    # Release button pins before creating PinAlarms
    btn_d0.deinit()
    btn_d1.deinit()
    btn_d2.deinit()

    # Configure wake alarms for all three buttons
    pin_alarm_d0 = PinAlarm(pin=board.D0, value=False, pull=True)
    pin_alarm_d1 = PinAlarm(pin=board.D1, value=True, pull=True)
    pin_alarm_d2 = PinAlarm(pin=board.D2, value=True, pull=True)

    # Enter deep sleep - device will restart on wake
    alarm.exit_and_deep_sleep_until_alarms(pin_alarm_d0, pin_alarm_d1, pin_alarm_d2)

# Restore state if waking from deep sleep
if waking_from_sleep and DEEP_SLEEP_AVAILABLE:
    restore_state_from_sleep_memory()

# --- Battery Stabilization ---
# The MAX17048 library constructor calls reset(), erasing the ModelGauge learned model.
# We must wait for the system to stabilize (display drawn, MCU settled), then trigger
# quick_start to recalibrate SOC from the current stable voltage.
if has_battery:
    time.sleep(2.0)  # Wait for voltage to settle under stable load
    try:
        battery.quick_start = True  # Trigger SOC recalibration
        time.sleep(0.5)  # Wait for algorithm to update
    except:
        pass


# --- Main Loop ---
while True:
    now = time.monotonic()

    # --- Read MIDI Input ---
    msg = midi.receive()
    if msg is not None:
        last_midi_activity = now  # Reset auto-sleep timer on MIDI activity
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

    # Track activity for display sleep and auto deep sleep
    any_button = d0 or d1 or d2
    wake_press = False  # Flag to consume button press when waking
    if any_button:
        last_activity_time = now
        last_midi_activity = now  # Buttons also reset auto-sleep timer
        if display_dimmed:
            display.brightness = FULL_BRIGHTNESS
            display_dimmed = False
            wake_press = True  # Consume this press - don't trigger actions

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
            if not d1_long_press_handled and not wake_press:
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

    # --- D0 and D2 behavior (edit mode only) ---
    if edit_mode and not wake_press:
        # D0/D2 adjust the selected parameter's value
        if d0 and (now - last_btn_time["d0"] > 0.15):
            adjust_param(-1)
            last_btn_time["d0"] = now

        if d2 and (now - last_btn_time["d2"] > 0.15):
            adjust_param(1)
            last_btn_time["d2"] = now
    # Normal mode: D0/D2 do nothing (only wake from sleep, handled above)

    # --- D0+D2 Combo: Deep Sleep Trigger ---
    if d0 and d2:
        if not d0d2_combo_active:
            d0d2_combo_start = now
            d0d2_combo_active = True
            # Switch to full-screen countdown display
            display.root_group = countdown_splash
        # Show countdown centered
        elapsed = now - d0d2_combo_start
        if elapsed < DEEP_SLEEP_HOLD_TIME:
            countdown_label.text = f"SLEEP {DEEP_SLEEP_HOLD_TIME - elapsed:.1f}"
        elif DEEP_SLEEP_AVAILABLE:
            enter_deep_sleep()
        else:
            countdown_label.text = "NO SLEEP"
            countdown_label.color = 0xFF0000
    else:
        if d0d2_combo_active:
            # Combo released - switch back to main UI
            display.root_group = splash
        d0d2_combo_active = False

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
    blink_interval = 0.5  # Consistent blink rate in edit mode
    if now - last_blink > blink_interval:
        blink_state = not blink_state
        last_blink = now

    # --- Read Battery (every 1 second, or 2 seconds after stabilized) ---
    # Wait for 4 reads to allow ModelGauge algorithm to settle after quick_start
    batt_interval = 1.0 if batt_reads < 4 else 2.0
    if now - last_batt_update > batt_interval:
        if has_battery:
            try:
                reading = battery.cell_percent
                voltage = battery.cell_voltage

                # During stabilization (first 4 reads), use voltage estimate to reject
                # wildly inaccurate readings from the ModelGauge before it settles
                if batt_reads < 4:
                    voltage_estimate = voltage_to_percent_estimate(voltage)
                    # Reject if reading differs from voltage estimate by >25%
                    # (indicates ModelGauge hasn't stabilized yet)
                    if abs(reading - voltage_estimate) <= 25 and 0 <= reading <= 120:
                        batt_pct = reading
                        batt_reads += 1
                else:
                    # After stabilization, trust the ModelGauge
                    if 0 <= reading <= 120:
                        batt_pct = reading

                # Detect USB connect/disconnect via voltage edge detection
                # Voltage drops ~0.04V when USB disconnected (battery takes load)
                # Voltage rises ~0.04V when USB reconnected (charger provides power)
                if last_voltage > 0:
                    voltage_delta = voltage - last_voltage
                    if voltage_delta < -0.03:  # Voltage dropped - USB disconnected
                        usb_connected = False
                    elif voltage_delta > 0.03:  # Voltage rose - USB reconnected
                        usb_connected = True
                last_voltage = voltage
            except:
                pass
        last_batt_update = now

    # --- Update Display (10 Hz) ---
    if now - last_display_update > 0.1:
        update_param_display(blink_state)

        # Update battery display - wait for 4 valid reads to stabilize after quick_start
        if has_battery and batt_reads >= 4:
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

            # Color logic based on battery level
            if pct <= 5:
                batt_label.color = 0xFF0000 if blink_state else 0x000000  # Blink red
            elif pct <= 10:
                batt_label.color = 0xFF8800  # Orange
            elif pct > 50:
                batt_label.color = 0x00FF00  # Green
            else:
                batt_label.color = 0x888888  # Grey

        last_display_update = now

    # Display sleep after inactivity
    if not display_dimmed and (now - last_activity_time > SLEEP_TIMEOUT):
        display.brightness = DIM_BRIGHTNESS
        display_dimmed = True

    # Auto deep sleep after extended MIDI inactivity
    if DEEP_SLEEP_AVAILABLE and (now - last_midi_activity > DEEP_SLEEP_TIMEOUT):
        enter_deep_sleep()

    time.sleep(0.002)  # 2ms loop for tight MIDI timing
