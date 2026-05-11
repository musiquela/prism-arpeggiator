# Prism MIDI Arpeggiator - Project Overview

**Device:** ESP32-S3 Reverse TFT Feather + MIDI FeatherWing  
**Language:** CircuitPython  
**Created:** 2026-05-09  
**Status:** Functional prototype

---

## Project Overview

A hardware MIDI arpeggiator that sits between a MIDI controller and synthesizer. It captures incoming MIDI notes and arpeggiate them according to selectable patterns, divisions, octave ranges, and scale quantization. Features a 240x135 color TFT display showing all parameters, battery status, and a custom boot screen ("David Wingo's Arpeggiator").

The device is fully battery-powered and features a comprehensive UI controlled by three buttons, with two distinct modes: normal operation and parameter editing.

---

## Hardware

### Main Board
- **Adafruit ESP32-S3 Reverse TFT Feather**
  - ESP32-S3 dual-core processor
  - 240x135 color TFT display (IPS, visible from all angles)
  - Display positioned on underside of board ("Reverse TFT")
  - Built-in LiPo battery charging
  - USB-C connector

### Peripherals
- **Adafruit MIDI FeatherWing** (stacks on Feather)
  - 5-pin DIN MIDI IN and OUT connectors
  - Hardware UART connection (TX/RX pins)
  - 31250 baud MIDI standard
  
- **MAX17048 Battery Monitor** (optional, integrated on some Feather models)
  - I2C battery fuel gauge
  - ModelGauge algorithm for accurate state-of-charge
  - Tracks charging state and cell voltage

### Pin Assignments
| Pin | Function |
|-----|----------|
| TX | MIDI OUT (to synth MIDI IN) |
| RX | MIDI IN (from synth MIDI OUT) |
| D0 | Button: Param decrease (edit) / Wake display |
| D1 | Button: Tap tempo / Edit mode / Param select |
| D2 | Button: Param increase (edit) / Wake display |
| I2C (default) | MAX17048 battery monitor |

### Display Specifications
- **Resolution:** 240x135 pixels
- **Colors:** 16-bit color (65,536 colors)
- **Layout:** Portrait orientation
- **Font:** terminalio.FONT (built-in monospace)
- **Scale:** 2x for all text (readable from distance)

---

## Current Features (Implemented)

### MIDI Functionality
- **Pass-through MIDI** when no notes held
- **Note buffer** tracks all held notes with velocity
- **Full MIDI implementation** via `adafruit_midi` library
- **Channel:** Listens on all channels (`in_channel=None`), outputs on channel 1 (`out_channel=0`)
- **Tight timing:** 2ms main loop for precise MIDI response

### Arpeggiator Patterns
Six distinct patterns, selected via button or edit mode:

1. **UP** - Notes ascending, low to high
2. **DOWN** - Notes descending, high to low  
3. **UPDOWN** - Ascend then descend (excludes endpoints on reverse)
4. **DOWNUP** - Descend then ascend
5. **RANDOM** - Randomized order (reshuffles each cycle)
6. **ORDER** - Notes in order played (preserves performance sequence)

### Time Divisions
Five note division options:
- **1/4** - Quarter notes
- **1/8** - Eighth notes (default)
- **1/8T** - Eighth note triplets
- **1/16** - Sixteenth notes
- **1/16T** - Sixteenth note triplets

Gate length fixed at 50% of note duration.

### Octave Range
- **1-4 octaves** selectable
- Notes expand upward from lowest held note
- Each octave adds +12 semitones to all notes

### Scale Quantization
Eight scale options (including OFF):
- **OFF** - No quantization (default)
- **MAJOR** - Major scale (Ionian)
- **MINOR** - Natural minor (Aeolian)
- **PENTATONIC** - Major pentatonic
- **BLUES** - Blues scale
- **DORIAN** - Dorian mode
- **MIXOLYDIAN** - Mixolydian mode
- **HARMONIC** - Harmonic minor

Root note fixed at C (0). Scale quantization snaps incoming notes to nearest scale degree before arpeggiating.

### BPM/Tempo Control
- **Range:** 40-240 BPM
- **Default:** 120 BPM
- **Tap tempo:** Average of last 4 taps
- **Timeout:** Tap buffer clears after 2 seconds of inactivity

### Display Layout
```
┌─────────────────────────────────┐
│                          75%+    │  Battery (top-right, scale=2)
│                                  │
│ BPM 120                          │  Line 1: Tempo
│ PAT UP                           │  Line 2: Pattern (cyan)
│ DIV 1/8                          │  Line 3: Division (cyan)
│ OCT 1                            │  Line 4: Octaves (yellow)
│ SCL OFF                          │  Line 5: Scale (magenta)
└─────────────────────────────────┘
```

