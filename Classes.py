from __future__ import annotations
import json
import socket
from datetime import datetime
from enum import Enum

# Will it contain names? Just addresses?
G_BUFFER = 2500000  # 2.5 mB
G_peerList: list[PeerList] = []


# Enumerations are used to guarantee consistent strings for communication between sockets
class CRequest(Enum):
    """
    Enumeration that contains strings that the client can send to the server.
    Server method ClientRequest will need to be updated as more enumerations are added
    """
    # Ex: CRequest.PeerList.name |  to get string name of enum
    ConnectRequest = 0
    PeerList = 1
    RequestFile = 2


class SResponse(Enum):
    """
    Enumeration that contains strings that the client can send to the client
    """
    Connected = 0


class Peer:
    """
    -Methods that take an address as a parameter AND sends data assumes two things
        1. The peer socket is created
        2. The peer socket is currently in a tcp connection
    """
    def __init__(self, address=('127.0.0.1', 5001), username: str=None, files=None, online: bool = True):
        if files is None:
            files = []
        self.address = address
        self.username = username
        self._files: list[File] = files
        self.online = online
        self.socket = None

    def createTCPSocket(self):
        # This socket should be used with 'with' keyword so no explicit closing of socket is needed
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return self.socket

    def addFile(self, file: File):
        self._files.append(file)

    def displayCurrentFiles(self):
        print("Your public downloadable Files:")
        for file in self._files:
            print(file.fileName, "; ", end="")
            print(file.date)

    def toggleOnline(self) -> bool:
        self.online = not self.online
        return self.online

    def requestPeerList(self, serverAddress: tuple) -> list:
        """
        Request List of peers from chosen serverAddress
        :param serverAddress:
        :return: List of peers currently online in network
        """
        self.socket.send(CRequest.PeerList.name.encode)

        # Receive json data containing peerlist data
        data = self.socket.recv(G_BUFFER)
        received_objects = [peerList_from_dict(item) for item in json.loads(data)]

    def fileRequest(self):
        # Send in chunks? What's the format? How to turn it back to list?
        # Start client side and come back to solve problems
        return

    def validConnection(self, serverResponse: str) -> bool:
        return serverResponse == SResponse.Connected.name




class Server:
    # Default should be set to macbook's actual ip later
    def __init__(self, address: tuple = ('127.0.0.1', 5001)):
        self.address = address
        self.socket = None

    def createTCPSocket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.address)
        return self.socket

# A client could request a file, peer list, etc. This is not exclusively for files
    def clientRequest(self, clientSocket: socket) -> bool:
        """
        This reads the client's request message and calls the proper method to handle it
        This will need to be updated as CRequest gets updated
        :param clientSocket:
        :param addr:
        :return:
        """
        requestHandled = True
        data = clientSocket.recv()
        # Matching string with string
        match data:
            case CRequest.ConnectRequest.name:
                requestHandled = self.confirmConnection(clientSocket)
            case CRequest.PeerList.name:
                
                requestHandled = self.sendPeerList(clientSocket)
            case CRequest.RequestFile.name:
                requestHandled = self.sendRequestedFile(clientSocket)
            case _:
                requestHandled = False

        return requestHandled

    def confirmConnection(self, clientSocket: socket) -> bool:
        success = True
        try:
            clientSocket.send(SResponse.Connected.name.encode())
        # Broad error, try to narrow later
        except OSError as err:
            success = False
            print(err)
        finally:
            return success

    def sendPeerList(self, clientSocket: socket) -> bool:
        # peerListStr = ""
        # for peer in G_peerList:
        #     peerListStr += str(peer) + ","
        # peerListStr.removesuffix(',')

        json_data = json.dumps([G_peerList.__dict__ for peerList in G_peerList])
        # Change to send in chunks perhaps
        clientSocket.send(json_data.encode())
        return True

    def sendRequestedFile(self, clientSocket: socket):
        """
        This will send the requested file
        Any file in the peer's file list is open to be requested and sent.
        There will be no confirmation message after it is added.
        If the file has been removed it will send a message saying this file is unavailable
        :return:
        """
        # To be implemented
        return True


class File:
    # True if fileName is Path, false otherwise
    #
    def __init__(self, fileName: str, username:str = None, isPath:bool=False):
        self.fileName = fileName
        self.date = datetime.now()
        # The underscore before the name means it's implied to be private (Not enforced)
        self.username = username
        self._isPath = True

    def isPath(self) -> bool:
        return self._isPath

    def changeFileName(self, fileName:str, isPath:bool=False):
        self.fileName = fileName
        self._isPath = isPath
        self.date = datetime.now()


class PeerList:
    """
    The peer list will be used to not only connect to peers but to display what users
    are online
    """
    def __init__(self, addr: tuple, username: str):
        self.addr = addr
        self.username = username

    # if you're unfamiliar with '__methodName__' look up "python dunder methods"
    def __dict__(self):
        return {'addr': self.addr, 'username': self.username}

    def __str__(self):
        return f"{{{self.addr},{self.username}}}"

    def __eq__(self, other: PeerList):
        return (self.addr, self.username) == (other.addr, other.username)


def peerList_from_dict(data):
    """
    Unpacks Json serialization of PeerList
    :param data:
    :return:
    """
    return PeerList(**data)


class FileList:
    def __init__(self, fileName: str, username):
        self.fileName = fileName
        self.username = username

    def __str__(self):
        return f"{{{self.fileName},{self.username}}}"

# For future security it might be useful to make methods that simply check the ip address
# Files and peer list should be separate. They can always be combined but separating is much harder