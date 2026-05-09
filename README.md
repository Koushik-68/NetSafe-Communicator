# Secure Chat & Protocol Visualization Lab

A Python-based secure real-time chat system with public and private messaging, read receipts, offline message queueing, encrypted file transfer, presence tracking, and a separate protocol visualization lab for educational packet-flow simulation.

## Project Overview

This project combines two closely related parts:

1. A secure multi-client chat application built with Tkinter, WebSockets, Flask, TLS, and cryptography.
2. A standalone protocol visualization module that demonstrates how messages are split into packets and delivered over TCP-like, UDP-like, and QUIC-like simulation profiles.

The chat system is designed to be practical and secure, while the visualization lab is designed to explain networking concepts in a simple, animated way.

## Introduction

The goal of this project is to demonstrate how secure communication can be implemented in a desktop application while still remaining usable and visually clear. The project addresses common chat-system requirements such as:

- secure transport
- message authenticity
- public and private messaging
- file sharing
- read receipts
- online/offline status
- offline message recovery

In addition, the visualization lab helps users understand how network packets behave during transmission, how messages are divided into chunks, and how delivery differs across simulated protocol styles.

## Problem Statement

Many simple chat applications provide basic messaging but do not handle security, delivery tracking, offline reliability, or educational visibility into how communication works. Common limitations include:

- no secure transport
- no message signature or integrity protection
- no read receipts or delivery status
- no offline message queueing
- no file transfer support
- no clear explanation of packet delivery behavior

This project solves those issues by combining secure real-time messaging with a structured visualization environment for learning and reporting.

## Objectives

The main objectives of the project are:

1. Build a secure multi-client chat application.
2. Support public and private messaging.
3. Provide file sharing through a controlled HTTP upload/download service.
4. Add delivery tracking with sent, delivered, and read states.
5. Support offline presence and automatic message recovery when users come back online.
6. Provide a modern desktop user interface.
7. Build a separate protocol visualization lab for packet-level learning.

## Features

### 1. Multi-client chat

The server supports multiple clients at the same time. Each client connects independently and receives a dynamic user list.

### 2. Public messaging

Public messages are broadcast to connected users. These messages are useful for group communication and announcements.

### 3. Private messaging

Users can switch to private mode and send messages to a specific recipient only. This is useful for one-to-one communication.

### 4. Message signing and integrity

Messages are signed before sending. Each signed payload contains:

- message data
- a monotonically increasing counter
- a digital signature

This helps protect message authenticity and reduces replay-style abuse.

### 5. Read receipts

The application tracks delivery and read status. Users can see:

- single tick for delivered
- double tick for read
- who read the message
- when each user read it

### 6. Read Receipt Details Drawer

Clicking a sent message opens a detailed drawer showing:

- sent time
- delivered time
- read-by users
- read timestamps
- status timeline

### 7. Reply-to message

Users can reply to a previous message using a quoted preview. This makes conversation threads easier to follow.

### 8. Search and filters

The chat interface includes a search window that supports filtering by:

- keyword
- sender
- date range

### 9. Presence management

Users can switch between online and offline without logging out. Presence changes are broadcast to other users.

### 10. User list with indicators

The user list shows online/offline status visually, including the current user marked as “you”.

### 11. Offline message queueing

If a user is offline, messages are queued on the server and delivered automatically when the user comes back online.

### 12. File transfer

Users can upload and share files through a Flask-based file service. Download and cleanup actions are supported.

### 13. Modern dark UI

The client uses a dark matte Tkinter interface with professional symbols and a clear layout for messaging and status tracking.

### 14. Network insight panel

The GUI includes a small live visualization of total, online, and offline users.

### 15. Protocol Visualization Lab

The separate visualization module allows users to select a protocol profile and observe packet delivery behavior in a learning-friendly way.

## System Components

### Chat Client

The main client in [client.py](client.py) provides:

- login prompt
- secure WebSocket connection
- message composition
- reply preview
- search/filter UI
- read receipt drawer
- presence toggle
- file sharing flow

### Chat Server

The main server in [server.py](server.py) provides:

- TLS-enabled WebSocket server
- message routing
- read receipt tracking
- user presence tracking
- offline queue management
- file transfer coordination

### File Transfer Service

The Flask file service embedded in [server.py](server.py) provides:

- file upload endpoint
- file retrieval endpoint
- file deletion endpoint

### Visualization Lab

The visualization package contains:

