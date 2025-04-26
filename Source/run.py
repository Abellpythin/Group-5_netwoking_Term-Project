from __future__ import annotations

import time

from Classes import (File,
                     Peer,
                     Server,
                     SyncFile,
                     )
from Classes.CRequest import CRequest
from Constants import (C_REQUEST_BYTE_LENGTH,
                       FIXED_LENGTH_HEADER,
                       INITIAL_CONNECTION_TIMEOUT,
                       DISPLAYED_USER_OPTIONS,)

from Helper_Functions import (create_connection_socket,
                              display_available_peers,
                              first_user_wait,
                              File_Functions as FF,
                              display_and_download_file,
                              display_and_subscribe_sync_file,
                              get_sync_file_hash,
                              sync_file_has_updated)

import json
import os
from pathlib import Path
import socket
import threading

"""
These fields should be filled out before starting the program
"""
G_USER_IP: str = '10.42.27.127'
G_USER_PORT: int = 59878  # By default 59878
G_USER_USERNAME: str = 'MarshMellow' #MarshMellow. Testing to see if username is causing problems
G_MAX_CONNECTIONS: int = 10  # The amount of connections a server listens to at once

"""
The server you wish to initially connect to

2 people are required to be in contact in order to start the process. The two users should have each other's
IP address and decide who starts the server and who connects to who first.
"""
g_server_ip: str = '10.42.19.112'  # This should be set before every
g_server_port: int = 59878

"""
Do not touch from here
"""
g_endprogram: bool = False  # a variable indicating the user wants to end the program
g_user_save_sync_file: bool = False

# ----------------------

g_peer_list: list[Peer] = []  # A list of peers currently connected to the P2P network
PEER_LIST_LOCK: threading.Lock = threading.Lock()

g_available_files: list[File] = []  # A list of files available to download
FILE_LOCK: threading.Lock = threading.Lock()

# Files that are available to subscribe to. Does not include files currently subscribed to
g_available_sync_files: list[SyncFile] = []
SYNC_FILE_LOCK: threading.Lock = threading.Lock()

g_subscribed_sync_files: list[SyncFile] = []  # A list of SyncFiles currently subscribed to


def main():
    """
    This method will manage threading within the program
    :return:
    """
    server_thread: threading.Thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    initial_connection()

    file_sync_thread: threading.Thread() = threading.Thread(target=check_sync_file_updates, daemon=True)
    file_sync_thread.start()

    peer_thread: threading.Thread = threading.Thread(target=run_peer, daemon=True)
    peer_thread.start()

    peer_thread.join()
    file_sync_thread.join()
    server_thread.join()

    print("The program has closed")


def initial_connection():
    """
    This function is used to connect the user to a server to get:
        Peer list information
        Available Non-sync files
        Available Sync files

    The server handles one connection at a time so ensure tcp sockets are opened and closed accordingly
    :return:
    """
    first_user_wait()

    user_socket: socket.socket = create_connection_socket()

    with user_socket:

        # First connection for AddMe
        user_socket = create_connection_socket()
        with user_socket:
            try:
                user_socket.settimeout(15)
                user_socket.connect((g_server_ip, g_server_port))

                user_as_peer = Peer((G_USER_IP, G_USER_PORT), G_USER_USERNAME)
                # Automatically OK's
                FF.send_peer_with_request(user_socket, user_as_peer, CRequest.AddMe)
            except TimeoutError as err:
                print(err)
                print("Double check that you have the correct server address")
                print("Try pinging the address first using your terminal. "
                      "If the ping has dropped packets, you have a different problem.")
                return

        # Second connection for RequestPeerList
        user_socket = create_connection_socket()
        with user_socket:
            try:
                user_socket.settimeout(INITIAL_CONNECTION_TIMEOUT)
                user_socket.connect((g_server_ip, g_server_port))

                FF.send_request(user_socket, CRequest.RequestPeerList)

                # Receive peer list
                FF.receive_Ok(user_socket)
                length_bytes = user_socket.recv(FIXED_LENGTH_HEADER)

                received_data = FF.receive_data(user_socket, length_bytes)


                json_peer_list = received_data.decode('utf-8')
                dict_peer_list = json.loads(json_peer_list)
                peer_list = [Peer.from_dict(peer_dict) for peer_dict in dict_peer_list]

                with PEER_LIST_LOCK:
                    for peer in peer_list:
                        if peer != user_as_peer and peer not in g_peer_list:
                            g_peer_list.append(peer)

            except TimeoutError as err:
                print(err)
                return

        # Request list of available Files
        with FILE_LOCK:
            with create_connection_socket() as user_socket:
                try:
                    user_socket.settimeout(INITIAL_CONNECTION_TIMEOUT)
                    user_socket.connect(peer.addr)

                    FF.send_request(user_socket, CRequest.RequestFiles)

                    FF.receive_Ok(user_socket)

                    FF.receive_files(user_socket, g_available_files)

                except TimeoutError:
                    pass

        user_file_objects: list[File] = get_current_files()
        # Send user available files to all peers in the network
        with FILE_LOCK:
            # Send the file list to each peer in the network
            for peer in g_peer_list:
                with create_connection_socket() as user_socket:
                    try:
                        user_socket.settimeout(INITIAL_CONNECTION_TIMEOUT)
                        user_socket.connect(peer.addr)

                        FF.send_request(user_socket, CRequest.SendFiles)

                        FF.receive_Ok(user_socket)

                        FF.send_file_list(user_socket, user_file_objects)

                    except TimeoutError:
                        pass
                    except Exception as e:
                        print(f"[Error] Failed to send to {peer.addr}: {e}")

        with SYNC_FILE_LOCK:
            """
            In the initial two connections the server will not have updated its available sync files
            """
            for peer in g_peer_list:
                with create_connection_socket() as user_socket:
                    try:
                        user_socket.settimeout(INITIAL_CONNECTION_TIMEOUT)
                        user_socket.connect(peer.addr)

                        FF.send_request(user_socket, CRequest.RequestSyncFiles)

                        FF.receive_Ok(user_socket)

                        FF.receive_sync_files(user_socket, g_available_sync_files)

                    except TimeoutError:
                        pass
                    except Exception as e:
                        print(f"[Error] Failed to send to {peer.addr}: {e}")

        user_sync_file_objects: list[SyncFile] = get_current_sync_files()

        with SYNC_FILE_LOCK:
            for peer in g_peer_list:
                with create_connection_socket() as user_socket:
                    try:
                        user_socket.settimeout(INITIAL_CONNECTION_TIMEOUT)
                        user_socket.connect(peer.addr)

                        FF.send_request(user_socket, CRequest.SendSyncFiles)

                        FF.receive_Ok(user_socket)

                        # This should send list of SyncFile objects from SyncFile directory
                        FF.send_sync_file_list(user_socket, user_sync_file_objects)

                    except TimeoutError:
                        pass
                    except Exception as e:
                        print(f"[Error] Failed to send to {peer.addr}: {e}")


