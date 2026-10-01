# AGENTS.md

This folder is **FixMyBack**: a macOS sit timer. After 30 minutes of HID activity without a 3+ minute idle break, a Tk overlay covers the screen until the user stretches (or snoozes).

Read `MANUAL.txt` for human run/stop commands. Do not duplicate that here.

## Rules

- Keep the overlay **hard to skip**, but never trap the user with no escape: 2 snoozes of 5 minutes, then stretch is required.
- Each overlay must run in a **fresh subprocess** (`--overlay`). Reusing one Tk root across cycles caused `invalid command name "...stay_on_top"`.
- Cancel every `root.after(...)` id in `close()` before destroying the window.
- Idle time comes from `ioreg` `HIDIdleTime`. Do not require Accessibility permissions for the core loop.
- **Never open the overlay without checking `session_is_ready()`.** Tk calls `Tcl_Panic` in `TkpInit` and the process dies with SIGABRT if there is no usable window server — this happened when the timer fired 3 seconds after a wake from sleep. Readiness comes from `ioreg -n Root -d1 -a`: `IOConsoleLocked` false and some console user with `kCGSSessionOnConsoleKey`.
- A wall-clock gap larger than `SLEEP_GAP_SECONDS` means the Mac slept. Reset the sit clock; the user was not at the desk.
- A crashed overlay returns `"failed"`. Never treat that as a completed stretch — retry instead.
- Do not change default timers (30 min sit, 60s stretch, 3 min break, 5 min snooze, 2 snoozes) unless the user asks.
- After changing `sit_timer.py` while the LaunchAgent is installed, restart it:

  `launchctl kickstart -k "gui/$(id -u)/com.fixmyback.sittimer"`

- The LaunchAgent plist hard-codes this machine path: `/Users/cherifouyahia/Mostafa/fixmyback/sit_timer.py`. If the folder moves, update the plist **and** re-run `install.sh`.
- Logs: `~/Library/Logs/fixmyback.log`. Label is `com.fixmyback.sittimer`.

## Test without locking for 30 minutes

```bash
python3 sit_timer.py --sit-seconds 10 --stretch-seconds 3
```

Ctrl+C when done. Do not leave a short `--sit-seconds` test running — it will re-lock every few seconds. The login agent is separate; tests in Terminal do not replace it.

## Do not

- Do not add `--no-verify` git flags, force-push, or commit unless asked.
- Do not "fix" snooze into a skip.
- Do not put secrets in this repo. There are none.