- [visualization/app.py](visualization/app.py)
- [visualization/home_page.py](visualization/home_page.py)
- [visualization/simulation_page.py](visualization/simulation_page.py)
- [visualization/simulator_logic.py](visualization/simulator_logic.py)
- [visualization/models.py](visualization/models.py)

This module is separate from live chat and is used for protocol learning and packet-flow visualization.

## Technical Workflow

### Chat workflow

1. User enters username.
2. Client generates/loads certificates and connects through secure WebSocket.
3. Client sends a signed hello message.
4. Server stores client session and broadcasts updated user list.
5. User sends public/private/file/presence events.
6. Server routes or queues the message.
7. Receiver gets the message and sends a read receipt.
8. Sender receives delivery/read status updates.

### File workflow

1. Sender uploads file to the Flask endpoint.
2. Server returns a URL.
3. Sender sends file metadata through WebSocket.
4. Receiver accepts or rejects the file.
5. File is downloaded and later deleted from the server.

### Offline queue workflow

1. Message arrives when user is offline.
2. Server stores the payload in the pending queue.
3. When user comes back online, queued messages are delivered automatically.

### Visualization workflow

1. User opens the protocol visualization lab.
2. User selects TCP, UDP, or QUIC simulation profile.
3. A message is split into packet chunks.
4. Packets are animated through sender, network, and receiver stages.
5. The simulator shows drops, retransmissions, ACKs, and reassembly.

## Methodology

The project was implemented using a layered methodology:

1. Requirement analysis

- secure messaging
- multi-client support
- file handling
- delivery status tracking
- packet visualization

2. Architectural design

- client-server architecture
- separate file service
- separate visualization module
- event-driven UI

3. Implementation

- Tkinter GUI client
- WebSocket server
- Flask upload/download API
- cryptographic signing and TLS setup
- packet simulation engine

4. Testing and refinement

- multiple-client joining
- public/private messaging
- offline queue behavior
- read receipts
- file transfer reliability
- visualization correctness

## Technology Stack

### Main language

- Python

### GUI

- Tkinter

### Real-time communication

- websockets

### File service

- Flask
- Flask-CORS

### Cryptography

- cryptography
- RSA
- AES-GCM
- PBKDF2-HMAC-SHA256
- SHA-256

### Utilities

- asyncio
- threading
- requests
- base64
- json

### Visualization lab

- Tkinter canvas and widgets
- custom simulation logic

## Repository Structure

```text
Secure-chat-app-main/
├── client.py
├── server.py
├── client-commandline.py
├── server-commandline.py
├── auth.py
├── encryption.py
├── visualization/
│   ├── app.py
│   ├── home_page.py
│   ├── simulation_page.py
│   ├── simulator_logic.py
│   └── models.py
├── uploads/
├── requirements.txt
├── README.md
└── testing_methods.md
```

## Installation

### 1. Create a virtual environment

```bash
python -m venv .venv
```

### 2. Activate the virtual environment

Windows PowerShell:

```bash
.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

If needed, install these manually:

```bash
pip install websockets cryptography Flask flask-cors requests
```

## Running the Project

### Run the chat server

```bash
python server.py
```

### Run the client

```bash
python client.py
```

### Run the visualization lab

From the project root:

```bash
python visualization/run_visualization.py
```

Or from inside the visualization folder:

```bash
python run_visualization.py
```

## Testing

Testing areas include:

- login and password entry
- multiple client connections
- public messaging
- private messaging
- file uploads and downloads
- TLS/certificate handling
- RSA key generation and storage
- offline client recovery
- replay protection behavior
- visualization simulation correctness

See [testing_methods.md](testing_methods.md) for the original testing checklist.

## Outcome

This project results in a secure and feature-rich communication platform with an additional educational module for networking concepts. The final outcome is:

- a working multi-client secure chat application
- message delivery and read tracking
- offline message recovery
- file sharing support
- a visually clear user interface
- a standalone protocol simulation lab for learning

## Limitations and Future Work

Current limitations:

- state is stored in memory, not a database
- queue and session data are lost when the server restarts
- protocol visualization is a simulation, not raw packet capture

Possible future work:

- database-backed persistence
- typing indicators
- group chat rooms
- chat export
- improved protocol comparison mode
- admin/moderation tools

## Project Team

- Ge Wang | a1880714
- Yong Yue Beh | a1843874
- Liew Yi Hui | a1907230
- Mustafa Jamale | a1863981

## Suggested GitHub Repository Name

`secure-chat-protocol-visualization-lab`

## Suggested GitHub Short Description

`Secure multi-client chat application with read receipts, offline queueing, file transfer, and a packet-level protocol visualization lab built in Python.`