def run_peer():
    """
    The run_peer method displays the program's available options to the user.
    :return:
    """

    global g_endprogram
    global g_user_save_sync_file

    user_option: int | chr = None
    user_as_peer: Peer = Peer((G_USER_IP, G_USER_PORT), G_USER_USERNAME)

    print("--------------------------------------------------------")
    print("ALWAYS remember to open your files before trying to send them to ensure they exist!")
    print("Choose a number to select an option or press . to exit\n")

    while not g_endprogram:
        try:
            print("1. View Available Peers in Network\n"  # No direct functionality needed
                  "2. Download Available File\n"
                  "3. List files available for subscription (file syncing service)\n"
                  "4. Save Subscribed File (Click this if you've edited a file in FilesForSync)\n"
                  "Press . to exit")
            user_option = input()
            print()
            user_digit: bool = user_option.isdigit()

            if (not user_digit) and (not (user_option == '.')):
                raise ValueError("Please enter a valid input!\n")

            if user_option == '.':
                g_endprogram = True
                break

            user_option = int(user_option)

            match user_option:
                case 1:
                    display_available_peers(g_peer_list)
                case 2:
                    display_and_download_file(g_available_files)
                case 3:
                    display_and_subscribe_sync_file(g_available_sync_files, g_subscribed_sync_files, user_as_peer)
                case 4:
                    g_user_save_sync_file = True
                case 5:
                    pass
                case _:
                    raise ValueError("Please enter a valid input")

        except ValueError as e:
            print(e)

    print("The program has closed. Thanks for using\n")
    return


def run_server():
    """


    :return:
    """

    """
    This will automatically add the current SyncFiles to the user's subscribed_file_list when they 
    first start the program
    """

    sync_file_directory_path: Path = Path.cwd() / 'SyncFiles'
    current_sync_files: list[str] = FF.list_files_in_directory(sync_file_directory_path)
    user_as_peer: Peer = Peer((G_USER_IP, G_USER_PORT), G_USER_USERNAME)

    if current_sync_files:
        for sync_file_name in current_sync_files:
            g_subscribed_sync_files.append(SyncFile(sync_file_name, [user_as_peer]))

    # This adds the user's initial files to the initial file attribute in the server method
    user_server: Server = Server((G_USER_IP, G_USER_PORT))
    user_server.username = G_USER_USERNAME

    file_directory_path: Path = Path.cwd() / 'Files'
    current_files: list[str] = FF.list_files_in_directory(file_directory_path)

    if current_files:
        for file_name in current_files:
            user_server.initial_files.append(File(file_name, G_USER_USERNAME, user_server.addr))

    with user_server.create_TCP_socket() as listening_socket:
        listening_socket.listen(G_MAX_CONNECTIONS)
        connection_threads: list[threading.Thread] = []

        try:
            while True:
                conn, addr = listening_socket.accept()

                thread: threading.Thread = threading.Thread(target=user_server.client_request,
                                                            args=(conn,
                                                                  g_peer_list,
                                                                  g_subscribed_sync_files,
                                                                  g_available_sync_files,
                                                                  g_available_files,
                                                                  FILE_LOCK,
                                                                  SYNC_FILE_LOCK,
                                                                  PEER_LIST_LOCK,))
                connection_threads.append(thread)
                thread.start()

                # Doesn't happen instantly but g_peer_list DOES update
                # time.sleep(5)
                # with PEER_LIST_LOCK:
                #     print(g_peer_list)

                # Do I need a .join here

        except KeyboardInterrupt:
            print("\nShutting Down Server")
        finally:
            for thread in connection_threads:
                thread.join()

            listening_socket.close()
            print("Server socket closed")

    return


