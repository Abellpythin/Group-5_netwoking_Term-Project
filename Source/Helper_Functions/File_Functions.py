import os

# noinspection PyUnresolvedReferences
from Constants import (FIXED_LENGTH_HEADER,
                       BUFFER_SIZE,
                       C_REQUEST_BYTE_LENGTH,
                       S_REQUEST_BYTE_LENGTH,
                       DOWNLOAD_FOLDER_TIMEOUT)

import json

# noinspection PyUnresolvedReferences
from Classes import (Peer,
                     File,
                     SyncFile)
# noinspection PyUnresolvedReferences
from Classes.CRequest import CRequest
# Import these separately to avoid compiler error
# noinspection PyUnresolvedReferences
from Classes.SRequest import SRequest
# noinspection PyUnresolvedReferences
from Classes.SyncFile import SyncFile

from pathlib import Path
import socket


def receive_data(connection_socket, length_bytes):
    """
    Receives data and returns it how it is.
    :param connection_socket:
    :param length_bytes:
    :return:
    """
    data_length: int = int.from_bytes(length_bytes, 'big')

    received_data: bytearray = bytearray()
    while len(received_data) < data_length:
        chunk = connection_socket.recv(BUFFER_SIZE)
        if not chunk:
            raise ConnectionError("Connection closed before full data received")
        received_data.extend(chunk)

    return received_data


def receive_Ok(connection_socket):
    response_bytes: bytes = connection_socket.recv(S_REQUEST_BYTE_LENGTH)
    response: str = response_bytes.rstrip(b'\x00').decode('utf-8')

    if response != SRequest.Ok.name:
        raise ValueError(f"Expected Ok, got: {response}")

    return response


def send_request(connection_socket, request_type):
    request_type_bytes: bytes = request_type.name.encode('utf-8').ljust(C_REQUEST_BYTE_LENGTH, b'\x00')

    connection_socket.sendall(request_type_bytes)


def receive_Peer(connection_socket):
    """
    This method receives a Peer object and returns the object
    :param connection_socket:
    :return:
    """
    # Receive data length
    length_bytes: bytes = connection_socket.recv(FIXED_LENGTH_HEADER)

    received_data = receive_data(connection_socket, length_bytes)

    json_user_as_peer: str = received_data.decode('utf-8')
    if not json_user_as_peer:
        return

    dict_user = json.loads(json_user_as_peer)

    client_user_as_peer = Peer.from_dict(dict_user)

    return client_user_as_peer


def send_Peer(connection_socket: socket.socket, user_peer):
    json_peer: str = json.dumps(user_peer.__dict__())
    bytes_peer: bytes = json_peer.encode('utf-8')

    data_length: int = len(bytes_peer)
    connection_socket.sendall(data_length.to_bytes(FIXED_LENGTH_HEADER, 'big'))

    connection_socket.sendall(bytes_peer)


def receive_File(connection_socket):
    """
    This method receives a File object then sends it back
    :param connection_socket:
    :return:
    """
    length_bytes: bytes = connection_socket.recv(FIXED_LENGTH_HEADER)

    received_data = receive_data(connection_socket, length_bytes)

    json_file: str = received_data.decode('utf-8')
    if not json_file:
        return

    dict_file = json.loads(json_file)
    client_file = File.from_dict(dict_file)

    return client_file


def send_file(connection_socket, file_object):
    json_file: str = json.dumps(file_object.__dict__())
    bytes_file: bytes = json_file.encode('utf-8')

    data_length: int = len(bytes_file)
    connection_socket.sendall(data_length.to_bytes(FIXED_LENGTH_HEADER, 'big'))

    connection_socket.sendall(bytes_file)


def send_file_list(connection_socket, user_file_objects):
    json_file_list: str = json.dumps([file.__dict__() for file in user_file_objects])
    bytes_file_list: bytes = json_file_list.encode('utf-8')

    data_length: int = len(bytes_file_list)
    connection_socket.sendall(data_length.to_bytes(FIXED_LENGTH_HEADER, 'big'))

    connection_socket.sendall(bytes_file_list)


def send_sync_file_list(connection_socket, user_sync_file_objects):
    json_sync_file_list: str = json.dumps([sync_file.__dict__() for sync_file in user_sync_file_objects])
    bytes_sync_file_list: bytes = json_sync_file_list.encode('utf-8')

    data_length: int = len(bytes_sync_file_list)
    connection_socket.sendall(data_length.to_bytes(FIXED_LENGTH_HEADER, 'big'))

    connection_socket.sendall(bytes_sync_file_list)


