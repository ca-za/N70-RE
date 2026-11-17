# Patch targets: A001 dispatch, key-remap functions, hidden features

Static reverse engineering of the **application core** image
`work/firmware-ht18-3.0.13/extracted/app_core_riscv_0x00169000.bin`
(RISC-V RV32IMAFC, load/run `0x34169020`, base `0x34169000`), done with radare2
(`r2 -a riscv -b 32 -m 0x34169000`; see [firmware_internals.md](firmware_internals.md)).
No device, no BLE, no flashing was done. **No image was modified.** This document
only *locates* patch points for the two user goals — (a) extend the touch-button
mapping beyond what the app allows, (b) add "more functions" — and proposes
concrete, minimal, reversible patches.

Addressing convention used throughout: **run address** = `0x34169000 + file
offset`, i.e. *file offset* = run − `0x34169000`. The image's first `0x20` bytes
are the `iot_flash_image_header_t`; code (run `0x34169020`) starts at file `0x20`.

Legend: ✅ = firmware-confirmed from disassembly · 🔶 = inferred / partially
traced · ❓ = ambiguous, noted as such.

---

## 1. A001 command dispatch (char `1001` / `FF`-frame) ✅

**Dispatcher function entry: run `0x341965f4`** (file `0x2d5f4`). radare2 mislabels
this function `fcn.341970b0` (it picked a middle block as the entry); the true
prologue (`addi sp,sp,-160`; `lui s1,0x60001`) is at `0x341965f4`. It is reached
through a trampoline `fcn.3420b6ea` from the GATT write path. `s1 = 0x60001000`
is the base of the in-RAM settings structure; per-opcode values are stored at
`s1 + <offset>` (e.g. `+176`, `+192`, `+232`, `+276`, `+372`, `+376`).

### Frame parse / validation ✅

| Run addr | File | Bytes | Meaning |
|---|---|---|---|
| `0x34196638` | `0x2d638` | `lbu a4,0(s4)` | load first frame byte |
| `0x34196644` | `0x2d644` | `63 1a f7 00` (`bne a4,0xFF,bail`) | **require first byte `0xFF`** |
| `0x3419664a` | `0x2d64a` | `bleu s2,3,bail` | require total length > 3 |
| `0x34196654` | `0x2d654` | `63 88 27 03` (`beq a5,s2,ok`) | **`len` field must equal `total−2`** (the `len = plen+2` rule) |
| `0x3419669e` | `0x2d69e` | loop top | iterate `<op><plen><params>` blocks; `lbu s10,0(s11)` loads the **opcode** |

### Opcode resolution ✅

The opcode (`s10`) is resolved by a **compiler-generated binary-search comparison
ladder** (a *sparse switch*, not a jump table), beginning at `0x3419670e`
(`li a5,20; beq s10,…`). This confirms the prior note in
[protocol.md](protocol.md) ("A001 dispatch is a sparse switch"). Opcodes with no
explicit case fall to the **generic default handler at `0x3419674a`**, which
stores the first param byte generically into the settings struct.

Opcode → case-body map recovered from the ladder (run addresses):

| Op | Case | Op | Case | Op | Case |
|---|---|---|---|---|---|
| `01` | `0x341969a0` | `0f` | default | `23` | `0x3419736c` |
| `02` | `0x341969cc` | `10` | `0x34196ccc` | `24` | default (store) |
| `03` | `0x341969f8` | `11` | default | `2a` | `0x34196a56` † |
| `04` | `0x3419674a`‡ | `12` | `0x34196cfe` | `2c` | `0x34196ae8` |
| `05` | `0x34196a4e` | `13` | `0x34196d52` | `43` | default (store) |
| `06` | `0x34196ab8` | `14` | `0x34196d5a` | `45` | `0x34196be0` |
| `07` | default (store) | `16` | `0x34196d06` | `46` | default (store) |
| `08` | `0x34196bc0` | `17` | `0x3419685e` → ANC-set | `47` | `0x34196bbc` |
| `09` | default (store) | `18` | `0x341972fc` | `48` | default (store) |
| `0a` | `0x34196cb4` | `19` | `0x3419730c` | `fe` | `0x34196dbe` (query) |
| `0b` | `0x34196cbc` | `1d` | `0x341974e0` | **`ff`** | **`0x34197230`** (see §3) |
| `0e` | `0x34196cc4` | `1f` | `0x34197446` | | |

