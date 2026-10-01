#!/usr/bin/env python3
"""
FixMyBack sit timer.

Tracks how long you've been at the desk (keyboard/mouse activity).
After 30 minutes without a real break, it covers the screen and
makes you stretch for at least 1 minute before you can work again.

Idle for 3+ minutes counts as a break (you stood up / walked away)
and resets the sit clock.
"""

from __future__ import annotations

import argparse
import os
import plistlib
import subprocess
import sys
import time
from datetime import datetime

SIT_LIMIT_SECONDS = 30 * 60
STRETCH_SECONDS = 60
BREAK_IDLE_SECONDS = 3 * 60
POLL_SECONDS = 5
SNOOZE_SECONDS = 5 * 60
MAX_SNOOZES = 2
SLEEP_GAP_SECONDS = 90
OVERLAY_RETRY_SECONDS = 60

# Apple's Command Line Tools Python 3.9 (/usr/bin/python3) ships a Tk that
# abort()s with "macOS 15 (1507) or later required, have instead 15 (1506)".
# The python.org 3.13 install does not.
WORKING_PYTHON_CANDIDATES = (
    "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
    "/opt/homebrew/bin/python3",
    "/usr/local/bin/python3",
)

STRETCHES = [
    "Stand up. Roll your shoulders back 10 times.",
    "Look at something far away for 20 seconds.",
    "Hands on hips. Lean back gently. Breathe.",
    "Walk in place. Shake out your legs.",
    "Chin tucks: sit tall, slide chin straight back.",
]


def apple_tk_is_broken() -> bool:
    exe = os.path.realpath(sys.executable)
    return exe == "/usr/bin/python3" or "CommandLineTools" in exe


def working_python() -> str | None:
    if not apple_tk_is_broken():
        return sys.executable
    for path in WORKING_PYTHON_CANDIDATES:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            if os.path.realpath(path) != os.path.realpath(sys.executable):
                return path
    return None


def ensure_working_python() -> None:
    """Re-exec on a Python whose Tk can open a window."""
    good = working_python()
    if good is None or os.path.realpath(good) == os.path.realpath(sys.executable):
        return
    os.execv(good, [good, *sys.argv])


def session_is_ready() -> bool:
    """True only when a GUI session is on screen and unlocked.

    Tk aborts (SIGABRT in TkpInit) if it opens a window with no usable
    window server, e.g. in the seconds after the Mac wakes from sleep.
    """
    try:
        out = subprocess.check_output(["ioreg", "-n", "Root", "-d1", "-a"])
        root = plistlib.loads(out)
    except (subprocess.CalledProcessError, plistlib.InvalidFileException, ValueError):
        return False
    if root.get("IOConsoleLocked"):
        return False
    users = root.get("IOConsoleUsers") or []
    return any(u.get("kCGSSessionOnConsoleKey") for u in users)


def hid_idle_seconds() -> float:
    try:
        out = subprocess.check_output(
            ["ioreg", "-c", "IOHIDSystem", "-d", "4"],
            text=True,
        )
    except subprocess.CalledProcessError:
        return 0.0
    for line in out.splitlines():
        if "HIDIdleTime" in line:
            ns = int(line.split("=")[-1].strip())
            return ns / 1_000_000_000
    return 0.0


