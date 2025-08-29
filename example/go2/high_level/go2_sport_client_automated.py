#!/usr/bin/env python3
"""
Go2 EDU: simple WASD + arrow-key teleop (discrete, one-command-at-a-time)

Requirements:
- Unitree SDK 2 Python: https://github.com/unitreerobotics/unitree_sdk2_python
- Runs in a terminal (uses curses)

Controls:
  w/s : forward/backward (vx)
  a/d : left/right (vy)
  ←/→ : rotate left/right (wz)
  space: StopMove()
  q or ESC: quit

Safety:
- Keep a clear area around the robot.
- Speeds/durations below are intentionally modest. Tune with care.
"""

import sys
import time
import curses

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient

# --- Tunable parameters (choose conservative values to start) ---
LINEAR_SPEED   = 0.30   # m/s forward/backward  (vx)
LATERAL_SPEED  = 0.30   # m/s left/right        (vy)  (positive vy is typically left)
ANGULAR_SPEED  = 0.60   # rad/s yaw rate        (wz)
MOVE_DURATION  = 0.25   # seconds per key press (short, discrete step)

SHOW_RETURNS   = False  # set True to print SDK return codes from Move/Stop

# ----------------------------------------------------------------

def do_move(client: SportClient, vx: float, vy: float, wz: float, duration: float = MOVE_DURATION):
    """Send a brief motion command, then stop."""
    # Immediately stop any current movement before starting new movement
    client.StopMove()
    time.sleep(0.05)  # Small delay to ensure stop command is processed
    
    if SHOW_RETURNS:
        print(f"Move(vx={vx:.2f}, vy={vy:.2f}, wz={wz:.2f}) for {duration:.2f}s")
    ret = client.Move(vx, vy, wz)
    if SHOW_RETURNS:
        print("ret:", ret)
    time.sleep(duration)
    ret = client.StopMove()
    if SHOW_RETURNS:
        print("Stop ret:", ret)

def curses_main(stdscr, client: SportClient):
    curses.curs_set(0)
    stdscr.nodelay(True)    # Don't block on key input (enables immediate response)
    stdscr.keypad(True)     # enable arrow keys

    lines = [
        "Go2 EDU Teleop (WASD + Arrow Keys)",
        "----------------------------------",
        "w/s : forward/backward",
        "a/d : left/right (strafe)",
        "←/→ : rotate left/right",
        "space: immediate stop",
        "q or ESC: quit",
        "",
        f"Speeds: vx={LINEAR_SPEED} m/s, vy={LATERAL_SPEED} m/s, wz={ANGULAR_SPEED} rad/s",
        f"Step duration per key: {MOVE_DURATION} s",
        "",
        "Ready. Press a key…"
    ]

    for i, t in enumerate(lines):
        stdscr.addstr(i, 0, t)
    stdscr.refresh()

    while True:
        ch = stdscr.getch()
        
        # Handle no key pressed
        if ch == -1:  # -1 means no key pressed
            time.sleep(0.01)  # Small delay to prevent excessive CPU usage
            continue

        # quit
        if ch in (ord('q'), 27):  # 'q' or ESC
            break

        # space -> hard stop
        if ch == ord(' '):
            client.StopMove()
            continue

        # normalized tap controls (one command at a time) - immediate override
        if ch in (ord('w'), ord('W')):
            do_move(client, LINEAR_SPEED, 0.0, 0.0)
        elif ch in (ord('s'), ord('S')):
            do_move(client, -LINEAR_SPEED, 0.0, 0.0)
        elif ch in (ord('a'), ord('A')):
            # NOTE: If left/right seems reversed on your setup, swap +/- below.
            do_move(client, 0.0,  LATERAL_SPEED, 0.0)   # left strafe
        elif ch in (ord('d'), ord('D')):
            do_move(client, 0.0, -LATERAL_SPEED, 0.0)   # right strafe
        elif ch == curses.KEY_LEFT:
            do_move(client, 0.0, 0.0,  ANGULAR_SPEED)   # rotate left (CCW)
        elif ch == curses.KEY_RIGHT:
            do_move(client, 0.0, 0.0, -ANGULAR_SPEED)   # rotate right (CW)
        else:
            # ignore any other keys
            pass

        # Refresh minimal status line (optional)
        stdscr.addstr(len(lines)+1, 0, f"Last key: {ch:>4}         ")
        stdscr.refresh()

def main():
    print("WARNING: Ensure a clear area around the robot before proceeding.")
    input("Press Enter to continue...")

    # Optional: pass robot address as first arg (matches Unitree samples).
    # e.g. python go2_teleop.py 192.168.12.1
    if len(sys.argv) > 1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)

    client = SportClient()
    client.SetTimeout(10.0)
    client.Init()

    # Bring robot to a safe, ready posture (comment out if you prefer manual control)
    try:
        client.StandUp()
        time.sleep(1.0)
    except Exception:
        # If already standing or command not available, just continue.
        pass

    try:
        curses.wrapper(curses_main, client)
    finally:
        # Always stop motion and leave the robot in a stable state on exit.
        try:
            client.StopMove()
        except Exception:
            pass
        # Prefer not to force StandDown automatically; uncomment if desired:
        # try:
        #     client.StandDown()
        # except Exception:
        #     pass
        print("\nExiting teleop.")

if __name__ == "__main__":
    main()
