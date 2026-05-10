# CircuitPython Deployment and Display Initialization

**Date:** 2026-05-09
**Context:** ESP32-S3 Reverse TFT Feather MIDI Arpeggiator

## Key Learnings

### 1. Deployment is Manual

CircuitPython has **no automatic sync** from a local `src/` folder to the device. Files must be explicitly copied to the CIRCUITPY drive.

**The failure mode:** Editing files locally, testing, seeing old behavior, and assuming the code is wrong when actually the device is running stale code.

**Solution:** Always verify deployment by either:
- Checking file timestamps on CIRCUITPY
- Adding a version indicator to the display
- Using a deploy script/command

### 2. Display Blanking Must Be Immediate

The REPL/terminal can flash on screen during the import phase of code.py, even if boot.py sets `root_group = None`.

**Wrong:**
```python
import board
import busio
import displayio  # REPL can flash during these imports
# ... more imports ...

display = board.DISPLAY
display.root_group = splash  # Too late
```

**Right:**
```python
import board
board.DISPLAY.root_group = None  # Blank immediately

import busio
import displayio
# ... rest of imports are safe now
```

### 3. Sensor Stabilization Pattern

Hardware sensors (like MAX17048 battery gauge) often return garbage on first reads. Don't display until readings stabilize.

**Pattern:**
```python
sensor_reads = 0
sensor_value = 0

# In main loop:
reading = sensor.value
if is_valid(reading):  # e.g., 0 < reading <= 100
    sensor_value = reading
    sensor_reads += 1

# Only display after N valid reads
if sensor_reads >= 2:
    show_value(sensor_value)
```

**Bonus:** Use faster polling during stabilization, then slow down:
```python
interval = 1.0 if sensor_reads < 2 else 2.0
```

### 4. Don't Add UI Elements Until Ready

For displayio, don't append labels/elements to the display group until you have valid data. An empty or zero-valued label can still cause visual artifacts (blinking, wrong colors).

**Wrong:**
```python
label = Label(text="")
splash.append(label)  # Added immediately
# Later: label.text = actual_value
```

**Right:**
```python
label = Label(text="")
label_shown = False
# Later, when ready:
if not label_shown:
    splash.append(label)
    label_shown = True
label.text = actual_value
```

### 5. Track boot.py in Source Control

boot.py runs before code.py and configures critical USB/display settings. It's easy to forget it exists since it's not in the typical edit cycle.

**Always keep boot.py in your src/ folder** alongside code.py.

## The Meta-Lesson: Audit Before Fixing

When incremental fixes aren't working, STOP. The problem isn't where you think it is.

In this session: Multiple attempts to fix "battery flashing" in the display logic failed because the actual problem was deployment - the device was running old code.

**The audit process:**
1. What am I assuming? (That code changes are being deployed)
2. How can I verify that assumption? (Check what's actually on the device)
3. What does the documentation/agent say? (CircuitPython has no auto-deploy)
