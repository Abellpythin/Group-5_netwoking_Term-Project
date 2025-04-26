# noinspection PyUnresolvedReferences
from Constants import (DOWNLOAD_FOLDER_TIMEOUT,
                       BUFFER_SIZE)
# noinspection PyUnresolvedReferences
from Helper_Functions import File_Functions as FF

import hashlib
import socket


def create_connection_socket() -> socket.socket:
    """
    This returns a socket for the user client to use
    :return:
    """
    user_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    return user_socket


def first_user_wait():
    """
    This method is called for the case of the first user connecting. It is required that they wait for the second
    user to connect to their server first before proceeding.
    :return:
    """
    print("If you are the first user, wait for the second user to connect...")

    while True:
        user_input: str = input("Press \".\" to proceed\n")
        print()
        if user_input == '.':
            return


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


def display_available_peers(peer_list):
    """
    Prints the available users to the screen
    :param peer_list:
    :return:
    """
    counter = 1
    for peer in peer_list:
        print(f"{counter}. {peer}")
        counter += 1
    userPressesPeriod()

    return


def display_and_download_file(file_list: list):
    """
    This will display the available files for the user to download and pass the user's selection to the download file
    function
    :param file_list:
    :return:
    """

    if not file_list:
        print("No files available to download.\n")

    counter: int = 1
    for file in file_list:
        print(f"|{counter}. Name: {file.filename}\n"
              f"|   Owner:{file.username if file.username else 'No Owner'}")

        counter += 1
    print()

    user_file_choice = None  # File object

    while True:
        user_choice: str | int = input("Select the number of the file you would like to download "
                                       "or press . to go back: ")
        print()
        if user_choice.isdigit():
            # Allow user_choice to be used as an index
            user_choice = int(user_choice) - 1
            if 0 <= user_choice < len(file_list):
                user_file_choice = file_list[user_choice]
                break
        elif user_choice == '.':
            return  # Return because the user wishes to go back to menu

        print("Please enter a valid input.\n")

    server_address = user_file_choice.addr

    FF.download_file(user_file_choice, server_address)
    print("File successfully downloaded!")


def display_and_subscribe_sync_file(available_sync_files, subscribed_available_files, user_as_peer):
    if not available_sync_files:
        print("There are no files available for subscription right now")
        userPressesPeriod()
        return

    for idx, file in enumerate(available_sync_files, start=1):
        print(f"|{idx}. File name: {file.filename}")
        print(f"|   Users Subscribed:")
        for user in file.users_subbed:
            print(f"| - {user.username}")

    user_sync_file_choice = None
    user_choice: int | str = ""

    while True:
        user_choice = input("Select the number of the file you want to subscribe to or press . to go back: ")
        print()
        if user_choice.isdigit():
            user_choice = int(user_choice) - 1
            if 0 <= user_choice < len(available_sync_files):
                user_sync_file_choice = available_sync_files[user_choice]
                break
        elif user_choice == '.':
            return
        print("Please enter a valid input.")

    """
    For future implementation, selecting a random user would be very nice
    """
    user_addr = user_sync_file_choice.users_subbed[0].addr
    FF.subscribe_to_file(user_sync_file_choice, user_as_peer, user_addr)
    available_sync_files.remove(user_sync_file_choice)
    subscribed_available_files.append(user_sync_file_choice)
    print("Sync File successfully downloaded!")


def get_sync_file_hash(file_path) -> str:
    hasher: hash = hashlib.md5()
    with open(file_path, 'rb') as file:
        while True:
            data = file.read(BUFFER_SIZE)
            if not data:
                break
            hasher.update(data)
    return hasher.hexdigest()


def sync_file_has_updated(file_path, previous_hash: str) -> bool:
    current_hash: str = get_sync_file_hash(file_path)
    return current_hash != previous_hash
