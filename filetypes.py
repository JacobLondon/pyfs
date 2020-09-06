import os
from threading import Semaphore

class File:
    def __init__(self, name: str, fd: int):
        self._users: int = 1
        self.lock: Semaphore = Semaphore(1)
        self.name: str = name
        self.fd: int = fd

    def write(self, val):
        return

    def read(self):
        return self.name
    
    def _incref(self):
        self.lock.acquire()
        self._users += 1
        self.lock.release()

    def _decref(self) -> bool:
        # return if self needs to be deleted
        self.lock.acquire()
        self._users -= 1
        self.lock.release()
        return self._users == 0

    def __repr__(self):
        return str(self.fd)

class TextFile(File):
    def __init__(self, *args):
        super().__init__(*args)
        self.file = open(self.name, "w+")

    def __del__(self):
        self.file.close()

    def write(self, val):
        self.file.seek(0)
        self.file.write(val)
        self.file.truncate()

    def read(self):
        self.file.seek(0)
        return self.file.read()
