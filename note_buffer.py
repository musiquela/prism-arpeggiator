# SPDX-License-Identifier: MIT
"""Note buffer for tracking held MIDI notes."""


class NoteBuffer:
    """Tracks currently held notes with velocity, in order received."""

    def __init__(self):
        self._notes = []  # List of (note, velocity) tuples

    def note_on(self, note, velocity):
        """Add a note to the buffer."""
        # Remove if already exists (re-trigger)
        self._notes = [(n, v) for n, v in self._notes if n != note]
        self._notes.append((note, velocity))

    def note_off(self, note):
        """Remove a note from the buffer."""
        self._notes = [(n, v) for n, v in self._notes if n != note]

    def clear(self):
        """Clear all notes."""
        self._notes = []

    @property
    def notes(self):
        """Return list of held notes (just note numbers, sorted low to high)."""
        return sorted([n for n, v in self._notes])

    @property
    def notes_with_velocity(self):
        """Return list of (note, velocity) tuples, sorted by note."""
        return sorted(self._notes, key=lambda x: x[0])

    @property
    def notes_in_order(self):
        """Return notes in the order they were played."""
        return [n for n, v in self._notes]

    @property
    def count(self):
        """Number of held notes."""
        return len(self._notes)

    def __len__(self):
        return len(self._notes)

    def __bool__(self):
        return len(self._notes) > 0
