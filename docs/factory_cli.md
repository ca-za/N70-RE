# Factory CLI (hidden command interface, service 7033)

The WuQi chip has a factory/debug command line that the QCY app never exposes to users. It is reachable over BLE service `7033`, characteristics `1001` (write) / `1002` (notify) — the same channel described in [ota.md](ota.md), CLI side. This is reconstructed from the WuQi ADK source (`work/zt210-sdk/`, a related product) cross-checked against the N70 firmware strings.

> ⚠️ **Documentation only.** Project rules forbid writing to service 7033. Many of these commands are destructive (arbitrary memory/flash writes, OEM MAC overwrite, reset, power-off, charger/voltage changes). Nothing here has been sent to the device; this records what the interface *is*.

## Framing (confirmed from `cli.c`)

```
23 23 | header(12 bytes) | payload(msg_length) | 40 40
```
Header (`cli_msg_header_t`, packed, little-endian):

| off | size | field |
|---|---|---|
| 0 | 2 | module_id |
| 2 | 2 | crc = high 16 bits of CRC-32(payload) |
| 4 | 2 | msg_id |
| 6 | 1 | flags (auto_ack:1, type:3 — 0=cmd/1=resp/2=ind) |
| 7 | 1 | result |
| 8 | 2 | msg_length (payload length) |
| 10 | 2 | msg_sn |

Markers `0x2323` / `0x4040`, `msg_length ≤ 512`. Dispatch is by `(module_id, msg_id)`. On the N70 this CLI is bridged to GATT 7033/1001(RX)/1002(TX); only the TWS master processes it. (The N70 uses the non-legacy 12-byte header; a legacy 24-byte variant with src/dst addresses exists behind a build flag.)

## Module IDs

`DEBUGLOG=0, COMMUNICATION=1, HOSTINTERFACE=2, FTM=3, COMMON=4, LOWPOWER=5, APPLICATION=6, BT_APPL=7, AUDIO=8, DRIVER_COMMON=0x100, DRIVER_CHARGER=0x101, DRIVER_LED=0x102`.

## Command catalog

67 commands registered via `CLI_ADD_COMMAND(module, msg_id, handler)`. `msg#` = numeric msg id. Behaviour read from the handler bodies. ⚠ marks destructive/risky.

### COMMON (module 4)
| msg# | name | what it does |
|---|---|---|
| 0 | GET_CHIP_INFO | SoC ID (2×32-bit) |
| 4 | READ_DATA | ⚠ **arbitrary read** of any REG/RAM address |
| 6 | SET_DATA | ⚠⚠ **arbitrary write** to any RAM/MMIO address (full chip control, can brick) |
| 17 | SET_KV | ⚠ persistent key-value / flash write |
| 18 | GET_KV | read a KV record |
| 23 | SOFT_RST | ⚠ reboot (optional delay + reason) |
| 24 | SET_CLOCK_MODE | ⚠ switch DVFS clock mode (can hang) |
| 25 | SET_LOG_LEVEL | set debug log level |
| 26 | OEM_PPM_SET | ⚠ rewrite OEM ppm in OEM flash |
| 27 | GET_FW_VER | firmware version string |
| 28 | GET_ATE_VER | hw version from cal data |
| 29 | GET_CAL_DATA | dump calibration data |
| 30 | GET_OEM_DATA | dump OEM data block |
| 31 | GET_ANC_DATA | ANC OEM blob |
| 32 | GET_ROM_VER | ROM library version |
| 33 | CALC_CRC | ⚠ CRC over an arbitrary address range (read primitive) |
| 34 | OEM_MAC_SET | ⚠⚠ overwrite the 6-byte BT MAC (device identity) |
| 35 | CAP_CODE_SET | ⚠ live crystal trim cap (clock/RF accuracy) |
| 37 | ROM_CRC_CHECK | ⚠ heavy clock/voltage manipulation; also writes a result into OEM flash |

