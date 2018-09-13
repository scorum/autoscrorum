import struct
from enum import Enum


class Game(Enum):
    soccer = 0
    hockey = 1

    def __bytes__(self):
        return struct.pack("<B", self.value)

    def __str__(self):
        return "{0}".format(self.name)
