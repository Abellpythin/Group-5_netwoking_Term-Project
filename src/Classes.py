#!/usr/bin/env python3

from __future__ import annotations
import json
import os
import socket
import threading
import time
from enum import Enum
from pathlib import Path

# -------------------------------------------------------------------------------------
# GLOBALS & CONSTANTS
# -------------------------------------------------------------------------------------

G_BUFFER = 2_500_000  # 2.5 MB
CHUNK_SIZE = 4096     # Size of each file read/write chunk

# Lists to hold peers and files discovered/registered throughout the network
G_peerList: list["PeerList"] = []
G_FileList: list["File"] = []

# A simple shared secret for demonstration. A real system would use TLS or a more secure handshake.
P2P_SECRET = "SOME_SHARED_SECRET"

# -------------------------------------------------------------------------------------
# ENUMS
# -------------------------------------------------------------------------------------

class CRequest(Enum):
    """
    Enumeration of possible client --> server messages.
    """
    ConnectRequest = 0
    AddMe = 1
    PeerList = 2
    ListFiles = 3      # <— CHANGE 2: added for listing files
    DownloadFile = 4   # <— CHANGE 2: added for requesting a download
    SendMyFiles = 5
    Handshake = 6
    SearchFiles = 7
    UploadFile = 8

class SResponse(Enum):
    """
    Enumeration of possible server --> client messages.
    """
    Connected = 0
    SendYourInfo = 1
    ReadyToReceive = 2
    FileNotFound = 3
    SendFileName = 4
    EndOfFile = 5
    SendSecret = 6
    HandshakeSuccess = 7
    HandshakeFailure = 8
    SendSearchQuery = 9
    SendUploadFileName = 10
    FileListJSON = 11

# -------------------------------------------------------------------------------------
# HELPER FUNCTIONS
# -------------------------------------------------------------------------------------

# A lock for synchronized console printing
G_print_lock = threading.Lock()

def synchronized_print(msg: str):
    """
    Thread-safe console output.
    """
    with G_print_lock:
        print(msg)

def list_files_in_directory(directory_path: Path | str) -> list[str]:
    """
    Reads all filenames in 'directory_path'.
    """
    try:
        directory_path = Path(directory_path)
        files = [f for f in os.listdir(directory_path) if os.path.isfile(directory_path / f)]
        return files
    except FileNotFoundError:
        synchronized_print(f"[Error] Directory not found: {directory_path}")
        return []
    except Exception as e:
        synchronized_print(f"[Error] Could not list directory {directory_path}: {e}")
        return []

# -------------------------------------------------------------------------------------
# DATA CLASSES
# -------------------------------------------------------------------------------------

class PeerList:
    """
    Represents a peer's address and username, used in the global peer list.
    """
    def __init__(self, addr: tuple[str, int], username: str):
        self.addr = addr
        self.username = username

    def __dict__(self):
        return {'addr': self.addr, 'username': self.username}

    def __str__(self):
        return f"{{{self.addr},{self.username}}}"

    def __eq__(self, other: "PeerList"):
        return (self.addr, self.username) == (other.addr, other.username)

class File:
    """
    Represents a file shared by a user in the network.
    """
    def __init__(self, fileName: str, userName: str, addr: tuple[str, int] = None):
        self.fileName = fileName
        self.userName = userName
        self.addr: tuple[str, int] | None = addr

    def __dict__(self):
        return {'fileName': self.fileName, 'userName': self.userName, 'addr': self.addr}

# -------------------------------------------------------------------------------------
# DESERIALIZERS
# -------------------------------------------------------------------------------------

def peerList_from_dict(obj: dict) -> PeerList | None:
    """
    Unpacks JSON into PeerList object (returns None if error).
    """
    try:
        # <— CHANGE 3: convert JSON list into tuple to avoid duplicate entries
        return PeerList(addr=tuple(obj['addr']), username=obj['username'])
    except (TypeError, ValueError) as e:
        synchronized_print(f"[Error] Failed to deserialize PeerList: {e}")
        return None

def file_from_dict(obj: dict) -> File | None:
    """
    Unpacks JSON into File object (returns None if error).
    """
    try:
        addr = tuple(obj['addr']) if obj.get('addr') else None
        return File(obj['fileName'], obj['userName'], addr)
    except (TypeError, ValueError) as e:
        synchronized_print(f"[Error] Failed to deserialize File: {e}")
        return None