### APPLICATION (module 6)
| msg# | name | what it does |
|---|---|---|
| 0 | SEND_USER_EVENT | ⚠ inject any internal UI event (see event list below) |
| 1 | SEND_APP_MSG | ⚠ inject an internal app message |
| 2 | SEND_BT_RPC_CMD | ⚠ send an RPC command to the BT core |
| 3 | SEND_HCI_CMD | ⚠⚠ raw HCI command to the controller |
| 4 | GET_BDADDR | local + peer BT address |
| 5 | TWS_PAIR | ⚠ re-pair the two earbuds |
| 6 | SEND_HCI_DATA | ⚠⚠ raw HCI ACL data |
| 7 | ENABLE_HCI_PASSTHROUGH | enable HCI event passthrough |
| 8 | GET_TWS_STATE | master/left/connected |
| 9 | GET_BATTERY_STATE | mV + charging |
| 11 | GET_KEY_STATE | is a key pressed |
| 12 | CONTROL_LED | force an LED on/off |
| 13 | SET_PEER_ADDR | ⚠ set TWS peer address |
| 14 | GET_OEM_BDADDR | OEM MAC |
| 15 | EN_BATTERY_REPORT | enable battery reporting |
| 16 | GET_TOUCH_KEY_INFO | touch-key raw CDC/counters |
| 17 | GET_TOUCH_INEAR_CDC | in-ear sensor raw CDC |
| 18 | EN_TONE | enable/disable prompt tones |
| 19 | GET_NTC_VOLT | thermistor voltage |
| 20 | GET_OEM_PPM | OEM ppm |
| 21 | GET_BTN_PRESSED | all-buttons-released state |
| 22 | GET_BT_NAME | local BT name |
| 23 | GET_CUSTOM_VER | custom/build version |
| 24 | GET_BAT | battery level local+peer |
| 25 | GET_INEAR | in-ear local+peer |
| 26 | GET_ANC | current ANC/listen mode |

(`AT_TEST`=10 is enumerated but has no binary handler — the N70 instead has a separate ASCII `AT+…` command parser, see below.)

### AUDIO (module 8)
Speaker trims — `SPK_DIG_GAIN_ADJUST`=2, `SPK_ANA_GAIN_ADJUST`=3, `SPK_DCDC_1P2_MODEFY`=4 (⚠ changes a 1.2 V core rail). The N70 additionally has a whole **ANC CLI** (`cli_audio_anc.c`, not in the reference SDK) backing the defined-but-unhandled ANC msgids: `ANC_SET_COEFF_PARAM`=0, dump 5/6, play-sweep 7/8, `ANC_WRITE_COEFF_TO_FLASH`=9 ⚠, `ANC_READ_COEFF_FROM_FLASH`=16, `ANC_SECRET_HANDSHAKE`=14, … (ANC filter-coefficient tuning), plus an N70-only **speaker DC-offset calibration** `cli_audio_spk_dc_cal_modify_handler` (per-channel L/R offset). Msgid numbers for the N70-only ANC/dc-cal handlers aren't confirmed (the enum is a superset).

### FTM (module 3) — factory test
MADC capture (`3000`–`3006`: start/stop/init/channel/poll/dump/set-audio-gain), `GPIO_SET`=5001 (⚠ drive any pin), touch-key vref trim `6000`.

### LOWPOWER (module 5)
`ENTER_LIGHT_SLEEP`=0, `ENTER_DEEP_SLEEP`=1 ⚠, `SET_WAKEUP_SRC`=2, `ENTER_SHUTDOWN`=3 ⚠ (device goes fully dark), `SET_SLEEP_THR`=4, `DISABLE_VOLTAGE_COMPATIBLE`=5.

### CHARGER (module 257) / LED (module 258)
Charger: disable pin GPIO mode=0 ⚠, set current=1 ⚠, get config=2. LED: `LED_OPERATE`=0 (off path).

## Internal user events (via APPLICATION/SEND_USER_EVENT)

