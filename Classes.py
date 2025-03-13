from __future__ import annotations
import socket
from datetime import datetime
from enum import Enum



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
    def __init__(self, address=('127.0.0.1', 5001), files=None, online: bool = True):
        if files is None:
            files = []
        self.address = address
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
            print(file.fileName, ";  ", end="")
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

    def sendRequest(self):

        # Send in chunks? What's the format? How to turn it back to list?
        # Start client side and come back to solve problems
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
    def clientRequest(self, clientSocket: socket, addr: tuple) -> bool:
        """
        This will need to be updated as CRequest gets updated
        :param clientSocket:
        :param addr:
        :return:
        """
        requestHandled = True
        data = clientSocket.recv()
        match data:
            case CRequest.ConnectRequest:
                # call method
            case CRequest.PeerList:
                # call method
            case CRequest.RequestFile:
                # call method
            case _:
                requesthandled = False
        return False


class File:
    # True if fileName is Path, false otherwise
    def __init__(self, fileName: str, isPath:bool=False):
        self.fileName = fileName
        self.date = datetime.now()
        # The underscore before the name means it's implied to be private (Not enforced)
        self._isPath = True

    def isPath(self) -> bool:
        return self._isPath

    def changeFileName(self, fileName:str, isPath:bool=False):
        self.fileName = fileName
        self._isPath = isPath
        self.date = datetime.now()


# For future security it might be useful to make methods that simply check the ip address
