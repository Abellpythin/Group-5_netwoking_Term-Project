from __future__ import annotations
import json
import queue
import threading
import socket  # For type annotation
import time # for debugging

import Classes  # Classes.G_peerList
from Classes import Peer
from Classes import Server
from Classes import CRequest
from Classes import SResponse
from Classes import PeerList

import HelperFunctions as hf

#!!!!!! Use 127.0.0.1 for debugging NOT 0.0.0.0


# Use your systems local IP address (IPV4 when typing ipconfig pn windows, env0 on mac)


# G for global variable
# The port number is preemptively defined so no need to ask user
G_MY_PORT: int = 59878
G_MY_IP: str = ''
G_MY_USERNAME: str | None = "Debugger"
G_MAX_CONNECTIONS: int = 5

g_serverIp: str | None
g_serverPort: int | None


# When the user wants to end the program this variable changes to True and
# runClient, runServer, and Main terminate
G_ENDPROGRAM: bool = False

# Queue necessary for I/O operations
G_input_queue: queue.Queue = queue.Queue()

# Used to synchronize print statements among threads. Used for debugging
G_print_lock: threading.Lock = threading.Lock()

# After running any socket, wait at least 30 seconds or else you'll get this error
# OSError: [Errno 48] Address already in use
def main():
    """
    The main method will be used for managing threads and initializing the initial connection to the 
    peer network
    """
    global G_MY_USERNAME
    global G_MY_IP

    print("Welcome to our P2P Network", end='\n\n')

    # ------------------------------------------------------------------------------------------------------------
    # Uncomment when done debugging
    G_MY_USERNAME = hf.setUserName()
    G_MY_IP = hf.setUserIP()
    print(G_MY_IP)
    print(G_MY_USERNAME)
    # ------------------------------------------------------------------------------------------------------------

    # IMPORTANT
    # FROM THIS POINT ON ANY I/O OPERATIONS (input, open, with, etc) NEEDS TO BE IN SEPARATE THREAD
    # Make sure when creating "Thread" not to include (). You are not calling the method
    serverThread: threading.Thread = threading.Thread(target=runServer, daemon=True)
    serverThread.start()

    initialConnect()

    peerThread: threading.Thread = threading.Thread(target=runPeer, daemon=True)
    peerThread.start()

    # Main will not conclude until both threads join so no need for infinite while loop
    serverThread.join()
    peerThread.join()

    print("Complete!")


# This will be the only function besides main that interacts with the user
def runPeer():
    """
    The runPeer method displays the program's available options to the user.
    1. View Available Peers in Network
    2. View Available Files in Network
    3. Download Available Files
    4. Refresh PeerList
    """
    global G_ENDPROGRAM

    #Debugging
    time.sleep(0.5)

    userOption: int | chr

    print("---------------")
    print("ALWAYS remember to open your files before trying to send them to ensure they exist!")
    print("Choose a number to select an option or press . to exit\n")
    while not G_ENDPROGRAM:
        try:
            print("1. View Available Peers in Network\n"  # No direct functionality needed
                  "2. View Available Files in Network\n"  # From 2. The user can select and download this file
                  "3. Download Available File\n"
                  "4. Refresh PeerList\n"
                  "Press . to exit")
            userOption = input()
            print()
            userDigit: bool = userOption.isdigit()

            if (not userDigit) and (not (userOption == '.')):
                raise ValueError("Please enter a valid input!\n")

            if userOption == '.':
                G_ENDPROGRAM = True
                break

            userOption = int(userOption)
            # This value (4) will change as options get implemented
            if 1 <= userOption <= 4:
                match userOption:
                    case 1:
                        hf.displayAvailablePeers()
                    case 2:
                        hf.displayAvailableFiles()
                    case 3:
                        hf.handleDownloadFileRequest((G_MY_IP, G_MY_PORT),
                                                     (g_serverIp, g_serverPort))
                    case 4:
                        pass
                    case _:
                        raise ValueError("runPeer match statement: Something seriously went wrong to get here")
            else:
                raise ValueError("Please select from the displayed options.\n")
        except ValueError as e:
            print(e)
        finally:
            print("---------------------")

    print("Program wrapped up. Thanks for using!\n")
    return


