from __future__ import annotations
from enum import Enum

import os
import json
import socket
import time
import threading
from pathlib import Path

G_BUFFER: int = 4096  # Bytes

# Ensure that any modifications to these list are used with Lock
G_peerList: list[PeerList] = []
G_FileList: list[File] = []
g_FilesForSync: list[FileForSync] = []
G_peerListLock: threading.Lock = threading.Lock()
G_SyncFileLock: threading.Lock = threading.Lock()


# Enumerations are used to guarantee consistent strings for communication between sockets
class CRequest(Enum):
    """
    Enumeration that contains strings that the client can send to the server.
    Server method ClientRequest will need to be updated as more enumerations are added
    """
    # Ex: CRequest.PeerList.name |  to get string name of enum
    ConnectRequest = 0
    AddMe = 1
    PeerList = 2  # Request PeerList
    RequestFile = 3  # To download
    SendMyFiles = 4  # Sends list of File names (Not the contents itself)
    RequestFileList = 5  # Request File list
    SendMySyncFiles = 6  # Sends List of Files and users subscribed to it
    SubscribeToFile = 7  # The client will subscribe to file
    UpdateSyncFile = 8  # This informs the server that the client has updated a file and the server should sync it


class SResponse(Enum):
    """
    Enumeration that contains strings that the server can send to the client
    """
    Connected = 0  # Handles standard connection
    SendYourInfo = 1  # Response when client wants to send info (peerlist, files, etc.)
    SendWantedFileName = 2  # Response when client wants to download file


def list_files_in_directory(directory_path) -> list[str]:
    """
    Returns list of file names
    Ex: ["CoolCat.jpeg", "CoolerDog.png"]
    :param directory_path:
    :return:
    """
    try:
        files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
        return files
    except FileNotFoundError:
        print("Fail")


def peerList_from_dict(peerAsDict):
    """
    Unpacks Json serialization of PeerList (not to be mistaken with G_PeerList)
    :param peerAsDict:
    :return:
    """
    return PeerList(**peerAsDict)


def file_from_dict(fileAsDict):
    return File(**fileAsDict)


def sync_file_from_dict(syncFileAsDict):
    usersSubbed = [peerList_from_dict(u) for u in syncFileAsDict['usersSubbed']]
    return FileForSync(fileName=syncFileAsDict['fileName'], usersSubbed=usersSubbed)


def receiveFileTo(receiving_socket: socket, filePath: Path):
    """
    Receive a file from a peer
    :param receiving_socket:
    :param filePath:
    :return:
    """

    fileSize: int = int(receiving_socket.recv(G_BUFFER).decode())

    #print(f"Function receiveFileTo: Server Received Updated File of Size: {fileSize}")

    # This implies that unless a user explicitly unsubscribes from a folder, they will forever receive updates
    os.makedirs(os.path.dirname(filePath), exist_ok=True)

    receivedSize: int = 0

    with open(filePath, 'wb') as f:
        while receivedSize < fileSize:
            data = receiving_socket.recv(G_BUFFER)
            if not data:
                break
            f.write(data)
            receivedSize += len(data)