# -------------------------------------------------------------------------------------
# PEER & SERVER CLASSES
# -------------------------------------------------------------------------------------

class Peer:
    """
    A "peer" in the network, with an address, username, files, etc.
    """
    def __init__(self,
                 address: tuple[str, int] = ('127.0.0.1', 5001),
                 username: str = None,
                 files: list[File] = None,
                 online: bool = True):
        if files is None:
            files = []
        self.address = address
        self.username = username
        self.files: list[File] = files
        self.online = online
        self.socket: socket.socket | None = None

    def createTCPSocket(self) -> socket.socket:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return self.socket

    def initializeFiles(self) -> None:
        """
        Scan a "Files" directory (one level up) for local files, store them in self.files.
        """
        try:
            parent_of_parent_directory = Path.cwd().parent / "Files"
            fileNames = list_files_in_directory(parent_of_parent_directory)
            for name in fileNames:
                self.files.append(File(name, self.username, self.address))
        except Exception as e:
            synchronized_print(f"[Error] initializeFiles() failed: {e}")

    def addFile(self, file: File):
        if file not in self.files:
            self.files.append(file)

    def displayCurrentFiles(self):
        print("Your public downloadable Files:")
        for f in self.files:
            print(f.fileName, "; ", end="")
        print()

    def toggleOnline(self) -> bool:
        self.online = not self.online
        return self.online

    def validConnection(self, serverResponse: str) -> bool:
        return serverResponse == SResponse.Connected.name

    def requestPeerList(self) -> None:
        """
        Example request to retrieve a peer list from a connected server.
        """
        if not self.socket:
            synchronized_print("[Error] requestPeerList() called but self.socket is None.")
            return
        try:
            self.socket.send(CRequest.PeerList.name.encode())
            data = self.socket.recv(G_BUFFER)
            raw_list = json.loads(data.decode())
            new_peers = []
            for item in raw_list:
                pl = peerList_from_dict(item)
                if pl:
                    new_peers.append(pl)
            G_peerList.clear()
            G_peerList.extend(new_peers)
            synchronized_print(f"[Peer] Successfully updated G_peerList with {len(new_peers)} peers.")
        except (socket.error, json.JSONDecodeError) as e:
            synchronized_print(f"[Error] requestPeerList() failed: {e}")

    def fileRequest(self, filename: str) -> None:
        """
        Send a request to the server to download a file, with chunk-based reading.
        """
        if not self.socket:
            synchronized_print("[Error] fileRequest() no socket established.")
            return
        try:
            self.socket.send(CRequest.DownloadFile.name.encode())
            response = self.socket.recv(G_BUFFER).decode()
            if response == SResponse.SendFileName.name:
                self.socket.send(filename.encode())
                response = self.socket.recv(G_BUFFER).decode()
                if response == SResponse.ReadyToReceive.name:
                    synchronized_print(f"[Client] Downloading '{filename}' ...")
                    Path("Downloads").mkdir(exist_ok=True)
                    local_path = Path("Downloads") / filename
                    with open(local_path, "wb") as f:
                        while True:
                            chunk = self.socket.recv(G_BUFFER)
                            if chunk.endswith(SResponse.EndOfFile.name.encode()):
                                actual_data = chunk.replace(SResponse.EndOfFile.name.encode(), b'')
                                if actual_data:
                                    f.write(actual_data)
                                synchronized_print("[Client] File download complete.")
                                break
                            else:
                                f.write(chunk)
                elif response == SResponse.FileNotFound.name:
                    synchronized_print(f"[Client] The file '{filename}' is not available on server.")
                else:
                    synchronized_print(f"[Error] Unexpected server response: {response}")
            elif response == SResponse.FileNotFound.name:
                synchronized_print(f"[Client] The server says file is not available.")
            else:
                synchronized_print(f"[Error] Unexpected server response: {response}")
        except socket.error as e:
            synchronized_print(f"[Error] fileRequest() socket error: {e}")
        except Exception as e:
            synchronized_print(f"[Error] fileRequest() general exception: {e}")

    def searchFiles(self, query: str) -> None:
        """
        Ask the server to return a list of files matching a query substring.
        """
        if not self.socket:
            synchronized_print("[Error] searchFiles() no socket established.")
            return
        try:
            self.socket.send(CRequest.SearchFiles.name.encode())
            response = self.socket.recv(G_BUFFER).decode()
            if response == SResponse.SendSearchQuery.name:
                self.socket.send(query.encode())
                response2 = self.socket.recv(G_BUFFER)
                data = json.loads(response2.decode())
                if isinstance(data, list):
                    synchronized_print(f"[Client] Search results for '{query}':")
                    for fname in data:
                        print(" -", fname)
                else:
                    synchronized_print("[Client] Unexpected search result format.")
            else:
                synchronized_print(f"[Error] Unexpected response to SearchFiles: {response}")
        except socket.error as e:
            synchronized_print(f"[Error] searchFiles() socket error: {e}")

    def uploadFile(self, filename: str) -> None:
        """
        Upload a local file to the server so that it can store it in its 'Files/' directory.
        """
        if not self.socket:
            synchronized_print("[Error] uploadFile() no socket established.")
            return
        try:
            local_path = Path.cwd().parent / "Files" / filename
            if not local_path.exists():
                synchronized_print(f"[Error] uploadFile() => local file '{filename}' does not exist.")
                return
            self.socket.send(CRequest.UploadFile.name.encode())
            response = self.socket.recv(G_BUFFER).decode()
            if response == SResponse.SendUploadFileName.name:
                self.socket.send(filename.encode())
                response2 = self.socket.recv(G_BUFFER).decode()
                if response2 == SResponse.ReadyToReceive.name:
                    synchronized_print(f"[Client] Uploading '{filename}' to server...")
                    with open(local_path, "rb") as f:
                        while True:
                            chunk = f.read(CHUNK_SIZE)
                            if not chunk:
                                break
                            self.socket.send(chunk)
                    self.socket.send(SResponse.EndOfFile.name.encode())
                    synchronized_print("[Client] Upload complete.")
                else:
                    synchronized_print(f"[Error] Unexpected server response to UploadFile: {response2}")
            else:
                synchronized_print(f"[Error] Unexpected response to UploadFile request: {response}")
        except socket.error as e:
            synchronized_print(f"[Error] uploadFile() socket error: {e}")
        except Exception as e:
            synchronized_print(f"[Error] uploadFile() general exception: {e}")

