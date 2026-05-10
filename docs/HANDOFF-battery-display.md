# Battery Display Fix - Handoff

**Branch:** main (or current)
**Device:** ESP32-S3 Reverse TFT Feather
**Battery Chip:** MAX17048

## Problem Statement

Battery percentage is not displaying on the device screen. The `+` USB indicator should also appear/disappear based on USB connection status.

## What the Previous Session Got Wrong

1. **Edited local git file instead of device file** - `/Users/keegandewitt/prism-arpeggiator/code.py` vs `/Volumes/CIRCUITPY/code.py`
2. **Made changes without verifying they deployed** - Device runs `/Volumes/CIRCUITPY/code.py` only
3. **When device went read-only, didn't recover properly** - Session ended with device ejected

## Current State

- Device was ejected (`diskutil eject /Volumes/CIRCUITPY`)
- User needs to **replug USB cable** to remount
- Git repo has the "fixed" code but we don't know if it actually works
- No debug output was captured

## The Code Structure (key locations)

**Battery init** (`code.py:142-156`):
```python
try:
    import adafruit_max1704x
    i2c = board.I2C()
    battery = adafruit_max1704x.MAX17048(i2c)
    has_battery = True
    if battery.hibernating:
        battery.wake()
    print(f"MAX17048: {battery.cell_voltage:.2f}V, {battery.cell_percent:.1f}%")
except Exception as e:
    print(f"Battery monitor not found: {e}")
    has_battery = False
```

**Battery read loop** (`code.py:381-398`):
```python
batt_interval = 1.0 if batt_reads < 2 else 2.0
if now - last_batt_update > batt_interval:
    if has_battery:
        try:
            reading = battery.cell_percent
            charge_rate = battery.charge_rate
            if 0 <= reading <= 100:
                batt_pct = reading
                batt_reads += 1
            usb_connected = charge_rate > 0
        except:
            pass
    last_batt_update = now
```

**Display gate** (`code.py:405`):
```python
if has_battery and batt_reads >= 2:
    # Only then show battery label
```

## Possible Failure Points

1. **`has_battery = False`** - Battery init failed silently
2. **`reading` outside 0-100** - MAX17048 returns >100% or negative
3. **Exception in try block** - Silent `except: pass` hides errors
4. **`batt_reads` never reaches 2** - Validation keeps rejecting readings

## What You Must Do First

### Step 1: Verify Device Mounted Read-Write
```bash
mount | grep CIRCUITPY
```
Must NOT say `read-only`. If it does, eject and replug.

### Step 2: Add Debug Output to Device Code
Edit `/Volumes/CIRCUITPY/code.py` directly (NOT the git repo file).

Change the battery read section to:
```python
batt_interval = 1.0 if batt_reads < 2 else 2.0
if now - last_batt_update > batt_interval:
    print(f"DEBUG: has_battery={has_battery}, batt_reads={batt_reads}")
    if has_battery:
        try:
            reading = battery.cell_percent
            charge_rate = battery.charge_rate
            print(f"DEBUG: reading={reading}, charge_rate={charge_rate}")
            if 0 <= reading <= 100:
                batt_pct = reading
                batt_reads += 1
                print(f"DEBUG: Valid! batt_reads now {batt_reads}")
            else:
                print(f"DEBUG: Invalid reading {reading}")
            usb_connected = charge_rate > 0
        except Exception as e:
            print(f"DEBUG: Exception: {e}")
    last_batt_update = now
```

### Step 3: Watch Serial Output
```bash
# Find the serial port
ls /dev/tty.usbmodem*

# Connect to it (replace with actual port)
screen /dev/tty.usbmodem14101 115200
```

Or use `minicom` or Mu editor's serial console.

### Step 4: Analyze Output

The debug prints will tell you exactly which condition is failing:
- `has_battery=False` → Battery chip init failed
- `reading=256` or similar → MAX17048 returning garbage
- `Exception: ...` → Something throwing in the try block
- `Invalid reading X` → Reading outside 0-100

## Key Documentation

- **Learnings doc:** `docs/learnings/2026-05-09-circuitpython-deployment.md`
- **MAX17048 library:** `adafruit_max1704x` - properties: `cell_percent`, `cell_voltage`, `charge_rate`
- **Deployment rule:** Always edit `/Volumes/CIRCUITPY/code.py` directly, then copy back to git repo AFTER verifying

## After Fix Works

1. Remove debug prints
2. Copy working code to git repo:
   ```bash
   cp /Volumes/CIRCUITPY/code.py /Users/keegandewitt/prism-arpeggiator/code.py
   ```
3. Commit with message explaining root cause

## What NOT To Do

- Don't edit the local git repo and expect device to update
- Don't make changes without serial console attached
- Don't use silent `except: pass` - always log exceptions
- Don't trust "I think I know what's wrong" - get debug output first
