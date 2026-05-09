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
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import threading
import stat
from werkzeug.serving import run_simple

# Group 11
## Ge Wang | a1880714
## Yong Yue Beh | a1843874
## Liew Yi Hui | a1907230
## Mustafa Jamale | a1863981

connected_clients = {}
message_owners = {}
pending_messages = {}

# Flask app setup
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Set permissions to 755 (rwxr-xr-x)
os.chmod(UPLOAD_FOLDER, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | 
                   stat.S_IRGRP | stat.S_IXGRP | 
                   stat.S_IROTH | stat.S_IXOTH)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    # Validate file name
    filename = sanitize_input(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    # Limit file size to 15MB
    app.config['MAX_CONTENT_LENGTH'] = 15 * 1024 * 1024

    file.save(file_path)

    # Return a URL that points to the uploaded file
    return jsonify({"url": f"http://localhost:5001/files/{filename}"}), 200

@app.route('/files/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    response = send_from_directory(UPLOAD_FOLDER, filename)
    
    # Clean up the file after sending it
    @response.call_on_close
    def cleanup_file():
        if os.path.exists(file_path):
            os.remove(file_path)
    
    return response

@app.route('/files/<filename>/delete', methods=['POST'])
def delete_file(filename):
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"status": "success", "message": "File deleted"}), 200
    else:
        return jsonify({"status": "error", "message": "File not found"}), 404

def run_flask():
    run_simple('localhost', 5001, app, use_reloader=False, use_debugger=True)

# WebSocket server setup
def sanitize_input(input_string):
    return re.sub(r'[^\w\s]', '', input_string)

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
    iv = os.urandom(12)
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

def generate_ssl_certificates(password):
    cert_file = "server.crt"
    key_file = "server.key"
    if not os.path.exists(cert_file) or not os.path.exists(key_file):
        subprocess.run([
            "openssl", "req", "-x509", "-newkey", "rsa:4096",
            "-keyout", key_file, "-out", cert_file, "-days", "365", "-nodes",
            "-subj", "/C=IN/ST=KA/L=Bangalore/O=ChatApp/OU=Dev/CN=localhost"
        ], check=True)
        with open(key_file, 'rb') as f:
            private_key = f.read()
        encrypted_private_key = encrypt_private_key(private_key, password)
        with open(key_file, 'wb') as f:
            f.write(encrypted_private_key)
        print("SSL/TLS certificates generated and private key encrypted.")

def cleanup():
    cert_file = "server.crt"
    key_file = "server.key"
    if os.path.exists(cert_file):
        os.remove(cert_file)
    if os.path.exists(key_file):
        os.remove(key_file)
    print("SSL/TLS certificates removed.")

generate_ssl_certificates("your_password_here")

def load_ssl_context(password):
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    with open("server.key", 'rb') as f:
        encrypted_private_key = f.read()
    private_key = decrypt_private_key(encrypted_private_key, password)
    
    temp_key_file = "temp_server.key"
    with open(temp_key_file, 'wb') as f:
        f.write(private_key)
    
    ssl_context.load_cert_chain(certfile="server.crt", keyfile=temp_key_file)
    os.remove(temp_key_file)
    
    return ssl_context

ssl_context = load_ssl_context("your_password_here")

def get_client_from_websocket(websocket):
    for client in connected_clients.values():
        if client['websocket'] == websocket:
            return client
    return None

def queue_message_for_user(username, payload):
    if username not in pending_messages:
        pending_messages[username] = []
    pending_messages[username].append(payload)

async def deliver_pending_messages(username, websocket):
    queued = pending_messages.get(username, [])
    if not queued:
        return

    undelivered = []
    for payload in queued:
        try:
            await websocket.send(json.dumps(payload))
        except websockets.ConnectionClosed:
            undelivered.append(payload)
            break
        except Exception:
            undelivered.append(payload)

    if undelivered:
        pending_messages[username] = undelivered
    else:
        pending_messages.pop(username, None)