‡ "default (store)" = opcode is compared but routed to the generic store at
`0x3419674a`; the value is persisted but no dedicated logic runs.
† `0x2A` on the N70 is **not** wind-detection here — see §3.

**The documented opcode `0x2B` (KEYFUN, "touch map") has NO dedicated case** in
this dispatch — it is not special-cased and would hit the generic store. The key
remap is therefore driven by the **key module / char `000D`**, not by A001 `0x2B`;
A001 `0x2B` is only a *read* representation (the `0xFE`-query/notify builder
re-serialises the stored map). This matches the live sweep in
[protocol.md](protocol.md): `0x2B` answers a read but is not a settable A001 op.

Cross-check: every opcode the device replies to in the live sweep
(`08,09,10,14,16,17,18,19,1d,1f,22,23,24,2a,2c,43,46,47,48`) has a case here or is
a generic-store value. **The firmware dispatch confirms the documented set; no
additional *queryable* A001 opcode exists.** (One write-only pseudo-opcode is
present — see §3.)

### ANC-set helper ✅
`0x34196858: li a5,23; bne s10,default; 0x3419685e: mv a0,s3; jal fcn.34195d6e`.
**`fcn.34195d6e` (run `0x34195d6e`) is the ANC apply function** (`[mode,scene,level]`).
Its callers are the A001 `0x17` handler, the `0xFE` read builder, and the
key-module ANC wrapper `fcn.3419b928` — the latter is how **long-press → ANC**
(touch funcId 11) reaches the same code.

---

## 2. Key-remap / touch-function logic

### Where the funcId is executed ✅ (structure) / 🔶 (per-case semantics)

**Touch-function switch: entry run `0x34174c4e`** (file `0x0bc4e`, prologue
`79 71 22 d4 26 d2 06 d6` = `addi sp,sp,-48; sw s0,..; sw s1,..; sw ra,..`). This
function lives in the **key/ANC module (`app_anc.c`** — asserts in its callee
`fcn.341749a2`/`fcn.34174a58` cite `app_anc.c`; on this earbud the touch handling
and ANC live in one source file, since long-press drives ANC). It switches on
`a0` with a binary-search ladder starting at `0x34174c62`.

