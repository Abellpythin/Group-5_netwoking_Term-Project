# Send Everything universally through bits
# Encoding is faster however images should not be encoded in utf-8
# By sending everything through bits this process is avoided
# Think about limiting how many files a user can download
# Limit how many files can be requested from one server

import socket
import threading
from Classes import Peer
from Classes import Server
from Classes import CRequest
import os


# G for global variable
G_MY_PORT = 12000
G_MY_IP = '127.0.0.1'
G_MAX_CONNECTIONS = 5

# The user
G_ENDPROGRAM = False

# After running any socket, wait at least 30 seconds or else you'll get this error
# OSError: [Errno 48] Address already in use
def main():
    """
    The main method will be used for io operations, managing threads, and creating classes.
    :return:
    """

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
    """
    The server is ran for the entire duration of the program.
    It only ends when the user decides to end the program.
    There should be NO IO OPERATIONS IN THE SERVER (Too complex and too little time)
    :return:
    """
    myServer = Server((G_MY_IP, G_MY_PORT))

    with myServer.createTCPSocket() as listening_socket:
        # Continuously listens so need to put in while loop
        listening_socket.listen(G_MAX_CONNECTIONS)
        threads = []

        while True:
            conn, addr = listening_socket.accept()  # Accepts 1 connection at a time
            thread = threading.Thread(target=myServer.clientRequest, args=(conn, addr))
            threads.append(thread)
            thread.start()
            #Create method to send in a thread
            break

        for thread in threads:
            thread.join()




    # myServer = Server()
    # with myServer.createTCPSocket() as server_socket:
    #     server_socket.listen(1)
    #
    #     conn, addr = server_socket.accept()
    #     with conn:
    #         print(f"Server: Connected by {addr}")
    #
    #         data = conn.recv(1024)
    #         if data:
    #             print("Received: {", data.decode(), '}', sep="")
    #         conn.sendall("Server: Thank god it sent".encode())


# Peer in front a print statement indicates the Peer sent it
def runPeer():



    # myPeer = Peer()
    # with myPeer.createTCPSocket() as peer_socket:
    #     peer_socket.connect(('127.0.0.1', 5001))
    #
    #     peer_socket.sendall("Please Work".encode())
    #     response = peer_socket.recv(1024)
    #
    #     print("Peer Received Response: {", response.decode(), "}", sep="")


def initialConnect(ip: str, port: int):
    # Create Peer class for user
    selfPeer = Peer(address=(G_MY_IP, G_MY_PORT))

    #Add a while loop to keep asking for ip and port if error occurs
    with selfPeer.createTCPSocket() as peer_socket:
        # When locally testing, '127.0.0.1' or '0.0.0.0' should be used
        serverIP: str = input("Type the Ip address of server: ")
        serverPort: int = int(input("Type the Port number of server: "))
        try:
            peer_socket.connect((serverIP, serverPort))
            # Send message to server asking to connect
            peer_socket.send(CRequest.ConnectRequest.name.encode())

            # Receive message from server confirming connection
            data, address = peer_socket.recvfrom()  # recvfrom in hopes of adding security features later
            data = data.decode()

            # Server implementation will send the string 'Server: Connected'
            if selfPeer.validConnection(data):


        except (TimeoutError, InterruptedError) as err:
            print(err)
            print("Connection did not go through. Check the Client IP and Port")

def getUserInput(inputQueue):
    """
    This MUST be run in a thread so that it doesn't block other threads.
    The input should be handled by a separate queue function
    :return:
    """
    return

if __name__ == '__main__':
    main()