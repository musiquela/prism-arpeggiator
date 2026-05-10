# SPDX-License-Identifier: MIT
"""Musical scales for note quantization."""


# Scale definitions as semitone offsets from root
SCALES = {
    "OFF": None,
    "MAJOR": (0, 2, 4, 5, 7, 9, 11),
    "MINOR": (0, 2, 3, 5, 7, 8, 10),
    "PENTATONIC": (0, 2, 4, 7, 9),
    "BLUES": (0, 3, 5, 6, 7, 10),
    "DORIAN": (0, 2, 3, 5, 7, 9, 10),
    "MIXOLYDIAN": (0, 2, 4, 5, 7, 9, 10),
    "HARMONIC": (0, 2, 3, 5, 7, 8, 11),
}

SCALE_NAMES = list(SCALES.keys())


def quantize_to_scale(note, scale_name, root=0):
    """
    Quantize a note to the nearest note in a scale.

    Args:
        note: MIDI note number (0-127)
        scale_name: Key from SCALES dict
        root: Root note (0=C, 1=C#, etc.)

    Returns:
        Quantized MIDI note number
    """
    if scale_name == "OFF" or SCALES.get(scale_name) is None:
        return note

    scale = SCALES[scale_name]

    # Get note's position relative to root
    note_in_octave = (note - root) % 12
    octave = (note - root) // 12

    # Find closest scale degree
    min_distance = 12
    closest = note_in_octave

    for degree in scale:
        # Check distance to this scale degree
        dist = abs(note_in_octave - degree)
        # Also check wrapping around octave
        dist_wrap = 12 - dist
        actual_dist = min(dist, dist_wrap)

        if actual_dist < min_distance:
            min_distance = actual_dist
            closest = degree

    # Reconstruct the note
    return root + (octave * 12) + closest
