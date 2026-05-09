import os
import subprocess
import asyncio
import websockets
import json
import base64
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.backends import default_backend
from datetime import datetime
import ssl
import signal
import re
import tkinter as tk
from tkinter import scrolledtext, ttk, simpledialog, filedialog, messagebox
import threading
import uuid
import requests
import webbrowser

# Group 11
## Ge Wang | a1880714
## Yong Yue Beh | a1843874
## Liew Yi Hui | a1907230
## Mustafa Jamale | a1863981

# Utility functions for encryption and decryption
def encrypt_private_key(private_key, password):
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode())
    iv = os.urandom(12)  # GCM requires a 12-byte IV
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padder = sym_padding.PKCS7(algorithms.AES.block_size).padder()
    padded_data = padder.update(private_key) + padder.finalize()
    encrypted_private_key = encryptor.update(padded_data) + encryptor.finalize()
    return salt + iv + encryptor.tag + encrypted_private_key

def decrypt_private_key(encrypted_private_key, password):
    salt = encrypted_private_key[:16]
    iv = encrypted_private_key[16:28]
    tag = encrypted_private_key[28:44]
    encrypted_data = encrypted_private_key[44:]
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode())
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted_padded_data = decryptor.update(encrypted_data) + decryptor.finalize()
    unpadder = sym_padding.PKCS7(algorithms.AES.block_size).unpadder()
    private_key = unpadder.update(decrypted_padded_data) + unpadder.finalize()
    return private_key

# Generate SSL/TLS certificates for the user
def generate_user_certificates(username, user_id, password):
    cert_file = f"{username}_{user_id}_cert.pem"
    key_file = f"{username}_{user_id}_key.pem"
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", key_file, "-out", cert_file, "-days", "365", "-nodes",
            f"-subj", f"/CN={username}/UID={user_id}"
        ],check=True)
        with open(key_file, 'rb') as f:
            private_key = f.read()
        encrypted_private_key = encrypt_private_key(private_key, password)
        with open(key_file, 'wb') as f:
            f.write(encrypted_private_key)
        print(f"SSL/TLS certificates generated for {username} with ID {user_id} and private key encrypted.")
    return cert_file, key_file

def load_user_ssl_context(username, user_id, password):
    cert_file = f"{username}_{user_id}_cert.pem"
    key_file = f"{username}_{user_id}_key.pem"
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    with open(key_file, 'rb') as f:
        encrypted_private_key = f.read()
    private_key = decrypt_private_key(encrypted_private_key, password)
    
    # Write the decrypted private key to a temporary file
    temp_key_file = f"temp_{username}_{user_id}_key.pem"
    with open(temp_key_file, 'wb') as f:
        f.write(private_key)
    
    ssl_context.load_cert_chain(certfile=cert_file, keyfile=temp_key_file)
    
    # Remove the temporary file after loading the SSL context
    os.remove(temp_key_file)
    
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context

def sanitize_input(input_string):
    return re.sub(r'[^\w\s]', '', input_string)

def cleanup(username, user_id):
    cert_file = f"{username}_{user_id}_cert.pem"
    key_file = f"{username}_{user_id}_key.pem"
    if os.path.exists(cert_file):
        os.remove(cert_file)
    if os.path.exists(key_file):
        os.remove(key_file)
    print(f"SSL/TLS certificates removed for {username} with ID {user_id}.")

# Generate RSA key pair
private_key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=2048
)
public_key = private_key.public_key()

# Serialize public key
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

# Counter for message signing
counter = 0

