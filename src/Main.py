#!/usr/bin/env python3

from __future__ import annotations
import json
import socket
import ssl   # For optional TLS
import threading
import time
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
G_MY_PORT         = 12000
G_MY_IP           = '127.0.0.1'
G_MY_USERNAME     = "Debugger"
G_MAX_CONNECTIONS = 5
G_ENDPROGRAM      = False

THREAD_POOL_SIZE = 4
USE_SSL          = False
CERTFILE         = "server_cert.pem"
KEYFILE          = "server_key.pem"

def wrap_socket_for_server(sock: socket.socket) -> ssl.SSLSocket:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
    return context.wrap_socket(sock, server_side=True)

def wrap_socket_for_client(sock: socket.socket) -> ssl.SSLSocket:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context.wrap_socket(sock, server_hostname="P2PServer")

def clientSendRequest(peer_socket: socket.socket, cRequest: CRequest) -> str:
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
    try:
        peer_socket.send(CRequest.Handshake.name.encode())
        response = peer_socket.recv(G_BUFFER).decode()
        if response != SResponse.SendSecret.name:
            synchronized_print(f"[Client] Unexpected handshake response: {response}")
            return False
        peer_socket.send(P2P_SECRET.encode())
        response2 = peer_socket.recv(G_BUFFER).decode()
        if response2 == SResponse.HandshakeSuccess.name:
            synchronized_print("[Client] Handshake succeeded.")
            return True
        else:
            synchronized_print("[Client] Handshake failed.")
            return False
    except socket.error as e:
        synchronized_print(f"[Error] handshakeWithServer() => {e}")
        return False

def list_all_files():
    """Lists all available files in the network across all peers"""
    if not Classes.G_peerList:
        synchronized_print("No peers available in the network.")
        return

    synchronized_print("\n=== Available Files ===")
    file_count = 0

    for peer in Classes.G_peerList:
        if peer.address == (G_MY_IP, G_MY_PORT):
            continue

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect(peer.address)

                s.send(CRequest.ListFiles.name.encode())
                response = s.recv(Classes.G_BUFFER).decode()

                if response == SResponse.SendYourInfo.name:
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

    available_peers = [p for p in Classes.G_peerList if p.address != (G_MY_IP, G_MY_PORT)]
    if not available_peers:
        synchronized_print("No other peers available to download from.")
        return

    synchronized_print("\nSelect a peer to download from:")
    for i, peer in enumerate(available_peers, 1):
        synchronized_print(f"{i}. {peer.username} - {peer.address[0]}:{peer.address[1]}")

    try:
        peer_choice = int(input().strip())
        selected_peer = available_peers[peer_choice - 1]

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10)
            s.connect(selected_peer.address)

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
                file_choice = int(input().strip())
                selected_file = files[file_choice - 1]

                s.send(CRequest.DownloadFile.name.encode())
                response = s.recv(Classes.G_BUFFER).decode()

                if response == SResponse.SendYourInfo.name:
                    s.send(selected_file['name'].encode())
                    file_data = b''
                    while True:
                        chunk = s.recv(Classes.G_BUFFER)
                        if not chunk:
                            break
                        file_data += chunk

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
    for peer in Classes.G_peerList[:]:
        if peer.address == (G_MY_IP, G_MY_PORT):
            continue

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect(peer.address)

                s.send(CRequest.PeerList.name.encode())
                response = s.recv(Classes.G_BUFFER).decode()

                if response == SResponse.SendYourInfo.name:
                    s.send("Ready".encode())
                    peer_data = s.recv(Classes.G_BUFFER).decode()
                    new_peers = [Classes.peerList_from_dict(item) for item in json.loads(peer_data)]

                    for new_peer in new_peers:
                        if new_peer and new_peer.address not in [p.address for p in Classes.G_peerList]:
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

    with selfPeer.createTCPSocket() as peer_socket:
        if USE_SSL:
            peer_socket = wrap_socket_for_client(peer_socket)
        try:
            peer_socket.connect((G_MY_IP, G_MY_PORT))
            synchronized_print(f"[Client] Connected to {G_MY_IP}:{G_MY_PORT}.")

            if not handshakeWithServer(peer_socket):
                synchronized_print("[Client] Handshake failed; aborting initial connect.")
                return

            serverResponse = clientSendRequest(peer_socket, CRequest.ConnectRequest)
            synchronized_print(f"[Client] ConnectRequest => {serverResponse}")
            if serverResponse != SResponse.Connected.name:
                raise Exception("Server did not return 'Connected'.")

            serverResponse = clientSendRequest(peer_socket, CRequest.AddMe)
            synchronized_print(f"[Client] AddMe => {serverResponse}")
            if serverResponse != SResponse.SendYourInfo.name:
                raise Exception("Expected 'SendYourInfo' after AddMe.")

            peer_socket.send(json.dumps(userPeerList.__dict__()).encode())

            updatedPeerListRaw = peer_socket.recv(G_BUFFER).decode()
            synchronized_print(f"[Client] Updated PeerList => {updatedPeerListRaw}")

            G_peerList.clear()
            for item in json.loads(updatedPeerListRaw):
                pl = peerList_from_dict(item)
                if pl:
                    G_peerList.append(pl)
            synchronized_print(f"[Client] G_peerList now has {len(G_peerList)} entries.")

            serverResponse = clientSendRequest(peer_socket, CRequest.SendMyFiles)
            synchronized_print(f"[Client] SendMyFiles => {serverResponse}")
            if serverResponse != SResponse.SendYourInfo.name:
                raise Exception("Expected 'SendYourInfo' after SendMyFiles.")

            fileJsonList = json.dumps([f.__dict__() for f in selfPeer.files])
            peer_socket.send(fileJsonList.encode())
            synchronized_print("[Client] Sent file list to server.")

        except Exception as e:
            synchronized_print(f"[Error] initialConnect() => {e}")

