from __future__ import annotations
import socket
from datetime import datetime


class Peer:
    def __init__(self, address=('127.0.0.1', 5001), files=None, online: bool = False):
        if files is None:
            files = []
        self.address = address
        self._files: list[File] = files
        self.online = online
        self.socket = None

    def createTCPSocket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return self.socket

    def addFile(self, file:File):
        self._files.append(file)

    def displayCurrentFiles(self):
        print("Your public downloadable Files:")
        for file in self._files:
            print(file.fileName, ";  ", end="")
            print(file.date)

    def toggleOnline(self) -> bool:
        self.online = not self.online
        return self.online

    # Redundant most likely
    def sendMessage(self, address: tuple, message: str) -> bool:
        if(not self.socket):
            raise TypeError # Change later
        self.socket.sendall(message.encode())




class Server:
    # Default should be set to macbook's actual ip later
    def __init__(self, address: tuple = ('127.0.0.1', 5001)):
        self.address = address
        self.socket = None

    def createTCPSocket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.address)
        return self.socket


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




