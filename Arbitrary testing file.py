import threading
import queue
import time
from Classes import CRequest
from Classes import PeerList
from Classes import G_peerList
import json


class Understand:
    def __init__(self, integer):
        self.number = integer

    def method(self, argument):
        print(argument)

    def noArg(self):
        print(self.number)


# obj = Understand(2)
# thread = threading.Thread(target=obj.method, args=(1,))
#
# thread.start()
# thread.join()








def testing2():
    def get_user_input(input_queue):
        while True:
            synchronized_print("Enter command: ")
            user_input = input()
            input_queue.put(user_input)


    def process_input(input_queue):
        while True:
            try:
                command = input_queue.get()
                synchronized_print(f"Processing command: {command}")
                # Add your command processing logic here
                input_queue.task_done()
            # Queue.Empty is an exception not a method or attribute
            except queue.Empty:
                # Check to see if return is ok
                time.sleep(0.1)


    def synchronized_print(message):
        with print_lock:
            print(message)


    print_lock = threading.Lock()
    input_queue = queue.Queue()

    input_thread = threading.Thread(target=get_user_input, args=(input_queue,), daemon=True)
    print_thread = threading.Thread(target=process_input, args=(input_queue,), daemon=True)

    input_thread.start()
    print_thread.start()

    """
    This block of code is neccessary. If the thread fails and everything makes sense. Make sure the 
    main method is also running in an "infinite" while loop so it doesn't terminate before other threads
    """
    try:
        while True:
            time.sleep(0.1)
    # Exit with crtl-c
    except KeyboardInterrupt:
        print("Exiting...")




def testing():
    peer = PeerList(('0.0.0.0', 12000), 'CoolGuy')
    peer2 = PeerList(('123.29.1.2', 13120), 'CoolGirl')
    peerList = []
    peerList.append(peer)
    peerList.append(peer2)
    peerListStr = ""
    for peer in peerList:
        peerListStr += str(peer) + ','
    peerListStr = peerListStr[:-1]
    print(peerListStr)

    # res = []
    # stk: list[int] = []
    #
    # # Used for {('0.0.0.0', 12000),CoolGuy},{('123.29.1.2', 13120),CoolGirl}, format
    # for index, char in enumerate(peerListStr):
    #     if char == '{':
    #         stk.append(index)
    #     elif char == '}' and stk:
    #         start: int = stk.pop()
    #         # is on '}' and is not included on string
    #         res.append(peerListStr[start + 1: index])
    # print(res)

    def peerList_from_dict(data):
        """
        Unpacks Json serialization of PeerList
        :param data:
        :return:
        """
        return PeerList(**data)


    # __data__() needs parentheses
    json_data = json.dumps([peerList.__dict__() for peerList in peerList])
    #print(json_data)

    received_objects = [peerList_from_dict(item) for item in json.loads(json_data)]
    #print(received_objects)

    send_str = CRequest.ConnectRequest.name + "," + json.dumps(peer.__dict__())
    print(send_str)
    seperator = send_str.find(",")
    clientRequest = send_str[:seperator]
    userPeerList = peerList_from_dict(json.loads(send_str[seperator + 1:]))

    print(peerList)

a = 2
x = a

x = 10

print(x)