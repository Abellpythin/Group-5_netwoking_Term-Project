import os
import socket
import json
import hashlib
from pathlib import Path

import Classes
from Classes import Peer
from Classes import FileForSync
from Classes import PeerList


def peerList_from_dict(peerAsDict):
    """
    Unpacks Json serialization of PeerList (not to be mistaken with G_PeerList)
    :param peerAsDict:
    :return:
    """
    return PeerList(**peerAsDict)


def sync_file_from_dict(syncFileAsDict):
    usersSubbed = [peerList_from_dict(u) for u in syncFileAsDict['usersSubbed']]
    return FileForSync(fileName=syncFileAsDict['fileName'], usersSubbed=usersSubbed)


def sendFileTo(sending_socket: socket, filePath: Path):
    """
    This method will send a file to some place
    :return:
    """

    fileSize: int = os.stat(str(filePath)).st_size

    # Debugging
    if fileSize == 0:
        raise Exception("fileSize is 0 check your stuff")

    sending_socket.send(f"{fileSize}".encode())

    with open(filePath, 'rb') as f:
        while True:
            data = f.read(Classes.G_BUFFER)
            if not data:
                break
            sending_socket.sendall(data)


def clientSendRequest(peer_socket: socket, cRequest: Classes.CRequest | int) -> str:
    """
    Sends a request to a server
    :param peer_socket:
    :param cRequest:
    :return: String representing Server response
    """
    sendStr: cRequest = cRequest.name
    peer_socket.send(sendStr.encode())
    return peer_socket.recv(Classes.G_BUFFER).decode()


def list_files_in_directory(directory_path) -> list[str]:
    """
    Lists file names in "Files" directory
    :param directory_path:
    :return:
    """
    try:
        files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
        return files
    except FileNotFoundError:
        print("list_files_in_directory SOMETHING UNHEARD OF HAPPENED!!!")


def setUserName() -> str:
    """
    Asks the user for a Username then returns said name
    :return: G_MY_USERNAME
    """
    G_MY_USERNAME: str
    while True:
        try:
            G_MY_USERNAME = input("Enter your username: ")
            if not G_MY_USERNAME:
                raise ValueError("Username cannot be empty.\n")
            if not G_MY_USERNAME[0].isalpha():
                raise ValueError("Username must start with a letter.\n")
            if not all(char.isalnum() or char == "_" for char in G_MY_USERNAME):
                raise ValueError("Username can only contain letters, numbers, and underscores.\n")
            if not 4 <= len(G_MY_USERNAME) <= 25:
                raise ValueError("Username must be between 4 and 25 characters long.\n")
            break
        except ValueError as e:
            print(f"Invalid username: {e}\n")

    return G_MY_USERNAME


def setUserIP() -> str:
    """
    Asks the for the user's IP address then returns it
    :return:
    """
    G_MY_IP: str
    while True:
        try:
            G_MY_IP = input("Enter your IP address (e.g., 127.0.0.1): ")
            parts = G_MY_IP.split(".")
            if len(parts) != 4:
                raise ValueError("IP address must have four parts separated by dots.\n")
            for part in parts:
                if not part.isdigit():
                    raise ValueError("Each part of the IP address must be a number.\n")
                if len(part) > 3:
                    raise ValueError("Each part of the IP address must have at most 3 digits.\n")
                num = int(part)
                if num < 0 or num > 255:
                    raise ValueError("Each part of the IP address must be between 0 and 255.\n")
            print(f"Valid IP address: {G_MY_IP}\n")
            break
        except ValueError as e:
            print(f"Invalid IP address: {e}\n")

    return G_MY_IP


def waitForSecondConnection() -> None:
    """
    This will wait for the user to confirm there is a second user that is online
    Automation of this function would require a callback from the runServer function.
    :return: void
    """
    print("If you're the first to connect, wait here")
    print("Press n to continue.")

    while True:
        start: str = input().lower()
        print()
        if(start == 'n'):
            break
        else:
            print("Please press n\n")
    return


def getServerAddress() -> tuple[str, int]:
    """
    Gets the server address from user input
    :return: (serverIp,serverPort) a tuple of the server's address
    """
    serverIp: str = ''
    while True:
        try:
            serverIp = input("Enter the peer's IP address (e.g., 127.0.0.1): ")
            print()
            parts = serverIp.split(".")
            if len(parts) != 4:
                raise ValueError("IP address must have four parts separated by dots.\n")
            for part in parts:
                if not part.isdigit():
                    raise ValueError("Each part of the IP address must be a number.\n")
                if len(part) > 3:
                    raise ValueError("Each part of the IP address must have at most 3 digits.\n")
                num = int(part)
                if num < 0 or num > 255:
                    raise ValueError("Each part of the IP address must be between 0 and 255.\n")
            print(f"Valid IP address: {serverIp}\n")
            break
        except ValueError as e:
            print(f"Invalid IP address: {e}\n")

    serverPort: int = 0
    while True:
        try:
            serverPort = int(input("Enter the Port Number of the peer (default is 59878): "))
            print()
            if (1024 <= serverPort <= 65535):
                break
            else:
                raise ValueError("Please Enter a port within the valid range: [1024, 65535]\n")
        except ValueError as e:
            print(f"Invalid Port number: {e}\n")

    return serverIp, serverPort