class Peer:
    """
    -Methods that take an address as a parameter AND sends data assumes two things
        1. The peer socket is created
        2. The peer socket is currently in a tcp connection
    """
    def __init__(self, address: tuple[str, int]=('127.0.0.1', 5001), username:str=None, files=None, online: bool=True):
        if files is None:
            files = []
        self.address: tuple[str, int] = address
        self.username: str = username
        self.files: list[File] = files
        self.online: bool = online
        self.socket: socket.socket | None = None

    def createTCPSocket(self):
        # This socket should be used with 'with' keyword so no explicit closing of socket is needed
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return self.socket

    def initializeFiles(self) -> None:
        """
        This function will automatically append the user's files in the Files folder to the user's files
        :return:
        """

        # The type of currentDirectory changes depending on what os software is being used
        # Ex: pathlib.WindowsPath, pathlib.PosixPath, etc...
        currentDirectory: Path = Path.cwd()
        parent_of_parent_directory: Path = currentDirectory.parent / "Files"
        #fileNames: list[str] = list_files_in_directory(parent_of_parent_directory)
        fileNames: list[str] = [fn for fn in list_files_in_directory(parent_of_parent_directory) if not fn.endswith('~')]

        # File names cannot be duplicates so need to set path
        # Just find file name in Files directory
        for name in fileNames:
            self.files.append(File(name, self.username, self.address))

    def addFile(self, file: File):
        self.files.append(file)

    def displayCurrentFiles(self):
        print("Your public downloadable Files:")
        for file in self.files:
            print(file.fileName, "; ", end="")

    def toggleOnline(self) -> bool:
        self.online = not self.online
        return self.online

    def requestPeerList(self, serverAddress: tuple) -> None:
        """
        Request List of peers from chosen serverAddress
        :param serverAddress:
        :return: List of peers currently online in network
        """
        global G_peerList
        self.socket.send(CRequest.PeerList.name.encode())

        # Receive json data containing peerlist data
        data: str = self.socket.recv(G_BUFFER).decode()
        with G_peerListLock:
            G_peerList = [peerList_from_dict(item) for item in json.loads(data)]

    def validConnection(self, serverResponse: str) -> bool:
        return serverResponse == SResponse.Connected.name


