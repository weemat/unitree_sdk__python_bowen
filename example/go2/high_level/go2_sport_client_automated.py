import time
import sys
import threading
import keyboard
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.idl.default import unitree_go_msg_dds__SportModeState_
from unitree_sdk2py.idl.unitree_go.msg.dds_ import SportModeState_
from unitree_sdk2py.go2.sport.sport_client import (
    SportClient,
    PathPoint,
    SPORT_PATH_POINT_SIZE,
)
import math
from dataclasses import dataclass

@dataclass
class TestOption:
    name: str
    id: int

option_list = [
    TestOption(name="damp", id=0),         
    TestOption(name="stand_up", id=1),     
    TestOption(name="stand_down", id=2),   
    TestOption(name="move nsew", id=3),          
    TestOption(name="move rotate", id=4),  
    TestOption(name="stop_move", id=5),  
    TestOption(name="hand stand", id=6),
    TestOption(name="balanced stand", id=8),     
    TestOption(name="recovery", id=9),       
    TestOption(name="left flip", id=10),      
    TestOption(name="back flip", id=11),
    TestOption(name="free walk", id=12),  
    TestOption(name="free bound", id=13), 
    TestOption(name="free avoid", id=14),  
    TestOption(name="walk upright", id=16),
    TestOption(name="cross step", id=17),
    TestOption(name="free jump", id=18)       
]

class LiveController:
    def __init__(self, sport_client):
        self.sport_client = sport_client
        self.running = False
        self.current_command = None
        self.command_lock = threading.Lock()
        
        # Movement speeds
        self.move_speed = 0.3
        self.rotate_speed = 0.5
        
        # Key mappings
        self.key_commands = {
            'w': ('forward', lambda: self.sport_client.Move(self.move_speed, 0, 0)),
            's': ('backward', lambda: self.sport_client.Move(-self.move_speed, 0, 0)),
            'a': ('left', lambda: self.sport_client.Move(0, -self.move_speed, 0)),
            'd': ('right', lambda: self.sport_client.Move(0, self.move_speed, 0)),
            'left': ('rotate_left', lambda: self.sport_client.Move(0, 0, self.rotate_speed)),
            'right': ('rotate_right', lambda: self.sport_client.Move(0, 0, -self.rotate_speed)),
        }
    
    def on_key_press(self, event):
        """Handle key press events"""
        key = event.name.lower()
        
        with self.command_lock:
            if key in self.key_commands and self.current_command != key:
                command_name, command_func = self.key_commands[key]
                self.current_command = key
                print(f"Executing: {command_name}")
                command_func()
    
    def on_key_release(self, event):
        """Handle key release events"""
        key = event.name.lower()
        
        with self.command_lock:
            if key == self.current_command:
                print(f"Stopping: {self.key_commands[key][0]}")
                self.sport_client.StopMove()
                self.current_command = None
    
    def start_control(self):
        """Start the live control system"""
        print("=== Live Robot Control ===")
        print("Controls:")
        print("  W - Move forward")
        print("  S - Move backward") 
        print("  A - Move left")
        print("  D - Move right")
        print("  Left Arrow - Rotate left")
        print("  Right Arrow - Rotate right")
        print("  ESC - Exit")
        print("Press any movement key to start controlling the robot...")
        
        # Register key event handlers
        for key in self.key_commands.keys():
            keyboard.on_press_key(key, self.on_key_press, suppress=True)
            keyboard.on_release_key(key, self.on_key_release, suppress=True)
        
        # Register escape key to exit
        keyboard.on_press_key('esc', self.stop_control, suppress=True)
        
        self.running = True
        
        try:
            while self.running:
                time.sleep(0.1)  # Small delay to prevent high CPU usage
        except KeyboardInterrupt:
            self.stop_control()
    
    def stop_control(self, event=None):
        """Stop the live control system"""
        print("\nStopping live control...")
        self.running = False
        
        # Stop any current movement
        with self.command_lock:
            if self.current_command:
                self.sport_client.StopMove()
                self.current_command = None
        
        # Unregister all key handlers
        keyboard.unhook_all()
        print("Live control stopped.")

if __name__ == "__main__":
    print("WARNING: Please ensure there are no obstacles around the robot while running this example.")
    input("Press Enter to continue...")
    
    if len(sys.argv) > 1:
        ChannelFactoryInitialize(0, sys.argv[1])
    else:
        ChannelFactoryInitialize(0)

    # Initialize sport client
    sport_client = SportClient()  
    sport_client.SetTimeout(10.0)
    sport_client.Init()
    
    # Make sure robot is standing
    print("Standing up robot...")
    sport_client.StandUp()
    time.sleep(2)
    
    # Create and start live controller
    controller = LiveController(sport_client)
    
    try:
        controller.start_control()
    except Exception as e:
        print(f"Error during control: {e}")
    finally:
        # Clean up
        print("Cleaning up...")
        sport_client.StopMove()
        sport_client.Damp()
        print("Robot set to damp mode.")