class ChatGUI:
    def __init__(self, master, username, user_id):
        self.master = master
        self.username = username
        self.user_id = user_id
        self.message_type = "public"  # Track the message type
        self.recipient = None  # Track the recipient for private messages
        self.message_widgets = {} # Track message locations for status updates
        self.message_details = {}
        self.message_meta = {}
        self.chat_history = []
        self.reply_context = None
        self.active_details_window = None
        self.active_details_message_id = None
        self.presence_status = "online"
        self.user_status_snapshot = {}
        master.title("Secure Chat Client  •  Secure Messaging")
        
        # Dark matte palette
        self.colors = {
            "bg_primary": "#121417",
            "bg_secondary": "#1A1D21",
            "bg_tertiary": "#22262B",
            "panel": "#171A1F",
            "text_primary": "#E6E9EE",
            "text_muted": "#A8AFB9",
            "accent": "#57B5A5",
            "accent_soft": "#3C8F82",
            "danger": "#D16B6B",
            "border": "#2A2F36"
        }

        self.font_ui = ("Segoe UI", 10)
        self.font_heading = ("Segoe UI Semibold", 11)
        self.font_body = ("Consolas", 10)

        master.configure(bg=self.colors["bg_primary"])
        
        master.minsize(width=400, height=500)

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('App.TFrame', background=self.colors["panel"])
        self.style.configure('AppHeader.TLabel', background=self.colors["panel"], foreground=self.colors["text_primary"], font=self.font_heading)
        self.style.configure('AppSub.TLabel', background=self.colors["panel"], foreground=self.colors["text_muted"], font=self.font_ui)
        self.style.configure('App.TPanedwindow', background=self.colors["bg_primary"], sashwidth=8)
        self.style.configure('App.TCombobox', fieldbackground=self.colors["bg_tertiary"], background=self.colors["bg_tertiary"], foreground=self.colors["text_primary"], arrowcolor=self.colors["text_primary"])

        # Create a PanedWindow
        self.paned_window = ttk.PanedWindow(master, orient=tk.HORIZONTAL, style='App.TPanedwindow')
        self.paned_window.pack(expand=True, fill='both')

        # Left pane for chat
        self.left_frame = ttk.Frame(self.paned_window, style='App.TFrame')
        self.paned_window.add(self.left_frame, weight=3)

        # Add a label to display the username and user ID
        self.username_label = tk.Label(
            self.left_frame,
            text=f"🔒  {self.username}   |   ID: {self.user_id}",
            font=self.font_heading,
            bg=self.colors["panel"],
            fg=self.colors["text_primary"],
            padx=10,
            pady=8,
            anchor='w'
        )
        self.username_label.pack(side='top', fill='x')

        self.chat_display = scrolledtext.ScrolledText(
            self.left_frame,
            state='disabled',
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            insertbackground=self.colors["text_primary"],
            selectbackground=self.colors["accent_soft"],
            selectforeground=self.colors["text_primary"],
            relief='flat',
            padx=10,
            pady=10,
            font=self.font_body,
            bd=1,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"]
        )
        self.chat_display.pack(expand=True, fill='both')

        self.reply_preview_frame = tk.Frame(
            self.left_frame,
            bg=self.colors["bg_tertiary"],
            bd=1,
            highlightthickness=1,
            highlightbackground=self.colors["border"]
        )
        self.reply_preview_label = tk.Label(
            self.reply_preview_frame,
            text="",
            bg=self.colors["bg_tertiary"],
            fg=self.colors["text_muted"],
            font=("Segoe UI", 9),
            anchor='w'
        )
        self.reply_preview_label.pack(side='left', fill='x', expand=True, padx=8, pady=4)
        self.reply_cancel_button = tk.Button(
            self.reply_preview_frame,
            text="✕",
            command=self.clear_reply_context,
            bg=self.colors["bg_tertiary"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["danger"],
            activeforeground=self.colors["text_primary"],
            relief='flat',
            bd=0,
            padx=8,
            font=("Segoe UI Semibold", 9),
            cursor='hand2'
        )
        self.reply_cancel_button.pack(side='right', padx=(0, 4))

        self.msg_entry = tk.Entry(
            self.left_frame,
            bg=self.colors["bg_tertiary"],
            fg=self.colors["text_primary"],
            insertbackground=self.colors["text_primary"],
            relief='flat',
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            font=self.font_ui
        )
        self.msg_entry.pack(side='left', expand=True, fill='x')

        self.send_button = tk.Button(
            self.left_frame,
            text="➤ Send",
            command=self.send_message,
            bg=self.colors["accent"],
            fg="#0E1412",
            activebackground=self.colors["accent_soft"],
            activeforeground=self.colors["text_primary"],
            relief='flat',
            bd=0,
            padx=12,
            pady=6,
            font=("Segoe UI Semibold", 10),
            cursor='hand2'
        )
        self.send_button.pack(side='right')

        # Bind the Return key to the send_message method
        self.msg_entry.bind('<Return>', self.send_message)

        # Right pane for user list
        self.right_frame = ttk.Frame(self.paned_window, style='App.TFrame')
        self.paned_window.add(self.right_frame, weight=1)

        self.user_list_label = tk.Label(
            self.right_frame,
            text="👥 Active Contacts",
            bg=self.colors["panel"],
            fg=self.colors["text_primary"],
            font=self.font_heading,
            pady=8
        )
        self.user_list_label.pack()

        self.user_listbox = tk.Listbox(
            self.right_frame,
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            selectbackground=self.colors["accent_soft"],
            selectforeground=self.colors["text_primary"],
            relief='flat',
            bd=1,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            highlightcolor=self.colors["accent"],
            font=self.font_ui
        )
        self.user_listbox.pack(expand=True, fill='both')

        # Lightweight visualization panel for live network presence
        self.network_viz_frame = tk.Frame(
            self.right_frame,
            bg=self.colors["bg_secondary"],
            bd=1,
            highlightthickness=1,
            highlightbackground=self.colors["border"]
        )
        self.network_viz_frame.pack(fill='x', padx=6, pady=8)

        self.network_viz_title = tk.Label(
            self.network_viz_frame,
            text="📊 Network Insight",
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            font=("Segoe UI Semibold", 10)
        )
        self.network_viz_title.pack(anchor='w', padx=8, pady=(6, 2))

        self.network_stats_label = tk.Label(
            self.network_viz_frame,
            text="Total: 0   Online: 0   Offline: 0",
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_muted"],
            font=("Segoe UI", 9)
        )
        self.network_stats_label.pack(anchor='w', padx=8, pady=(0, 6))

        self.network_bar_canvas = tk.Canvas(
            self.network_viz_frame,
            height=18,
            bg=self.colors["bg_secondary"],
            highlightthickness=0,
            bd=0
        )
        self.network_bar_canvas.pack(fill='x', padx=8, pady=(0, 8))

        # Command buttons
        self.command_frame = ttk.Frame(self.left_frame, style='App.TFrame')
        self.command_frame.pack(side='bottom', fill='x')

        self.private_button = tk.Button(
            self.command_frame,
            text="✉ Private",
            command=self.toggle_message_type,
            bg=self.colors["bg_tertiary"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["accent_soft"],
            activeforeground=self.colors["text_primary"],
            relief='flat',
            bd=0,
            padx=10,
            pady=6,
            font=self.font_ui,
            cursor='hand2'
        )
        self.private_button.pack(side='left')

        self.file_button = tk.Button(
            self.command_frame,
            text="📎 File",
            command=self.send_file_command,
            bg=self.colors["bg_tertiary"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["accent_soft"],
            activeforeground=self.colors["text_primary"],
            relief='flat',
            bd=0,
            padx=10,
            pady=6,
            font=self.font_ui,
            cursor='hand2'
        )
        self.file_button.pack(side='left')

        self.presence_button = tk.Button(
            self.command_frame,
            text="🟢 Online",
            command=self.toggle_presence,
            bg=self.colors["bg_tertiary"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["accent_soft"],
            activeforeground=self.colors["text_primary"],
            relief='flat',
            bd=0,
            padx=10,
            pady=6,
            font=self.font_ui,
            cursor='hand2'
        )
        self.presence_button.pack(side='left')

        self.search_button = tk.Button(
            self.command_frame,
            text="🔎 Search",
            command=self.open_search_filters_window,
            bg=self.colors["bg_tertiary"],
            fg=self.colors["text_primary"],
            activebackground=self.colors["accent_soft"],
            activeforeground=self.colors["text_primary"],
            relief='flat',
            bd=0,
            padx=10,
            pady=6,
            font=self.font_ui,
            cursor='hand2'
        )
        self.search_button.pack(side='left')

        # Add a "Log Out" button at the top right corner
        self.logout_button = tk.Button(
            master,
            text="⏻ Log Out",
            command=self.log_out,
            bg=self.colors["danger"],
            fg=self.colors["text_primary"],
            activebackground="#B35959",
            activeforeground=self.colors["text_primary"],
            relief='flat',
            bd=0,
            padx=10,
            pady=5,
            font=("Segoe UI Semibold", 9),
            cursor='hand2'
        )
        self.logout_button.pack(side='top', anchor='ne')

        self.websocket = None
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.start_loop, daemon=True).start()

        # Bind the window close event to the cleanup function
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start_chat_client(self):
        password = simpledialog.askstring("Password", "Enter your password:", show='*')
        asyncio.run_coroutine_threadsafe(self.chat_client(password), self.loop)

    async def chat_client(self, password):
        uri = "wss://localhost:8766"
        cert_file, key_file = generate_user_certificates(self.username, self.user_id, password)
        ssl_context = load_user_ssl_context(self.username, self.user_id, password)

        try:
            async with websockets.connect(uri, ssl=ssl_context) as websocket:
                self.websocket = websocket
                await self.send_hello()
                await self.listen_for_messages()
        except Exception as e:
            self.display_message(f"Error: {e}")

    async def send_hello(self):
        global counter
        hello_message = {
            "type": "signed_data",
            "data": {
                "type": "hello",
                "public_key": public_pem,
                "username": self.username,
                "user_id": self.user_id
            },
            "counter": counter,
            "signature": sign_message({"type": "hello", "public_key": public_pem, "username": self.username, "user_id": self.user_id}, counter)
        }
        counter += 1
        await self.websocket.send(json.dumps(hello_message))

    async def send_chat(self, message):
        global counter
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message_id = str(uuid.uuid4())
        reply_to = self.reply_context
        chat_message = {
            "type": "signed_data",
            "data": {
                "type": "public_chat",
                "message_id": message_id,
                "sender": self.username,
                "user_id": self.user_id,
                "message": message,
                "timestamp": timestamp,
                "reply_to": reply_to
            },
            "counter": counter,
            "signature": sign_message({"type": "public_chat", "message_id": message_id, "sender": self.username, "user_id": self.user_id, "message": message, "timestamp": timestamp, "reply_to": reply_to}, counter)
        }
        counter += 1
        await self.websocket.send(json.dumps(chat_message))
        self.display_message(
            f"You [{timestamp}]: {message}",
            message_id=message_id,
            is_outgoing=True,
            sent_at=timestamp,
            sender=self.username,
            timestamp=timestamp,
            body=message,
            reply_to=reply_to
        )
        self.clear_reply_context()

    async def send_private_chat(self, recipient, message):
        global counter
        message_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        reply_to = self.reply_context
        private_chat_message = {
            "type": "signed_data",
            "data": {
                "type": "private_chat",
                "message_id": message_id,
                "recipient": recipient,
                "message": message,
                "sender": self.username,
                "user_id": self.user_id,
                "timestamp": timestamp,
                "reply_to": reply_to
            },
            "counter": counter,
            "signature": sign_message({"type": "private_chat", "message_id": message_id, "recipient": recipient, "message": message, "sender": self.username, "user_id": self.user_id, "timestamp": timestamp, "reply_to": reply_to}, counter)
        }
        counter += 1
        await self.websocket.send(json.dumps(private_chat_message))
        self.display_message(
            f"[Private] You -> {recipient} [{timestamp}]: {message}",
            message_id=message_id,
            is_outgoing=True,
            sent_at=timestamp,
            sender=self.username,
            timestamp=timestamp,
            body=message,
            is_private=True,
            reply_to=reply_to
        )
        self.clear_reply_context()

    async def send_presence_update(self, status):
        global counter
        message = {
            "type": "signed_data",
            "data": {
                "type": "presence_update",
                "status": status,
                "username": self.username,
                "user_id": self.user_id
            },
            "counter": counter,
            "signature": sign_message({"type": "presence_update", "status": status, "username": self.username, "user_id": self.user_id}, counter)
        }
        counter += 1
        await self.websocket.send(json.dumps(message))

    async def send_file_transfer(self, recipient, file_url, file_name):
        global counter
        try:
            file_transfer_message = {
                "type": "signed_data",
                "data": {
                    "type": "file_transfer",
                    "recipient": recipient,
                    "file_url": file_url,
                    "sender": self.username,
                    "file_name": file_name
                },
                "counter": counter,
                "signature": sign_message({"type": "file_transfer", "recipient": recipient, "file_url": file_url, "sender": self.username, "file_name": file_name}, counter)
            }
            counter += 1
            await self.websocket.send(json.dumps(file_transfer_message))
            self.display_message(f"File sent to {recipient}: {file_name}", is_link=True)
        except Exception as e:
            self.display_message(f"Error: {e}")

    async def send_read_receipt(self, message_id):
        try:
            await self.websocket.send(json.dumps({
                "type": "read_receipt",
                "message_id": message_id
            }))
        except:
            pass

    async def listen_for_messages(self):
        try:
            async for message in self.websocket:
                data = json.loads(message)
                if data['type'] == 'chat_message':
                    message_id = data.get('message_id')
                    parsed_sender, parsed_ts, parsed_body, parsed_private = self.parse_chat_message(data['message'])
                    self.display_message(
                        data['message'],
                        message_id=message_id,
                        sender=parsed_sender,
                        timestamp=parsed_ts,
                        body=parsed_body,
                        is_private=parsed_private,
                        reply_to=data.get('reply_to')
                    )
                    
                    if message_id:
                        asyncio.run_coroutine_threadsafe(
                            self.send_read_receipt(message_id),
                            self.loop
                        )
                elif data['type'] == 'user_list':
                    self.update_user_list(data['users'])
                elif data['type'] == 'file_transfer':
                    self.receive_file(data['file_url'], data['sender'], data['file_name'])
                elif data['type'] == 'message_status':
                    status = data.get('status')
                    msg_id = data.get('message_id')
                    seen_by = data.get('seen_by', [])
                    seen_details = data.get('seen_details', [])
                    status_time = data.get('status_time')
                    self.update_message_status(msg_id, status, seen_by, seen_details, status_time)

        except websockets.ConnectionClosed:
            self.display_message("Connection closed.")
        except Exception as e:
            self.display_message(f"Error: {e}")

    def receive_file(self, file_url, sender, file_name):
        if messagebox.askyesno("File Transfer", f"{sender} wants to send you a file: {file_name}. Do you want to download it?"):
            try:
                response = requests.get(file_url, timeout=5)
                if not file_name.endswith(('.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx')):
                    self.display_message(f"File received from {sender}: {file_name} is invalid file type.")
                    requests.post(f"{file_url}/delete", timeout=5)
                    return
                
                response.raise_for_status()
                file_path = filedialog.asksaveasfilename(defaultextension=".bin", initialfile=file_name)
                if file_path:
                    with open(file_path, 'wb') as f:
                        f.write(response.content)
                    self.display_message(f"File received from {sender}: {file_name}", is_link=True)
                    requests.post(f"{file_url}/delete", timeout=5)
            except Exception as e:
                self.display_message(f"Error receiving file: {e}")
                requests.post(f"{file_url}/delete", timeout=5)
        else:
            requests.post(f"{file_url}/delete", timeout=5)

    def send_message(self, event=None):
        message = sanitize_input(self.msg_entry.get())
        if message:
            if self.message_type == "public":
                asyncio.run_coroutine_threadsafe(self.send_chat(message), self.loop)
            elif self.message_type == "private" and self.recipient:
                asyncio.run_coroutine_threadsafe(self.send_private_chat(self.recipient, message), self.loop)
            self.msg_entry.delete(0, tk.END)

    def parse_chat_message(self, raw_message):
        # Expected: [Public] sender [YYYY-MM-DD HH:MM:SS]: message
        #           [Private] sender [YYYY-MM-DD HH:MM:SS]: message
        match = re.match(r"^\[(Public|Private)\]\s(.+?)\s\[(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})\]:\s(.*)$", raw_message)
        if match:
            chat_type, sender, timestamp, body = match.groups()
            return sender, timestamp, body, chat_type == "Private"
        return "Unknown", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), raw_message, False

    def set_reply_context_from_message(self, message_id):
        meta = self.message_meta.get(message_id)
        if not meta:
            return

        preview = (meta.get("body") or "").strip()
        if len(preview) > 70:
            preview = preview[:67] + "..."

        self.reply_context = {
            "message_id": message_id,
            "sender": meta.get("sender", "Unknown"),
            "timestamp": meta.get("timestamp", "Unknown"),
            "preview": preview
        }
        self.reply_preview_label.config(
            text=f"Replying to {self.reply_context['sender']}: {self.reply_context['preview']}"
        )
        self.reply_preview_frame.pack(fill='x', padx=2, pady=(0, 4), before=self.msg_entry)

    def clear_reply_context(self):
        self.reply_context = None
        self.reply_preview_frame.pack_forget()

    def open_search_filters_window(self):
        search_win = tk.Toplevel(self.master)
        search_win.title("Search & Filters")
        search_win.geometry("680x420")
        search_win.configure(bg=self.colors["bg_primary"])

        filter_frame = tk.Frame(search_win, bg=self.colors["bg_primary"])
        filter_frame.pack(fill='x', padx=10, pady=10)

        tk.Label(filter_frame, text="Keyword", bg=self.colors["bg_primary"], fg=self.colors["text_primary"], font=self.font_ui).grid(row=0, column=0, sticky='w', padx=4, pady=4)
        keyword_entry = tk.Entry(filter_frame, bg=self.colors["bg_tertiary"], fg=self.colors["text_primary"], insertbackground=self.colors["text_primary"], relief='flat', font=self.font_ui)
        keyword_entry.grid(row=0, column=1, sticky='ew', padx=4, pady=4)

        tk.Label(filter_frame, text="Sender", bg=self.colors["bg_primary"], fg=self.colors["text_primary"], font=self.font_ui).grid(row=0, column=2, sticky='w', padx=4, pady=4)
        sender_entry = tk.Entry(filter_frame, bg=self.colors["bg_tertiary"], fg=self.colors["text_primary"], insertbackground=self.colors["text_primary"], relief='flat', font=self.font_ui)
        sender_entry.grid(row=0, column=3, sticky='ew', padx=4, pady=4)

        tk.Label(filter_frame, text="From (YYYY-MM-DD)", bg=self.colors["bg_primary"], fg=self.colors["text_primary"], font=self.font_ui).grid(row=1, column=0, sticky='w', padx=4, pady=4)
        from_entry = tk.Entry(filter_frame, bg=self.colors["bg_tertiary"], fg=self.colors["text_primary"], insertbackground=self.colors["text_primary"], relief='flat', font=self.font_ui)
        from_entry.grid(row=1, column=1, sticky='ew', padx=4, pady=4)

        tk.Label(filter_frame, text="To (YYYY-MM-DD)", bg=self.colors["bg_primary"], fg=self.colors["text_primary"], font=self.font_ui).grid(row=1, column=2, sticky='w', padx=4, pady=4)
        to_entry = tk.Entry(filter_frame, bg=self.colors["bg_tertiary"], fg=self.colors["text_primary"], insertbackground=self.colors["text_primary"], relief='flat', font=self.font_ui)
        to_entry.grid(row=1, column=3, sticky='ew', padx=4, pady=4)

        filter_frame.grid_columnconfigure(1, weight=1)
        filter_frame.grid_columnconfigure(3, weight=1)

        result_list = tk.Listbox(
            search_win,
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            selectbackground=self.colors["accent_soft"],
            selectforeground=self.colors["text_primary"],
            relief='flat',
            bd=1,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            font=("Consolas", 10)
        )
        result_list.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        search_result_ids = []

        def run_filter():
            keyword = keyword_entry.get().strip().lower()
            sender_filter = sender_entry.get().strip().lower()
            from_date = from_entry.get().strip()
            to_date = to_entry.get().strip()

            result_list.delete(0, tk.END)
            search_result_ids.clear()

            for item in self.chat_history:
                text = item.get("body", "")
                sender = item.get("sender", "")
                ts = item.get("timestamp", "")
                date_only = ts[:10] if len(ts) >= 10 else ""

                if keyword and keyword not in text.lower():
                    continue
                if sender_filter and sender_filter not in sender.lower():
                    continue
                if from_date and date_only and date_only < from_date:
                    continue
                if to_date and date_only and date_only > to_date:
                    continue

                row = f"[{ts}] {sender}: {text}"
                result_list.insert(tk.END, row)
                search_result_ids.append(item.get("message_id"))

            if result_list.size() == 0:
                result_list.insert(tk.END, "No matching messages found.")

        def jump_to_selected(_event=None):
            if not result_list.curselection():
                return
            idx = result_list.curselection()[0]
            if idx >= len(search_result_ids):
                return
            message_id = search_result_ids[idx]
            if not message_id:
                return
            tag_name = self.message_widgets.get(message_id)
            if not tag_name:
                return
            ranges = self.chat_display.tag_ranges(tag_name)
            if len(ranges) >= 1:
                self.chat_display.see(ranges[0])
                self.chat_display.focus_set()

        action_frame = tk.Frame(search_win, bg=self.colors["bg_primary"])
        action_frame.pack(fill='x', padx=10, pady=(0, 10))

        tk.Button(action_frame, text="Apply Filters", command=run_filter, bg=self.colors["accent"], fg="#0E1412", activebackground=self.colors["accent_soft"], relief='flat', bd=0, padx=12, pady=6, font=("Segoe UI Semibold", 10), cursor='hand2').pack(side='left')
        tk.Button(action_frame, text="Close", command=search_win.destroy, bg=self.colors["bg_tertiary"], fg=self.colors["text_primary"], activebackground=self.colors["accent_soft"], relief='flat', bd=0, padx=12, pady=6, font=("Segoe UI", 10), cursor='hand2').pack(side='right')

        result_list.bind('<Double-Button-1>', jump_to_selected)
        run_filter()

    def toggle_presence(self):
        if self.presence_status == "online":
            self.presence_status = "offline"
            self.presence_button.config(text="⚪ Offline")
            self.display_message("You are now offline (still connected).")
        else:
            self.presence_status = "online"
            self.presence_button.config(text="🟢 Online")
            self.display_message("You are now online.")

        if self.websocket:
            asyncio.run_coroutine_threadsafe(
                self.send_presence_update(self.presence_status),
                self.loop
            )

    def toggle_message_type(self):
        if self.message_type == "public":
            self.message_type = "private"
            self.private_button.config(text="🌐 Public")
            self.select_recipient()
        else:
            self.message_type = "public"
            self.private_button.config(text="✉ Private")
            self.display_message("Switched to public message mode.")

    def select_recipient(self):
        users = [
            u for u in self.user_listbox.get(0, tk.END)
            if self.extract_username_from_userlist_entry(u) != self.username
        ]
        if not users:
            self.display_message("No other users connected.")
            return

        recipient_selection_window = tk.Toplevel(self.master)
        recipient_selection_window.title("Select Recipient")
        recipient_selection_window.configure(bg=self.colors["bg_primary"])
        tk.Label(
            recipient_selection_window,
            text="Select recipient for private message:",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            font=self.font_ui
        ).pack(pady=10)

        recipient_var = tk.StringVar(recipient_selection_window)
        recipient_var.set(users[0])
        recipient_dropdown = ttk.Combobox(recipient_selection_window, textvariable=recipient_var, values=users, style='App.TCombobox')
        recipient_dropdown.pack(pady=10)

        def set_recipient():
            selected = recipient_var.get()
            clean_name = self.extract_username_from_userlist_entry(selected)
            self.recipient = clean_name
            self.display_message(f"Switched to private message mode. Recipient: {self.recipient}")
            recipient_selection_window.destroy()

        tk.Button(
            recipient_selection_window,
            text="Select",
            command=set_recipient,
            bg=self.colors["accent"],
            fg="#0E1412",
            activebackground=self.colors["accent_soft"],
            activeforeground=self.colors["text_primary"],
            relief='flat',
            bd=0,
            padx=12,
            pady=6,
            font=("Segoe UI Semibold", 10),
            cursor='hand2'
        ).pack(pady=10)

    def send_file_command(self):
        users = [
            u for u in self.user_listbox.get(0, tk.END)
            if self.extract_username_from_userlist_entry(u) != self.username
        ]
        if not users:
            self.display_message("No other users connected.")
            return

        recipient_selection_window = tk.Toplevel(self.master)
        recipient_selection_window.title("Select Recipient")
        recipient_selection_window.configure(bg=self.colors["bg_primary"])
        tk.Label(
            recipient_selection_window,
            text="Select recipient for file transfer:",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            font=self.font_ui
        ).pack(pady=10)

        recipient_var = tk.StringVar(recipient_selection_window)
        recipient_var.set(users[0])
        recipient_dropdown = ttk.Combobox(recipient_selection_window, textvariable=recipient_var, values=users, style='App.TCombobox')
        recipient_dropdown.pack(pady=10)

        def set_recipient():
            selected = recipient_var.get()
            recipient = self.extract_username_from_userlist_entry(selected)
            if recipient == self.username:
                self.display_message("You cannot send a file to yourself.")
            else:
                file_path = filedialog.askopenfilename()
                if file_path:
                    asyncio.run_coroutine_threadsafe(self.upload_file(file_path, recipient), self.loop)
            recipient_selection_window.destroy()

        tk.Button(
            recipient_selection_window,
            text="Select",
            command=set_recipient,
            bg=self.colors["accent"],
            fg="#0E1412",
            activebackground=self.colors["accent_soft"],
            activeforeground=self.colors["text_primary"],
            relief='flat',
            bd=0,
            padx=12,
            pady=6,
            font=("Segoe UI Semibold", 10),
            cursor='hand2'
        ).pack(pady=10)

    async def upload_file(self, file_path, recipient):
        try:
            with open(file_path, 'rb') as f:
                response = requests.post('http://localhost:5001/upload', files={'file': f}, timeout=5)
                response.raise_for_status()
                file_url = response.json()['url']
                file_name = os.path.basename(file_path)
                if file_name.endswith(('.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx')):
                    await self.send_file_transfer(recipient, file_url, file_name)
                else:
                    self.display_message("Invalid file type.")
                    requests.post(f"{file_url}/delete", timeout=5)
        except Exception as e:
            self.display_message(f"Error uploading file: {e}")

    def display_message(self, message, is_link=False, message_id=None, is_outgoing=False, sent_at=None, sender=None, timestamp=None, body=None, is_private=False, reply_to=None):
        self.chat_display.configure(state='normal')
        start_index = self.chat_display.index(tk.END + "-1c")
        
        if reply_to and isinstance(reply_to, dict):
            reply_sender = reply_to.get("sender", "Unknown")
            reply_preview = reply_to.get("preview", "")
            quoted = f"↪ {reply_sender}: {reply_preview}\n"
        else:
            quoted = ""

        # Format my own messages with a sent indicator
        if is_outgoing or message.startswith("You:") or message.startswith("You [") or message.startswith("[Private] You"):
            display_text = quoted + "[✔] " + message + "\n"
        else:
            display_text = quoted + message + "\n"

        if is_link:
            self.chat_display.insert(tk.END, display_text, ('link',))
            self.chat_display.tag_config('link', foreground="#6EB8FF", underline=True)
            self.chat_display.tag_bind('link', '<Button-1>', lambda e: webbrowser.open(message.split()[-1]))
        else:
            self.chat_display.insert(tk.END, display_text)
        
        end_index = self.chat_display.index(tk.END + "-1c")

        if message_id:
            tag_name = f"msg_{message_id}"
            self.chat_display.tag_add(tag_name, start_index, end_index)
            self.message_widgets[message_id] = tag_name

            if message_id not in self.message_meta:
                self.message_meta[message_id] = {
                    "sender": sender or (self.username if is_outgoing else "Unknown"),
                    "timestamp": timestamp or sent_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "body": body or message,
                    "is_private": is_private,
                    "reply_to": reply_to
                }

                self.chat_history.append({
                    "message_id": message_id,
                    "sender": self.message_meta[message_id]["sender"],
                    "timestamp": self.message_meta[message_id]["timestamp"],
                    "body": self.message_meta[message_id]["body"],
                    "is_private": is_private,
                    "reply_to": reply_to
                })

            self.chat_display.tag_bind(tag_name, '<Button-3>', lambda e, mid=message_id: self.set_reply_context_from_message(mid))

            if is_outgoing:
                self.message_details[message_id] = {
                    "sent_at": sent_at or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "delivered_at": None,
                    "status": "sent",
                    "seen_details": {}
                }
                self.chat_display.tag_config(tag_name, foreground=self.colors["text_primary"])
                self.chat_display.tag_bind(tag_name, '<Button-1>', lambda e, mid=message_id: self.open_message_details_drawer(mid))

        self.chat_display.configure(state='disabled')
        self.chat_display.see(tk.END)

    def update_message_status(self, message_id, status, seen_by=None, seen_details=None, status_time=None):
        if not message_id or message_id not in self.message_widgets:
            return

        if message_id not in self.message_details:
            self.message_details[message_id] = {
                "sent_at": None,
                "delivered_at": None,
                "status": "sent",
                "seen_details": {}
            }

        details = self.message_details[message_id]
        if status == "delivered" and status_time:
            details["delivered_at"] = status_time
            details["status"] = "delivered"
        elif status == "failed":
            details["status"] = "failed"
        elif status == "read":
            details["status"] = "read"

        if seen_details:
            for event in seen_details:
                username = event.get("username")
                read_at = event.get("read_at")
                if username and read_at:
                    details["seen_details"][username] = read_at

        if seen_by:
            for username in seen_by:
                if username not in details["seen_details"]:
                    details["seen_details"][username] = status_time or "Unknown"

        tag_name = self.message_widgets[message_id]
        ranges = self.chat_display.tag_ranges(tag_name)
        if len(ranges) < 2:
            return

        start, end = ranges[0], ranges[1]
        self.chat_display.configure(state='normal')

        current_text = self.chat_display.get(start, end).strip()
        clean_text = re.sub(r"^\[(?:✔|✔✔)\]\s*", "", current_text)
        clean_text = clean_text.split("  👁 Seen by:")[0].strip()

        seen_users = sorted(details["seen_details"].keys())
        prefix = "[✔✔]" if seen_users else "[✔]"
        new_text = f"{prefix} {clean_text}"

        if seen_users:
            new_text += "  👁 Seen by: " + ", ".join(seen_users)

        self.chat_display.delete(start, end)
        self.chat_display.insert(start, new_text)
        new_end = self.chat_display.index(f"{start} + {len(new_text)} chars")
        self.chat_display.tag_remove(tag_name, "1.0", tk.END)
        self.chat_display.tag_add(tag_name, start, new_end)

        self.chat_display.configure(state='disabled')

        if self.active_details_window and self.active_details_message_id == message_id:
            self.refresh_active_message_details()

    def open_message_details_drawer(self, message_id):
        if message_id not in self.message_details:
            return

        self.active_details_message_id = message_id

        if self.active_details_window and self.active_details_window.winfo_exists():
            self.active_details_window.destroy()

        drawer = tk.Toplevel(self.master)
        drawer.title("Read Receipt Details")
        drawer.geometry("420x340")
        drawer.configure(bg=self.colors["bg_primary"])
        drawer.resizable(False, False)

        self.active_details_window = drawer

        def on_close():
            self.active_details_window = None
            self.active_details_message_id = None
            drawer.destroy()

        drawer.protocol("WM_DELETE_WINDOW", on_close)

        title = tk.Label(
            drawer,
            text="Message Delivery Timeline",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_primary"],
            font=("Segoe UI Semibold", 12)
        )
        title.pack(anchor='w', padx=12, pady=(10, 8))

        self.details_timeline_label = tk.Label(
            drawer,
            text="",
            justify='left',
            anchor='w',
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            font=("Segoe UI", 10),
            padx=10,
            pady=10,
            relief='flat'
        )
        self.details_timeline_label.pack(fill='x', padx=12, pady=(0, 10))

        seen_title = tk.Label(
            drawer,
            text="Seen By (with time)",
            bg=self.colors["bg_primary"],
            fg=self.colors["text_muted"],
            font=("Segoe UI", 10)
        )
        seen_title.pack(anchor='w', padx=12)

        self.details_seen_box = tk.Listbox(
            drawer,
            bg=self.colors["bg_secondary"],
            fg=self.colors["text_primary"],
            selectbackground=self.colors["accent_soft"],
            selectforeground=self.colors["text_primary"],
            relief='flat',
            bd=1,
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            font=("Consolas", 10)
        )
        self.details_seen_box.pack(fill='both', expand=True, padx=12, pady=(6, 12))

        self.refresh_active_message_details()

    def refresh_active_message_details(self):
        if not self.active_details_window or not self.active_details_window.winfo_exists():
            return
        if not self.active_details_message_id:
            return
        if self.active_details_message_id not in self.message_details:
            return

        details = self.message_details[self.active_details_message_id]
        sent_at = details.get("sent_at") or "Unknown"
        delivered_at = details.get("delivered_at") or "Pending"
        status = details.get("status", "sent").upper()

        timeline_text = (
            f"Message ID: {self.active_details_message_id}\n"
            f"Sent: {sent_at}\n"
            f"Delivered: {delivered_at}\n"
            f"Current Status: {status}"
        )
        self.details_timeline_label.config(text=timeline_text)

        self.details_seen_box.delete(0, tk.END)
        seen_events = sorted(details.get("seen_details", {}).items(), key=lambda item: item[1])
        if not seen_events:
            self.details_seen_box.insert(tk.END, "No read receipts yet.")
        else:
            for username, read_at in seen_events:
                self.details_seen_box.insert(tk.END, f"{username}  |  {read_at}")

    def update_user_list(self, users):
        previous_snapshot = dict(self.user_status_snapshot)
        current_snapshot = {}

        self.user_listbox.delete(0, tk.END)
        for user in users:
            username = user['username']
            status = user.get("status", "offline")
            current_snapshot[username] = status

            status_icon = "●"
            status_text = "ONLINE" if status == "online" else "OFFLINE"
            self_suffix = " (you)" if username == self.username else ""
            display_text = f"{status_icon} {username}{self_suffix}  [{status_text}]"
            self.user_listbox.insert(tk.END, display_text)
            row_index = self.user_listbox.size() - 1
            row_color = "#44C28B" if status == "online" else "#D16B6B"
            self.user_listbox.itemconfig(row_index, fg=row_color)

        for username, status in current_snapshot.items():
            old_status = previous_snapshot.get(username)
            if username != self.username and old_status and old_status != status:
                indicator = "🟢" if status == "online" else "🔴"
                self.display_message(f"{indicator} {username} is now {status}.")

        self.user_status_snapshot = current_snapshot
        self.update_network_visualization(current_snapshot)
        self.highlight_recipient()

    def update_network_visualization(self, status_snapshot):
        total = len(status_snapshot)
        online = sum(1 for s in status_snapshot.values() if s == "online")
        offline = total - online

        self.network_stats_label.config(
            text=f"Total: {total}   Online: {online}   Offline: {offline}"
        )

        self.network_bar_canvas.delete("all")
        width = max(self.network_bar_canvas.winfo_width(), 40)
        bar_height = 12
        y0 = 3
        y1 = y0 + bar_height

        # Track background
        self.network_bar_canvas.create_rectangle(
            0,
            y0,
            width,
            y1,
            fill=self.colors["bg_tertiary"],
            outline=self.colors["border"]
        )

        if total > 0:
            online_width = int((online / total) * width)
            self.network_bar_canvas.create_rectangle(
                0,
                y0,
                online_width,
                y1,
                fill="#44C28B",
                outline=""
            )

            self.network_bar_canvas.create_rectangle(
                online_width,
                y0,
                width,
                y1,
                fill="#C05D5D",
                outline=""
            )

    def extract_username_from_userlist_entry(self, entry):
        # Expected format: "● username  [ONLINE]" or "● username  [OFFLINE]"
        if "  [" in entry:
            entry = entry.split("  [", 1)[0]
        parts = entry.split(" ", 1)
        name = parts[1].strip() if len(parts) == 2 else entry.strip()
        return name.replace(" (you)", "").strip()

    def highlight_recipient(self):
        if self.recipient:
            try:
                users = self.user_listbox.get(0, tk.END)
                index = next(i for i, u in enumerate(users) if self.extract_username_from_userlist_entry(u) == self.recipient)
                self.user_listbox.selection_set(index)
                self.user_listbox.activate(index)
            except (ValueError, StopIteration):
                self.recipient = None

    def log_out(self):
        cleanup(self.username, self.user_id)
        self.master.destroy()

    def on_closing(self):
        cleanup(self.username, self.user_id)
        self.master.destroy()

def sign_message(data, counter):
    message = json.dumps(data) + str(counter)
    signature = private_key.sign(
        message.encode(),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=32
        ),
        hashes.SHA256()
    )
    return base64.b64encode(signature).decode('utf-8')

def get_fingerprint(public_key):
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    digest = hashes.Hash(hashes.SHA256())
    digest.update(public_bytes)
    return base64.b64encode(digest.finalize()).decode('utf-8')

def signal_handler(signal, frame):
    cleanup(username, user_id)
    os._exit(0)

if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw() 
    username = sanitize_input(simpledialog.askstring("Username", "Enter your username:"))
    if username:
        user_id = str(uuid.uuid4())
        root.deiconify() 
        root.geometry("800x400")
        chat_gui = ChatGUI(root, username, user_id)
        signal.signal(signal.SIGINT, signal_handler)
        chat_gui.start_chat_client() 
        root.mainloop()
    else:
        print("Username is required to start the chat.")