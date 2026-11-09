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

## Open points

- Meaning of the preset ID (0x81; qcyx lists `0x80` = custom, `0x01..0x0A` presets for HT08). Whether other IDs activate factory presets is untested.
- Type codes: reliably tell 2 and 3 apart (listening test with a shelf at 100 Hz).
- Does the master gain act as real gain? (A neutral profile with −12 dB was not reported as quieter, but this wasn't tested specifically.)
- Contradiction in the sources about byte 0 for a custom EQ: OpenQCY 8, Quicky 2. On the N70 keeping 0x81 works.
