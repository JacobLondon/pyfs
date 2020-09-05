import sys
from typing import Dict, List

_MAX_DESCRIPTORS = 128

class File:
    def __init__(self, name: str, fd: int):
        self.name = name
        self.fd: int = fd

    def write(self, val):
        raise NotImplementedError

    def read(self):
        return self.name
    
    def __repr__(self):
        return str(self.fd)

class FileSystem:
    def __init__(self, port: int=None):
        self._files: Dict[int, File] = {}
        self._available_fds = iter(range(_MAX_DESCRIPTORS))
        self._reusable_fds: List[int] = []
        self._port: int = port

    def _file_or_none(self, fd: int) -> File:
        if fd in self._files:
            return self._files[fd]
        return None
    
    def _next_fd(self):
        if self._reusable_fds:
            return self._reusable_fds.pop(0)
        try:
            return next(self._available_fds)
        except StopIteration:
            print(f"FileSystem: _next_fd: File descriptor limit reached: {_MAX_DESCRIPTORS}", file=sys.stderr)
            exit(1)

    def open(self, name: str, fileclass=File) -> int:
        # already in it
        for i, file in enumerate(self._files.values()):
            if file.name == name:
                return i

        # not in it
        fd = self._next_fd()
        self._files[fd] = fileclass(name, fd)
        return fd

    def close(self, fd: int):
        if fd in self._files:
            del self._files[fd]
            self._reusable_fds.append(fd)

    def write(self, fd: int, val):
        file = self._file_or_none(fd)
        if file:
            file.write(val)

    def read(self, fd: int):
        file = self._file_or_none(fd)
        if file:
            return file.read()