def send_sync_file(connection_socket: socket.socket, sync_file_object):
    json_sync_file: str = json.dumps(sync_file_object.__dict__())
    bytes_sync_file: bytes = json_sync_file.encode('utf-8')

    data_length: int = len(bytes_sync_file)
    connection_socket.sendall(data_length.to_bytes(FIXED_LENGTH_HEADER, 'big'))

    connection_socket.sendall(bytes_sync_file)


def receive_SyncFile(connection_socket: socket.socket):
    length_bytes: bytes = connection_socket.recv(FIXED_LENGTH_HEADER)

    received_data = receive_data(connection_socket, length_bytes)

    json_sync_file: str = received_data.decode('utf-8')
    if not json_sync_file:
        return

    dict_sync_file = json.loads(json_sync_file)
    client_sync_file = SyncFile.from_dict(dict_sync_file)

    return client_sync_file


def send_peer_with_request(connection_socket, user, request_type):
    """
    This method sends a peer using a specified format

    Todo: This is a method that can and should be abstracted down but was made early. There is no need to do this but
          if ever continuing in the future, it would be nice to do.
    :param connection_socket:
    :param user:
    :param request_type:
    :return:
    """
    request_type_bytes: bytes = request_type.name.encode('utf-8').ljust(C_REQUEST_BYTE_LENGTH, b'\x00')

    connection_socket.sendall(request_type_bytes)

    receive_Ok(connection_socket)

    json_user: str = json.dumps(user.__dict__())
    bytes_user: bytes = json_user.encode('utf-8')

    # Send the data length to socket using big endian
    data_length: int = len(bytes_user)
    connection_socket.sendall(data_length.to_bytes(FIXED_LENGTH_HEADER, 'big'))

    # Send the actual data of the user
    connection_socket.sendall(bytes_user)


def list_files_in_directory(directory_path):
    """
    Returns a list of names for files in this directory_path
    :param directory_path:
    :return:
    """
    try:
        # files = [f for f in os.listdir(directory_path) if os.path.isfile(os.path.join(directory_path, f))]
        files = [f.name for f in directory_path.iterdir() if f.is_file()]
        return files
    except FileNotFoundError:
        print("File not found")


def receive_files(connection_socket, file_list):
    length_bytes: bytes = connection_socket.recv(FIXED_LENGTH_HEADER)

    received_data = receive_data(connection_socket, length_bytes)

    json_file_list: str = received_data.decode('utf-8')
    if not json_file_list or json_file_list == '[]':
        return

    dict_file_list = json.loads(json_file_list)
    client_file_list = [File.from_dict(file_dict) for file_dict in dict_file_list]

    file_directory_path: Path = Path.cwd() / 'Files'
    current_files: list[str] = list_files_in_directory(file_directory_path)

    """
    This makes a new list that...
    1. The file is NOT in the current available files for download (sync_file_list)
    2. AND the file is NOT already downloaded (not in current_files)
    """

    new_files = [
        f for f in client_file_list
        if not any(sf.filename == f.filename for sf in file_list)
        and f.filename not in current_files
    ]

    file_list.extend(new_files)


def receive_sync_files(connection_socket, sync_file_list):
    """
    THis receives a LIST of sync files
    :param connection_socket:
    :param sync_file_list:
    :return:
    """
    length_bytes: bytes = connection_socket.recv(FIXED_LENGTH_HEADER)

    received_data = receive_data(connection_socket, length_bytes)

    json_sync_file_list: str = received_data.decode('utf-8')
    if not json_sync_file_list or json_sync_file_list == '[]':
        print("An empty list of sync files were sent")
        return

    dict_sync_file_list = json.loads(json_sync_file_list)
    client_sync_file_list = [SyncFile.from_dict(sync_file) for sync_file in dict_sync_file_list]

    sync_file_directory_path: Path = Path.cwd() / 'SyncFiles'
    current_files: list[str] = list_files_in_directory(sync_file_directory_path)

    new_files = [
        f for f in client_sync_file_list
        if not any(sf.filename == f.filename for sf in sync_file_list)
        and f.filename not in current_files
    ]

    sync_file_list.extend(new_files)


