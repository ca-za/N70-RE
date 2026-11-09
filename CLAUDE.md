# N70-RE – notes for Claude

- **The repo is English-only** (docs, comments, commit messages, tool output). Talk to the user in German, plain language.
- The current knowledge is in `README.md` and `docs/`. Add new findings there and clearly mark verified on device ✅ vs. source only.
- **Commit and push after every change** (`main`, remote `https://github.com/ca-za/N70-RE`, public).
- No unknown commands to the earbuds. Only commands from a source; save the original state first, read back afterwards and restore.
- **Never write to service 7033.**
- Another app on this Mac may already hold a BLE connection to the earbuds; do not disconnect or interfere with it.
- Downloaded files (APK, firmware) go into their own empty folder under `work/` (not in the repo), never execute them; run Python on them with `-I`.