def userPressesPeriod():
    """
    Used when user is viewing a display and want
    :return:
    """
    while True:
        print("Press . to go back")
        userInput = input()
        if userInput == '.':
            break
        print()
    print()


def displayAvailablePeers() -> None:
    """
    Prints available peers to screen for the user
    :return:
    """
    counter = 1
    for peer in Classes.G_peerList:
        print(f"{counter}. {peer}")
        counter += 1
    userPressesPeriod()

    return


def displayAvailableFiles() -> None:
    """
    Displays the available files to download for the user
    :return:
    """
    counter: int = 1
    for file in Classes.G_FileList:
        print(f"|{counter}. file name: {file.fileName}\n"
              # Preferably we want files to have owners
              f"|   Owner: {file.userName if file.userName else "No owner"}\n"
              # Location should never be unknown. How else would you get the file
              f"|   Address: {file.addr if file.addr else "Location Unknown"}\n")
        counter += 1
    userPressesPeriod()


def handleSubscriptionToFile(userAsPeerList: PeerList) -> None:
    """
    Display Available Files to Subscribe to. Does not include files the user is already subbed to.
    :param userAsPeerList:
    :return:
    """
    counter: int = 1
    for file in Classes.g_FilesForSync:
        print(f"| {counter}. File name: {file.fileName}")
        print(f"|   Users Subscribed:")
        for user in file.usersSubbed:
            print(f"| - {user.username}")
        counter += 1

    userSyncFileChoice: FileForSync | None = None
    userChoice: int | str | None = None

    while True:
        userChoice = input("Select the number of the file you want to subscribe to or press . to go back: ")
        print()
        if userChoice.isdigit():
            userChoice = int(userChoice) - 1
            if 0 <= userChoice <= (len(Classes.g_FilesForSync) - 1):
                userSyncFileChoice = Classes.g_FilesForSync[userChoice]
                break
        elif userChoice == '.':
            return
        print("Please enter a valid input.")

    downloadSubscribedFile(userSyncFileChoice, userAsPeerList)
    print("File successfully downloaded")
    print("Stop the program to see your download\n")


def downloadSubscribedFile(syncFile: FileForSync, userAsPeerList: PeerList) -> None:
    selfPeer: Peer = Peer(userAsPeerList.addr)

    with selfPeer.createTCPSocket() as peer_socket:
        try:
            print(syncFile.usersSubbed[0].addr)
            # This is a list most likely due to json conversion
            peer_socket.connect(tuple(syncFile.usersSubbed[0].addr))
            peer_socket.settimeout(120)

            serverResponse: str = clientSendRequest(peer_socket, Classes.CRequest.SubscribeToFile)
            if serverResponse != Classes.SResponse.SendWantedFileName.name:
                raise Exception("Subscribing to file failed in downloadSubscribedFile() HelperFunctions.py")

            jsonSyncFile: str = json.dumps(syncFile.__dict__())
            peer_socket.send(jsonSyncFile.encode())

            fileSize: int = int(peer_socket.recv(Classes.G_BUFFER).decode())
            print(f"Received Sync File size{fileSize}\n")
            if not fileSize:
                raise FileNotFoundError("MakeSure File is openable")

            currentDirectory: Path = Path.cwd()
            directoryPath: Path = currentDirectory.parent / "FilesForSync" / syncFile.fileName

            os.makedirs(os.path.dirname(directoryPath), exist_ok=True)

            receivedSize: int = 0
            with open(directoryPath, 'wb') as f:
                while receivedSize < fileSize:
                    data = peer_socket.recv(Classes.G_BUFFER)
                    if not data:
                        break
                    f.write(data)
                    print(data)
                    receivedSize += len(data)

        except (TimeoutError, InterruptedError, ConnectionRefusedError) as err:
            print("handleSubscriptionToFile Failed")
            print(err)


def handleDownloadFileRequest(clientAddress: tuple[str, int], serverAddress: tuple[str, int]):
    """
    This functions allows the user to select what file they wish to download from the p2p network
    :param clientAddress:
    :param serverAddress:
    :return:
    """
    counter: int = 1
    for file in Classes.G_FileList:
        print(f"|{counter}. Name: {file.fileName}\n"
              # Preferably we want files to have owners
              f"|   Owner: {file.userName if file.userName else "No owner"}\n"
              # Location should never be unknown. How else would you get the file
              f"|   Address: {file.addr if file.addr else "Location Unknown"}\n")
        counter += 1
    print()

    userFileChoice: Classes.File | None = None
    userChoice: str | int = ""  # The number they picked
    while True:
        userChoice = input("Select the number of the file you want to download or press . to go back: ")
        print()
        if userChoice.isdigit():
            userChoice = int(userChoice) - 1
            if 0 <= userChoice <= (len(Classes.G_FileList) - 1):
                userFileChoice = Classes.G_FileList[userChoice]
                break
        elif userChoice == '.':
            return
        print("Please enter a valid input.\n")

    downloadFile(userFileChoice, clientAddress, serverAddress)
    print("File successfully downloaded")
    print("Stop the program to see your download\n")


