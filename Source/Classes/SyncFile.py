from __future__ import annotations
from .Peer import Peer


class SyncFile:
    def __init__(self, filename: str, users_subbed: list[Peer]):
        self.filename: str = filename
        if users_subbed is None:
            self.users_subbed: list[Peer] = []
        else:
            self.users_subbed: list[Peer] = list(users_subbed)  # Create copy to avoid modification of original array

    def remove_user(self, peer: Peer) -> None:
        """
        This method will remove the user from the syncFile
        :param peer: the peer to be removed
        :return:
        """
        try:
            self.users_subbed.remove(peer)
        except ValueError:
            pass

    def __dict__(self):
        return {'filename': self.filename, 'users_subbed': [us.__dict__() for us in self.users_subbed]}

    def __eq__(self, other: SyncFile):
        return (self.filename, self.users_subbed) == (other.filename, other.users_subbed)

    @classmethod
    def from_dict(cls, data: dict):
        users_subbed = [Peer.from_dict(user) for user in data['users_subbed']]
        return SyncFile(data['filename'], users_subbed)