class Server:
    # Default should be set to macbook's actual ip later
    def __init__(self, address: tuple[str, int]= ('127.0.0.1', 5001)):
        self.address: tuple[str, int] = address
        self.socket: socket.socket | None = None

        self.userName: str | None = None  # Used for initial connect

    def createTCPSocket(self):
        """
        This method creates and assigns a tcp socket to this server object
        :return: socket object owned by this object
        """
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.address)
        return self.socket

    def serverSendResponse(self, server_socket: socket, sResponse: SResponse) -> str:
        """
        This method sends the server's response to the client
        :param server_socket:
        :param sResponse:
        :return: client's response in utf8 characters
        """
        sendStr: sResponse = sResponse.name
        server_socket.send(sendStr.encode())
        return server_socket.recv(G_BUFFER).decode()

    def clientRequest(self, clientSocket: socket) -> bool:
        """
        This reads the client's request message and calls the proper method to handle it. It will remain
        open until the timer times out
        This will need to be updated as CRequest gets updated
        :param clientSocket:
        :return: True if Client Request is handled, False otherwise
        """
        # If ever false, something went wrong
        requestsHandled: bool = True
        clientRequest: str = clientSocket.recv(G_BUFFER).decode()

        # a timer to ensure the server doesn't wait forever
        startTime: float = time.time()
        endTime: float = time.time()
        length: float = endTime - startTime

        with clientSocket:
            while (length < 5) and (requestsHandled):
                # Reset everytime a successful connection occurs
                startTime = time.time()

                """
                Always remember to add .name at the end of each enumeration case
                """
                match clientRequest:
                    case CRequest.ConnectRequest.name:
                        requestsHandled = self.confirmConnection(clientSocket)

                    case CRequest.AddMe.name:
                        requestsHandled = self.initialConnectionHandler(clientSocket)

                    case CRequest.PeerList.name:
                        requestsHandled = self.sendPeerList(clientSocket)

                    case CRequest.RequestFile.name:
                        requestsHandled = self.sendRequestedFile(clientSocket)

                    case CRequest.SendMyFiles.name:
                        requestsHandled = self.receiveRequestedFiles(clientSocket)

                    case CRequest.RequestFileList.name:
                        requestsHandled = self.sendFileList(clientSocket)

                    case CRequest.SendMySyncFiles.name:
                        requestsHandled = self.receiveSyncFileList(clientSocket)

                    case CRequest.SubscribeToFile.name:
                        requestsHandled = self.sendSyncFileContent(clientSocket)

                    case CRequest.UpdateSyncFile.name:
                        requestsHandled = self.update_send_fileUpdate(clientSocket)

                    case _:
                        requestsHandled = False

                # This will optionally timeout after 60 seconds
                try:
                    clientRequest: str = clientSocket.recv(G_BUFFER).decode()
                except TimeoutError as e:
                    # If we timeout then good, the while loop will simply end
                    # The socket timeout is equivalent to the function timer so no worries
                    print(f"Client took too long. Tell them hurry up")
                    continue

                endTime = time.time()
                length = endTime - startTime

        return requestsHandled

    def initialConnectionHandler(self, clientSocket: socket) -> bool:
        """
        This method handles a new client connected to the P2P network for the first time
        :param clientSocket:
        :return:
        """
        # Ask client to Send their PeerList describing themselves
        # Receive client's PeerList object describing themselves
        clientResponse: str = self.serverSendResponse(clientSocket, SResponse.SendYourInfo)

        clientPeer: PeerList = peerList_from_dict(json.loads(clientResponse))

        with G_peerListLock:
            # Puts the peer in peerlist if not currently in peerlist
            G_peerList.append(clientPeer) if clientPeer not in G_peerList else None

            thisServerInfo: PeerList = PeerList(self.address, self.userName)

            G_peerList.append(thisServerInfo) if thisServerInfo not in G_peerList else None

        # Send back this server's G_peerList
        self.sendPeerList(clientSocket)

        # Now create Peer to get list of File objects then send to client
        fileObjectList: list[File] = self.fileObject_list()

        for file in fileObjectList:
            G_FileList.append(file)

        return True

    def sendPeerList(self, clientSocket: socket):
        json_data: str = json.dumps([peer.__dict__() for peer in G_peerList])

        clientSocket.send(json_data.encode())

        return True

    def sendFileList(self, clientSocket: socket):

        json_data: str = json.dumps([file.__dict__() for file in G_FileList])

        clientSocket.send(json_data.encode())
        return True

    def sendSyncFileList(self, clientSocket: socket):

        with G_SyncFileLock:
            json_data: str = json.dumps([fs.__dict__() for fs in g_FilesForSync])

            clientSocket.send(json_data.encode())

    def confirmConnection(self, clientSocket: socket) -> bool:
        success: bool = True
        try:
            clientSocket.send(SResponse.Connected.name.encode())

        # Broad error, try to narrow later
        except OSError as err:
            success = False
            print(err)
        return True

    def sendRequestedFile(self, clientSocket: socket):
        """
        This will send the requested file
        Any file in the peer's file list is open to be requested and sent.
        There will be no confirmation message after it is added.
        If the file has been removed it will send a message saying this file is unavailable
        :return: bool
        """

        clientResponse: str = self.serverSendResponse(clientSocket, SResponse.SendWantedFileName)

        wantedFile: File = file_from_dict(json.loads(clientResponse))
        #print(f"Client sent File to Server: {wantedFile}\n")

        currentDirectory: Path = Path.cwd()
        parent_of_parent_directory: Path = currentDirectory.parent / "Files/"
        #fileNames: list[str] = list_files_in_directory(parent_of_parent_directory)
        fileNames: list[str] = [fn for fn in list_files_in_directory(parent_of_parent_directory) if not fn.endswith('~')]


        #print(f"WantedFile: {wantedFile.fileName}")

        if wantedFile.fileName in fileNames:
            filePath: Path = parent_of_parent_directory / wantedFile.fileName
            fileSize: int = os.stat(str(filePath)).st_size

            # Path does exist
            #print(os.path.exists(filePath))
            clientSocket.send(f"{fileSize}".encode())
            #print(f"Sent file size {fileSize}\n")

            with open(filePath, 'rb') as f:
                while True:
                    data = f.read(1024)
                    if not data:
                        break
                    clientSocket.sendall(data)

        return True

    def sendSyncFileContent(self, clientSocket: socket):

        # Receive Client's wanted SyncFile (File in FilesForSync)
        clientResponse: str = self.serverSendResponse(clientSocket, SResponse.SendWantedFileName)

        # Receive client as a PeerList
        jsonClientPeerList: str = clientSocket.recv(G_BUFFER).decode()
        clientPeerList: PeerList = peerList_from_dict(json.loads(jsonClientPeerList))

        wantedSyncFile: FileForSync = sync_file_from_dict(json.loads(clientResponse))

        currentDirectory: Path = Path.cwd()
        syncFilePath: Path = currentDirectory.parent / "FilesForSync/"

        #fileNames: list[str] = list_files_in_directory(syncFilePath)
        fileNames: list[str] = [fn for fn in list_files_in_directory(syncFilePath) if not fn.endswith('~')]

        if wantedSyncFile.fileName in fileNames:
            filePath: Path = syncFilePath / wantedSyncFile.fileName
            fileSize: int = os.stat(str(filePath)).st_size
            clientSocket.send(f"{fileSize}".encode())

            with G_SyncFileLock:
                for syncFile in g_FilesForSync:
                    if syncFile == wantedSyncFile:
                        syncFile.usersSubbed.append(clientPeerList)

                with open(filePath, 'rb') as f:
                    while True:
                        data = f.read(1024)
                        if not data:
                            break
                        clientSocket.sendall(data)

        return True

    def update_send_fileUpdate(self, clientSocket: socket) -> bool:
        """
        This method will receive the fileUpdate from the client, update OR append it to this user's file, then send it
        to the next user
        :param clientSocket:
        :return:
        """

        with G_SyncFileLock:
            # What if clientResponse is empty?
            sendStr: str = SResponse.SendYourInfo.name
            clientSocket.send(sendStr.encode())

            fileName: str = clientSocket.recv(G_BUFFER).decode()

            # Receive a list of users who need the update
            jsonUsersToBeSent: str = clientSocket.recv(G_BUFFER).decode()

            # If empty then move on
            usersToBeSent: list[PeerList] = []
            if jsonUsersToBeSent:
                usersToBeSent = [peerList_from_dict(item) for item in json.loads(jsonUsersToBeSent)]

            currentDirectory: Path = Path.cwd()
            filePath: Path = currentDirectory.parent / "FilesForSync" / fileName

            receiveFileTo(clientSocket, filePath)

            for user in usersToBeSent:
                if user.username == self.userName:
                    usersToBeSent.remove(user)
            # print("Server Line 442: I got the update")

            sendFileSyncUpdate(fileName, filePath, Peer(self.address, self.userName), usersToBeSent)

        return True


    def receiveRequestedFiles(self, clientSocket: socket) -> bool:
        """
        This will send a response back to the client and receive their available files
        :param clientSocket:
        :return: bool
        """

        clientResponse: str = self.serverSendResponse(clientSocket, SResponse.SendYourInfo)

        if clientResponse:
            G_FileList.extend([file_from_dict(item) for item in json.loads(clientResponse)])
        else:
            print("Classes 342: File list client sent was empty")

        return True

    def receiveSyncFileList(self, clientSocket: socket) -> bool:
        """
        This will receive the client's FilesForSync directory
        :param clientSocket:
        :return:
        """
        clientResponse: str = self.serverSendResponse(clientSocket, SResponse.SendYourInfo)

        if clientResponse:

            for fileSyncObj in [sync_file_from_dict(item) for item in json.loads(clientResponse)]:
                if not any(fs.fileName == fileSyncObj.fileName for fs in g_FilesForSync):
                    g_FilesForSync.append(fileSyncObj)

            jsonFilesForSync: str = json.dumps([fs.__dict__() for fs in g_FilesForSync])
            clientSocket.send(jsonFilesForSync.encode())

        else:
            print("Classes 358: FilesForSync is empty.")

        return True

    def fileObject_list(self) -> list[File]:
        """
        This return a list of file objects (not just file names)
        :return: fileObjectList
        """
        currentDirectory: Path = Path.cwd()
        filePath: Path = currentDirectory.parent / "Files"
        fileObjectList: list[File] = []

        if os.path.exists(filePath):
            #files: list[str] = list_files_in_directory(filePath)
            files: list[str] = [fn for fn in list_files_in_directory(filePath) if not fn.endswith('~')]

            for fileName in files:
                fileObjectList.append(File(fileName, self.userName, self.address))

        return fileObjectList



