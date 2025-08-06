import sys
import time
from threading import Event
from pynput import keyboard
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.go2.sport.sport_client import SportClient

# Movement speeds
MOVE_SPEED = 0.3
ROTATE_SPEED = 0.5

# Global flags
exit_event = Event()
last_key = None

def on_press(key):
    global last_key
    try:
        if key.char in ['w', 'a', 's', 'd']:
            last_key = key.char
    except AttributeError:
        if key == keyboard.Key.left:
            last_key = 'left'
        elif key == keyboard.Key.right:
            last_key = 'right'
        elif key == keyboard.Key.esc:
            exit_event.set()

def on_release(key):
    global last_key
    # Reset on key release to ensure only one command at a time
    last_key = None

def main():
    global last_key

    print("WARNING: Please ensure there are no obstacles around the robot while running this example.")
    input("Press Enter to continue...")

    if len(sys.argv) > 1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)

    sport_client = SportClient()
    sport_client.SetTimeout(10.0)
    sport_client.Init()

    print("Standing up...")
    sport_client.StandUp()
    time.sleep(2)

    print("Control the robot with W/A/S/D and arrow keys. Press ESC to stop and enter Damp mode.")

    # Start listening to keyboard events
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.start()

    try:
        while not exit_event.is_set():
            if last_key == 'w':
                sport_client.Move(MOVE_SPEED, 0, 0)
            elif last_key == 's':
                sport_client.Move(-MOVE_SPEED, 0, 0)
            elif last_key == 'a':
                sport_client.Move(0, MOVE_SPEED, 0)
            elif last_key == 'd':
                sport_client.Move(0, -MOVE_SPEED, 0)
            elif last_key == 'left':
                sport_client.Move(0, 0, ROTATE_SPEED)
            elif last_key == 'right':
                sport_client.Move(0, 0, -ROTATE_SPEED)
            else:
                sport_client.StopMove()

            time.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        print("Exiting... Entering Damp mode.")
        sport_client.StopMove()
        sport_client.Damp()
        listener.stop()

if __name__ == "__main__":
    main()
