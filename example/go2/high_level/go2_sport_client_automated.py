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

def do_move(client: SportClient, vx: float, vy: float, wz: float, duration: float = MOVE_DURATION, override: bool = True):
    """Send a brief motion command, then stop."""
    if override:
        # Only stop current movement if we're overriding (different movement)
        client.StopMove()
        time.sleep(0.05)  # Small delay to ensure stop command is processed
    
    if SHOW_RETURNS:
        print(f"Move(vx={vx:.2f}, vy={vy:.2f}, wz={wz:.2f}) for {duration:.2f}s")
    ret = client.Move(vx, vy, wz)
    if SHOW_RETURNS:
        print("ret:", ret)
    
    # Don't sleep here - let the main loop handle timing and override detection
    # The movement will continue until another key is pressed or space is pressed

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
    
    # Track current movement for smart override
    current_movement = {'vx': 0.0, 'vy': 0.0, 'wz': 0.0}
    movement_start_time = None
    is_moving = False

    while True:
        ch = stdscr.getch()
        
        # Handle no key pressed and check movement timer
        if ch == -1:  # -1 means no key pressed
            # Check if current movement has exceeded duration
            if is_moving and movement_start_time and (time.time() - movement_start_time) >= MOVE_DURATION:
                client.StopMove()
                is_moving = False
                movement_start_time = None
                current_movement = {'vx': 0.0, 'vy': 0.0, 'wz': 0.0}
                if SHOW_RETURNS:
                    print("Movement duration expired - stopping")
            
            time.sleep(0.01)  # Small delay to prevent excessive CPU usage
            continue

        # quit
        if ch in (ord('q'), 27):  # 'q' or ESC
            break

        # space -> master stop (override all movements)
        if ch == ord(' '):
            client.StopMove()
            # Reset current movement tracking to indicate complete stop
            current_movement = {'vx': 0.0, 'vy': 0.0, 'wz': 0.0}
            is_moving = False
            movement_start_time = None
            continue

        # Smart movement controls - override only when movement changes
        if ch in (ord('w'), ord('W')):
            new_movement = {'vx': LINEAR_SPEED, 'vy': 0.0, 'wz': 0.0}
            override = (new_movement != current_movement)
            do_move(client, LINEAR_SPEED, 0.0, 0.0, override=override)
            current_movement = new_movement
            movement_start_time = time.time()
            is_moving = True
        elif ch in (ord('s'), ord('S')):
            new_movement = {'vx': -LINEAR_SPEED, 'vy': 0.0, 'wz': 0.0}
            override = (new_movement != current_movement)
            do_move(client, -LINEAR_SPEED, 0.0, 0.0, override=override)
            current_movement = new_movement
            movement_start_time = time.time()
            is_moving = True
        elif ch in (ord('a'), ord('A')):
            # NOTE: If left/right seems reversed on your setup, swap +/- below.
            new_movement = {'vx': 0.0, 'vy': LATERAL_SPEED, 'wz': 0.0}
            override = (new_movement != current_movement)
            do_move(client, 0.0, LATERAL_SPEED, 0.0, override=override)   # left strafe
            current_movement = new_movement
            movement_start_time = time.time()
            is_moving = True
        elif ch in (ord('d'), ord('D')):
            new_movement = {'vx': 0.0, 'vy': -LATERAL_SPEED, 'wz': 0.0}
            override = (new_movement != current_movement)
            do_move(client, 0.0, -LATERAL_SPEED, 0.0, override=override)   # right strafe
            current_movement = new_movement
            movement_start_time = time.time()
            is_moving = True
        elif ch == curses.KEY_LEFT:
            new_movement = {'vx': 0.0, 'vy': 0.0, 'wz': ANGULAR_SPEED}
            override = (new_movement != current_movement)
            do_move(client, 0.0, 0.0, ANGULAR_SPEED, override=override)   # rotate left (CCW)
            current_movement = new_movement
            movement_start_time = time.time()
            is_moving = True
        elif ch == curses.KEY_RIGHT:
            new_movement = {'vx': 0.0, 'vy': 0.0, 'wz': -ANGULAR_SPEED}
            override = (new_movement != current_movement)
            do_move(client, 0.0, 0.0, -ANGULAR_SPEED, override=override)   # rotate right (CW)
            current_movement = new_movement
            movement_start_time = time.time()
            is_moving = True
        else:
            # ignore any other keys
            pass

        # Refresh status line with movement info
        if ch == ord(' '):
            movement_type = "MASTER STOP"
        elif ch in (ord('w'), ord('W'), ord('s'), ord('S'), ord('a'), ord('A'), ord('d'), ord('D')) or ch in (curses.KEY_LEFT, curses.KEY_RIGHT):
            # Check if this is the same movement as current
            is_same_movement = False
            if ch in (ord('w'), ord('W')) and current_movement['vx'] == LINEAR_SPEED and current_movement['vy'] == 0.0 and current_movement['wz'] == 0.0:
                is_same_movement = True
            elif ch in (ord('s'), ord('S')) and current_movement['vx'] == -LINEAR_SPEED and current_movement['vy'] == 0.0 and current_movement['wz'] == 0.0:
                is_same_movement = True
            elif ch in (ord('a'), ord('A')) and current_movement['vx'] == 0.0 and current_movement['vy'] == LATERAL_SPEED and current_movement['wz'] == 0.0:
                is_same_movement = True
            elif ch in (ord('d'), ord('D')) and current_movement['vx'] == 0.0 and current_movement['vy'] == -LATERAL_SPEED and current_movement['wz'] == 0.0:
                is_same_movement = True
            elif ch == curses.KEY_LEFT and current_movement['vx'] == 0.0 and current_movement['vy'] == 0.0 and current_movement['wz'] == ANGULAR_SPEED:
                is_same_movement = True
            elif ch == curses.KEY_RIGHT and current_movement['vx'] == 0.0 and current_movement['vy'] == 0.0 and current_movement['wz'] == -ANGULAR_SPEED:
                is_same_movement = True
            
            movement_type = "QUEUE" if is_same_movement else "OVERRIDE"
        else:
            movement_type = ""
        
        status_line = f"Last key: {ch:>4} | Movement: {movement_type} | Current: vx={current_movement['vx']:6.2f} vy={current_movement['vy']:6.2f} wz={current_movement['wz']:6.2f}"
        stdscr.addstr(len(lines)+1, 0, status_line + " " * 20)  # Clear any leftover text
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