Parameter labels (BPM, PAT, DIV, OCT, SCL) are dim grey (0x666666).  
Values are color-coded for quick recognition:
- **BPM:** White (0xFFFFFF)
- **PAT:** Green (0x00FF88)
- **DIV:** Cyan (0x00FFFF)
- **OCT:** Yellow (0xFFFF00)
- **SCL:** Magenta (0xFF88FF)

In edit mode, the selected parameter blinks (500ms on/off).

### Battery Monitoring
- **Percentage display** in top-right corner
- **Stabilization:** Waits for 2 valid reads before showing (prevents garbage data)
- **Sampling rate:** 1 second during stabilization, 2 seconds after
- **USB power indicator:** `+` symbol appears when USB connected
  - Detection via voltage edge detection (not `supervisor.runtime.usb_connected` which doesn't update on ESP32-S3)
  - Voltage drop >0.03V between readings → USB disconnected → `+` disappears
  - Voltage rise >0.03V between readings → USB reconnected → `+` reappears
- **Color coding:**
  - **Red (blinking):** ≤5% - Critical low battery
  - **Orange:** 6-10% - Low battery
  - **Grey:** 11-50% - Normal
  - **Green:** >50% - Good charge
- **Range clamping:** Displays 0-100% even if chip reports >100% (fully charged batteries)

### Display Sleep Mode
- **Trigger:** 10 seconds of inactivity (no button presses)
- **Behavior:** Display dims to 10% brightness
- **Wake:** Any button press restores full brightness
- **Wake press consumed:** The button press that wakes the display does not trigger any other action
- **Purpose:** Battery conservation and reduced visual distraction during performance

### Deep Sleep Mode
- **Manual trigger:** Hold D0 + D2 simultaneously for 2+ seconds
- **Auto trigger:** 15 minutes of no MIDI activity or button presses
- **Countdown display:** Full-screen centered "SLEEP X.X" countdown while holding buttons
- **Sleep sequence:** Shows "SLEEP", then blanks screen before entering deep sleep
- **Wake:** Any button press (D0, D1, or D2) wakes the device
- **Wake message:** Brief "Waking..." indicator (0.3s) on blank screen, then restores UI
- **State preservation:** BPM, pattern, division, octave, and scale settings are saved to sleep memory and restored on wake
- **Power consumption:** ~18µA in deep sleep (vs ~70mA active)
- **Graceful fallback:** If alarm module unavailable, device operates normally without deep sleep
- **Button release detection:** Waits for all buttons to be released before entering deep sleep to prevent immediate wake
- **Peripheral cleanup before sleep:**
  - Display root_group released
  - UART (MIDI) deinitialized
  - I2C (battery monitor) deinitialized
  - TFT_I2C_POWER disabled
  - NEOPIXEL_POWER disabled
  - Button pins deinitialized before PinAlarm creation

**Sleep memory layout (6 bytes):**
| Offset | Content | Valid Range |
|--------|---------|-------------|
| 0 | Magic byte | 0xAB |
| 1 | BPM | 40-240 |
| 2 | pattern_index | 0-5 |
| 3 | division_index | 0-4 |
| 4 | octaves | 1-4 |
| 5 | scale_index | 0-7 |

### Button Controls

#### Normal Mode (default)
- **D0:** Wake display only (no action)
- **D1 (short press):** Tap tempo (2-4 taps to set BPM)
- **D1 (long press > 1 sec):** Enter edit mode
- **D2:** Wake display only (no action)
- **D0+D2 (hold 2 sec):** Enter deep sleep mode

#### Edit Mode
- **D0:** Decrease selected parameter value
- **D1 (short press):** Cycle to next parameter
- **D1 (long press > 1 sec):** Exit edit mode
- **D2:** Increase selected parameter value
- **D0+D2 (hold 2 sec):** Enter deep sleep mode (overrides param adjust)

#### Deep Sleep Mode
- **Any button (D0, D1, or D2):** Wake from deep sleep

**Parameters in edit mode cycle:**
BPM → Pattern → Division → Octave → Scale → (back to BPM)

Each parameter blinks while selected (original color ↔ black, 500ms).

**Button debouncing:**
- 150ms debounce for edit mode buttons (tight response)
- 250ms debounce for normal mode pattern/octave (prevents accidental double-press)
- 2 second hold threshold for deep sleep combo (D0+D2)

### Boot Sequence
1. **boot.py** runs first:
   - Blanks display immediately (prevents REPL flash)
   - Disables USB HID (ESP32-S3 endpoint limitation)
   - Enables USB MIDI
   - Sets USB identification: "Prism MIDI Arpeggiator"

2. **code.py** main sequence:
   - Blanks display immediately (again, to prevent import-time REPL flash)
   - Shows boot splash: "David Wingo's / Arpeggiator" (1.5 seconds)
   - Initializes MIDI, battery, buttons
   - Transitions to main UI
   - Prints "Arpeggiator Ready" to serial console

Total boot time: ~2 seconds

### Architecture Details

**Main loop structure:**
```
while True:
    1. Read MIDI input (non-blocking)
    2. Update note buffer on NoteOn/NoteOff
    3. Read button states
    4. Process D1 long-press detection (edit mode toggle)
    5. Process D0/D2 based on current mode
    6. Tick arpeggiator (returns note_on/note_off)
    7. Send MIDI output
    8. Update blink state (250ms interval)
    9. Read battery (1-2 second interval)
    10. Update display (100ms / 10 Hz)
    11. sleep(0.002)  # 2ms for tight MIDI timing
```

**State persistence:**
- Settings preserved across deep sleep via `alarm.sleep_memory` (BPM, pattern, division, octave, scale)
- All settings reset on full power cycle (no EEPROM storage)
- Last held notes persist in buffer until released
- Tap tempo buffer clears after 2 seconds

---

## Planned Features (Not Yet Implemented)

### Future Enhancements
- Adjustable gate length (currently fixed at 50%)
- Root note selection for scale quantization (currently fixed at C)
- Settings persistence across full power cycles (EEPROM/flash storage) - note: deep sleep already preserves settings via sleep memory
- MIDI clock sync (external tempo source)

---

## Code Architecture

### File Structure
```
/
├── boot.py              # USB/display pre-config (runs before code.py)
├── code.py              # Main program (UI, MIDI I/O, main loop)
├── arpeggiator.py       # Arpeggiator engine (pattern generation, timing)
├── note_buffer.py       # MIDI note buffer (tracks held notes)
├── scales.py            # Scale definitions and quantization logic
└── docs/
    ├── PROJECT-OVERVIEW.md       # This file
    ├── HANDOFF-battery-display.md # Battery debugging context
    └── learnings/
        └── 2026-05-09-circuitpython-deployment.md
```

### Key Classes and Responsibilities

#### `NoteBuffer` (note_buffer.py)
**Purpose:** Track currently held MIDI notes with velocity, preserving play order.

**Key methods:**
- `note_on(note, velocity)` - Add/re-trigger note
- `note_off(note)` - Remove note
- `notes` (property) - Returns sorted list of note numbers
- `notes_in_order` (property) - Returns notes in play order
- `count` (property) - Number of held notes

**Data structure:** List of (note, velocity) tuples

#### `Arpeggiator` (arpeggiator.py)
**Purpose:** Generate arpeggiated sequences from held notes and manage timing.

**Key methods:**
- `set_bpm(bpm)` - Set tempo (40-240)
- `set_pattern(pattern)` - Set arpeggio pattern
- `set_division(division)` - Set note division
- `set_octaves(octaves)` - Set octave spread (1-4)
- `set_scale(scale)` - Set scale quantization
- `build_sequence(notes)` - Rebuild arp sequence from note list
- `tick(now)` - Main timing tick, returns (note_on, note_off)

**Internal state:**
- `_sequence` - Current arpeggio sequence (list of MIDI note numbers)
- `_seq_index` - Current position in sequence
- `_current_note` - Currently playing note (or None)
- `_last_tick` - Time of last note trigger
- `_note_on_time` - Time current note was triggered (for gate timing)

**Timing logic:**
- `tick_interval()` - Seconds between notes (based on BPM and division)
- `gate_time()` - Note duration (tick_interval × gate)
- Note-off sent when gate time expires OR next note starts (whichever first)

#### Scale Quantization (scales.py)
**Purpose:** Snap notes to nearest scale degree.

**Function:** `quantize_to_scale(note, scale_name, root)`
- Takes MIDI note number, scale name, root note
- Returns nearest in-scale MIDI note number
- Handles octave wrapping correctly

**Scale storage:** Dictionary of scale names → semitone offset tuples

### Main Loop Structure

Located in `code.py`, runs at ~500 Hz (2ms sleep).

**Three timing domains:**
1. **MIDI I/O:** Every loop (0.002s) - Critical for low latency
2. **Arpeggiator tick:** Checked every loop, fires based on BPM/division
3. **Display update:** 10 Hz (0.1s) - Balance between responsiveness and efficiency
4. **Battery read:** 1-2 Hz (1-2s) - Slow-changing value, no need for high rate

**Button handling:**
- D0/D2: Simple state read with timestamp-based debouncing
- D1: Complex long-press detection with state machine:
  - `d1_was_pressed` - Tracks button down state
  - `d1_press_time` - Time button was pressed
  - `d1_long_press_handled` - Prevents repeat triggers while held
  - Short press (< 1 sec): Tap tempo or cycle params
  - Long press (≥ 1 sec): Toggle edit mode

**Display optimization:**
- Elements created once at startup
- Only text/color updated in main loop
- `update_param_display(blink)` centralizes all parameter rendering
- Battery label not added to display group until readings stabilize

---

## Controls Reference

### Quick Reference Card

```
╔══════════════════════════════════════════════════════════╗
║  PRISM MIDI ARPEGGIATOR - CONTROLS                       ║
╠══════════════════════════════════════════════════════════╣
║  NORMAL MODE (default)                                   ║
║  ───────────────────────────────────────────────────     ║
║  D0            Wake display only (no action)             ║
║  D1 (tap)      Tap tempo (2-4 taps sets BPM)            ║
║  D1 (hold 1s)  Enter edit mode                           ║
║  D2            Wake display only (no action)             ║
║  D0+D2 (2s)    Enter deep sleep                          ║
║                                                           ║
║  EDIT MODE (selected param blinks)                       ║
║  ───────────────────────────────────────────────────     ║
║  D0            Decrease value                            ║
║  D1 (tap)      Next parameter                            ║
║  D1 (hold 1s)  Exit edit mode                            ║
║  D2            Increase value                            ║
║  D0+D2 (2s)    Enter deep sleep                          ║
║                                                           ║
║  DEEP SLEEP (auto after 15 min idle)                     ║
║  ───────────────────────────────────────────────────     ║
║  Any button    Wake (settings preserved)                 ║
║                                                           ║
║  Parameters: BPM → Pattern → Division → Octave → Scale   ║
╚══════════════════════════════════════════════════════════╝
```

### Parameter Details

| Param | Values | Edit Behavior |
|-------|--------|---------------|
| **BPM** | 40-240 | D0/D2 increment/decrement by 1 |
| **Pattern** | UP, DOWN, UPDOWN, DOWNUP, RANDOM, ORDER | D0/D2 cycle through list |
| **Division** | 1/4, 1/8, 1/8T, 1/16, 1/16T | D0/D2 cycle through list |
| **Octave** | 1, 2, 3, 4 | D0/D2 cycle (wraps 4→1, 1→4) |
| **Scale** | OFF, MAJOR, MINOR, PENTATONIC, BLUES, DORIAN, MIXOLYDIAN, HARMONIC | D0/D2 cycle through list |

### Visual Feedback

**Display colors:**
- White = BPM value
- Green = Pattern name
- Cyan = Division
- Yellow = Octave number
- Magenta = Scale name
- Grey = Parameter labels

**Battery colors:**
- Red (blink) = ≤5%
- Orange = 6-10%
- Grey = 11-50%
- Green = >50%

**Edit mode:** Selected parameter blinks (500ms on/off)

---

## Development Notes

### Known Issues
- **CircuitPython deployment:** No auto-sync from git repo to device. Files must be manually copied to `/Volumes/CIRCUITPY/`. See `docs/learnings/2026-05-09-circuitpython-deployment.md`.

### Testing
- **MIDI Routing:** Synth OUT → Feather IN → Feather OUT → Synth IN
- **Serial Console:** Connect via `/dev/tty.usbmodem*` at 115200 baud for debug output
- **Device Status:** `mount | grep CIRCUITPY` to verify read-write status

### Deployment Workflow
1. Edit code on device: `/Volumes/CIRCUITPY/code.py`
2. Device auto-reloads on save (REPL prints "Soft reboot")
3. Test changes via serial console
4. When working, copy back to git repo:
   ```bash
   cp /Volumes/CIRCUITPY/code.py ~/prism-arpeggiator/code.py
   ```
5. Commit with descriptive message

**Critical rule:** Never edit git repo files and expect device to update. Device only runs `/Volumes/CIRCUITPY/code.py`.

---

## References

**Hardware:**
- [ESP32-S3 Reverse TFT Feather](https://www.adafruit.com/product/5691)
- [MIDI FeatherWing](https://www.adafruit.com/product/4740)

**CircuitPython Libraries:**
- `adafruit_midi` - MIDI protocol implementation
- `adafruit_display_text` - Text rendering
- `adafruit_display_shapes` - Shape primitives
- `adafruit_max1704x` - MAX17048 battery monitor

**Documentation:**
- `docs/learnings/2026-05-09-circuitpython-deployment.md` - Deployment and display learnings
- `docs/HANDOFF-battery-display.md` - Battery debugging context
- `CLAUDE.md` - Project-level Claude Code instructions
- `README.md` - Quick start guide

---

*Document created: 2026-05-10 by Thomas (Research Agent)*
