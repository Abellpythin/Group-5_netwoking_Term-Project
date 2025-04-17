from __future__ import annotations
from datetime import datetime
from enum import Enum

import json
import socket
import time
import threading
from pathlib import Path
import HelperFunctions


# Will it contain names? Just addresses?
G_BUFFER: int = 2500000  # 2.5 mB

# ------------------------------------------------------------------------------------------------------------
# Remember to add thread lock to this object. If multiple threads try to add new clients then we're doomed
G_peerList: list[PeerList] = []
G_FileList: list[File] = []
G_peerListLock: threading.Lock = threading.Lock()


# Enumerations are used to guarantee consistent strings for communication between sockets
class CRequest(Enum):
    """
    Enumeration that contains strings that the client can send to the server.
    Server method ClientRequest will need to be updated as more enumerations are added
    """
    # Ex: CRequest.PeerList.name |  to get string name of enum
    ConnectRequest = 0
    AddMe = 1
    PeerList = 2
    RequestFile = 3
    SendMyFiles = 4  # Sends list of File names (Not the contents itself)


class SResponse(Enum):
    """
    Enumeration that contains strings that the client can send to the client
    Please keep the names simple
    """
    Connected = 0  # Handles standard connection
    SendYourInfo = 1  # Response when client wants to send info (peerlist, files, etc.)


def peerList_from_dict(peerAsDict):
    """
    Unpacks Json serialization of PeerList (not to be mistaken with G_PeerList)
    :param objectAsDict:
    :return:
    """
    return PeerList(**peerAsDict)


def file_from_dict(fileAsDict):
    return File(**fileAsDict)


class Peer:
    """
    -Methods that take an address as a parameter AND sends data assumes two things
        1. The peer socket is created
        2. The peer socket is currently in a tcp connection
    """
    def __init__(self, address=('127.0.0.1', 5001), username: str=None, files=None, online: bool=True):
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

        # The type of currenDirectory changes depending on what os software is being used
        # Ex: pathlib.WindowsPath, pathlib.PosixPath, etc...
        currentDirectory = Path.cwd()
        parent_of_parent_directory = currentDirectory.parent / "Files"
        fileNames = HelperFunctions.list_files_in_directory(parent_of_parent_directory)

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
        global G_peerListLock
        self.socket.send(CRequest.PeerList.name.encode())

        # Receive json data containing peerlist data
        data: str = self.socket.recv(G_BUFFER).decode()
        with G_peerListLock:
            G_peerList = [peerList_from_dict(item) for item in json.loads(data)]

    def fileRequest(self):
        # Send in chunks? What's the format? How to turn it back to list?
        # Start client side and come back to solve problems
        return

    def validConnection(self, serverResponse: str) -> bool:
        return serverResponse == SResponse.Connected.name




class Server:
    # Default should be set to macbook's actual ip later
    def __init__(self, address: tuple = ('127.0.0.1', 5001)):
        self.address: tuple[str, int] = address
        self.socket: socket.socket | None = None

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

    """
    Future self
    Thread safety is always a concern. Lists [] are thread safe luckily but any modifications to custom 
    data types could be worrisome. Keep them to a minimum if not none at all
    """
    # A client could request a file, peer list, etc. This is not exclusively for files
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

        while (length < 5) and (requestsHandled):
            # Reset everytime a successful connection occurs
            startTime = time.time()

            # Matching string with string
            match clientRequest:
                case CRequest.ConnectRequest.name:
                    print("Server: I have been requested to connect ------")
                    requestsHandled = self.confirmConnection(clientSocket)

                case CRequest.AddMe.name:
                    print("Server: Client wants me to add them")
                    requestsHandled = self.initialConnectionHandler(clientSocket)

                case CRequest.PeerList.name:
                    requestsHandled = self.sendPeerList(clientSocket)

                case CRequest.RequestFile.name:
                    requestsHandled = self.sendRequestedFile(clientSocket)

                case CRequest.SendMyFiles.name:
                    requestsHandled = self.receiveRequestedFiles(clientSocket)

                case _:
                    requestsHandled = False

            print("Server: Successfully sent data back")

            # This will timeout after 60 seconds
            #I have set timeout to 10 seconds for debugging purposes
            try:
                clientRequest: str = clientSocket.recv(G_BUFFER).decode()
            except TimeoutError as e:
                # If we timeout then good, the while loop will simply end
                # The socket timeout is equivalent to the function timer so no worries
                continue

            endTime = time.time()
            length = endTime - startTime

        return requestsHandled

    def initialConnectionHandler(self, clientSocket: socket) -> bool:
        """
        This method
        :param clientSocket:
        :return:
        """
        global G_peerListLock
        # Ask client to Send their PeerList describing themselves
        # Receive client's PeerList object describing themselves
        clientResponse: str = self.serverSendResponse(clientSocket, SResponse.SendYourInfo)

        print("Server client peer data: ", clientResponse)
        clientPeer: PeerList = peerList_from_dict(json.loads(clientResponse))

        with G_peerListLock:
            # Puts the peer in peerlist if not currently in peerlist
            G_peerList.append(clientPeer) if clientPeer not in G_peerList else None

        #Send back this server's G_peerList
        self.sendPeerList(clientSocket)

        return True

    def sendPeerList(self, clientSocket: socket):

        # Adding this to show on local clients that it will send the whole list
        # Remember, on local clients both the server and client have the same username, ip, and port
        #REMOVE LATER DEBUGGING
        global G_peerListLock
        with G_peerListLock:
            G_peerList.append(PeerList(('Debugging', 12000), "Let's Go"))
        # ------------------------------------------------------------------------------------------------------------

        json_data: str = json.dumps([peer.__dict__() for peer in G_peerList])

        # Change to send in chunks perhaps
        clientSocket.send(json_data.encode())

        return True

    def confirmConnection(self, clientSocket: socket) -> bool:
        success: bool = True
        try:
            clientSocket.send(SResponse.Connected.name.encode())

        # Broad error, try to narrow later
        except OSError as err:
            success = False
            print(err)
        finally:
            return success

    #Todo: This method
    def sendRequestedFile(self, clientSocket: socket):
        """
        This will send the requested file
        Any file in the peer's file list is open to be requested and sent.
        There will be no confirmation message after it is added.
        If the file has been removed it will send a message saying this file is unavailable
        :return: bool
        """

        # giToDo: To be implemented
        return

    def receiveRequestedFiles(self, clientSocket: socket) -> bool:
        """
        This will send a response back to the client and receive their available files
        :param clientSocket:
        :return: bool
        """

        clientResponse: str = self.serverSendResponse(clientSocket, SResponse.SendYourInfo)

        G_FileList.extend([file_from_dict(item) for item in json.loads(clientResponse)])

        print("I have received files")

        for file in G_FileList:
            print(file.fileName)

        return True



class File:
    def __init__(self, fileName: str, userName, addr=None):
        self.fileName: str = fileName
        self.userName: str = userName
        self.addr: tuple[str, int] | None = addr

    def __dict__(self):
        return {'fileName': self.fileName, 'userName': self.userName, 'addr': self.addr}


class PeerList:
    """
    The peer list will be used to not only connect to peers but to display what users
    are online
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



# For future security it MIGHT be useful to make methods that check the ip address
# Files and peer list should be separate. They can always be combined but separating is much harder
