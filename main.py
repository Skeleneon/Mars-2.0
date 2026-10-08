
# Imports
from pystray import Icon, Menu, MenuItem
from vosk import Model, KaldiRecognizer
from pydualsense import pydualsense
from ctypes import cast,POINTER
from cProfile import label
from pygame import mixer
from PIL import Image
from gtts import gTTS
import pyautogui as g
import tkinter as tk
import pyaudio as au
import subprocess
import traceback
import threading
import tempfile
import logging
import pickle
import pygame
import random
import psutil
import queue
import time
import json
import sys
import os

current_pid = os.getpid()
python_processes = [p for p in psutil.process_iter(['pid', 'name']) if p.info['name'] and 'python' in p.info['name'].lower()]

if len(python_processes) > 1:
    for proc in python_processes:
        if proc.info['pid'] != current_pid:
            proc.kill()

def log_uncaught_exceptions(exctype, value, tb):
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    # Write to your log file or logger
    with open("crash.log", "a", encoding="utf-8") as f:
        f.write("=== CRASH DETECTED ===\n")
        f.write(error_msg + "\n")
    sys.__excepthook__(exctype, value, tb)







#Event flags
model_ready = threading.Event()
settings_ready = threading.Event()
speaker_ready = threading.Event()
mars_speaking=threading.Event()

# Controller IDs
DUALSENSE_VENDOR_ID = 0x54C
DUALSENSE_PRODUCT_IDS = [0xCE6, 0xDF2] 

# Paths
STEAM_PATH = r"D:\Programs\Steam\steam.exe"
MODEL_PATH = r"D:\Useful\Speech Model\vosk-model-small-en-us-0.15"
LOG_PATH = r"logs/"

# Other Variables
settings={}
logfilename = "logs/log_" + time.strftime("%Y-%m-%d--%H %M %S") + ".log"

# Vosk setup
model = None
recognizer = None


# Audio settings and setup
FRAMES_PER_BUFFER = 3200
FORMAT = au.paInt16
CHANNELS = 1
RATE = 16000
stream = None
p = None

# Queues
log_queue = queue.Queue()
tts_queue = queue.Queue()
audio_queue = queue.Queue()
text_queue = queue.Queue()


num_dict_ones = {"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10,
            "eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,"sixteen":16,"seventeen":17,
            "eighteen":18,"nineteen":19}

num_dict_tens = {"twenty":20,"thirty":30,"forty":40,"fifty":50,"sixty":60,"seventy":70,"eighty":80,"ninety":90,}

open(logfilename, "w").close()

def log(message):
    if not message:
        return
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}"
    with open(logfilename, "a") as log_file:
        log_file.write(log_entry)

def convertToNum(sentence):
    
    tens = 0
    ones = 0
    sentence2 = sentence.split()

    finished_sentence=""
    next=True
    
    for i in range(0,len(sentence2)):
        if next==False:
            next=True
            continue
        if sentence2[i]=="hundred":
            finished_sentence+="100 "
            continue
        
        if sentence2[i] in num_dict_tens or sentence2[i] in num_dict_ones:
            if sentence2[i] in num_dict_tens:
                tens = num_dict_tens[sentence2[i]]
                try:
                    a = sentence2[i+1]
                except: 
                    final_num = tens
                    finished_sentence+=str(final_num)+" "
                    continue
                if len(sentence2)>1 and sentence2[i+1] in num_dict_ones:
                    ones = num_dict_ones[sentence2[i+1]]
                    final_num = tens+ones
                    finished_sentence+=str(final_num)+" "
                    next=False
                    
                else:
                    final_num = tens
                    finished_sentence+=str(final_num)+" "
            else:
                ones = num_dict_ones[sentence2[i]]
                final_num = ones
                finished_sentence+=str(final_num)+" "
        else:
            finished_sentence+=sentence2[i]+" "

    return finished_sentence.strip()

def queue_add(q, item):
    if q.full():
        q.get()  
        q.put(item)
    else:
        q.put(item)

def _check_dualsense():
    result = [False]
    def _check():
        try:
            ds = pydualsense()
            ds.init()
            result[0] = False
            ds.close()
        except:
            result[0] = False

    t = threading.Thread(target=_check)
    t.start()
    t.join(timeout=1.0)  # give it 1 second max
    return result[0]
    
def _controller_worker():
    
    pygame.joystick.quit()
    pygame.joystick.init()
    print("Controllers: ", pygame.joystick.get_count())
    was_connected = queue.Queue(3)
    was_connected.put(True)
    was_connected.put(True)
    was_connected.put(False)

    while True:
        
        pygame.joystick.quit()
        pygame.joystick.init()
        connected = pygame.joystick.get_count() > 0
        

        if _steam_running():
            
            time.sleep(1)
            continue

        if connected and True not in list(was_connected.queue):
            print("Controllers: ", pygame.joystick.get_count())
            print("[System] Controller connected!")
            _launch_steam_bigpicture()
       
        elif _check_dualsense():
           pass

        queue_add(was_connected, connected)
        time.sleep(1)

def playAudio(fname, volume=None):
    print(f"[System] Playing audio: {fname}")
    if not speaker_ready.is_set():
        print("[Error] Sound output not initialized, cannot play audio.")
        return
    
    mars_speaking.set()

    if settings.get("current_output_device") is None:
        mars_speaking.clear()
        return
   
    mixer.music.load(fname)
    if volume is not None:
        mixer.music.set_volume(volume)
    else:
        mixer.music.set_volume(settings.get("tts_volume", 1.0))
    
    mixer.music.play()
    while mixer.music.get_busy():
        time.sleep(0.01)
    try:
        mixer.music.stop()
        mixer.music.unload()
    except:
        pass
    mars_speaking.clear()

