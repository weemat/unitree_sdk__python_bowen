#!/usr/bin/env python3
"""
Go2 EDU: continuous WASD + arrow-key teleop (hold-to-move)

Requirements:
- Unitree SDK 2 Python: https://github.com/unitreerobotics/unitree_sdk2_python
- Runs in a terminal (uses curses)

Controls:
  w/s : forward/backward (vx) - hold to move continuously
  a/d : left/right (vy) - hold to move continuously  
  ←/→ : rotate left/right (wz) - hold to rotate continuously
  space: StopMove()
  q or ESC: quit

Safety:
- Keep a clear area around the robot.
- Speeds/durations below are intentionally modest. Tune with care.
"""

import sys
import time
import curses
import threading

from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient

# --- Tunable parameters (choose conservative values to start) ---
LINEAR_SPEED   = 0.50   # m/s forward/backward  (vx) - moderate speed
LATERAL_SPEED  = 0.40   # m/s left/right        (vy) - moderate speed
ANGULAR_SPEED  = 1.0   # rad/s yaw rate        (wz) - moderate rotation
UPDATE_RATE    = 0.10   # seconds between movement updates (10 Hz) - balanced for responsiveness and smoothness

SHOW_RETURNS   = True   # set True to print SDK return codes from Move/Stop

# ----------------------------------------------------------------

class ContinuousController:
    def __init__(self, client: SportClient):
        self.client = client
        self.current_vx = 0.0
        self.current_vy = 0.0
        self.current_wz = 0.0
        self.walk_upright_active = False  # Track walk upright state
        self.running = True
        self.lock = threading.Lock()
        
        # Start movement update thread
        self.update_thread = threading.Thread(target=self._movement_updater)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def _movement_updater(self):
        """Background thread that continuously sends movement commands"""
        last_vx, last_vy, last_wz = 0.0, 0.0, 0.0
        freewalk_enabled = False
        
        while self.running:
            with self.lock:
                vx, vy, wz = self.current_vx, self.current_vy, self.current_wz
            
            # Only send command if movement has changed significantly or if stopping
            movement_changed = (abs(vx - last_vx) > 0.01 or 
                              abs(vy - last_vy) > 0.01 or 
                              abs(wz - last_wz) > 0.01)
            
            if abs(vx) > 0.01 or abs(vy) > 0.01 or abs(wz) > 0.01:
                # Enable FreeWalk mode for continuous movement
                if not freewalk_enabled:
                    if SHOW_RETURNS:
                        print("Enabling FreeWalk mode")
                    ret = self.client.FreeWalk()
                    if SHOW_RETURNS:
                        print("FreeWalk ret:", ret)
                    freewalk_enabled = True
                    time.sleep(0.1)  # Small delay for mode switch
                
                if movement_changed:
                    if SHOW_RETURNS:
                        print(f"Move(vx={vx:.2f}, vy={vy:.2f}, wz={wz:.2f})")
                    ret = self.client.Move(vx, vy, wz)
                    if SHOW_RETURNS:
                        print("ret:", ret)
                    last_vx, last_vy, last_wz = vx, vy, wz
            else:
                # Stop if no movement and we were moving before
                if abs(last_vx) > 0.01 or abs(last_vy) > 0.01 or abs(last_wz) > 0.01:
                    ret = self.client.StopMove()
                    if SHOW_RETURNS:
                        print("Stop ret:", ret)
                    last_vx, last_vy, last_wz = 0.0, 0.0, 0.0
                
                # Disable FreeWalk mode when stopped
                if freewalk_enabled:
                    if SHOW_RETURNS:
                        print("Disabling FreeWalk mode")
                    ret = self.client.StopMove()
                    if SHOW_RETURNS:
                        print("StopMove ret:", ret)
                    freewalk_enabled = False
            
            time.sleep(UPDATE_RATE)
    
    def set_movement(self, vx: float, vy: float, wz: float):
        """Set the current movement velocities directly"""
        with self.lock:
            self.current_vx = vx
            self.current_vy = vy
            self.current_wz = wz
    
    def set_walk_upright(self, enable: bool):
        """Enable or disable walk upright mode"""
        with self.lock:
            if enable != self.walk_upright_active:
                self.walk_upright_active = enable
                if enable:
                    if SHOW_RETURNS:
                        print("Enabling walk upright mode")
                    # First stop any current movement to avoid conflicts
                    self.client.StopMove()
                    time.sleep(0.2)  # Longer delay to ensure stop command is processed
                    
                    # Try to ensure robot is in a stable state
                    try:
                        ret = self.client.WalkUpright(True)
                        if SHOW_RETURNS:
                            print("WalkUpright(True) ret:", ret)
                        if ret != 0:
                            print(f"Warning: WalkUpright(True) returned error code: {ret}")
                    except Exception as e:
                        print(f"Exception during WalkUpright(True): {e}")
                        self.walk_upright_active = False  # Reset state on error
                else:
                    if SHOW_RETURNS:
                        print("Disabling walk upright mode")
                    try:
                        ret = self.client.WalkUpright(False)
                        if SHOW_RETURNS:
                            print("WalkUpright(False) ret:", ret)
                        if ret != 0:
                            print(f"Warning: WalkUpright(False) returned error code: {ret}")
                    except Exception as e:
                        print(f"Exception during WalkUpright(False): {e}")
                    time.sleep(0.2)  # Longer delay after disabling
    
    def stop(self):
        """Stop all movement and clean up"""
        self.running = False
        with self.lock:
            self.current_vx = 0.0
            self.current_vy = 0.0
            self.current_wz = 0.0
        self.client.StopMove()

