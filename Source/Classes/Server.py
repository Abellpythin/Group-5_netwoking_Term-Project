from __future__ import annotations

# noinspection PyUnresolvedReferences
from Classes.CRequest import CRequest
# noinspection PyUnresolvedReferences
from Classes.SRequest import SRequest

from .File import File
from .Peer import Peer
from .SyncFile import SyncFile

# This error is ok because we are running relative from the run.py folder

# noinspection PyUnresolvedReferences
from Constants import (FIXED_LENGTH_HEADER,
                       C_REQUEST_BYTE_LENGTH,
                       S_REQUEST_BYTE_LENGTH,
                       BUFFER_SIZE)

# noinspection PyUnresolvedReferences
from Helper_Functions import File_Functions as FF

import json
import socket
import threading
from pathlib import Path


class Server:
    """
    Only one server should be initialized per-peer.
    """

    def __init__(self, addr: tuple[str, int]):
        self.addr: tuple[str, int] = addr
        self.socket: socket.socket | None = None
        self.username: str | None = None
        self.initial_files: list[File] | None = []

    def create_TCP_socket(self) -> socket.socket:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(self.addr)
        return self.socket

    def client_request(self,
                       connection_socket: socket,
                       peer_list: list[Peer],
                       subscribed_sync_files: list[SyncFile],
                       available_sync_files: list[SyncFile],
                       available_files: list[File],
                       file_lock: threading.Lock,
                       sync_file_lock: threading.Lock,
                       peer_list_lock: threading.Lock,
                       ):

        # Make sure to have specified format for receiving and sending requests
        request_type_bytes: bytes = connection_socket.recv(C_REQUEST_BYTE_LENGTH)
        request_type: str = request_type_bytes.rstrip(b'\x00').decode('utf-8')

        with connection_socket:
            # The request the client made
            """
            DO NOT FORGET ".name" AT THE END
            """
            match request_type:
                case CRequest.AddMe.name:
                    with peer_list_lock:
                        self.send_Ok(connection_socket)
                        self.add_client(connection_socket, peer_list)

                case CRequest.UserJoined.name:
                    with peer_list_lock:
                        self.send_Ok(connection_socket)
                        self.receive_new_user(connection_socket, peer_list)

                case CRequest.RequestPeerList.name:
                    """
                    The peer list is a fixed size which can overflow and include the ok if fast enough
                    When sending objects or anything for that matter, we will send the ok first
                    """
                    with peer_list_lock:
                        self.send_Ok(connection_socket)
                        self.send_peer_list(connection_socket, peer_list)

                case CRequest.SendFiles.name:
                    with file_lock:
                        self.send_Ok(connection_socket)
                        """
                        Todo: Add attribute called initial files to check for the case of when the server starts
                        and a client requests a list of available files
                        The available files does not include files the user already has before starting the program
                        """
                        FF.receive_files(connection_socket, available_files)

                case CRequest.RequestFiles.name:
                    with file_lock:
                        self.send_Ok(connection_socket)
                        FF.send_file_list(connection_socket, available_files + self.initial_files)

                case CRequest.SendSyncFiles.name:
                    with sync_file_lock:
                        self.send_Ok(connection_socket)
                        FF.receive_sync_files(connection_socket, available_sync_files)
                        print(f"[DEBUG] available sync files in server match CRequest.SendSyncFiles: "
                              f"{available_sync_files}")

                case CRequest.RequestSyncFiles.name:
                    with sync_file_lock:
                        self.send_Ok(connection_socket)
                        # This sends all available SyncFiles to the client
                        FF.send_sync_file_list(connection_socket, available_sync_files + subscribed_sync_files)

                case CRequest.DownloadFile.name:
                    self.send_Ok(connection_socket)
                    self.send_file_for_download(connection_socket)

                case CRequest.SubscribeFile.name:
                    with sync_file_lock:
                        self.send_Ok(connection_socket)
                        self.add_user_send_sync_file(connection_socket, subscribed_sync_files)

                case CRequest.UserSubscribed.name:
                    with sync_file_lock:
                        self.send_Ok(connection_socket)
                        self.receive_new_subscribed_user(connection_socket, subscribed_sync_files)

                case CRequest.SyncFileUpdate.name:
                    with sync_file_lock:
                        self.send_Ok(connection_socket)
                        self.receive_sync_file_update(connection_socket, subscribed_sync_files)



    @classmethod
    def send_Ok(cls, connection_socket):
        response: str = SRequest.Ok.name
        response_bytes: bytes = response.encode('utf-8').ljust(S_REQUEST_BYTE_LENGTH, b'\x00')

        connection_socket.sendall(response_bytes)

    def add_client(self, connection_socket: socket, peer_list: list[Peer]):
        """
        This function receives a Peer Object from the connection_socket, adds modifies the given list by adding it
        :param connection_socket:
        :param peer_list:
        :return:
        """
        user_as_peer: Peer = FF.receive_Peer(connection_socket)

        #If the user is already in the network, move on. Think about the first two connections
        if user_as_peer in peer_list:
            return

        self.send_new_user_to_peers(user_as_peer, peer_list)

        peer_list.append(user_as_peer)

    @staticmethod
    def send_new_user_to_peers(new_user: Peer, peer_list: list[Peer]):
        """
        This method sends new users to peers and informs them using the CRequest of UserJoined that they only need to
        update their peer list
        :param new_user:
        :param peer_list:
        :return:
        """

        for peer in peer_list:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                try:
                    server_socket.settimeout(20)
                    server_socket.connect(peer.addr)

                    # automatically OK's
                    FF.send_peer_with_request(server_socket, new_user, CRequest.UserJoined)

                except TimeoutError:
                    pass
                except Exception as e:
                    print(f"[Error] Failed to send to {peer.addr}: {e}")

    @staticmethod
    def receive_new_user(connection_socket: socket.socket, peer_list: list[Peer]):
        """
        Todo: If the peer is already in the peer list, then what?
        :param connection_socket:
        :param peer_list:
        :return:
        """

        user_as_peer: Peer = FF.receive_Peer(connection_socket)

        # If the user is already in the network, move on.
        if user_as_peer in peer_list:
            return

        peer_list.append(user_as_peer)

    def send_peer_list(self, connection_socket: socket.socket, peer_list: list[Peer]):
        # Always make sure to handle empty case
        modified_peer_list: list[Peer] = list(peer_list)
        modified_peer_list.append(Peer(self.addr, self.username))

        """
        Checking for empty is unnecessary but just in case I forget how to in the future
        """
        json_peer_list: str = json.dumps([peer.__dict__() for peer in modified_peer_list])  # if peer_list else '[]'
        bytes_peer_list: bytes = json_peer_list.encode('utf-8')

        data_length: int = len(bytes_peer_list)
        connection_socket.sendall(data_length.to_bytes(FIXED_LENGTH_HEADER, 'big'))

        connection_socket.sendall(bytes_peer_list)

    def send_file_for_download(self, connection_socket: socket.socket):
        """
         1. Receive File Object (Send Ok after)
         2. Get Size of File with the File Object's name
         3. Send Length of file
         4. Send File
         :param connection_socket:
         :return:
         """
        requested_file: File = FF.receive_File(connection_socket)

        # [DEBUG] Send ok is working
        self.send_Ok(connection_socket)

        FF.send_full_file(connection_socket, requested_file)

    def add_user_send_sync_file(self, connection_socket: socket.socket, subscribed_sync_files: list[SyncFile]):
        """
        Todo: The server should then send this user to other peers to let them know an update occurred
        Todo: The subscribe list should be passed so this method can this user to subscribed users
        :param connection_socket:
        :param subscribed_sync_files:
        :return:
        """
        new_user: Peer = FF.receive_Peer(connection_socket)

        self.send_Ok(connection_socket)

        requested_sync_file: SyncFile = FF.receive_SyncFile(connection_socket)

        self.send_Ok(connection_socket)



        """
        Todo: In future implementation, this case should be handled
        """
        if requested_sync_file not in subscribed_sync_files:
            return

        FF.send_full_sync_file(connection_socket, requested_sync_file)

        # Add user to user list
        for sync_file in subscribed_sync_files:
            if sync_file == requested_sync_file:
                sync_file.users_subbed.append(new_user)
                break

        # Send this sync_file to users who are subbed to the file (excluding user who just joined)
        this_user_as_peer: Peer = Peer(self.addr, self.username)

        for index, peer in enumerate(requested_sync_file.users_subbed):
            if peer != new_user and peer != this_user_as_peer:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                    try:
                        server_socket.settimeout(20)
                        server_socket.connect(peer.addr)

                        FF.send_request(server_socket, CRequest.UserSubscribed)

                        FF.receive_Ok(connection_socket)

                        FF.send_Peer(connection_socket, new_user)

                        FF.receive_Ok(connection_socket)

                        FF.send_sync_file(connection_socket, requested_sync_file)

                    except TimeoutError:
                        pass
                    except Exception as e:
                        print(f"[Error] Failed to send to {peer.addr}: {e}")

    @staticmethod
    def receive_new_subscribed_user(connection_socket: socket.socket, subscribed_sync_files):
        subscribed_peer = FF.receive_Peer(connection_socket)

        Server.send_Ok(connection_socket)

        new_user_sync_file = FF.receive_SyncFile(connection_socket)

        for sync_file in subscribed_sync_files:
            if new_user_sync_file.filename == sync_file.filename:
                sync_file.users_subbed.append(subscribed_peer)

    @staticmethod
    def receive_sync_file_update(connection_socket, subscribed_sync_files):
        updated_sync_file: SyncFile = FF.receive_SyncFile(connection_socket)

        Server.send_Ok(connection_socket)

        FF.download_sync_file(connection_socket, updated_sync_file)

        Server.send_Ok(connection_socket)