`a0` is the **funcId**: case `11` (`0x34174d66: bne a0,11,default`; `0x34174d6a`)
loads the event struct and routes to the ANC apply wrapper `fcn.3419b928` →
`fcn.34195d6e`. **funcId 11 = ANC is confirmed**, exactly matching the N70
control panel ("11 = ANC mode", not the generic app's "11 = redial"). This anchors
`a0 = funcId`.

Recovered funcId cases (run address of each case body):

| funcId | case body | funcId | case body | funcId | case body |
|---|---|---|---|---|---|
| 1 | `0x34174dac` → `fcn.3417470a` | 8 | `0x34174ed8` → `fcn.341745c8` | 17 | `0x34174f76` |
| 2 | `0x34174d96` → `fcn.341749a2` | 9 | `0x34174ef2` (branch on `s1[0]`==2/3 → `fcn.34182720`/`fcn.34182754`) | 18 | `0x34174fd0` |
| 3 | `0x34174f84` → `fcn.34174a58` | 10 | `0x34174f30` (indirect `jr` via config fn-ptr) | 21 | `0x34174d8e` → `fcn.3418c818` |
| 4 | `0x34174ca0` (inline, gated by `fcn.341774da`/`fcn.341cca88`) | 11 | `0x34174d6a` → **ANC** | 22 | `0x34174f7c` |
| 5 | `0x34174de8` → ANC-config path | 16 | `0x34174f6a` → `fcn.3418c818` | 23 | `0x34174f9a` |
| 6 | `0x34174d06` (inline, gated) | | | **default** | `0x34174c8a` (no-op, returns 0) |

`fcn.3418c818`/`fcn.3418c832` are left/right-role gates; `fcn.341774da`/
`fcn.341cca88` are "busy?" guards (in-call / OTA). The exact end action of each
hidden case (8,9,10,16,17,18,21,22,23) is only **partially traced** 🔶 — they
hand off to the role-gated media/call helpers above — but the *dispatch cases
provably exist in firmware*.

### How many functions: firmware vs app ✅

- **App / N70 control panel exposes 9 funcIds:** `0 none, 1 play/pause, 2 prev,
  3 next, 4 voice, 5 vol+, 6 vol−, 7 gaming, 11 ANC`
  ([controlpanel.md](controlpanel.md)).
- **Firmware switch handles 16 funcIds:** `1,2,3,4,5,6,8,9,10,11,16,17,18,21,22,23`.

So the firmware implements **9 funcIds the app never offers: `8, 9, 10, 16, 17,
18, 21, 22, 23`** (`21–23` are in the generic protocol's "+20 = call-mode" band →
likely answer/reject/hang-up; `8/9/10` are the generic answer/reject/hold; `16/17/18`
are extra, source-undocumented). Conversely **funcId 7 (gaming) has *no* case in
this switch and falls to the no-op default** ❓ — gaming is likely toggled through
a different path, or is a no-op for the gesture types routed here.

### Practical consequence (important) 🔶

Because the firmware already dispatches funcIds `8,9,10,16,17,18,21,22,23`, the
app's restriction to `{0–7,11}` is a **server-side control-panel (JSON) limit, not
a firmware limit**. Writing a raw `[eventID, funcId]` pair with one of these
hidden funcIds to **char `000D`** over BLE should exercise the existing firmware
case **without any firmware patch** — *provided* the `000D` write handler does not
range-check the funcId. That write handler was **not isolated** in this pass
(char-`000D` routing is separate from the A001 `1001` path analysed in §1), so the
clamp question is **open**; the recommended first step is an on-device raw-write
test, not a flash.

---

## 3. Hidden / undocumented features (from the dispatch map)

1. **A001 pseudo-opcode `0xFF` — paired-device (MAC) list.** ✅
   Case at **run `0x34197230`** (file `0x2e230`). It `memset`s a 48-byte buffer,
   enumerates entries in **6-byte strides** (`fcn.3417a1ee`, stride `+6` = MAC
   addresses), filters with `fcn.341cc1fa`, allocates a 20-byte reply
   (`li a0,20`) and fills `0xFF`/`18`/`16` marker bytes — i.e. it returns the
   connected/paired **device list**, equivalent to the generic app's `0x4D`
   PHONE_INFO. It is **not in [protocol.md](protocol.md)'s opcode table**. Being
   write-/event-only it cannot appear in a `FE`-query sweep, which is why it was
   not found before. Inferred invocation (untested, write-only): a frame whose
   block opcode is `0xFF`, e.g. `FF 03 FF 01 00`.

2. **Firmware funcIds beyond the app panel** (§2): `8,9,10,16,17,18,21,22,23`.

No other hidden *queryable* A001 opcode exists (every readable responder is
already documented; the generic-store opcodes `07/09/24/43/46/48` run no special
logic). LE Audio / KWS remain absent (see [firmware_internals.md](firmware_internals.md)).

---

## 4. Proposed patch targets (NOT applied)

All offsets are into `app_core_riscv_0x00169000.bin`. Every patch below sits at
file offset ≥ `0x20`, so **`tools/ota_repack.py` fixes the image automatically**:
on repack it recomputes the image's `iot_flash_image_header_t.crc` (the 5th u32,
at image offset `0x10`) as CRC-32 over `body[0x20 : 0x20 + header.length]`, then
recomputes the pack `header_crc`/`data_crc` and the 18-byte wrapper CRC. Since
these are **in-place, same-size** edits, `header.length` is unchanged and no
manual CRC edit is needed. There is no secure boot / image signing
([custom_firmware.md](custom_firmware.md)), so a correct-CRC repack is flashable
in principle. **Hand-encoding RISC-V replacement bytes is error-prone — assemble
replacements in radare2 (`wa`/`wx` at the run address) rather than by hand.**