`SEND_USER_EVENT` calls `app_evt_send(evt)` with an event id from `EVTUSR_BASE = 1000`. This can fire actions the A001 protocol never exposes. Order/IDs from the reference SDK (the N70's exact numbering may differ):

1000 POWER_ON, 1001 POWER_OFF, 1002 FACTORY_RESET ⚠, 1003 CLEAR_PDL ⚠, 1004 START_WWS_PAIR, 1005 WWS_ROLE_SWITCH, 1006 ENTER_PAIRING, 1007 CANCEL_PAIRING, 1008 CONNECT_LAST, 1009 VOICE_TRANSFER_TOGGLE, 1010 VOICE_RECOGNITION_TOGGLE, 1011 REDIAL_LAST, 1012 ANSWER, 1013 REJECT, 1014 HANGUP, 1015–1017 three-way call control, 1018 AUDIO_PROMPT_LANGUAGE_TOGGLE, 1019–1024 music transport, 1025/1026 volume up/down, 1027–1029 mic mute, 1030–1032 speaker mute, 1033–1035 user EQ on/off/toggle, 1036 LISTEN_MODE_TOGGLE (ANC), **1037 ENTER_FACTORY_TEST_MODE** ⚠, **1038 ENTER_OTA_MODE** ⚠, **1039 ENTER_AUDIO_TEST_MODE** ⚠, 1040–1047 CUSTOM_1..8, 1048 GAME_MODE_TOGGLE, 1049 FACTORY_RESET_KEEP_WWS ⚠, **1050 ENTER_DUT_MODE** ⚠, 1051 USER_INEAR_ENABLE_TOGGLE, 1052/1053 VOICE_RECOGNITION activate/deactivate.

## ASCII AT-command parser (N70-only)

Separate from the binary CLI, the N70 app core has an `AT+…` text command surface — a production / line-test interface. The parser uses a `{name, handler}` table (app core, around vaddr `0x34209800`); each handler replies over the same channel (common send routine at `0x341d10ba`, id `0xE0`). Transport not confirmed (likely the same 7033/SPP channel or UART). Full list:

`AT+custom, AT+getcolor/AT+setcolor, AT+getid/AT+setid, AT+getinear=/AT+setinear=, AT+getlink, AT+gettouch, AT+gettwsinfo, AT+getvbat, AT+getver/AT+getVER, AT+keytest, AT+NTC, AT+poweroff, AT+setMEMS, AT+stomode, AT+twsgetlocal, AT+twssetremote, AT+voldefault, AT+VOLMAX`.

Mostly read/set production data (color, serial id), sensors (touch CDC, in-ear, NTC temp, battery), version, TWS info, and volume defaults. Two decoded by disassembly:

- **`AT+setMEMS <d>`** — MEMS **microphone test/select** (handler `0x3419dd0c`). Takes one ASCII digit: `0`/`1` disable/enable a mic path; `3`/`4`/`5`/`6` select one of four mic channels (internal indices 4/3/1/2); other = default/query. The N70 has **up to 4 MEMS mics** — confirmed by firmware strings `ffmic_into_queue` (feedforward ANC mic), `fbmic_into_queue(_aec)` (feedback ANC mic) and `n_mems <= 4`. A line-test command to exercise each microphone.
- **`AT+stomode`** — enters a special power mode (handler `0x3419d710`): same shape as `AT+poweroff` but fires internal event **1054** instead of poweroff's **1001** (`EVTUSR_POWER_OFF`). 1054 is an N70-specific event. Given the name and the poweroff-like flow, this is most likely a **store / shipping mode** (retail-demo or transport low-power state); no literal "store"/"ship" string exists to pin the exact word, so the name is the main evidence.

(`AT+poweroff` → event 1001 = power off; verified. This is how the event-id reading was validated.)

## Status

All command IDs, framing and behaviours are **from code** (WuQi ADK). Confirmed present in the N70 firmware (filename strings): `app_cli.c` (all APPLICATION cmds), `cli_common_basic.c`, `cli_common_kv.c`, `cli_audio_spk.c`, and N70-only `cli_audio_anc.c` / `cli_audio.c` / the DC-cal handler + the AT parser. Inclusion of the memory/OEM/charger/LED/lowpower/FTM modules in this exact build is unconfirmed (assert strings may be stripped) — not proof of removal. The banner string `703XWuQiCli` / `wq-cli` confirms the CLI runs.