async def broadcast_message(message, sender, message_id, timestamp, sender_websocket, reply_to=None):
    for client in connected_clients.values():
        if client['websocket'] == sender_websocket:
            continue
        payload = {
            'type': 'chat_message',
            'message': f"[Public] {sender} [{timestamp}]: {message}",
            'message_id': message_id,
            'reply_to': reply_to
        }

        if client.get('status') == 'online':
            try:
                await client['websocket'].send(json.dumps(payload))
            except websockets.ConnectionClosed:
                client['status'] = 'offline'
                queue_message_for_user(client['username'], payload)
            except Exception:
                queue_message_for_user(client['username'], payload)
        else:
            queue_message_for_user(client['username'], payload)

async def send_private_message(recipient, message, sender, message_id, timestamp, reply_to=None):
    recipient_fingerprint = None
    for fp, client in connected_clients.items():
        if client['username'] == recipient:
            recipient_fingerprint = fp
            break

    payload = {
        'type': 'chat_message',
        'message': f"[Private] {sender} [{timestamp}]: {message}",
        'message_id': message_id,
        'reply_to': reply_to
    }

    if recipient_fingerprint and recipient_fingerprint in connected_clients:
        recipient_client = connected_clients[recipient_fingerprint]
        if recipient_client.get('status') == 'online':
            try:
                await recipient_client['websocket'].send(json.dumps(payload))
                print(f"{sender} sent a private message to {recipient}")
                return True
            except websockets.ConnectionClosed:
                recipient_client['status'] = 'offline'
                queue_message_for_user(recipient, payload)
                return True
            except Exception:
                queue_message_for_user(recipient, payload)
                return True

        queue_message_for_user(recipient, payload)
        print(f"{recipient} is offline. Message queued.")
        return True

    print(f"Recipient {recipient} not found")
    return False

