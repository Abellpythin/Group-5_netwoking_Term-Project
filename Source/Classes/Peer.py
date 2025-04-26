from __future__ import annotations


class Peer:

    def __init__(self, addr: tuple[str, int], username: str):
        self.addr: tuple[str, int] = addr
        self.username: str = username

    def __dict__(self):
        return {'addr': self.addr, 'username': self.username}

    def __str__(self):
        return f"{{{self.addr}, {self.username}}}"

    def __eq__(self, other: Peer):
        return (self.addr, self.username) == (other.addr, other.username)

    @classmethod
    def from_dict(cls, data: dict):
        return Peer(tuple(data["addr"]), data["username"])
