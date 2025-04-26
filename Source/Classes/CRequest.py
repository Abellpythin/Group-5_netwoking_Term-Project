from enum import Enum


class CRequest(Enum):
    """
    A class representing the type of requests a client can send

    AddMe: The Client asks the server to add them to the network. The server will then add them to their list of peers
           then send this client to others in the network
           Todo: A server needs a specific request from other servers indicating that a new client has been added and
                 to ONLY receive the data (and not send it to other clients as one server is already doing that)

    RequestPeerList: The client asks the server to send the list of peers in the P2P network

    UserJoined: The client (which is actually a request from another peer server) sends a message indicating that
                another peer has joined the server

    SendFiles: The client is requesting to send files to this server

    RequestFiles: The client is requesting for a list of available files in the network.

    SendSyncFiles: The client is requesting to send SyncFiles to this server

    RequestSyncFiles: The client is requesting for a list of available SyncFiles

    DownloadFile: The client is requesting to download the file from the server

    SubscribeFile: The client wants to subscribe to a file available in the network

    UserSubscribed: A server has received a client who has subscribed to a syncFile, so this server is now sending an
                    updated syncFile object for users also subscribed to the network

    SyncFileUpdate: A user has updated a sync file and is sending the update to this server
    """
    AddMe = 1
    RequestPeerList = 2
    UserJoined = 3
    SendFiles = 4
    RequestFiles = 5
    SendSyncFiles = 6
    RequestSyncFiles = 7
    DownloadFile = 8
    SubscribeFile = 9
    UserSubscribed = 10
    SyncFileUpdate = 11


