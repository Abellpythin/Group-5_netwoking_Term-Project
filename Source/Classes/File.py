from __future__ import annotations


class File:
    def __init__(self, filename: str, username: str, addr: tuple[str, int] = None):
        self.filename: str = filename
        self.username: str = username
        self.addr: tuple[str, int] = addr

    def __dict__(self):
        return {'filename': self.filename, 'username': self.username, 'addr': self.addr}

    def __eq__(self, other: File):
        return (self.filename, self.username, self.addr) == (other.filename, other.username, other.addr)

    @classmethod
    def from_dict(cls, data: dict):
        return File(data['filename'], data['username'], tuple(data['addr']))