class File:
    """
    This is an object that contains:
    1. The name of the file
    2. What user owns the file
    3. The address of the file
    """
    def __init__(self, fileName: str, userName, addr=None):
        self.fileName: str = fileName
        self.userName: str = userName
        self.addr: tuple[str, int] | None = addr

    def __dict__(self):
        return {'fileName': self.fileName, 'userName': self.userName, 'addr': self.addr}

    def __eq__(self, other: File):
        return(self.fileName, self.userName, self.addr) == (other.fileName, other.userName, other.addr)


class FileForSync:
    def __init__(self, fileName: str, usersSubbed: list[PeerList]):
        self.fileName: str = fileName
        self.usersSubbed: list[PeerList] = usersSubbed

    def __dict__(self):
        return {'fileName': self.fileName, 'usersSubbed': [us.__dict__() for us in self.usersSubbed]}

    def __eq__(self, other: FileForSync):
        return (self.fileName, self.usersSubbed) == (other.fileName, other.usersSubbed)


class PeerList:
    """
    This class is used to send peer information to the clients. Peer is used locally, PeerList is used
    to communicate between servers an clients.
    """
    def __init__(self, addr: tuple[str, int], username: str):
        self.addr: tuple[str, int] | None = addr
        self.username: str = username

    # if you're unfamiliar with '__methodName__' look up "python dunder methods"
    def __dict__(self):
        return {'addr': self.addr, 'username': self.username}

    def __str__(self):
        return f"{{{self.addr},{self.username}}}"

    def __eq__(self, other: PeerList):
        return (self.addr, self.username) == (other.addr, other.username)