### (a) Extend / alter the key-remap function set

**Primary recommendation: no firmware patch.** Write raw `[eventID, funcId]` with
a hidden funcId (`8,9,10,16,17,18,22,23`) to char `000D`; the switch at
`0x34174c4e` already dispatches it (§2). Patch only if an on-device test shows the
`000D` writer rejects the value.

**Concrete byte-patch example (remap one funcId to an existing action):** in the
switch ladder, the comparison that sends funcId 6 to its handler is at
**run `0x34174d00`** (`li a5,6`, file `0x0bd00`, current bytes `99 47`). Changing
the compared immediate from 6 to 7 (`li a5,7`) makes **funcId 7 (gaming, today a
no-op in this switch) execute the funcId-6 body (vol−)** instead — a minimal,
reversible 2-byte change that routes a currently-dead funcId to a live action.
Trade-off: it reassigns the value, it does not add a new slot. (Assemble with
`wa li a5, 7 @ 0x34174d00`.) Risk: low — confined to one switch arm; reversible by
restoring `99 47`.

- Run `0x34174c4e` / file `0x0bc4e` — switch entry (reference).
- Run `0x34174c8a` / file `0x0bc8a` — the no-op **default** case (bytes
  `b2 50 22 54 …`); redirecting this is the place to give *all* unknown funcIds a
  fallback action, but that needs added code space, so it is **not** minimal.

### (b) Change a default / limit (safe example: auto-power-off `0x1F`)

The A001 `0x1F` (auto-power-off minutes) handler **range-checks** the value before
storing it, at **run `0x34197474`** (file `0x2e474`, bytes `63 6b f7 00` =
`bltu a4,a5, reject`; accepted values are stored to `s1+376` just below at
`0x34197478`). Replacing that conditional branch with a no-op / unconditional
fall-through widens the accepted timeout range (e.g. to allow values the app's
preset list omits). Minimal (one 4-byte branch), reversible (restore
`63 6b f7 00`). Risk: low — only widens user-supplied input validation; the user
still chooses the value.

Note: the *factory default* auto-off value (device reads 5 min) is written at
runtime init / factory-reset, **not** stored as a locatable literal constant, so
the **validation bound above is the concrete patchable surface**; there is no
single "default = 5" byte to flip. Marked 🔶 for that reason.

### (c) Enable a hidden function

The `0xFF` device-list command (§3) is **already enabled** in firmware — no patch
is needed to *use* it, only to *expose* it (that is an app/JSON change, not
firmware). Likewise the hidden funcIds (a) are already live. If the goal is to
make a firmware function reachable from an app-driven gesture, the lever is (a):
map an event to a hidden funcId. A firmware byte-patch to "enable" would only be
the immediate-redirect shown in (a); there is no disabled-by-flag feature found
that a single bit would switch on.

---

## Limitations / open items

- The **char `000D` write handler** (keymap setter) was not isolated this pass; it
  is on a different GATT path from the A001 `1001` handler in §1. Whether it
  range-checks funcId on write is **unresolved** and gates whether patch (a) is
  even necessary.
- Per-funcId **end actions** for the hidden cases `8,9,10,16,17,18,21,22,23` are
  only partially traced (they reach role-gated media/call helpers); the cases
  provably exist, the exact AVRCP/HFP command each sends is 🔶.
- radare2 merged several adjacent functions in the `0x34174xxx`/`0x34196xxx`
  regions (shared epilogues); function *entries* cited here were verified from
  prologues and call targets, but r2's `afl`/`axt` names for them are unreliable.