def runServer():
    """
    The server is run for the entire duration of the program.
    It only ends when the user decides to end the program.
    There should be NO IO OPERATIONS IN THE SERVER
    :return:
    """
    global G_ENDPROGRAM
    myServer: Server = Server((G_MY_IP, G_MY_PORT))
    myServer.userName = G_MY_USERNAME  # Needed to send this server's info to peer

    with myServer.createTCPSocket() as listening_socket:
        # Continuously listens so no need to put in while loop
        listening_socket.listen(G_MAX_CONNECTIONS)
        threads: list[threading.Thread] = []

        while not G_ENDPROGRAM:
            # Todo: What happens when user ends program while server listens?
            conn, addr = listening_socket.accept()  # Accepts 1 connection at a time

            # Optional settimeout so clients can't linger for too long
            # conn.settimeout(60)

            #IMPORTANT You will feel suicidal if you don't heed this warning
            # WHEN MAKING A THREAD THAT HAS ARGUMENTS
            # ENSURE THAT IT HAS A COMMA AT THE END OF THE TUPLE
            # EX: (number, str, letter,) <-----
            # Notice the comma at the end. This tells the method that it is an iterable
            thread: threading.Thread = threading.Thread(target=myServer.clientRequest, args=(conn,))
            threads.append(thread)
            thread.start()
            # Create method to send in a thread: No clue what this means future me
            # Remember you put a break here earlier which meant no continuous listening

        for thread in threads:
            thread.join()


def initialConnect():
    """
    The initial Connection will connect to a peer currently online. This method handles updating the global peer list
    and the global file list
    :return:
    """
    global g_serverIp
    global g_serverPort

    hf.waitForSecondConnection()

    # Create Peer class for user
    selfPeer: Peer = Peer(address=(G_MY_IP, G_MY_PORT))
    selfPeer.initializeFiles()

    userPeer: PeerList = PeerList((G_MY_IP, G_MY_PORT), G_MY_USERNAME)

    with selfPeer.createTCPSocket() as peer_socket:

        connectionSuccess: bool = False

        while not connectionSuccess:
            g_serverIp, g_serverPort = hf.getServerAddress()

            try:
                # Timeout of 15 seconds
                peer_socket.settimeout(15)
                peer_socket.connect((g_serverIp, g_serverPort))

                # Ask to connect to server and Receive message from server confirming connection
                serverResponse: str = hf.clientSendRequest(peer_socket, CRequest.ConnectRequest)

                # For future error implementation
                if serverResponse != SResponse.Connected.name:
                    raise Exception("Something went wrong")

                # Sends a second request asking to add this user into the peer network
                serverResponse = hf.clientSendRequest(peer_socket, CRequest.AddMe)

                if serverResponse != SResponse.SendYourInfo.name:
                    raise Exception("Something went wrong")

                # Sends the user's info to be added to peer list
                jsonUserPeer: str = json.dumps(userPeer.__dict__())
                peer_socket.send(jsonUserPeer.encode())

                # Receives an updated list of peer (including this user)
                serverResponse = peer_socket.recv(Classes.G_BUFFER).decode()

                print(f"PeerList{serverResponse}")

                # Turns the json LIST of peerList(the class) into separate peerList(object individually)
                # objects to be added to G_peerList(global peerlist that holds all the peers)
                # Yeah I know bad name deal with it or change all uses of it
                Classes.G_peerList = [Classes.peerList_from_dict(item) for item in json.loads(serverResponse)]

                serverResponse = hf.clientSendRequest(peer_socket, CRequest.SendMyFiles)

                if serverResponse != SResponse.SendYourInfo.name:
                    raise Exception("Something went wrong")

                fileJsonList: str = json.dumps([file.__dict__() for file in selfPeer.files])

                peer_socket.send(fileJsonList.encode())

                # Receive file list
                print("Main 275: About to send file list request")
                fileObjectJsonList = hf.clientSendRequest(peer_socket, CRequest.RequestFileList)

                Classes.G_FileList = [Classes.file_from_dict(file) for file in json.loads(fileObjectJsonList)]
                print(f"Main 279: File list is {Classes.G_FileList}")

                connectionSuccess = not connectionSuccess

            except (TimeoutError, InterruptedError, ConnectionRefusedError) as err:
                print("Connection did not go through. Check the Client IP and Port")
                peer_socket.close()
                peer_socket = selfPeer.createTCPSocket()


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

# git push origin HEAD is goated when working with branches with comically large names