def play_alert() -> None:
    sound = "/System/Library/Sounds/Glass.aiff"
    subprocess.Popen(
        ["afplay", sound],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def log(msg: str) -> None:
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


def show_stretch_overlay(stretch_seconds: int, snoozes_left: int) -> str:
    """Show the lock screen. Returns "stretched" or "snoozed"."""
    import tkinter as tk

    play_alert()
    remaining = {"n": stretch_seconds}
    result = {"value": "stretched"}
    stretch = STRETCHES[int(time.time()) % len(STRETCHES)]

    root = tk.Tk()
    root.title("FixMyBack")
    root.attributes("-fullscreen", True)
    root.attributes("-topmost", True)
    root.configure(bg="#0b1220")
    root.focus_force()
    root.protocol("WM_DELETE_WINDOW", lambda: None)

    for seq in ("<Escape>", "<Command-q>", "<Command-w>", "<Alt-F4>"):
        root.bind(seq, lambda _e: "break")

    wrap = tk.Frame(root, bg="#0b1220")
    wrap.place(relx=0.5, rely=0.5, anchor="center")

    tk.Label(
        wrap,
        text="STAND UP",
        fg="#f8fafc",
        bg="#0b1220",
        font=("Helvetica Neue", 56, "bold"),
    ).pack()

    timer = tk.Label(
        wrap,
        text="",
        fg="#38bdf8",
        bg="#0b1220",
        font=("Helvetica Neue", 120, "bold"),
    )
    timer.pack(pady=(16, 8))

    tk.Label(
        wrap,
        text="Screen stays locked until the timer hits 0.",
        fg="#94a3b8",
        bg="#0b1220",
        font=("Helvetica Neue", 18),
    ).pack()

    tk.Label(
        wrap,
        text=stretch,
        fg="#e2e8f0",
        bg="#0b1220",
        font=("Helvetica Neue", 24),
        wraplength=900,
        justify="center",
    ).pack(pady=(28, 36))

    pending: dict[str, str | None] = {"tick": None, "top": None}

    def close(outcome: str) -> None:
        result["value"] = outcome
        for key in pending:
            if pending[key] is not None:
                try:
                    root.after_cancel(pending[key])
                except tk.TclError:
                    pass
                pending[key] = None
        root.destroy()

    buttons = tk.Frame(wrap, bg="#0b1220")
    buttons.pack()

    done_btn = tk.Button(
        buttons,
        text="Wait for the timer…",
        state="disabled",
        command=lambda: close("stretched"),
        font=("Helvetica Neue", 20, "bold"),
        fg="#0b1220",
        bg="#22c55e",
        disabledforeground="#64748b",
        activebackground="#16a34a",
        relief="flat",
        padx=28,
        pady=14,
        cursor="hand2",
    )
    done_btn.pack(side="left", padx=8)

    if snoozes_left > 0:
        snooze_btn = tk.Button(
            buttons,
            text=f"Busy — remind me in {SNOOZE_SECONDS // 60} min ({snoozes_left} left)",
            command=lambda: close("snoozed"),
            font=("Helvetica Neue", 18),
            fg="#e2e8f0",
            bg="#1e293b",
            activebackground="#334155",
            activeforeground="#f8fafc",
            highlightbackground="#0b1220",
            relief="flat",
            padx=22,
            pady=14,
            cursor="hand2",
        )
        snooze_btn.pack(side="left", padx=8)
        root.bind("<space>", lambda _e: close("snoozed"))
    else:
        tk.Label(
            buttons,
            text="No snoozes left — stand up.",
            fg="#f87171",
            bg="#0b1220",
            font=("Helvetica Neue", 18),
        ).pack(side="left", padx=16)

    def tick() -> None:
        n = remaining["n"]
        mins, secs = divmod(max(n, 0), 60)
        timer.config(text=f"{mins:02d}:{secs:02d}")
        if n <= 0:
            done_btn.config(state="normal", text="I stretched — back to work")
            play_alert()
            return
        remaining["n"] -= 1
        pending["tick"] = root.after(1000, tick)

    def stay_on_top() -> None:
        try:
            root.lift()
            root.attributes("-topmost", True)
            pending["top"] = root.after(400, stay_on_top)
        except tk.TclError:
            return

    tick()
    stay_on_top()
    root.mainloop()
    return result["value"]


def run_overlay_subprocess(stretch_seconds: int, snoozes_left: int) -> str:
    """Each overlay gets a fresh process so Tk never reuses a torn-down state."""
    script = os.path.abspath(__file__)
    proc = subprocess.run(
        [
            sys.executable,
            script,
            "--overlay",
            "--stretch-seconds",
            str(stretch_seconds),
            "--snoozes-left",
            str(snoozes_left),
        ],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        log(f"Overlay failed: {proc.stderr.strip() or proc.returncode}")
        return "failed"
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT:"):
            return line.split(":", 1)[1].strip()
    return "stretched"


def run_loop(sit_limit: int, stretch_seconds: int, break_idle: int) -> None:
    sit_started = time.time()
    snoozes_used = 0
    log(
        f"Watching your desk. Sit limit {sit_limit // 60} min. "
        f"Stretch {stretch_seconds}s. Break if idle {break_idle // 60} min."
    )

    last_tick = time.time()

    while True:
        idle = hid_idle_seconds()
        now = time.time()

        # A wall-clock jump much larger than the poll interval means the Mac
        # slept or was suspended. You were not at the desk for any of it.
        gap = now - last_tick
        last_tick = now
        if gap > max(SLEEP_GAP_SECONDS, POLL_SECONDS * 4):
            sit_started = now
            snoozes_used = 0
            log(f"Woke after {int(gap)}s away. Sit clock reset.")
            time.sleep(POLL_SECONDS)
            continue

        if idle >= break_idle:
            sit_started = now
            snoozes_used = 0
            log(f"Break detected ({int(idle)}s idle). Sit clock reset.")
            time.sleep(POLL_SECONDS)
            continue

        seated = now - sit_started
        left = sit_limit - seated
        if left <= 0:
            if not session_is_ready():
                log("Screen locked or asleep. Holding the stretch until you are back.")
                time.sleep(POLL_SECONDS)
                continue
            log(f"{sit_limit // 60} min at the desk. Locking screen for a stretch.")
            outcome = run_overlay_subprocess(
                stretch_seconds, MAX_SNOOZES - snoozes_used
            )
            if outcome == "failed":
                sit_started = time.time() - (sit_limit - OVERLAY_RETRY_SECONDS)
                log(f"Retrying the stretch in {OVERLAY_RETRY_SECONDS}s.")
            elif outcome == "snoozed":
                snoozes_used += 1
                sit_started = time.time() - (sit_limit - SNOOZE_SECONDS)
                log(
                    f"Snoozed {SNOOZE_SECONDS // 60} min "
                    f"({MAX_SNOOZES - snoozes_used} left)."
                )
            else:
                sit_started = time.time()
                snoozes_used = 0
                log("Stretch done. Sit clock reset.")
        elif int(seated) % 300 < POLL_SECONDS:
            log(f"Seated {int(seated) // 60} min. Stretch in {int(left) // 60} min.")

        time.sleep(POLL_SECONDS)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="FixMyBack sit timer")
    p.add_argument(
        "--test",
        action="store_true",
        help="Fire after 20s sitting, stretch 10s. For trying it out.",
    )
    p.add_argument("--sit-seconds", type=int, default=None)
    p.add_argument("--stretch-seconds", type=int, default=None)
    p.add_argument("--overlay", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--snoozes-left", type=int, default=MAX_SNOOZES)
    return p.parse_args()


def main() -> int:
    ensure_working_python()
    if apple_tk_is_broken():
        log(
            "Stretch screen cannot open: this Python's Tk crashes on this Mac. "
            "Install Python 3.13 from python.org, then run install.sh again."
        )
        return 1
    args = parse_args()

    if args.overlay:
        outcome = show_stretch_overlay(
            args.stretch_seconds or STRETCH_SECONDS, args.snoozes_left
        )
        print(f"RESULT:{outcome}", flush=True)
        return 0

    sit_limit = SIT_LIMIT_SECONDS
    stretch = STRETCH_SECONDS
    if args.test:
        sit_limit = 20
        stretch = 10
        log("TEST MODE: overlay in 20 seconds.")
    if args.sit_seconds is not None:
        sit_limit = args.sit_seconds
    if args.stretch_seconds is not None:
        stretch = args.stretch_seconds

    try:
        run_loop(sit_limit, stretch, BREAK_IDLE_SECONDS)
    except KeyboardInterrupt:
        log("Stopped.")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
