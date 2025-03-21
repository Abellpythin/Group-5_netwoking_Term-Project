# Send Everything universally through bits
# Encoding is faster however images should not be encoded in utf-8
# By sending everything through bits this process is avoided
# Think about limiting how many files a user can download
# Limit how many files can be requested from one server
from __future__ import annotations
import json
import os
import queue
import threading
import socket # For type annotation

import Classes  # Classes.G_peerList
from Classes import Peer
from Classes import Server
from Classes import CRequest
from Classes import SResponse
from Classes import PeerList

#from Classes import G_peerList | This does not work like c++


# G for global variable
# The port number is preemptively defined so no need to ask user
G_MY_PORT: int = 12000
G_MY_IP: str = '127.0.0.1'
G_MY_USERNAME: str | None = "Debugger"
G_MAX_CONNECTIONS: int = 5


# When the user wants to end the program this variable changes to True and
# runClient, runServer, and Main terminate
G_ENDPROGRAM: bool = False

# Queue necessary for I/O operations
G_input_queue = queue.Queue()

# Used to synchronize print statements among threads. Used for debugging
G_print_lock = threading.Lock()


# After running any socket, wait at least 30 seconds or else you'll get this error
# OSError: [Errno 48] Address already in use
def main():
    """
    The main method will be used for managing threads and initializing the initial connection to the 
    peer network
    """
    print("Welcome to our P2P Network", end='\n\n')

    # ------------------------------------------------------------------------------------------------------------
    # Uncomment when done debugging
    # while True:
    #     try:
    #         G_MY_USERNAME = input("Enter your username: ")
    #         if not G_MY_USERNAME:
    #             raise ValueError("Username cannot be empty.")
    #         if not G_MY_USERNAME[0].isalpha():
    #             raise ValueError("Username must start with a letter.")
    #         if not all(char.isalnum() or char == "_" for char in G_MY_USERNAME):
    #             raise ValueError("Username can only contain letters, numbers, and underscores.")
    #         if not 4 <= len(G_MY_USERNAME) <= 25:
    #             raise ValueError("Username must be between 4 and 25 characters long.")
    #         break
    #     except ValueError as e:
    #         print(f"Invalid username: {e}")
    #
    # while True:
    #     try:
    #         ip_address = input("Enter your IP address (e.g., 127.0.0.1): ")
    #         parts = ip_address.split(".")
    #         if len(parts) != 4:
    #             raise ValueError("IP address must have four parts separated by dots.")
    #         for part in parts:
    #             if not part.isdigit():
    #                 raise ValueError("Each part of the IP address must be a number.")
    #             if len(part) > 3:
    #                 raise ValueError("Each part of the IP address must have at most 3 digits.")
    #             num = int(part)
    #             if num < 0 or num > 255:
    #                 raise ValueError("Each part of the IP address must be between 0 and 255.")
    #         print(f"Valid IP address: {ip_address}")
    #         break
    #     except ValueError as e:
    #         print(f"Invalid IP address: {e}")
    # ------------------------------------------------------------------------------------------------------------


    #IMPORTANT
    # FROM THIS POINT ON ANY I/O OPERATIONS (input, open, with, etc) NEEDS TO BE IN SEPARATE THREAD
    # Make sure when creating "Thread" not to include (). You are not calling the method
    serverThread = threading.Thread(target=runServer, daemon=True)
    serverThread.start()

    initialConnect()

    peerThread = threading.Thread(target=runPeer, daemon=True)
    peerThread.start()

    # Main will not conclude until both threads join so no need for infinite while loop
    serverThread.join()
    peerThread.join()

    # try:
    #     while G_ENDPROGRAM:
    #         time.sleep(0.1)
    # except KeyboardInterrupt:
    #     print("Exiting...")

    print("Complete!")


# "Server" in front a print statement indicates the Server sent it
# Ex: "Server: Got your message bud"
def runServer():
    """
    The server is run for the entire duration of the program.
    It only ends when the user decides to end the program.
    There should be NO IO OPERATIONS IN THE SERVER
    :return:
    """
    myServer = Server((G_MY_IP, G_MY_PORT))

    with myServer.createTCPSocket() as listening_socket:
        # Continuously listens so need to put in while loop
        listening_socket.listen(G_MAX_CONNECTIONS)
        threads = []

        while True:
            conn, addr = listening_socket.accept()  # Accepts 1 connection at a time

            #Set to 60 once done debugging
            conn.settimeout(10)


            #IMPORTANT You will feel suicidal if you don't heed this warning
            # WHEN MAKING A THREAD THAT HAS ARGUMENTS
            # ENSURE THAT IT HAS A COMMA AT THE END OF THE TUPLE
            # EX: (number, str, letter,) <-----
            # Notice the comma at the end. This tells the method that it is an iterable
            thread = threading.Thread(target=myServer.clientRequest, args=(conn,))
            threads.append(thread)
            thread.start()
            # Create method to send in a thread
            break

        for thread in threads:
            thread.join()