def check_sync_file_updates():
    """
    Todo:
    1. You need to add this user to the list of users subscribed
    2. Remove the subscribed file from avaialable files and add it to subscribed
    :return:
    """
    global g_user_save_sync_file

    user_as_peer: Peer = Peer((G_USER_IP,G_USER_PORT), G_USER_USERNAME)

    sync_file_hash: dict[str: str] = {}

    sync_files_dir: Path = Path.cwd() / "SyncFiles"

    sync_file_names: list[str] = FF.list_files_in_directory(sync_files_dir)

    for fn in sync_file_names:
        sync_file_hash[fn] = get_sync_file_hash(sync_files_dir / fn)

    while not g_endprogram:
        """
        This constantly checks to see what files are currently in the SyncFiles directory
        """
        # This prevents backups from being saved
        sync_file_names: list[str] = [fn for fn in FF.list_files_in_directory(sync_files_dir) if not fn.endswith('~')]

        # This checks to see if any files have been deleted and deletes them if so
        sync_file_names_to_remove: list[str] = []
        for fn in sync_file_hash.keys():
            if fn not in sync_file_names:
                sync_file_names_to_remove.append(fn)
        for name in sync_file_names_to_remove:
            sync_file_hash.pop(name)

        # This checks if a new file has been added and if so, add it to the hash
        for fn in sync_file_names:
            if fn not in sync_file_hash.keys():
                sync_file_hash[fn] = get_sync_file_hash(sync_files_dir / fn)

        if g_user_save_sync_file:
            for fn in sync_file_names:
                sync_file_path: Path = sync_files_dir / fn

                # This checks to see if the file has been modified
                modified: bool = sync_file_has_updated(sync_file_path, sync_file_hash[fn])
                if modified:
                    # Update previous hash to current
                    sync_file_hash[fn] = get_sync_file_hash(sync_file_path)

                    subbed_users: list[Peer] = []
                    this_sync_file: SyncFile = None

                    for sync_file in g_subscribed_sync_files:
                        if sync_file.filename == fn:
                            subbed_users = sync_file.users_subbed
                            this_sync_file = sync_file
                            break
                    subbed_users = [user for user in subbed_users if user != user_as_peer]

                    if subbed_users:
                        with SYNC_FILE_LOCK:
                            FF.send_sync_file_update(this_sync_file, subbed_users)
                    else:
                        print("No user are subscribed to this file")

        g_user_save_sync_file = False
        time.sleep(0.5)


def get_current_files() -> list[File] | None:
    """

    :return:
        A list of File objects that contain the names of files in the user's file directory
    """
    current_directory: Path = Path.cwd()
    directory_path: Path = current_directory / "Files"

    file_names: list[str] = [f.name for f in directory_path.iterdir() if f.is_file() if not f.name.endswith('~')]
    if not file_names:
        return

    user_file_objects: list[File] = []
    for fn in file_names:
        user_file_objects.append(File(fn, G_USER_USERNAME, (G_USER_IP, G_USER_PORT)))

    return user_file_objects


def get_current_sync_files() -> list[SyncFile] | None:
    """

    :return:
        A list of SyncFile objects that contain the names of files available for sync in the user's SyncFiles directory
    """
    current_directory: Path = Path.cwd()
    directory_path: Path = current_directory / "SyncFiles"

    file_names: list[str] = [f.name for f in directory_path.iterdir() if f.is_file() if not f.name.endswith('~')]
    if not file_names:
        return

    user_sync_file_objects: list[SyncFile] = []
    user_addr: tuple[str, int] = (G_USER_IP, G_USER_PORT)
    for fn in file_names:
        user_sync_file_objects.append(SyncFile(fn, [Peer(user_addr, G_USER_USERNAME)]))

    return user_sync_file_objects


if __name__ == '__main__':
    main()
