import os
from threading import Semaphore

class File:
    def __init__(self, name: str, fd: int):
        self._users: int = 1
        self.lock: Semaphore = Semaphore(1)
        self.name: str = name
        self.fd: int = fd

    def write(self, val) -> int:
        # perform the operation, return error code
        return 0

    def read(self):
        # perform read, return value which defines __str__
        return self.name

    def close(self) -> None:
        # operation when _one_ user closes the file,
        # note __del__ when all users close the file and gc occurs
        pass

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
        return self.name

class TextFile(File):
    def __init__(self, *args):
        super().__init__(*args)
        self.file = open(self.name, "w+")

    def __del__(self):
        self.file.truncate()
        self.file.close()

    def write(self, val) -> int:
        self.file.write(val)
        return 0

    def read(self):
        self.file.seek(0)
        return self.file.read()
