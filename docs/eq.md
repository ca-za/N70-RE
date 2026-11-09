# Equalizer (opcode 0x22)

The N70 has **no preset characteristic `000B`** (the legacy EQ of other models), but a **parametric EQ with 20 filter slots** via the command channel.

## Format

Read: `FF 03 FE 01 22` → reply `FF 91 22 8F <143 bytes>`

```
[0]      preset ID           (factory: 0x81)
[1..2]   master gain int16 LE, /100 dB   (factory: 0xFB50 = −12.00 dB)
[3..]    20 × 7 bytes:
         freq  u16 LE (Hz)
         gain  int16 LE (/100 dB)
         Q     u16 LE (/100)
         type  u8   (0xFF = placeholder/unused, 2 = bell/peak, 3 = probably shelf)
         empty slots: 7 × 0x00
```

Write: **the same layout** with `FF 91 22 8F <143 bytes>` ✅ tested – the device applies it and reading back returns exactly the written bytes. Audibly confirmed ("more bass": 62 Hz +4 dB, 200 Hz −5 instead of −9 dB).

Also tested ✅: filters on **new frequencies** (50 Hz, 100 Hz in the "gentle bass" profile) are accepted.

## Factory curve (`data/eq_original.hex`)

| Slot | Frequency | Gain | Q | Type |
|---|---|---|---|---|
| 0 | 31 Hz | 0 | 1.00 | FF |
| 1 | 62 Hz | 0 | 1.00 | FF |
| 2 | 125 Hz | 0 | 1.00 | FF |
| 3 | 200 Hz | −9.0 dB | 0.70 | 2 |
| 4 | 250 Hz | 0 | 1.00 | FF |
| 5 | 500 Hz | 0 | 1.00 | FF |
| 6 | 900 Hz | −1.0 dB | 0.70 | 2 |
| 7 | 1000 Hz | +1.0 dB | 1.00 | FF |
| 8 | 2800 Hz | +2.0 dB | 1.20 | 2 |
| 9 | 7000 Hz | −1.0 dB | 1.20 | 3 |
| 10 | 8000 Hz | 0 | 1.00 | FF |
| 11 | 8500 Hz | −7.0 dB | 3.50 | 2 |
| 12 | 15000 Hz | −2.0 dB | 4.00 | 2 |
| 13 | 16000 Hz | 0 | 1.00 | FF |
| 14–19 | empty | | | |

Notable: slot 7 (1000 Hz) has +1 dB but type FF – probably has no effect.

## Factory curve = the "Spatial" preset

The factory EQ in `data/eq_original.hex` is **exactly the N70's "Spatial sound effects" preset** (id 10) from the server control panel: same 6 bands (200/900/2800/8500/7000/15000 Hz), same gains (−9/−1/+2/−7/−1/−2), same Q, same types, same master gain −12 dB. The device ships with this preset applied but stores it under the custom-EQ ID `0x81` (not id 10). So byte 0 is only a tag; the content is what matters.

## Presets (from the N70 control panel)

All N70 presets, master gain −12 dB each (raw values from `data/controlpanel_n70.json`; gains in dB, freq in Hz). The app sends these as a 0x22 frame; unused of the 20 slots are padded. "Default" is identical to "Spatial".

| id | Name | Freq | Gain | Q | iitType |
|---|---|---|---|---|---|
| 10 | Spatial sound effects | 200,900,2800,8500,7000,15000 | −9,−1,2,−7,−1,−2 | 0.7,0.7,1.2,3.5,1.2,4 | 2,2,2,2,3,2 |
| 1 | Default | (same as Spatial) | | | |
| 14 | Soft Soundstage | 50,200,900,2800,8500,7000,15000 | 2,−8.5,−1,2,−10.5,−1,−2.5 | 0.5,0.7,0.7,1.2,3.8,1.2,4 | 2,2,2,2,2,3,2 |
| 2 | Pop | 60,200,900,2800,8000 | −3,−9,−1,2,−7 | 0.5,0.7,0.7,1.2,3.5 | 2,2,2,2,2 |
| 3 | Heavy Bass | 60,200,900,2800,8000 | 5,−7,−1,1,−7 | 0.5,0.7,0.7,1.2,0.8 | 2,2,2,2,2 |
| 4 | Rock | 60,200,900,2800,8000 | 5,−12,−2,2,−7 | 0.5,0.7,0.7,1.2,3.5 | 2,2,2,2,2 |
| 5 | Soft | 50,200,900,2800,8000 | −2,−9,−1,1,−8 | 0.5,0.7,0.7,1.2,1 | 2,2,2,2,2 |
| 6 | Classic | 60,200,900,2800,8000 | 3,−5,−1,2,−7 | 0.5,0.7,0.7,1.2,3.5 | 2,2,2,2,2 |

"Personalized" (id 11) is an 8-band curve (63…8000 Hz) derived from a hearing test (`soundDB` per band). Almost every band uses iitType 2; only the top band of Spatial/Soft-Soundstage uses 3.

## Open points

- Meaning of the preset ID (0x81; qcyx lists `0x80` = custom, `0x01..0x0A` presets for HT08). Confirmed: the N70 stores the factory Spatial preset under 0x81, so the ID is a tag, not a selector. Whether writing id 1–14 makes the device load its own stored preset is untested.
- Type codes: reliably tell 2 and 3 apart (listening test with a shelf at 100 Hz).
- Does the master gain act as real gain? (A neutral profile with −12 dB was not reported as quieter, but this wasn't tested specifically.)
- Contradiction in the sources about byte 0 for a custom EQ: OpenQCY 8, Quicky 2. On the N70 keeping 0x81 works.