# Peer in front a print statement indicates the Peer sent it
def runPeer():
    """
    Needs to be implemented. This will display the files to the user, show them lists of peers, allow them
    to download files etc.
    You have to interact with the user here. No need for a gui, just assume they know what they're doing
    """


    return


def initialConnect():
    """
    The initial connection will try to connect to an online peer. If successful it will retrieve a list
    of peers in the network with their address and username.
    -IF ONE PEER IS IN THE NETWORK NO THEY CANNOT CONNECT TO A PEER
    -IF TWO PEERS ARE IN THE NETWORK THEN THERE'S ONLY TWO PEOPLE
    -IF ONE PERSON CONNECTS TO A PEER WITH A LIST OF PEERS THEN THEY ARE ADDED TO THE NETWORK AND THE LIST
     IS UPDATED AMONG PEERS
    :return:
    """
    # Create Peer class for user
    selfPeer = Peer(address=(G_MY_IP, G_MY_PORT))
    selfPeer.initializeFiles()

    userPeer = PeerList((G_MY_IP, G_MY_PORT), G_MY_USERNAME)

    # !!!! Add a while loop to keep asking for ip and port if error occurs
    with selfPeer.createTCPSocket() as peer_socket:


        #Uncomment when done debugging
        # When locally testing, '127.0.0.1' or '0.0.0.0' should be used
        # inputs needs to be put into a separate function so it can run as a thread
        # Make sure to error handle later
        # serverIP: str = input("Type the Ip address of server: ")
        # serverPort: int = int(input("Type the Port number of server: "))


        #Delete this and uncomment above when done debugging
        serverIP = '127.0.0.1'
        serverPort = 12000

        try:
            peer_socket.connect((serverIP, serverPort))


            # Ask to connect to server and Receive message from server confirming connection
            serverResponse = clientSendRequest(peer_socket, CRequest.ConnectRequest)

            # For future error implementation
            print("1. Server Response: ", serverResponse)
            if serverResponse != SResponse.Connected.name:
                raise Exception("Something went wrong")


            # Sends a second request asking to add this user into the peer network
            serverResponse = clientSendRequest(peer_socket, CRequest.AddMe)

            print("2. Server Response: ", serverResponse)
            if serverResponse != SResponse.SendYourInfo.name:
                raise Exception("Something went wrong")

            # Sends the user's info to be added to peer list
            jsonUserPeer = json.dumps(userPeer.__dict__())
            peer_socket.send(jsonUserPeer.encode())

            # Receives an updated list of peer (including this user)
            serverResponse = peer_socket.recv(Classes.G_BUFFER).decode()

            #Debugging
            print("Server's peer list: ", serverResponse)

            # Turns the json LIST of peerList(the class) into separate peerList(object individually)
            # objects to be added to G_peerList(global peerlist that holds all the peers)
            # Yeah I know bad name deal with it or change all uses of it
            Classes.G_peerList = [Classes.peerList_from_dict(item) for item in json.loads(serverResponse)]

            print(Classes.G_peerList)

            serverResponse = clientSendRequest(peer_socket, CRequest.SendMyFiles)

            if serverResponse != SResponse.SendYourInfo.name:
                raise Exception("Something went wrong")

            fileJsonList = json.dumps([file.__dict__() for file in selfPeer.files])

            peer_socket.send(fileJsonList.encode())

        except (TimeoutError, InterruptedError) as err:
            print(err)
            print("Connection did not go through. Check the Client IP and Port")


def clientSendRequest(peer_socket: socket, cRequest: CRequest) -> str:
    """
    Sends a request to a server
    :param peer_socket:
    :param cRequest:
    :return: String representing Server response
    """
    sendStr = cRequest.name
    peer_socket.send(sendStr.encode())
    return peer_socket.recv(Classes.G_BUFFER).decode()


def get_user_input(input_queue):
    while True:
        synchronized_print("Enter command: ")
        user_input = input()
        input_queue.put(user_input)


def synchronized_print(message):
    """
    This is used mainly for debugging as of right now. Only main/runPeer should be printing to user so
    there is no need to use this in the main program
    :param message:
    :return:
    """
    with G_print_lock:
        print(message)


if __name__ == '__main__':
    main()
