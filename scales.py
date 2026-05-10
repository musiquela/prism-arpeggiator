# SPDX-License-Identifier: MIT
"""Musical scales for note quantization."""


# Scale definitions as semitone offsets from root
SCALES = {
    "OFF": None,  # No quantization
    "MAJ": (0, 2, 4, 5, 7, 9, 11),  # Major
    "MIN": (0, 2, 3, 5, 7, 8, 10),  # Natural Minor
    "PEN": (0, 2, 4, 7, 9),  # Major Pentatonic
    "BLU": (0, 3, 5, 6, 7, 10),  # Blues
    "DOR": (0, 2, 3, 5, 7, 9, 10),  # Dorian
    "MIX": (0, 2, 4, 5, 7, 9, 10),  # Mixolydian
    "HMN": (0, 2, 3, 5, 7, 8, 11),  # Harmonic Minor
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
