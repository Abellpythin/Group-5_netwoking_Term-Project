# Send Everything universally through bits
# Encoding is faster however images should not be encoded in utf-8
# By sending everything through bits this process is avoided

import socket
import threading
from Classes import Peer
from Classes import Server
import os


# After running any socket, wait at least 30 seconds or else you'll get this error
# OSError: [Errno 48] Address already in use
def main():
    """
    The main method will be used for io operations, managing threads, and creating classes.
    :return:
    """
    # Implement later and make sure to add try and catch blocks
    print("What is your name?")
    userRealName = input()

    # Implement Later
    print("Input a file name: ")
    fileName = input()

    # Make sure when creating "Thread" not to include (). You are not calling the method
    serverThread = threading.Thread(target=runServer, daemon=True)
    peerThread = threading.Thread(target=runPeer, daemon=True)

    peerThread.start()
    serverThread.start()

    serverThread.join()
    peerThread.join()

    print("Complete!")

# Server in front a print statement indicates the Server sent it
def runServer():
    myServer = Server()
    with myServer.createTCPSocket() as server_socket:
        server_socket.listen(1)

        conn, addr = server_socket.accept()
        with conn:
            print(f"Server: Connected by {addr}")

            data = conn.recv(1024)
            if data:
                print("Received: {", data.decode(), '}', sep="")
            conn.sendall("Server: Thank god it sent".encode())

# Peer in front a print statement indicates the Peer sent it
def runPeer():
    myPeer = Peer()
    with myPeer.createTCPSocket() as peer_socket:
        peer_socket.connect(('127.0.0.1', 5001))

        peer_socket.sendall("Please Work".encode())
        response = peer_socket.recv(1024)

        print("Peer Received Response: {", response.decode(), "}",sep="")


if __name__ == '__main__':
    main()