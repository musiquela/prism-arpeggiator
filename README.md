# Prism MIDI Arpeggiator

A MIDI arpeggiator running on the ESP32-S3 Reverse TFT Feather with MIDI FeatherWing.

## Hardware

- [Adafruit ESP32-S3 Reverse TFT Feather](https://www.adafruit.com/product/5691)
- [Adafruit MIDI FeatherWing](https://www.adafruit.com/product/4740)
- LiPo battery (optional)

## Features

- Multiple arpeggiator patterns: Up, Down, Up-Down, Random, Order (as played)
- Tap tempo with visual BPM display
- Adjustable time divisions: 1/4, 1/8, 1/8T, 1/16, 1/16T
- 1-4 octave range
- Scale quantization
- Battery percentage display with USB charging indicator
- Edit mode for all parameters via 3 buttons

## Controls

- **D0**: Cycle pattern (normal) / decrease value (edit mode)
- **D1**: Tap tempo (normal) / long press to enter/exit edit mode / short press to cycle parameters (edit mode)
- **D2**: Cycle octaves (normal) / increase value (edit mode)

## Installation

1. Install CircuitPython on your ESP32-S3 Reverse TFT Feather
2. Copy the required libraries to `CIRCUITPY/lib/`:
   - `adafruit_midi`
   - `adafruit_display_text`
   - `adafruit_display_shapes`
   - `adafruit_max1704x`
3. Copy all `.py` files to `CIRCUITPY/`:
   - `boot.py`
   - `code.py`
   - `arpeggiator.py`
   - `note_buffer.py`
   - `scales.py`

## Wiring

Connect your MIDI controller/synth:
- Synth MIDI OUT → FeatherWing MIDI IN
- FeatherWing MIDI OUT → Synth MIDI IN

## License

MIT