def speak(text, volume=None):
    
    
    
    if not text:
        return
    mars_speaking.set()
    
    
    # Name pronunciation fixes
    text = text.replace("aman", "Aa men")
    text = text.replace("Aman", "Aa men")
    text = text.replace("AMAN", "Aa men")

    print(f"[Mars] {text}")

    if not settings.get("speech", True):
        pass

    vol = settings.get("tts_volume", 1.0) if volume is None else volume

    
    tts_queue.put((text, vol))

def _tts_worker():
   
   
    
    
    print("[System] TTS worker started...")
    while True:
        
        

        item = tts_queue.get()
        if item is None:  # poison pill
            print("[System] TTS worker exiting...")
            break

        text, volume = item
        fname = None
        try:
            # Generate MP3
            tts = gTTS(text, lang="en")
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                fname = f.name
            tts.save(fname)

            # Play
            playAudio(fname, volume)

        except Exception as e:
            print(f"[Error] while generating TTS: {e}")
        finally:
            try:
                mixer.music.stop()
                mixer.music.unload()
            except:
                pass
            if fname and os.path.exists(fname):
                os.remove(fname)
            tts_queue.task_done()



def _steam_running():
    return any(process.name().lower() == "steam.exe" for process in psutil.process_iter(["name"]))

def _launch_steam_bigpicture():
    if _steam_running():
        print("[System] Steam already running, skipping launch")
        return
    print("[System] Launching Steam Big Picture")
    
    
    playAudio("assets/sounds/hotkey.wav", 1.0)
    subprocess.Popen([STEAM_PATH, "-bigpicture"])

class FakeConsole:
    def __init__(self, q): self.q = q
    def write(self, text): self.q.put(text)
    def flush(self): pass


def _load_stuff():
    global model, recognizer, settings
    model_ready.clear()
    settings=pickle.load(open("subfiles/settings.dat", "rb"))
    settings_ready.set()
    
    
    print("[System] Loading Vosk model...")
    model_ready.clear()
    model = Model(MODEL_PATH)
    recognizer = KaldiRecognizer(model, RATE)
    print("[System] Vosk Model ready!")
    model_ready.set()  
      
    
    try:
       mixer.init()
       speaker_ready.set()
       print("[System] Audio mixer initialized!")
    except Exception as e:
        print(f"[Error] Audio mixer initialization failed: {e}")
        speaker_ready.clear()

    

# --- Tray icon ---
def build_tray(root):
    def show(icon, item): root.after(0, root.deiconify)
    #def show_settings(icon, item): root.after(0, lambda: open_settings(root));show(icon, item)
    
    def quit_app(icon, item):
        print("[System] Quitting...")
        log("[System] Quitting...")
        icon.stop()
        root.after(0, root.destroy)


    icon_image = Image.open("assets/icon.ico")
    menu = Menu(
        MenuItem("Show Console", show),
        #MenuItem("Settings", show_settings),
        MenuItem("Quit", quit_app),
    )
    return Icon("Mars: Voice Assistant", icon_image, "Mars", menu)


    

def main():




    def poll():
        while not log_queue.empty():
            msg = log_queue.get_nowait()
            log(msg)
            at_bottom = text.yview()[1] >= 0.99
            text.configure(state="normal")
            if msg.split():
                mode = msg.split()[0].lower()
            else:
                mode = "normal"

            match mode:
                case "[error]":
                    text.insert("end", msg, "error")
                case "[system]":
                    text.insert("end", msg, "system")
                case "[mars]":
                    text.insert("end", msg, "mars")
                case "[user]":
                    text.insert("end", msg, "user")
                case _:
                    text.insert("end", msg, "normal")

            if at_bottom:
                text.see("end")
            text.configure(state="disabled")
        root.after(100, poll)

    
    root = tk.Tk()
    root.title("Mars: Terminal")
    root.iconphoto(True, tk.PhotoImage(file="assets/icon.png"))

    root.geometry("650x450+30+20")

    
    

    text = tk.Text(root, state="disabled", bg="black", fg="lime",
                                      font=("Consolas", 10))
    
    text.pack(fill="both", expand=True)
    text.tag_configure("error", foreground="red")
    text.tag_configure("system", foreground="blue")
    text.tag_configure("mars", foreground="orange")
    text.tag_configure("user", foreground="yellow")
    text.tag_configure("normal", foreground="lime")
    
  
    

    
    sys.stdout = FakeConsole(log_queue)
    sys.stderr = FakeConsole(log_queue)
    sys.excepthook = log_uncaught_exceptions
  
    
    
    root.protocol("WM_DELETE_WINDOW", root.withdraw)

    
    icon = build_tray(root)
    

   
    
    #initialization threads
    print("[System] Initializing...")
    
    threading.Thread(target=icon.run, daemon=True).start() 

    threading.Thread(target=_load_stuff, daemon=True).start()
    while not settings_ready.is_set():
        time.sleep(0.1)


    #loop threads
    threading.Thread(target=_tts_worker, daemon=True).start()
    threading.Thread(target=_controller_worker, daemon=True).start()
    time.sleep(2)
    
    

    # Hidden on startup
    root.withdraw()

    poll()
    root.mainloop()
   


if __name__ == "__main__":
    main()
    