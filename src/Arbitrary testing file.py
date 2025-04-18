import threading
import queue
import time
from src.Classes import CRequest
from src.Classes import PeerList
import json
import os
from pathlib import Path

import socket

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("127.0.0.1", 12000))
server_socket.listen(1)
print("Server listening on port 12000")

conn, addr = server_socket.accept()
print("Connection from", addr)
conn.sendall(b"Hello from server")
conn.close()
server_socket.close()