def downloadFile(file: Classes.File, clientAddress: tuple[str, int], serverAddress: tuple[str, int]) -> None:
    """
    Ths method is responsible for sending and receiving the requested file for the user.

    :param file: The file object that the user wants to download which contains who has it
    :param clientAddress: The client's address to make a socket for
    :param serverAddress: This is for knowing where to send the request to
    :return:
    """
    selfPeer: Peer = Peer(address=clientAddress)

    with selfPeer.createTCPSocket() as peer_socket:
        try:
            #https://github.com/Microsoft/WSL/issues/2523
            peer_socket.connect(serverAddress)

            peer_socket.settimeout(120)

            serverResponse: str = clientSendRequest(peer_socket, Classes.CRequest.ConnectRequest)
            if serverResponse != Classes.SResponse.Connected.name:
                raise Exception("Something went wrong")

            serverResponse = clientSendRequest(peer_socket, Classes.CRequest.RequestFile)

            if serverResponse != Classes.SResponse.SendWantedFileName.name:
                raise Exception("Something went wrong")

            jsonUserPeer: str = json.dumps(file.__dict__())
            peer_socket.send(jsonUserPeer.encode())

            fileSize: int = int(peer_socket.recv(Classes.G_BUFFER).decode())
            print(f"received file size{fileSize}\n")
            if not fileSize:
                raise FileNotFoundError("This is BAD!!!")

            currentDirectory: Path = Path.cwd()
            directoryPath: Path = currentDirectory.parent / "Files" / file.fileName

            # Makes the directory if it doesn't exist
            os.makedirs(os.path.dirname(directoryPath), exist_ok=True)

            receivedSize: int = 0
            with open(directoryPath, 'wb') as f:
                while receivedSize < fileSize:
                    data = peer_socket.recv(Classes.G_BUFFER)
                    if not data:
                        break
                    f.write(data)
                    print(receivedSize, len(data))
                    receivedSize += len(data)
                    print(data)

            print("File successfully downloaded! You will see your download once you end the P2P session.")

        except (TimeoutError, InterruptedError, ConnectionRefusedError) as err:
            print(err)
            print("Connection did not go through. Check the Client IP and Port")
            peer_socket.close()


def setInitialFilesForSync(userAddr: tuple[str, int], userName: str) -> None:
    currentDirectory: Path = Path.cwd()
    parent_of_parent_directory: Path = currentDirectory.parent / "FilesForSync"
    fileNames: list[str] = list_files_in_directory(parent_of_parent_directory)

    fileForSyncObjList: list[FileForSync] = []
    thisUser: PeerList = PeerList(userAddr, userName)

    # Initially only this user is subscribed to the folder
    for fn in fileNames:
        Classes.g_FilesForSync.append(FileForSync(fn, [thisUser]))


def getFileHash(filePath: Path) -> str:
    hasher: hash = hashlib.md5()
    with open(filePath, 'rb') as file:
        while True:
            data = file.read(Classes.G_BUFFER)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()


def fileHasChanged(filePath: Path, previousHash: str) -> bool:
    """
    This method checks to see if the file has changed in the directory
    :param filePath:
    :param previousHash:
    :return:
    """
    currentHash: str = getFileHash(filePath)
    if currentHash != previousHash:
        return True
    return False


def sendFileSyncUpdate(fileName: str, filePath: Path, userAsPeerList: Peer, usersToBeSent: list[PeerList]):
    """
    Whenever a file in the FilesForSync directory is updated, this method will be called to send the update to the server

    :param fileName:
    :param filePath:
    :param userAsPeerList:
    :return:
    """

    # subbedUser: list[PeerList] = []
    # for syncFile in Classes.g_FilesForSync:
    #     if syncFile.fileName == fileName:
    #         subbedUser = syncFile.usersSubbed
    #
    # for user in subbedUser:
    #     if user.username == userAsPeerList.username:
    #         subbedUser.remove(user)

    if not usersToBeSent:
        print("sendFileSyncUpdate 437: No more users to send update to\n")
        return

    userToSendTo: tuple[str, int] = usersToBeSent[0].addr

    # Acquire Lock to ensure nothing else edits data while sending
    with Classes.G_SyncFileLock:
        with userAsPeerList.createTCPSocket() as peer_socket:
            connectionSuccess: bool = False

            while not connectionSuccess:
                try:
                    peer_socket.settimeout(15)
                    peer_socket.connect(userToSendTo)

                    serverResponse: str = clientSendRequest(peer_socket, Classes.CRequest.UpdateSyncFile)

                    if serverResponse != Classes.SResponse.SendYourInfo.name:
                        raise Exception("Main Line 275: Server is not ready to receive File Sync Update")

                    sendFileTo(peer_socket, filePath)

                    connectionSuccess = not connectionSuccess

                except (TimeoutError, InterruptedError, ConnectionRefusedError) as err:
                    print("File Sync Update connection did not go through. Check the Client IP and Port")
                    userSocket.close()
                    userSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    pass