def download_file(file, server_address: tuple[str, int]):
    user_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with user_socket:
        try:
            user_socket.settimeout(DOWNLOAD_FOLDER_TIMEOUT)
            user_socket.connect(server_address)

            # Send a request to download file from server
            send_request(user_socket, CRequest.DownloadFile)

            receive_Ok(user_socket)

            # Send file object to server so server knows what the name of it is
            send_file(user_socket, file)

            # [DEBUG] Receive ok is working
            receive_Ok(user_socket)

            length_bytes: bytes = user_socket.recv(FIXED_LENGTH_HEADER)

            file_length: int = int.from_bytes(length_bytes, 'big')

            file_path: Path = Path.cwd() / "Files" / file.filename

            received_size: int = 0
            with open(file_path, 'wb') as f:
                while received_size < file_length:
                    data = user_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    f.write(data)
                    received_size += len(data)

        except TimeoutError as e:
            print(e)
            print(f"The file download was not able to go through in the specified time: "
                  f"{DOWNLOAD_FOLDER_TIMEOUT} seconds")


def send_full_file(connection_socket: socket, file):
    file_path: Path = Path.cwd() / "Files" / file.filename

    # Get the size of the file
    file_size: int = os.stat(str(file_path)).st_size

    connection_socket.sendall(file_size.to_bytes(FIXED_LENGTH_HEADER, 'big'))

    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            connection_socket.sendall(data)


def send_full_sync_file(connection_socket: socket, sync_file):
    """
    This functions sends a sync function to a client
    :param connection_socket:
    :param sync_file:
    :return:
    """
    file_path: Path = Path.cwd() / "SyncFiles" / sync_file.filename

    file_size: int = os.stat(str(file_path)).st_size

    connection_socket.sendall(file_size.to_bytes(FIXED_LENGTH_HEADER, 'big'))

    with open(file_path, 'rb') as f:
        while True:
            data = f.read(BUFFER_SIZE)
            if not data:
                break
            connection_socket.sendall(data)


def subscribe_to_file(sync_file, user_as_peer, server_address: tuple[str, int]):
    """
    This method:
    1. Sends the user to be added to subscription
    2. Sends the wanted file
    3. Receives the wanted file
    :param sync_file:
    :param user_as_peer:
    :param server_address:
    :return:
    """
    user_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with user_socket:
        try:
            user_socket.settimeout(DOWNLOAD_FOLDER_TIMEOUT)
            user_socket.connect(server_address)

            send_request(user_socket, CRequest.SubscribeFile)

            receive_Ok(user_socket)

            send_Peer(user_socket, user_as_peer)

            receive_Ok(user_socket)

            send_sync_file(user_socket, sync_file)

            receive_Ok(user_socket)

            length_bytes: bytes = user_socket.recv(FIXED_LENGTH_HEADER)

            file_length: int = int.from_bytes(length_bytes, 'big')

            file_path: Path = Path.cwd() / "SyncFiles" / sync_file.filename

            received_size: int = 0
            with open(file_path, 'wb') as f:
                while received_size < file_length:
                    data = user_socket.recv(BUFFER_SIZE)
                    if not data:
                        break
                    f.write(data)
                    received_size += len(data)

        except TimeoutError as e:
            print(e)
            print(f"The file download was not able to go through in the specified time: "
                  f"{DOWNLOAD_FOLDER_TIMEOUT} seconds")


def download_sync_file(connection_socket, sync_file):
    length_bytes: bytes = connection_socket.recv(FIXED_LENGTH_HEADER)

    file_length: int = int.from_bytes(length_bytes, 'big')

    file_path: Path = Path.cwd() / "SyncFiles" / sync_file.filename

    received_size: int = 0
    with open(file_path, 'wb') as f:
        while received_size < file_length:
            data = connection_socket.recv(BUFFER_SIZE)
            if not data:
                break
            f.write(data)
            received_size += len(data)


def send_sync_file_update(sync_file, users_to_send_update: list):
    """
    This method is called whenever a user saves their changes to a syncFile
    :param sync_file:
    :param users_to_send_update:
    :return:
    """
    if not users_to_send_update:
        print("There are no users to send this update to")
        return

    for user in users_to_send_update:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as user_socket:
            try:
                user_socket.settimeout(15)
                user_socket.connect(user.addr)

                send_request(user_socket, CRequest.SyncFileUpdate)

                receive_Ok(user_socket)

                send_sync_file(user_socket, sync_file)

                receive_Ok(user_socket)

                send_full_sync_file(user_socket, sync_file)

                receive_Ok(user_socket)


            except TimeoutError as e:
                print("File Sync could not go through")
