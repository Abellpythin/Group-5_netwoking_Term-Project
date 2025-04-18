import os

import Classes

"""
Someday it will be best to move all global functions into here.
Today's that day
"""


def list_files_in_directory(directory_path) -> list[str]:
    try:
        files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
        return files
    except FileNotFoundError:
        print("Fail")


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
    serverIp: str
    while True:
        try:
            serverIp = input("Enter the peer's IP address (e.g., 127.0.0.1): ")
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

    serverPort: int
    while True:
        try:
            serverPort = int(input("Enter the Port Number of the peer (default is 12000): "))
            if (1024 <= serverPort <= 65535):
                break
            else:
                raise ValueError("Please Enter a port within the valid range: [1024, 65535]\n")
        except ValueError as e:
            print(f"Invalid Port number: {e}\n")

    return (serverIp, serverPort)


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
    counter = 1
    for peer in Classes.G_peerList:
        print(f"{counter}. {peer}")
        counter += 1
    userPressesPeriod()

    return

def displayAvailableFiles() -> None:
    counter = 1
    for file in Classes.G_FileList:
        print(f"| Name: {file.fileName}\n"
              # Preferably we want files to have owners
              f"| Owner: {file.userName if file.userName else "No owner"}\n"
              # Location should never be unknown. How else would you get the file
              f"| Address: {file.addr if file.addr else "Location Unknown"}\n")
        counter += 1
    userPressesPeriod()

    return