def curses_main(stdscr, controller: ContinuousController):
    curses.curs_set(0)
    stdscr.nodelay(True)   # Don't block on key input (enables continuous polling)
    stdscr.keypad(True)    # enable arrow keys

    lines = [
        "Go2 EDU Continuous Teleop (WASD + Arrow Keys)",
        "---------------------------------------------",
        "w/s : forward/backward (hold to move)",
        "a/d : left/right (strafe) (hold to move)",
        "←/→ : rotate left/right (hold to rotate)",
        "↑ : walk upright",
        "↓ : leave walk upright",
        "space: immediate stop",
        "q or ESC: quit",
        "",
        f"Speeds: vx={LINEAR_SPEED} m/s, vy={LATERAL_SPEED} m/s, wz={ANGULAR_SPEED} rad/s",
        f"Update rate: {1.0/UPDATE_RATE:.1f} Hz",
        "",
        "Ready. Hold keys to move continuously..."
    ]

    for i, t in enumerate(lines):
        stdscr.addstr(i, 0, t)
    stdscr.refresh()

    # Track which keys are currently pressed
    pressed_keys = set()
    # Track keys that were just pressed (for single-press actions)
    just_pressed = set()

    while True:
        ch = stdscr.getch()
        
        # Handle key press/release
        if ch != -1:  # -1 means no key pressed
            if ch in (ord('q'), 27):  # 'q' or ESC
                break
            elif ch == ord(' '):  # space
                controller.set_movement(0.0, 0.0, 0.0)
                pressed_keys.clear()
                just_pressed.clear()
            else:
                # Check if this is a new key press
                if ch not in pressed_keys:
                    just_pressed.add(ch)
                pressed_keys.add(ch)
        else:
            # No key pressed, clear all pressed keys
            pressed_keys.clear()
            just_pressed.clear()

        # Determine movement based on currently pressed keys
        vx, vy, wz = 0.0, 0.0, 0.0
        
        # Forward/backward
        if ord('w') in pressed_keys or ord('W') in pressed_keys:
            vx += LINEAR_SPEED
        if ord('s') in pressed_keys or ord('S') in pressed_keys:
            vx -= LINEAR_SPEED
            
        # Left/right strafe
        if ord('a') in pressed_keys or ord('A') in pressed_keys:
            vy += LATERAL_SPEED  # left strafe
        if ord('d') in pressed_keys or ord('D') in pressed_keys:
            vy -= LATERAL_SPEED  # right strafe
            
        # Rotation
        if curses.KEY_LEFT in pressed_keys:
            wz += ANGULAR_SPEED  # rotate left (CCW)
        if curses.KEY_RIGHT in pressed_keys:
            wz -= ANGULAR_SPEED  # rotate right (CW)

        # Walk upright controls (up/down arrows) - single press only
        if curses.KEY_UP in just_pressed:
            print("Up arrow pressed - enabling walk upright")  # Debug output
            try:
                controller.set_walk_upright(True)  # Enable walk upright
            except Exception as e:
                print(f"Error enabling walk upright: {e}")
        elif curses.KEY_DOWN in just_pressed:
            print("Down arrow pressed - disabling walk upright")  # Debug output
            try:
                controller.set_walk_upright(False)  # Disable walk upright
            except Exception as e:
                print(f"Error disabling walk upright: {e}")

        # Send movement command
        controller.set_movement(vx, vy, wz)
        
        # Debug output for movement
        if vx != 0.0 or vy != 0.0 or wz != 0.0:
            print(f"Movement command: vx={vx:.2f}, vy={vy:.2f}, wz={wz:.2f}")

        # Refresh status display
        walk_status = "WALK UPRIGHT" if controller.walk_upright_active else "Normal"
        status_line = f"Movement: vx={vx:6.2f} vy={vy:6.2f} wz={wz:6.2f} | Mode: {walk_status}"
        stdscr.addstr(len(lines)+1, 0, status_line + " " * 20)  # Clear any leftover text
        stdscr.refresh()

        # Small delay to prevent excessive CPU usage
        time.sleep(0.01)

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

    # Create continuous controller
    controller = ContinuousController(client)

    try:
        curses.wrapper(curses_main, controller)
    finally:
        # Always stop motion and leave the robot in a stable state on exit.
        controller.stop()
        print("\nExiting teleop.")

if __name__ == "__main__":
    main()
