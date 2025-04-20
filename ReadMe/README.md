# Group-5_netwoking_Term-Project

python version 3.12

# Important to know 
> When downloading a file, it won't show in the until AFTER you stop
> the IDE until after you stop program. You should see it in the files
> though.

# If using windows, everything will give you problems
> Here's a checklist to ensure your windows machine can use our p2p
> network
> 1. Go to command and try pinging the other computer
> on a local network. Make sure to use the local IP address
> 2. Make sure your windows machine identifies the network as private
> and ENABLE FILE AND PRINTER SHARING
> 3. If File and Printer sharing was off and you turned it off,
> make sure to restart your device. 

# Steps to Running P2P Network
> 1. Go to terminal and type "ipconfig getifaddr en0" (or for windows
> "ipconfig" and find the IPv4 Address). This will be your IP address.
> 2. Next make sure you have another peer's IP address and port
> number.
> 3. Any files you want available for download, put in the Files folder 
>of your IDE.
> 4. Follow the on-screen instructions
> 5. If you encounter connection problems try using terminal to ping to
> other computer to ensure it's an application problem.

# For A-lee-a when you do documentation
> In case I forget, I'll list the major processes here and try to break
> down everything as simple as possible so presenting is easy. There is 
> no particular order of any of these, it's just stuff that should be 
> covered in slides or diagrams
> - (Clarification) Any peer currently in the P2P network ALWAYS has
> its server on (runServer). The client side only connects to a server
> when a user makes an explicit request for server info (file downloads,
> peer list requests, synchronization, etc...)
> - At least 2 users need to be online in order for the P2P network to 
> function. The first user needs to start their server THEN WAIT for
> the second client to connect their server. Only then should the first
> client attempt to connect to the second client
> - Every file is sent through bits
> - The user has these available options
> - 1. View Available Peers in Network
>   2. View Available Files in Network
>   3. Download Available Files


## Notes for Brejon 
> When the first client starts the P2P network, they are required to only
> run the server initially. This means that they have no files and no
> peers in their peerlist. Now when the second client enters and connects
> to the first client, they receive a list of peers containing nothing.
> Fix this by (from the perspective of the first peer) initializing a new 
> PeerList object and adding it to the peer listif it is not currently in 
> the PeerList.

### Computer Networking Term Project 
![img.png](img.png)

 Main.py FSM Diagram:
The diagram represents a Finite State Machine 
(FSM) for the main.py module.
States include:
Start --> User input --> Pinpoint -->
--> Server listening --> Peer listening -->
--> Connect --> Server running --> End

Threads synchronized

Activity Diagram: Main.py Module:

The activity diagram describes 
the flow of the program:

Start the program.
prompt the user to validate an utterance.
Prompt and validate the IP address.
Start the server thread.
Perform final conversion.
Start the peer thread.
Wait for threads to join (server and peer threads).
Program completion.

![img_2.png](img_2.png)

The provided diagrams and code defines 
three classes—Peer, Server, and File—for 
a peer-to-peer file-sharing system. 
The Peer class represents a network peer, 
capable of creating a TCP socket, managing shared files, 
toggling its online status, and sending messages. 
It maintains a list of File objects, which store file names, timestamps, and path information.
The Server class sets up a TCP socket bound to a specific address, acting as a central point for peer connections. 
The File class encapsulates file details, including whether the file name represents a path, 
and allows updates to the file name and timestamp.

The system’s activity diagram involves peers creating sockets, sharing files, and communicating with the server, 
while the finite state machine (FSM) includes states like Online/Offline for peers and Listening for the server. 
The File class manages states related to file paths and updates. Although the code provides a foundational structure, 
it lacks full implementation details, such as handling incoming connections and messages, which are essential for a functional peer-to-peer network.