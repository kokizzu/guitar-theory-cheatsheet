# Guitar Theory Cheatsheet

Programmatically drawn dark-mode guitar theory cheatsheet with:

- String 1 (high E) on the top line and string 6 (low E) on the bottom line
- CAGED and arpeggio diagrams
- Ionian, Aeolian, pentatonic, and blues scale diagrams
- Rainbow interval colors
- SVG plus 1920×1080 and 3840×2160 PNG outputs

## Preview

[![Guitar theory cheatsheet preview](guitar_theory_cheatsheet_programmatic_1920x1080.png)](guitar_theory_cheatsheet_programmatic.svg)

Open the [SVG preview](guitar_theory_cheatsheet_programmatic.svg) for the scalable version.

## Poster Guide

The poster is a movable interval map. C is used only as the drawing reference, so the same shapes can be moved to any root.

- The left side shows the CAGED chord shapes and arpeggios across the C, A, G, E, and D shape positions.
- The right side shows scale patterns across five connected CAGED positions.
- Fretboards are drawn with string 1, high E, on top and string 6, low E, on the bottom.
- Each colored note is labeled by interval function: `R`, `2`, `b3`, `3`, `4`, `b5`, `5`, `b6`, `6`, `b7`, `7`, or `bb7`.

## Interval Names

Intervals are named by letter distance and size from the root, not only by the fret where the note appears. `b` means lowered one semitone, and `bb` means lowered two semitones.

| Label | Meaning |
| --- | --- |
| `R` or `1` | Root |
| `2` | Major 2nd |
| `b3` | Minor 3rd |
| `3` | Major 3rd |
| `4` | Perfect 4th |
| `b5` | Diminished 5th |
| `5` | Perfect 5th |
| `b6` | Minor 6th |
| `6` | Major 6th |
| `b7` | Minor 7th |
| `7` | Major 7th |
| `bb7` | Diminished 7th |

`bb7` is enharmonically the same pitch as `6` in 12-tone equal temperament, but it has a different harmonic name. In C, `6` is A, while `bb7` is B double-flat. Both sound as A, but a diminished seventh chord is spelled as stacked thirds:

```text
C  Eb  Gb  Bbb
R  b3  b5  bb7
```

Writing the last note as `bb7` shows that it is a seventh chord. Writing it as `6` would describe the same fret, but it would hide the diminished-seventh spelling.

## Formulas

Scale step formulas are measured from one note to the next up to the octave. `1` means a whole step, `1/2` means a half step, and `1 1/2` means three frets.

| Poster item | Interval formula | Step formula |
| --- | --- | --- |
| CAGED major chord | `R 3 5` | - |
| Major arpeggio | `R 3 5` | - |
| Minor arpeggio | `R b3 5` | - |
| Diminished arpeggio | `R b3 b5` | - |
| Major 7 arpeggio | `R 3 5 7` | - |
| Dominant 7 arpeggio | `R 3 5 b7` | - |
| Minor 7 arpeggio | `R b3 5 b7` | - |
| Diminished 7 arpeggio | `R b3 b5 bb7` | - |
| Ionian mode, major scale | `R 2 3 4 5 6 7` | `1-1-1/2-1-1-1-1/2` |
| Aeolian mode, natural minor scale | `R 2 b3 4 5 b6 b7` | `1-1/2-1-1-1/2-1-1` |
| Major pentatonic scale | `R 2 3 5 6` | `1-1-1 1/2-1-1 1/2` |
| Minor pentatonic scale | `R b3 4 5 b7` | `1 1/2-1-1-1 1/2-1` |
| Major blues scale | `R 2 b3 3 5 6` | `1-1/2-1/2-1 1/2-1-1 1/2` |
| Minor blues scale | `R b3 4 b5 5 b7` | `1 1/2-1-1/2-1/2-1 1/2-1` |

## Output Files

- `guitar_cheatsheet_generator.py`: source generator
- `guitar_theory_cheatsheet_programmatic.svg`: scalable vector output
- `guitar_theory_cheatsheet_programmatic_1920x1080.png`: lower-resolution preview PNG
- `guitar_theory_cheatsheet_programmatic_3840x2160.png`: high-resolution PNG
- `guitar_cheatsheet_programmatic_bundle.zip`: bundled source, SVG, and PNG outputs

The generated files and Python source are committed directly to this repository.