"""
Just leaving this comment to say circular imports are dumb and so is Python. That's why these methods needs to pasted
Into this file
"""


def sendFileSyncUpdate(fileName: str, filePath: Path, userAsPeerList: Peer, usersToBeSent: list[PeerList]):
    """
    Whenever a file in the FilesForSync directory is updated, this method will be called to send the update to the server

    :param fileName:
    :param filePath:
    :param userAsPeerList:
    :param usersToBeSent: A list of users that need to be sent the update.
    :return:
    """



    if not usersToBeSent:
        print("sendFileSyncUpdate 437: No more users to send update to\n")
        return

    userToSendTo: tuple[str, int] = usersToBeSent.pop(0).addr

    # Acquire Lock to ensure nothing else edits data while sending
    with G_SyncFileLock:
        with userAsPeerList.createTCPSocket() as peer_socket:
            connectionSuccess: bool = False

            while not connectionSuccess:
                try:
                    peer_socket.settimeout(15)
                    peer_socket.connect(userToSendTo)

                    # Request to send update to server
                    serverResponse: str = clientSendRequest(peer_socket, CRequest.UpdateSyncFile)

                    if serverResponse != SResponse.SendYourInfo.name:
                        raise Exception("Main Line 275: Server is not ready to receive File Sync Update")

                    peer_socket.send(fileName.encode())

                    # Send the users that still need the update
                    jsonUsersToBeSent: str = json.dumps([user.__dict__() for user in usersToBeSent])
                    peer_socket.send(jsonUsersToBeSent.encode())

                    sendFileTo(peer_socket, filePath)

                    connectionSuccess = not connectionSuccess

                except (TimeoutError, InterruptedError, ConnectionRefusedError) as err:
                    print("File Sync Update connection did not go through. Check the Client IP and Port")
                    userSocket.close()
                    userSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    pass


def clientSendRequest(peer_socket: socket, cRequest: CRequest | int) -> str:
    """
    Sends a request to a server
    :param peer_socket:
    :param cRequest:
    :return: String representing Server response
    """
    sendStr: cRequest = cRequest.name
    peer_socket.send(sendStr.encode())
    return peer_socket.recv(G_BUFFER).decode()


def sendFileTo(sending_socket: socket, filePath: Path):
    """
    This method will send a file to some place
    :return:
    """

    fileSize: int = os.stat(str(filePath)).st_size

    # Debugging ------------
    if fileSize == 0:
        raise Exception("fileSize is 0 check your stuff")
    # ----------------

    sending_socket.send(f"{fileSize}".encode())

    with open(filePath, 'rb') as f:
        while True:
            data = f.read(G_BUFFER)
            if not data:
                break
            sending_socket.sendall(data)

# For future security it MIGHT be useful to make methods that check the ip address
# Files and peer list should be separate. They can always be combined but separating is much harder