class Server:
    """
    The "server" side that listens on a socket and responds to requests from peers.
    """
    def __init__(self, address: tuple[str, int] = ('127.0.0.1', 5001)):
        self.address = address
        self.socket: socket.socket | None = None

    def createTCPSocket(self) -> socket.socket | None:
        """
        Creates and binds a socket for listening. Return None if something fails.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(self.address)
            return sock
        except socket.error as e:
            synchronized_print(f"[Error] Could not create or bind server socket on {self.address}: {e}")
            return None

    def confirmConnection(self, clientSocket: socket.socket) -> bool:
        """
        Sends back a "Connected" message to the client.
        """
        try:
            clientSocket.send(SResponse.Connected.name.encode())
            return True
        except OSError as err:
            synchronized_print(f"[Error] confirmConnection() failed: {err}")
            return False

    def serverSendResponse(self, clientSocket: socket.socket, sResponse: SResponse) -> str:
        """
        Sends an SResponse, then attempts to read next message from the client.
        """
        try:
            clientSocket.send(sResponse.name.encode())
            response_bytes = clientSocket.recv(G_BUFFER)
            return response_bytes.decode()
        except (socket.error, UnicodeDecodeError) as e:
            synchronized_print(f"[Error] serverSendResponse() failed: {e}")
            return ""

    def sendPeerList(self, clientSocket: socket.socket) -> bool:
        """
        Sends the global G_peerList in JSON form to the client.
        """
        try:
            # CHANGE 4: removed debug stub
            json_data = json.dumps([peer.__dict__() for peer in G_peerList])
            clientSocket.send(json_data.encode())
            return True
        except (socket.error, TypeError) as e:
            synchronized_print(f"[Error] sendPeerList() could not send data: {e}")
            return False

    def sendRequestedFile(self, clientSocket: socket.socket) -> bool:
        """
        File-sending logic:
          1) Send SResponse.SendFileName to client
          2) Read the filename from client
          3) If file is found, send SResponse.ReadyToReceive, then file in chunks, then EndOfFile marker
        """
        try:
            clientSocket.send(SResponse.SendFileName.name.encode())
        except socket.error as e:
            synchronized_print(f"[Error] sendRequestedFile() - step1 => {e}")
            return False

        try:
            filename = clientSocket.recv(G_BUFFER).decode()
        except (socket.error, UnicodeDecodeError) as e:
            synchronized_print(f"[Error] sendRequestedFile() - step2 => {e}")
            return False

        synchronized_print(f"[Server] Client requests file '{filename}'")
        base_path = Path.cwd().parent / "Files"
        requested_path = base_path / filename
        try:
            if not requested_path.resolve().is_file() or base_path not in requested_path.resolve().parents:
                clientSocket.send(SResponse.FileNotFound.name.encode())
                synchronized_print(f"[Server] FileNotFound or path not allowed: '{filename}'")
                return False
        except Exception as e:
            synchronized_print(f"[Error] Checking file path => {e}")
            try:
                clientSocket.send(SResponse.FileNotFound.name.encode())
            except:
                pass
            return False

        try:
            clientSocket.send(SResponse.ReadyToReceive.name.encode())
        except socket.error as e:
            synchronized_print(f"[Error] sendRequestedFile() => ReadyToReceive => {e}")
            return False

        try:
            with open(requested_path, "rb") as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    clientSocket.send(chunk)

            clientSocket.send(SResponse.EndOfFile.name.encode())
            synchronized_print(f"[Server] Finished sending file '{filename}'.")
            return True
        except (OSError, socket.error) as e:
            synchronized_print(f"[Error] sendRequestedFile() => read/send chunk => {e}")
            return False

    def receiveRequestedFiles(self, clientSocket: socket.socket) -> bool:
        """
        After telling client 'SendYourInfo', receive a JSON list of File objects
        to add to the global G_FileList.
        """
        # CHANGE 5: clear stale file list to avoid duplicates
        G_FileList.clear()

        clientResponse = self.serverSendResponse(clientSocket, SResponse.SendYourInfo)
        if not clientResponse:
            synchronized_print("[Error] receiveRequestedFiles(): No file data from client.")
            return False

        try:
            file_dicts = json.loads(clientResponse)
            for fd in file_dicts:
                f_obj = file_from_dict(fd)
                if f_obj:
                    G_FileList.append(f_obj)

            synchronized_print("[Server] I have received files:")
            for f in G_FileList:
                synchronized_print(f" - {f.fileName}")
            return True
        except json.JSONDecodeError as e:
            synchronized_print(f"[Error] Failed to decode file list: {e}")
            return False

    def handleHandshake(self, clientSocket: socket.socket) -> bool:
        """
        A basic handshake with a shared secret.
        """
        try:
            clientSocket.send(SResponse.SendSecret.name.encode())
            client_secret = clientSocket.recv(G_BUFFER).decode()

            if client_secret == P2P_SECRET:
                clientSocket.send(SResponse.HandshakeSuccess.name.encode())
                return True
            else:
                clientSocket.send(SResponse.HandshakeFailure.name.encode())
                synchronized_print("[Server] Handshake failed. Closing connection.")
                return False
        except (socket.error, UnicodeDecodeError) as e:
            synchronized_print(f"[Error] handleHandshake(): {e}")
            return False

    def handleSearchFiles(self, clientSocket: socket.socket) -> bool:
        """
        Ask client for a query substring, then respond with a JSON array of matching filenames from G_FileList.
        """
        try:
            clientSocket.send(SResponse.SendSearchQuery.name.encode())
        except socket.error as e:
            synchronized_print(f"[Error] handleSearchFiles => {e}")
            return False

        try:
            query = clientSocket.recv(G_BUFFER).decode()
        except (socket.error, UnicodeDecodeError) as e:
            synchronized_print(f"[Error] handleSearchFiles => reading query => {e}")
            return False

        matched = [f.fileName for f in G_FileList if query.lower() in f.fileName.lower()]
        try:
            clientSocket.send(json.dumps(matched).encode())
            synchronized_print(f"[Server] Sent {len(matched)} search results for '{query}'.")
            return True
        except socket.error as e:
            synchronized_print(f"[Error] handleSearchFiles => sending results => {e}")
            return False

    def handleUploadFile(self, clientSocket: socket.socket) -> bool:
        """
        Server side of uploading a file from client.
        """
        try:
            clientSocket.send(SResponse.SendUploadFileName.name.encode())
        except socket.error as e:
            synchronized_print(f"[Error] handleUploadFile() => step1 => {e}")
            return False

        try:
            filename = clientSocket.recv(G_BUFFER).decode()
        except (socket.error, UnicodeDecodeError) as e:
            synchronized_print(f"[Error] handleUploadFile() => read filename => {e}")
            return False

        try:
            clientSocket.send(SResponse.ReadyToReceive.name.encode())
        except socket.error as e:
            synchronized_print(f"[Error] handleUploadFile() => step3 => {e}")
            return False

        base_path = Path.cwd().parent / "Files"
        target_path = base_path / filename

        try:
            with open(target_path, "wb") as f:
                while True:
                    chunk = clientSocket.recv(G_BUFFER)
                    if chunk.endswith(SResponse.EndOfFile.name.encode()):
                        actual_data = chunk.replace(SResponse.EndOfFile.name.encode(), b'')
                        if actual_data:
                            f.write(actual_data)
                        break
                    else:
                        f.write(chunk)
            synchronized_print(f"[Server] Successfully uploaded file '{filename}'.")
        except (socket.error, OSError) as e:
            synchronized_print(f"[Error] handleUploadFile() => writing => {e}")
            return False

        new_file = File(filename, "UnknownUploader", None)
        G_FileList.append(new_file)
        return True

    def initialConnectionHandler(self, clientSocket: socket.socket) -> bool:
        """
        When client wants to be added to the network, instruct them to 'SendYourInfo',
        read their PeerList, then send back the updated global peer list.
        """
        clientResponse = self.serverSendResponse(clientSocket, SResponse.SendYourInfo)
        if not clientResponse:
            synchronized_print("[Error] initialConnectionHandler() => No response from client.")
            return False

        try:
            obj = json.loads(clientResponse)
            clientPeer = peerList_from_dict(obj)
            if not clientPeer:
                synchronized_print("[Error] Could not deserialize client PeerList.")
                return False
        except json.JSONDecodeError as e:
            synchronized_print(f"[Error] Could not decode PeerList JSON: {e}")
            return False

        if clientPeer not in G_peerList:
            G_peerList.append(clientPeer)

        return self.sendPeerList(clientSocket)

    def clientRequest(self, clientSocket: socket.socket) -> bool:
        """
        Reads the client's request, then dispatches based on CRequest.
        Loops until 60s of inactivity or an error occurs.
        """
        try:
            clientSocket.settimeout(60)
        except socket.error as e:
            synchronized_print(f"[Error] Could not set timeout: {e}")
            return False

        try:
            clientRequest = clientSocket.recv(G_BUFFER).decode()
        except (socket.timeout, socket.error, UnicodeDecodeError) as e:
            synchronized_print(f"[Error] Failed initial read from client: {e}")
            return False

        startTime = time.time()
        while (time.time() - startTime) < 60:
            if not clientRequest:
                synchronized_print("[Info] clientRequest() => empty request. Possibly client closed.")
                break

            match clientRequest:
                case 'Handshake':
                    ok = self.handleHandshake(clientSocket)
                case 'ConnectRequest':
                    ok = self.confirmConnection(clientSocket)
                case 'AddMe':
                    ok = self.initialConnectionHandler(clientSocket)
                case 'PeerList':
                    ok = self.sendPeerList(clientSocket)
                case 'ListFiles':
                    ok = self.sendPeerList(clientSocket)
                case 'DownloadFile':
                    ok = self.sendRequestedFile(clientSocket)
                case 'SendMyFiles':
                    ok = self.receiveRequestedFiles(clientSocket)
                case 'SearchFiles':
                    ok = self.handleSearchFiles(clientSocket)
                case 'UploadFile':
                    ok = self.handleUploadFile(clientSocket)
                case _:
                    synchronized_print(f"[Error] Unknown request from client: {clientRequest}")
                    ok = False

            if not ok:
                break

            try:
                clientRequest = clientSocket.recv(G_BUFFER).decode()
            except socket.timeout:
                synchronized_print("[Info] Client socket timed out, ending loop.")
                break
            except (socket.error, UnicodeDecodeError) as e:
                synchronized_print(f"[Error] Reading subsequent request failed: {e}")
                break

        clientSocket.close()
        return True
