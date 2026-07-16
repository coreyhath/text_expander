import subprocess
import time

# CONFIGURATION: Change this to match your USB Microphone's exact system name
USB_MIC_NAME = "K66"  

def get_current_input():
    try:
        result = subprocess.run(
            ["SwitchAudioSource", "-c", "-t", "input"], 
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None

def set_input_device(device_name):
    try:
        # 1. Switch the hardware input source
        subprocess.run(["SwitchAudioSource", "-t", "input", "-s", device_name], check=True)
        print(f"Successfully forced input back to: {device_name}")
        
        # 2. Maximize the system input volume (100%)
        subprocess.run(["osascript", "-e", "set volume input volume 100"], check=True)
        print("Microphone gain maximized to 100%.")
    except subprocess.CalledProcessError as e:
        print(f"Error handling audio changes: {e}")

def main():
    print(f"--- Audio & Gain Daemon Started: Prioritizing '{USB_MIC_NAME}' ---")
    while True:
        current_device = get_current_input()
        
        if current_device and current_device != USB_MIC_NAME:
            print(f"Detected layout change! Current: {current_device}. Reverting...")
            set_input_device(USB_MIC_NAME)
            
        time.sleep(2)

if __name__ == "__main__":
    main()
