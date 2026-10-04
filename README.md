# FixMyBack

Sits with you at the desk. After **30 minutes** of using the computer without a real break, it covers the screen and makes you stand and stretch for **1 minute**.

**Human how-to:** open `MANUAL.txt` (run, stop, logs, timers).
**For Cursor / agents:** `AGENTS.md`.

## How it thinks

- Keyboard or mouse use = you are sitting
- Idle for **3+ minutes** = you stood up / walked away → sit clock resets
- Overlay cannot be closed until the 1-minute stretch timer hits 0

## When you are mid-thought

The lock screen has a **snooze** button (or press space): it disappears and comes
back in **5 minutes**. You get **2 snoozes** per cycle — after that the only way
out is the full minute. A real break resets your snoozes.

## Install (runs at login)

```bash
cd ~/fixmyback
chmod +x install.sh uninstall.sh
./install.sh
```

## Try it in 20 seconds

```bash
python3 ~/fixmyback/sit_timer.py --test
```

Use the mouse a little so it knows you are at the desk. After 20 seconds the stretch screen appears. Wait 10 seconds, then click **I stretched**.
<img width="2560" height="1440" alt="image" src="https://github.com/user-attachments/assets/2f8e6e70-3f2b-45b2-96bf-ccee4f6cf833" />
