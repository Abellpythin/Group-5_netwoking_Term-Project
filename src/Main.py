#!/usr/bin/env python3

from __future__ import annotations
import json
import socket
import ssl   # For optional TLS
import threading
import time
import queue
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Import everything from Classes
import Classes
from Classes import (
    Peer, Server, CRequest, SResponse, PeerList,
    G_peerList, G_FileList, G_BUFFER, synchronized_print, peerList_from_dict,
    P2P_SECRET
)

# Configuration for our local node
G_MY_PORT: int = 12000
G_MY_IP: str = '127.0.0.1'
G_MY_USERNAME: str = "Debugger"
G_MAX_CONNECTIONS: int = 5
G_ENDPROGRAM: bool = False

# Queue necessary for I/O operations
G_input_queue = queue.Queue()

# You can adjust this to handle concurrency
THREAD_POOL_SIZE = 4

# Set to True to enable minimal TLS. You must provide your own cert and key if you do.
USE_SSL = False
CERTFILE = "server_cert.pem"
KEYFILE = "server_key.pem"

def wrap_socket_for_server(sock: socket.socket) -> ssl.SSLSocket:
    """
    Minimal TLS usage for demonstration (server side).
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
    wrapped = context.wrap_socket(sock, server_side=True)
    return wrapped

def wrap_socket_for_client(sock: socket.socket) -> ssl.SSLSocket:
    """
    Minimal TLS usage for demonstration (client side).
    """
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    # If you had a real CA-signed cert, you'd do:
    # context.load_verify_locations(cafile="ca_cert.pem")
    wrapped = context.wrap_socket(sock, server_hostname="P2PServer")
    return wrapped


def clientSendRequest(peer_socket: socket.socket, cRequest: CRequest) -> str:
    """
    Helper to encode & send a CRequest, then read the server's response.
    """

    try:
        peer_socket.send(cRequest.name.encode())
        return peer_socket.recv(G_BUFFER).decode()
    except socket.error as e:
        synchronized_print(f"[Error] clientSendRequest() socket error: {e}")
        return ""
    except UnicodeDecodeError as e:
        synchronized_print(f"[Error] clientSendRequest() decode error: {e}")
        return ""


def handshakeWithServer(peer_socket: socket.socket) -> bool:
    """
    Simple handshake with the server using a shared secret.
    """
    try:
        peer_socket.send(CRequest.Handshake.name.encode())
        response = peer_socket.recv(G_BUFFER).decode()

        if response == SResponse.SendSecret.name:
            peer_socket.send(P2P_SECRET.encode())
            response2 = peer_socket.recv(G_BUFFER).decode()
            if response2 == SResponse.HandshakeSuccess.name:
                synchronized_print("[Client] Handshake succeeded.")
                return True
            else:
                synchronized_print("[Client] Handshake failed.")
                return False
        else:
            synchronized_print(f"[Client] Unexpected handshake response: {response}")
            return False

    except socket.error as e:
        synchronized_print(f"[Error] handshakeWithServer() => {e}")
        return False

    """
    Handles user interactions in the peer network. Displays available files and peers,
    allows file downloads, and provides a menu for user actions.
    """
    input_thread = threading.Thread(target=get_user_input, args=(G_input_queue,), daemon=True)
    input_thread.start()

    while not G_ENDPROGRAM:
        try:
            # Display menu options:
            synchronized_print("\n===== Peer Network Menu =====")
            synchronized_print("0. Add Peer to server ")
            synchronized_print("1. List all available files in network")
            synchronized_print("2. List all peers in network")
            synchronized_print("3. Download a file")
            synchronized_print("4. Refresh peer list")
            synchronized_print("5. Exit")
            synchronized_print("============================")

            # Get user input from queue
            try:
                user_input = G_input_queue.get(timeout=1)
            except queue.Empty:
                continue
            if user_input == "0":
                synchronized_print("[Peer] Registering with server…")
                initialConnect()
                synchronized_print("[Peer] → Live peers from server:")
                for i, peer in enumerate(G_peerList, 1):
                    synchronized_print(f"  {i}. {peer.username} @ {peer.addr}")
                continue
            if user_input == "1":
                list_all_files()
            elif user_input == "2":
                list_all_peers()
            elif user_input == "3":
                download_file()
            elif user_input == "4":
                refresh_peer_list()
            elif user_input == "5":
                G_ENDPROGRAM = True
                synchronized_print("Exiting program...")
            else:
                synchronized_print("Invalid option. Please try again.")

        except Exception as e:
            synchronized_print(f"Error in peer operations: {e}")

def list_all_files():
    """Lists all available files in the network across all peers"""
    if not Classes.G_peerList:
        synchronized_print("No peers available in the network.")
        return

    synchronized_print("\n=== Available Files ===")
    file_count = 0

    for peer in Classes.G_peerList:
        if peer.address == (G_MY_IP, G_MY_PORT):
            continue  # Skip our own files



        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect(peer.address)

                # Request file list
                s.send(CRequest.ListFiles.name.encode())
                response = s.recv(Classes.G_BUFFER).decode()

                if response == SResponse.SendYourInfo.name:
                    # Our peer is expecting a confirmation
                    s.send("Ready".encode())
                    file_data = s.recv(Classes.G_BUFFER).decode()
                    files = json.loads(file_data)

                    if files:
                        synchronized_print(f"\nFiles from {peer.username} ({peer.address[0]}:{peer.address[1]}):")
                        for file in files:
                            synchronized_print(f" - {file['name']} (Size: {file['size']} bytes)")
                            file_count += 1
        except Exception as e:
            synchronized_print(f"Could not connect to peer {peer.username}: {e}")

    if file_count == 0:
        synchronized_print("No files available in the network.")

def list_all_peers():
    """Lists all peers currently in the network"""
    synchronized_print("\n=== Peers in Network ===")
    if not Classes.G_peerList:
        synchronized_print("No peers available.")
        return

    for i, peer in enumerate(Classes.G_peerList, 1):
        status = " (You)" if peer.address == (G_MY_IP, G_MY_PORT) else ""
        synchronized_print(f"{i}. {peer.username}{status} - {peer.address[0]}:{peer.address[1]}")

def download_file():
    """Handles file download from another peer"""
    if not Classes.G_peerList:
        synchronized_print("No peers available to download from.")
        return

    # List peers to choose from (excluding ourselves)
    available_peers = [p for p in Classes.G_peerList if p.address != (G_MY_IP, G_MY_PORT)]
    if not available_peers:
        synchronized_print("No other peers available to download from.")
        return

    synchronized_print("\nSelect a peer to download from:")
    for i, peer in enumerate(available_peers, 1):
        synchronized_print(f"{i}. {peer.username} - {peer.address[0]}:{peer.address[1]}")

    try:
        peer_choice = int(G_input_queue.get())
        selected_peer = available_peers[peer_choice - 1]

        # Connect to peer and request file list
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect(selected_peer.address)

            # Request file list
            s.send(CRequest.ListFiles.name.encode())
            response = s.recv(Classes.G_BUFFER).decode()

            if response == SResponse.SendYourInfo.name:
                s.send("Ready".encode())
                file_data = s.recv(Classes.G_BUFFER).decode()
                files = json.loads(file_data)

                if not files:
                    synchronized_print("No files available from this peer.")
                    return

                synchronized_print("\nAvailable files:")
                for i, file in enumerate(files, 1):
                    synchronized_print(f"{i}. {file['name']} (Size: {file['size']} bytes)")

                synchronized_print("Enter the number of the file to download:")
                file_choice = int(G_input_queue.get())
                selected_file = files[file_choice - 1]

                # Request file download
                s.send(CRequest.DownloadFile.name.encode())
                response = s.recv(Classes.G_BUFFER).decode()

                if response == SResponse.SendYourInfo.name:
                    # Send the filename we want to download
                    s.send(selected_file['name'].encode())

                    # Receive the file data in binary
                    file_data = b''
                    while True:
                        chunk = s.recv(Classes.G_BUFFER)
                        if not chunk:
                            break
                        file_data += chunk

                    # Save the file
                    download_dir = "downloads"
                    os.makedirs(download_dir, exist_ok=True)
                    file_path = os.path.join(download_dir, selected_file['name'])

                    with open(file_path, 'wb') as f:
                        f.write(file_data)

                    synchronized_print(f"File '{selected_file['name']}' downloaded successfully to {download_dir}/")
                else:
                    synchronized_print("Failed to initiate download.")
    except (ValueError, IndexError):
        synchronized_print("Invalid selection.")
    except Exception as e:
        synchronized_print(f"Download failed: {e}")

def refresh_peer_list():
    """Refreshes the list of peers in the network"""
    synchronized_print("Refreshing peer list...")

    # Try to connect to each known peer to get updated list
    for peer in Classes.G_peerList[:]:  # Create a copy for iteration
        if peer.address == (G_MY_IP, G_MY_PORT):
            continue

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect(peer.address)

                # Request peer list
                s.send(CRequest.ListPeers.name.encode())
                response = s.recv(Classes.G_BUFFER).decode()

                if response == SResponse.SendYourInfo.name:
                    s.send("Ready".encode())
                    peer_data = s.recv(Classes.G_BUFFER).decode()
                    new_peers = [Classes.peerList_from_dict(item) for item in json.loads(peer_data)]

                    # Update our peer list with new information
                    for new_peer in new_peers:
                        if new_peer.address not in [p.address for p in Classes.G_peerList]:
                            Classes.G_peerList.append(new_peer)

                    synchronized_print("Peer list updated successfully.")
                    return
        except Exception as e:
            synchronized_print(f"Could not connect to peer {peer.username}: {e}")

    synchronized_print("Could not refresh peer list from any known peers.")

def initialConnect():
    """
    Attempts to connect to a known peer (hard-coded IP/port),
    performs a handshake, registers this user, fetches G_peerList, sends local files.
    """
    selfPeer = Peer(address=(G_MY_IP, G_MY_PORT), username=G_MY_USERNAME)
    selfPeer.initializeFiles()

    userPeerList = PeerList((G_MY_IP, G_MY_PORT), G_MY_USERNAME)

    serverIP = '127.0.0.1'
    serverPort = 12000

    with selfPeer.createTCPSocket() as peer_socket:
        if USE_SSL:
            try:
                peer_socket = wrap_socket_for_client(peer_socket)
            except Exception as e:
                synchronized_print(f"[Error] SSL wrap (client) => {e}")
                return

        try:
            peer_socket.connect((serverIP, serverPort))
            synchronized_print(f"[Client] Connected to {serverIP}:{serverPort}.")

            # 1) Do handshake
            if not handshakeWithServer(peer_socket):
                synchronized_print("[Client] Handshake failed; aborting initial connect.")
                return

            # 2) ConnectRequest
            serverResponse = clientSendRequest(peer_socket, CRequest.ConnectRequest)
            synchronized_print(f"[Client] ConnectRequest => {serverResponse}")
            if serverResponse != SResponse.Connected.name:
                raise Exception("Server did not return 'Connected'.")

            # 3) AddMe
            serverResponse = clientSendRequest(peer_socket, CRequest.AddMe)
            synchronized_print(f"[Client] AddMe => {serverResponse}")
            if serverResponse != SResponse.SendYourInfo.name:
                raise Exception("Expected 'SendYourInfo' after AddMe.")

            # Send userPeerList
            jsonUserPeer = json.dumps(userPeerList.__dict__())
            peer_socket.send(jsonUserPeer.encode())

            # 4) Receive updated PeerList
            updatedPeerListRaw = peer_socket.recv(G_BUFFER).decode()
            synchronized_print(f"[Client] Updated PeerList => {updatedPeerListRaw}")

            G_peerList.clear()
            for item in json.loads(updatedPeerListRaw):
                pl = peerList_from_dict(item)
                if pl:
                    G_peerList.append(pl)
            synchronized_print(f"[Client] G_peerList now has {len(G_peerList)} entries.")

            # 5) SendMyFiles
            serverResponse = clientSendRequest(peer_socket, CRequest.SendMyFiles)
            synchronized_print(f"[Client] SendMyFiles => {serverResponse}")
            if serverResponse != SResponse.SendYourInfo.name:
                raise Exception("Expected 'SendYourInfo' after SendMyFiles.")

            fileJsonList = json.dumps([f.__dict__() for f in selfPeer.files])
            peer_socket.send(fileJsonList.encode())
            synchronized_print("[Client] Sent file list to server.")

        except (TimeoutError, ConnectionRefusedError, InterruptedError) as err:
            synchronized_print(f"[Error] initialConnect() => Could not connect to {serverIP}:{serverPort} => {err}")
        except Exception as e:
            synchronized_print(f"[Error] initialConnect() => {e}")


def runServer():
    """
    Launches the server socket that listens for incoming client requests.
    Uses a ThreadPoolExecutor to manage concurrency with a fixed pool size.
    Optionally wraps in TLS (if USE_SSL = True).
    """
    srv = Server((G_MY_IP, G_MY_PORT))
    listening_socket = srv.createTCPSocket()
    if not listening_socket:
        synchronized_print("[Fatal] runServer(): Could not create listening socket.")
        return

    if USE_SSL:
        try:
            listening_socket = wrap_socket_for_server(listening_socket)
        except Exception as e:
            synchronized_print(f"[Error] SSL wrap (server) => {e}")
            return

    with listening_socket:
        listening_socket.listen(G_MAX_CONNECTIONS)
        synchronized_print(f"[Server] Listening on {G_MY_IP}:{G_MY_PORT} with max {G_MAX_CONNECTIONS} connections. SSL={USE_SSL}")

        with ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE) as executor:
            while True:
                try:
                    conn, addr = listening_socket.accept()
                    synchronized_print(f"[Server] Accepted connection from {addr}.")

                    conn.settimeout(10)
                    executor.submit(srv.clientRequest, conn)
                except OSError as e:
                    synchronized_print(f"[Error] accept() failed: {e}")
                    break

def connectToPeerViaIndex(index: int) -> socket.socket | None:
    """
    Let the user pick a peer from G_peerList by index and connect to them,
    returning a newly created socket if successful. Also performs handshake + connect request.
    """
    if index < 0 or index >= len(G_peerList):
        print("Invalid peer index.")
        return None

    peer_info = G_peerList[index]
    peer_addr = peer_info.addr
    synchronized_print(f"[Peer] Connecting to {peer_info.username} at {peer_addr}...")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if USE_SSL:
            sock = wrap_socket_for_client(sock)

        sock.connect(peer_addr)
        synchronized_print(f"[Peer] Connected to {peer_info.username} at {peer_addr}.")

        if not handshakeWithServer(sock):
            sock.close()
            synchronized_print("[Peer] Handshake failed. Closing connection.")
            return None

        resp = clientSendRequest(sock, CRequest.ConnectRequest)
        if resp != SResponse.Connected.name:
            synchronized_print("[Peer] Server did not confirm connection. Closing.")
            sock.close()
            return None

        return sock
    except Exception as e:
        synchronized_print(f"[Error] connectToPeerViaIndex => {e}")
        return None


def runPeer():
    """
    A simple CLI loop for user actions:
      0) Register with server & show live peers
      1) List local files
      2) List known peers
      3) Connect to a chosen peer
      4) Search for a file on the chosen peer
      5) Download a file from the chosen peer
      6) Upload a file to the chosen peer
      7) Quit
    """
    global G_ENDPROGRAM  # <-- declare 'global' BEFORE referencing it

    current_peer_socket: socket.socket | None = None
    chosen_peer_index: int | None = None

    local_peer = Peer((G_MY_IP, G_MY_PORT), G_MY_USERNAME)
    local_peer.initializeFiles()

    try:
        while not G_ENDPROGRAM:
            print("\n--- P2P MENU ---")
            print("0) Register with server & show live peers")  # <— ADDED
            print("1) List local files")
            print("2) List known peers")
            print("3) Connect to a chosen peer from G_peerList")
            print("4) Search for a file on the chosen peer")
            print("5) Download a file from the chosen peer")
            print("6) Upload a file to the chosen peer")
            print("7) Quit")

            choice = input("Enter choice: ").strip()

            # <— BEGIN ADDED BLOCK
            if choice == "0":
                synchronized_print("[Peer] Registering with server…")
                initialConnect()
                synchronized_print("[Peer] → Live peers from server:")
                for i, p in enumerate(G_peerList, 1):
                    synchronized_print(f"   {i}. {p.username} @ {p.addr}")
                continue
            # END ADDED BLOCK —>

            if choice == "1":
                local_peer.displayCurrentFiles()

            elif choice == "2":
                if len(G_peerList) == 0:
                    synchronized_print("[Info] No peers known yet.")
                else:
                    synchronized_print("Known peers (index: username @ addr):")
                    for i, p in enumerate(G_peerList):
                        print(f" [{i}] {p.username} @ {p.addr}")

            elif choice == "3":
                if len(G_peerList) == 0:
                    synchronized_print("[Info] No peers known yet.")
                    continue
                index_str = input("Enter the index of the peer to connect: ")
                try:
                    idx = int(index_str)
                    sock = connectToPeerViaIndex(idx)
                    if sock:
                        # Close old peer socket if open
                        if current_peer_socket:
                            current_peer_socket.close()
                        current_peer_socket = sock
                        chosen_peer_index = idx
                        synchronized_print("[Peer] Connected to chosen peer successfully.")
                except ValueError:
                    print("Invalid input, must be an integer.")

            elif choice == "4":
                if current_peer_socket is None:
                    print("No peer connected. Use option 3 to connect first.")
                    continue
                query = input("Enter search query (substring): ")
                temp_peer = Peer()
                temp_peer.socket = current_peer_socket
                temp_peer.searchFiles(query)

            elif choice == "5":
                if current_peer_socket is None:
                    print("No peer connected. Use option 3 to connect first.")
                    continue
                filename = input("Enter the filename to download: ").strip()
                temp_peer = Peer()
                temp_peer.socket = current_peer_socket
                temp_peer.fileRequest(filename)

            elif choice == "6":
                if current_peer_socket is None:
                    print("No peer connected. Use option 3 to connect first.")
                    continue
                filename = input("Enter the local filename to upload (must be in local 'Files/' folder): ").strip()
                temp_peer = Peer()
                temp_peer.socket = current_peer_socket
                temp_peer.uploadFile(filename)

            elif choice == "7":
                print("Exiting peer UI.")
                break

            else:
                print("Invalid choice, try again.")

            time.sleep(0.2)

    except KeyboardInterrupt:
        synchronized_print("[Peer] Interrupted, shutting down.")
    finally:
        # Mark the end of the program, close sockets
        G_ENDPROGRAM = True
        if current_peer_socket:
            current_peer_socket.close()



def main():
    print("Welcome to our *Enhanced* P2P Network!\n")

    # 1) Start the server in a separate thread
    serverThread = threading.Thread(target=runServer, daemon=True)
    serverThread.start()

    # 2) Attempt an initial connection to a known peer
    initialConnect()

    # 3) Start the peer interaction thread (not daemon, so main waits for it)
    peerThread = threading.Thread(target=runPeer, daemon=False)
    peerThread.start()

    # 4) Wait for the peer thread to finish
    peerThread.join()

    synchronized_print("Complete! Exiting main().")


if __name__ == "__main__":
    main()