async def handle_client(websocket, path):
    global connected_clients
    try:
        async for message in websocket:
            data = json.loads(message)
            if data['type'] == 'read_receipt':
                message_id = data.get('message_id')
                owner_data = message_owners.get(message_id)
                reader_client = get_client_from_websocket(websocket)

                if owner_data and reader_client:
                    owner_username = owner_data.get('sender')
                    reader_username = reader_client.get('username')

                    if reader_username and reader_username != owner_username:
                        owner_data['seen_by'].add(reader_username)
                        read_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        owner_data['seen_details'][reader_username] = read_at

                        seen_details = [
                            {
                                "username": username,
                                "read_at": read_time
                            }
                            for username, read_time in sorted(owner_data['seen_details'].items())
                        ]

                        await owner_data['websocket'].send(json.dumps({
                            "type": "message_status",
                            "message_id": message_id,
                            "status": "read",
                            "seen_by": sorted(owner_data['seen_by']),
                            "seen_details": seen_details,
                            "status_time": read_at
                        }))
                continue

            if data['type'] == 'signed_data':
                if data['data']['type'] == 'hello':
                    username = sanitize_input(data['data']['username'])
                    user_id = data['data']['user_id']
                    public_key_pem = data['data']['public_key']
                    public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
                    fingerprint = get_fingerprint(public_key)
                    connected_clients[fingerprint] = {
                        'websocket': websocket,
                        'username': username,
                        'user_id': user_id,
                        'public_key': public_key,
                        'status': 'online'
                    }
                    await deliver_pending_messages(username, websocket)
                    await broadcast_user_list()
                
                elif data['data']['type'] == 'public_chat':
                    message_id = data['data'].get('message_id')
                    sender = data['data']['sender']
                    message = data['data']['message']
                    timestamp = data['data'].get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    reply_to = data['data'].get('reply_to')

                    if message_id:
                        message_owners[message_id] = {
                            'websocket': websocket,
                            'sender': sender,
                            'seen_by': set(),
                            'seen_details': {}
                        }

                    await broadcast_message(message, sender, message_id, timestamp, websocket, reply_to)

                    # send delivery status back to sender
                    await websocket.send(json.dumps({
                        "type": "message_status",
                        "message_id": message_id,
                        "status": "delivered",
                        "status_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }))

                elif data['data']['type'] == 'private_chat':
                    recipient = sanitize_input(data['data']['recipient'])
                    message = sanitize_input(data['data']['message'])
                    sender = data['data']['sender']
                    message_id = data['data'].get('message_id')
                    timestamp = data['data'].get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    reply_to = data['data'].get('reply_to')

                    if message_id:
                        message_owners[message_id] = {
                            'websocket': websocket,
                            'sender': sender,
                            'seen_by': set(),
                            'seen_details': {}
                        }

                    delivered = await send_private_message(recipient, message, sender, message_id, timestamp, reply_to)
                    
                    # send delivery status
                    await websocket.send(json.dumps({
                        "type": "message_status",
                        "message_id": message_id,
                        "status": "delivered" if delivered else "failed",
                        "status_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }))

                elif data['data']['type'] == 'presence_update':
                    requested_status = data['data'].get('status', 'online')
                    status = 'offline' if requested_status == 'offline' else 'online'
                    client = get_client_from_websocket(websocket)
                    if client:
                        client['status'] = status
                        if status == 'online':
                            await deliver_pending_messages(client['username'], websocket)
                        await broadcast_user_list()

                elif data['data']['type'] == 'file_transfer':
                    recipient = sanitize_input(data['data']['recipient'])
                    file_url = data['data']['file_url']
                    sender = data['data']['sender']
                    file_name = data['data']['file_name']
                    await send_file_transfer(recipient, file_url, sender, file_name)
                    print(f"File transfer from {sender} to {recipient} initiated")           
                
                elif data['data']['type'] == 'list_members':
                    await send_user_list(websocket)

    except websockets.ConnectionClosed:
        fingerprint = None
        for fp, client in connected_clients.items():
            if client['websocket'] == websocket:
                fingerprint = fp
                break
        if fingerprint:
            connected_clients[fingerprint]['status'] = 'offline'
            await broadcast_user_list()

async def send_file_transfer(recipient, file_url, sender, file_name):
    recipient_fingerprint = None
    for fp, client in connected_clients.items():
        if client['username'] == recipient:
            recipient_fingerprint = fp
            break

    if recipient_fingerprint and recipient_fingerprint in connected_clients:
        await connected_clients[recipient_fingerprint]['websocket'].send(json.dumps({
            'type': 'file_transfer',
            'file_url': file_url,
            'sender': sender,
            'file_name': file_name
        }))
    else:
        print(f"Recipient {recipient} not found")

async def send_user_list(websocket):
    users = [
        {
            "username": client['username'],
            "user_id": client['user_id'],
            "status": client.get('status', 'offline')
        }
        for client in connected_clients.values()
    ]
    await websocket.send(json.dumps({
        'type': 'user_list',
        'users': users
    }))

async def broadcast_user_list():
    users = [
        {
            "username": client['username'],
            "user_id": client['user_id'],
            "status": client.get('status', 'offline')
        }
        for client in connected_clients.values()
    ]
    for client in connected_clients.values():
        await client['websocket'].send(json.dumps({
            'type': 'user_list',
            'users': users
        }))

def get_fingerprint(public_key):
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    digest = hashes.Hash(hashes.SHA256())
    digest.update(public_bytes)
    return base64.b64encode(digest.finalize()).decode('utf-8')

start_server = websockets.serve(handle_client, "localhost", 8766, ssl=ssl_context)

loop = asyncio.get_event_loop()

def signal_handler(signal, frame):
    loop.stop()
    cleanup()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

flask_thread = threading.Thread(target=run_flask)
flask_thread.start()

try:
    loop.run_until_complete(start_server)
    loop.run_forever()
finally:
    cleanup()