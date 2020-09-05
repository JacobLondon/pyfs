import socketserver
import sys
from typing import Dict, List

_MAX_DESCRIPTORS = 128

class File:
    def __init__(self, name: str, fd: int):
        self._users: int = 1
        self.name: str = name
        self.fd: int = fd

    def write(self, val):
        raise NotImplementedError

    def read(self):
        return self.name
    
    def _incref(self):
        self._users += 1

    def _decref(self) -> bool:
        # return if self needs to be deleted
        self._users -= 1
        return self._users == 0

    def __repr__(self):
        return str(self.fd)

class FileSystem:
    def __init__(self):
        self._files: Dict[int, File] = {}
        self._available_fds = iter(range(_MAX_DESCRIPTORS))
        self._reusable_fds: List[int] = []

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
                self._files[i]._incref()
                return i

        # not in it
        fd = self._next_fd()
        self._files[fd] = fileclass(name, fd)
        return fd

    def close(self, fd: int):
        if fd in self._files:
            if self._files[fd]._decref():
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

_CMD_READ = b"\27R"
_CMD_WRITE = b"\27W"
_CMD_OPEN = b"\27O"
_CMD_CLOSE = b"\27C"

class FileSystemUDPServer(FileSystem):
    # to connect to a FSUDPServer, you need a FSUDPClient
    # alternatively, standard writes/reads/close/open will work from this end
    # so local programs can just use as a normal FS
    def __init__(self, port: int):
        # give a port and True to act as server, False as client
        super().__init__()
        self.port = port

        class Handler(socketserver.BaseRequestHandler):
            server = self
            def handle(self):
                message = self.request[0]
                socket = self.request[1]
                resp = None

                if message.startswith(_CMD_READ):
                    resp = Handler.server.read(message[2:])

                elif message.startswith(_CMD_WRITE):
                    Handler.server.write(message[2:])

                elif message.startswith(_CMD_OPEN):
                    resp = Handler.server.open()

                # TODODOWODOWDF
                elif message.startswith(_CMD_CLOSE):
                    pass
                
                if resp is not None:
                    socket.sendto(bytes(resp, "utf-8"), self.client_address)
        self.handler = Handler

    def start(self):
        with socketserver.UDPServer(("localhost", self.port), self.handler) as server:
            server.serve_forever()