def runServer():
    """
    Launches the server socket that listens for incoming client requests.
    """
    srv = Server((G_MY_IP, G_MY_PORT))
    listening_socket = srv.createTCPSocket()
    if not listening_socket:
        synchronized_print("[Fatal] runServer(): Could not create listening socket.")
        return

    if USE_SSL:
        listening_socket = wrap_socket_for_server(listening_socket)

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
    Let the user pick a peer by index and connect to them.
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
      2) List all peers
      3) Download a file
      4) Refresh peer list
      5) Exit
    """
    global G_ENDPROGRAM

    current_peer_socket: socket.socket | None = None
    local_peer = Peer((G_MY_IP, G_MY_PORT), G_MY_USERNAME)
    local_peer.initializeFiles()

    try:
        while not G_ENDPROGRAM:
            print("\n--- P2P MENU ---")
            print("0) Register with server & show live peers")  # CHANGE 6
            print("1) List local files")
            print("2) List all peers")
            print("3) Download a file")
            print("4) Refresh peer list")
            print("5) Exit")

            choice = input("Enter choice: ").strip()

            if choice == "0":  # CHANGE 7
                synchronized_print("[Peer] Registering with server…")
                initialConnect()
                synchronized_print("[Peer] → Live peers from server:")
                for i, p in enumerate(G_peerList, 1):
                    synchronized_print(f"   {i}. {p.username} @ {p.addr}")
                continue

            if choice == "1":
                local_peer.displayCurrentFiles()
            elif choice == "2":
                list_all_peers()
            elif choice == "3":
                download_file()
            elif choice == "4":
                refresh_peer_list()
            elif choice == "5":
                G_ENDPROGRAM = True
                synchronized_print("Exiting program...")
                break
            else:
                synchronized_print("Invalid choice, please try again.")

            time.sleep(0.2)

    except KeyboardInterrupt:
        synchronized_print("[Peer] Interrupted, shutting down.")
    finally:
        G_ENDPROGRAM = True
        if current_peer_socket:
            current_peer_socket.close()

def main():
    print("Welcome to our *Enhanced* P2P Network!\n")
    serverThread = threading.Thread(target=runServer, daemon=True)
    serverThread.start()

    initialConnect()
    runPeer()

    synchronized_print("Complete! Exiting main().")

if __name__ == "__main__":
    main()
