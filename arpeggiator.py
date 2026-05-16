# SPDX-License-Identifier: MIT
"""Arpeggiator engine with multiple patterns and timing."""

import random
import time


class Arpeggiator:
    """Core arpeggiator engine."""

    # Pattern types
    PATTERNS = ["up", "down", "updown", "downup", "random", "order"]

    # Note divisions (relative to quarter note)
    # Use exact fractions for triplets to prevent cumulative drift
    DIVISIONS = {
        "1/4": 1.0,
        "1/8": 0.5,
        "1/8T": 1.0 / 3.0,   # Exact third
        "1/16": 0.25,
        "1/16T": 1.0 / 6.0,  # Exact sixth
    }

    def __init__(self):
        self.bpm = 120
        self.pattern = "up"
        self.division = "1/8"
        self.octaves = 1  # 1-4
        self.gate = 0.5  # 0.25, 0.5, 0.75, 1.0
        self.swing = 0  # Swing percentage (0-50, increments of 5)

        self._sequence = []
        self._seq_index = 0
        self._direction = 1  # 1=up, -1=down (for updown/downup)
        self._swing_phase = 0  # 0 or 1, toggles each tick
        self._last_tick = 0
        self._current_note = None
        self._note_on_time = 0

    def set_bpm(self, bpm):
        """Set tempo (40-240 BPM)."""
        self.bpm = max(40, min(240, bpm))

    def set_pattern(self, pattern):
        """Set arpeggio pattern."""
        if pattern in self.PATTERNS:
            self.pattern = pattern
            self._seq_index = 0
            self._direction = 1

    def set_division(self, division):
        """Set note division."""
        if division in self.DIVISIONS:
            self.division = division

    def set_octaves(self, octaves):
        """Set octave spread (1-4)."""
        self.octaves = max(1, min(4, octaves))

    def set_gate(self, gate):
        """Set gate length (0.25-1.0)."""
        self.gate = max(0.25, min(1.0, gate))

    def set_swing(self, swing):
        """Set swing percentage (0-50, increments of 5)."""
        self.swing = max(0, min(50, swing))

    def build_sequence(self, notes):
        """Build arpeggiated sequence from held notes."""
        if not notes:
            self._sequence = []
            return

        old_len = len(self._sequence)
        old_first = self._sequence[0] if self._sequence else None

        # Use notes directly (no scale quantization)
        quantized = list(notes)

        # Expand octaves
        expanded = []
        for octave in range(self.octaves):
            for note in quantized:
                expanded.append(note + (octave * 12))

        # Apply pattern
        if self.pattern == "up":
            self._sequence = sorted(expanded)
        elif self.pattern == "down":
            self._sequence = sorted(expanded, reverse=True)
        elif self.pattern == "updown":
            up = sorted(expanded)
            if len(up) > 1:
                self._sequence = up + up[-2:0:-1]  # Exclude endpoints on reverse
            else:
                self._sequence = up
        elif self.pattern == "downup":
            down = sorted(expanded, reverse=True)
            if len(down) > 1:
                self._sequence = down + down[-2:0:-1]
            else:
                self._sequence = down
        elif self.pattern == "random":
            self._sequence = expanded[:]
            random.shuffle(self._sequence)
        elif self.pattern == "order":
            # Notes in order played, with octave expansion
            self._sequence = []
            for note in notes:  # notes should be in play order
                for octave in range(self.octaves):
                    self._sequence.append(note + (octave * 12))

        # Handle index when sequence changes
        if self._seq_index >= len(self._sequence):
            self._seq_index = 0
        # Prevent double-play of first note when chord is being built:
        # If sequence grew, index is at 0, and first note is same, advance to skip replay
        elif (len(self._sequence) > old_len and
              self._seq_index == 0 and
              old_first is not None and
              self._sequence[0] == old_first):
            self._seq_index = 1 if len(self._sequence) > 1 else 0

    def tick_interval(self):
        """Calculate time between notes in seconds."""
        quarter_note = 60.0 / self.bpm
        return quarter_note * self.DIVISIONS[self.division]

    def gate_time(self):
        """Calculate note-on duration in seconds."""
        return self.tick_interval() * self.gate

    def tick(self, now):
        """
        Called every loop iteration.
        Returns: (note_on, note_off) where each is None or a note number.
        """
        note_on = None
        note_off = None

        if not self._sequence:
            # No notes held - turn off any playing note
            if self._current_note is not None:
                note_off = self._current_note
                self._current_note = None
            return note_on, note_off

        base_interval = self.tick_interval()

        # Apply swing timing
        if self.swing > 0:
            swing_factor = self.swing / 100.0
            if self._swing_phase == 0:
                interval = base_interval * (1 + swing_factor)
            else:
                interval = base_interval * (1 - swing_factor)
        else:
            interval = base_interval

        # Gate based on base interval (consistent note lengths)
        gate_duration = base_interval * self.gate

        # Check if current note should turn off
        if self._current_note is not None:
            if now - self._note_on_time >= gate_duration:
                note_off = self._current_note
                self._current_note = None

        # Check if it's time for next note
        if now - self._last_tick >= interval:
            # Get next note from sequence
            next_note = self._sequence[self._seq_index]

            # Turn off previous note if still on
            if self._current_note is not None and self._current_note != next_note:
                note_off = self._current_note

            # Turn on new note
            note_on = next_note
            self._current_note = next_note
            self._note_on_time = now

            # Absolute timing: advance by exactly one interval
            # This prevents cumulative drift from loop latency
            self._last_tick += interval

            # Catch-up: if we've fallen too far behind (>2 intervals),
            # reset to now to prevent burst of notes after pause/tempo change
            if now - self._last_tick > interval * 2:
                self._last_tick = now

            # Advance sequence index
            self._seq_index = (self._seq_index + 1) % len(self._sequence)

            # Toggle swing phase
            self._swing_phase = 1 - self._swing_phase

            # For random pattern, reshuffle when we loop
            if self.pattern == "random" and self._seq_index == 0:
                random.shuffle(self._sequence)

        return note_on, note_off

    def reset(self):
        """Reset arpeggiator state."""
        self._sequence = []
        self._seq_index = 0
        self._direction = 1
        self._swing_phase = 0
        self._last_tick = 0
        self._current_note = None

    @property
    def current_note(self):
        """Currently playing note."""
        return self._current_note

    @property
    def sequence_length(self):
        """Length of current sequence."""
        return len(self._sequence)
