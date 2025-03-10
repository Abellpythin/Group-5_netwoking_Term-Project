import socket
import threading
import json

# Peer Initial List - example ip and prot may change
initial_peers = [
    {"ip": "127.0.0.1", "port": 5001},
    {"ip": "127.0.0.1", "port": 5002},
    {"ip": "127.0.0.1", "port": 5003}
]

# Method List
class P2PNetwork:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.peers = initial_peers
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.ip, self.port))
        self.server_socket.listen(5)
        print(f"Peer listening on {self.ip}:{self.port}")

    def start(self):
        threading.Thread(target=self.accept_connections).start()
        self.connect_to_peers()

    def accept_connections(self):
        while True:
            client_socket, addr = self.server_socket.accept()
            print(f"Connected to {addr}")
            threading.Thread(target=self.handle_client, args=(client_socket,)).start()

    def handle_client(self, client_socket):
        while True:
            try:
                data = client_socket.recv(1024).decode('utf-8')
                if not data:
                    break
                print(f"Received: {data}")
                # Process the received data (e.g., update peer list, share files, etc.)
            except ConnectionResetError:
                break
        client_socket.close()

    def connect_to_peers(self):
        for peer in self.peers:
            if peer["ip"] != self.ip or peer["port"] != self.port:
                try:
                    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    peer_socket.connect((peer["ip"], peer["port"]))
                    print(f"Connected to peer {peer['ip']}:{peer['port']}")
                    threading.Thread(target=self.handle_client, args=(peer_socket,)).start()
                except ConnectionRefusedError:
                    print(f"Could not connect to peer {peer['ip']}:{peer['port']}")

    def send_data(self, peer_ip, peer_port, data):
        try:
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((peer_ip, peer_port))
            peer_socket.send(data.encode('utf-8'))
            peer_socket.close()
        except ConnectionRefusedError:
            print(f"Could not send data to {peer_ip}:{peer_port}")

    def broadcast_data(self, data):
        for peer in self.peers:
            if peer["ip"] != self.ip or peer["port"] != self.port:
                self.send_data(peer["ip"], peer["port"], data)

# Example Usage
if __name__ == "__main__":
    # Initialize a peer with its own IP and port
    peer = P2PNetwork("127.0.0.1", 5001)
    peer.start()

    # Example: Broadcast a message to all peers
    peer.broadcast_data("Hello, this is a broadcast message!")


    '''Documentation and Notes:
The peer initial list is a list of known peers that a new peer can 
connect to when it joins the network. 
This list can be hardcoded, loaded from a file, or discovered dynamically.

Method List:
The method list includes functions for:
Peer Discovery: Finding other peers in the network.
Data Sharing: Sending and receiving data between peers.
Connection Management: Handling connections and disconnections.
Peer Initial List: The initial_peers list contains the IP addresses and ports of known peers.
This list can be expanded or modified dynamically.

P2PNetwork Class:
__init__: Initializes the peer with its IP and port, sets up the server socket, 
and starts listening for incoming connections.

start: Starts the peer by accepting incoming connections and connecting to known peers.
accept_connections: Listens for incoming connections and spawns a new thread to handle each client.
handle_client: Handles communication with a connected client.
connect_to_peers: Connects to all known peers in the initial list.
send_data: Sends data to a specific peer.
broadcast_data: Sends data to all known peers.
    
Notes
lacks  features for a robust P2P network, such as peer discovery, NAT traversal, and security.
The peer list is a static example, but in a real-world application, 
it should be dynamic and updated as peers join or leave the network.
Error handling and logging should be added for production use.
'''