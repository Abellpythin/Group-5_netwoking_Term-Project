import socket

class Peer:
    def __init__(self, address=('127.0.0.1', 5001), files=None, online: bool=False):
        if files is None:
            files = []
        self.address = address
        self.files = files
        self.online = online
        self.socket = None

    def createTCPSocket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        return self.socket

    def addFile(self, fileName: str):
        self.files.append(fileName)

    def toggleOnline(self) -> bool:
        self.online = not self.online
        return self.online


class Server:
    # Default should be set to macbook's actual ip later
    def __init__(self, address: tuple = ('127.0.0.1', 5001)):
        self.address = address
        self.socket = None

    def createTCPSocket(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.address)
        return self.socket
