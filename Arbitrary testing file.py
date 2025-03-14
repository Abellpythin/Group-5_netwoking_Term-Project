from Classes import CRequest
from Classes import PeerList
from Classes import peerListAppend
from Classes import G_peerList
import json

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
print(json_data)

received_objects = [peerList_from_dict(item) for item in json.loads(json_data)]
print(received_objects)

send_str = CRequest.ConnectRequest.name + "," + json.dumps(peer.__dict__())
seperator = send_str.find(",")
clientRequest = send_str[:seperator]
userPeerList = peerList_from_dict(json.loads(send_str[seperator + 1:]))
peerListAppend(userPeerList)
peerListAppend(userPeerList)

