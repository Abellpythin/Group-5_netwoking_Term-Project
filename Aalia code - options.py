import socket
import threading
import json
import time

# Constants
BOOTSTRAP_NODE = ("127.0.0.1", 12000)  # Bootstrap server address

# Message Types
MESSAGE_TYPE_PING = "PING"
MESSAGE_TYPE_PEER_LIST = "PEER_LIST"
MESSAGE_TYPE_REQUEST_FILE = "REQUEST_FILE"
MESSAGE_TYPE_RESPONSE_FILE = "RESPONSE_FILE"

# Class to represent a Peer
class Peer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.peers = []  # List of connected peers
        self.files = {}  # Files shared by this peer

    def start(self):
        "Start the peer server to listen for incoming connections."
        server_thread = threading.Thread(target=self._run_server)
        server_thread.start()

    def _run_server(self):
        "Run the server to accept connections from other peers.""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.host, self.port))
        server_socket.listen(5)
        print(f"Peer running on {self.host}:{self.port}")

        while True:
            client_socket, addr = server_socket.accept()
            print(f"Connection from {addr}")
            threading.Thread(target=self._handle_client, args=(client_socket,)).start()

    def _handle_client(self, client_socket):
        "Handle incoming messages from a client.""
        data = client_socket.recv(1024).decode()
        if data:
            message = Message.from_json(data)
            self._process_message(message, client_socket)
        client_socket.close()

    def _process_message(self, message, client_socket):
        """Process incoming messages."""
        if message.type == MESSAGE_TYPE_PING:
            print(f"Received PING from {message.sender}")
            self._send_message(client_socket, Message(MESSAGE_TYPE_PING, self.get_address()))
        elif message.type == MESSAGE_TYPE_PEER_LIST:
            print(f"Received PEER_LIST from {message.sender}")
            self.peers.extend(message.data)
            print(f"Updated peer list: {self.peers}")
        elif message.type == MESSAGE_TYPE_REQUEST_FILE:
            print(f"Received REQUEST_FILE for {message.data} from {message.sender}")
            if message.data in self.files:
                file_content = self.files[message.data]
                self._send_message(client_socket, Message(MESSAGE_TYPE_RESPONSE_FILE, file_content))
            else:
                print(f"File {message.data} not found.")
        elif message.type == MESSAGE_TYPE_RESPONSE_FILE:
            print(f"Received RESPONSE_FILE: {message.data}")

    def _send_message(self, client_socket, message):
        """Send a message to a client."""
        client_socket.send(message.to_json().encode())

    def connect_to_peer(self, peer_address):
        """Connect to another peer."""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(peer_address)
            self._send_message(client_socket, Message(MESSAGE_TYPE_PING, self.get_address()))
            client_socket.close()
        except Exception as e:
            print(f"Failed to connect to {peer_address}: {e}")

    def request_peer_list(self, bootstrap_node):
        """Request the list of peers from the bootstrap node."""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(bootstrap_node)
            self._send_message(client_socket, Message(MESSAGE_TYPE_PEER_LIST, self.get_address()))
            client_socket.close()
        except Exception as e:
            print(f"Failed to request peer list: {e}")

    def request_file(self, file_name, peer_address):
        """Request a file from another peer."""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(peer_address)
            self._send_message(client_socket, Message(MESSAGE_TYPE_REQUEST_FILE, file_name))
            client_socket.close()
        except Exception as e:
            print(f"Failed to request file: {e}")

    def get_address(self):
        """Get the address of this peer."""
        return (self.host, self.port)

    def add_file(self, file_name, file_content):
        """Add a file to this peer's shared files."""
        self.files[file_name] = file_content
        print(f"Added file {file_name} to shared files.")

# Class to represent a Message
class Message:
    def __init__(self, type, data, sender=None):
        self.type = type
        self.data = data
        self.sender = sender

    def to_json(self):
        """Convert the message to JSON format."""
        return json.dumps({"type": self.type, "data": self.data, "sender": self.sender})

    @staticmethod
    def from_json(json_str):
        """Create a Message object from JSON."""
        data = json.loads(json_str)
        return Message(data["type"], data["data"], data["sender"])

# Main function to start the P2P network
if __name__ == "__main__":
    # Create a peer
    peer1 = Peer("127.0.0.1", 5001)
    peer1.start()

    # Add a file to the peer
    peer1.add_file("example.txt", "This is the content of example.txt.")

    # Connect to the bootstrap node
    peer1.connect_to_peer(BOOTSTRAP_NODE)
    peer1.request_peer_list(BOOTSTRAP_NODE)

    # Wait for peers to connect
    time.sleep(2)

    # Request a file from another peer
    peer1.request_file("example.txt", ("127.0.0.1", 5002))