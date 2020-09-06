import json
import signal
import socket
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

class Message:
    def __init__(self, func, args):
        self.func = func
        self.args = args

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
                message = json.loads(self.request[0])
                socket = self.request[1]

                # this is insane and crazy, but look up the func name from the network,
                # call it from the server and pass the network args
                resp = str(getattr(Handler.server, message["func"])(*message["args"]))
                print(message, resp)
                if resp is not None:
                    socket.sendto(bytes(resp, "utf-8"), self.client_address)
        self.handler = Handler

    def start(self):
        signal.signal(signal.SIGINT, lambda sig, frame: exit(0))
        with socketserver.UDPServer(("localhost", self.port), self.handler) as server:
            server.serve_forever()

class FileSystemUDPClient(FileSystem):
    def __init__(self, ip: str, port: int):
        super().__init__()
        self.host = (ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def open(self, name: str):
        message = bytes(json.dumps(Message("open", (name,)).__dict__), "utf-8")
        self.sock.sendto(message, self.host)

        fd = int(self.sock.recv(32))
        return fd

    def close(self, fd: int):
        message = bytes(json.dumps(Message("close", (fd,)).__dict__), "utf-8")
        self.sock.sendto(message, self.host)
    
    def write(self, fd: int, val):
        message = bytes(json.dumps(Message("write", (fd, val)).__dict__), "utf-8")
        self.sock.sendto(message, self.host)
    
    def read(self, fd: int):
        message = bytes(json.dumps(Message("read", (fd,)).__dict__), "utf-8")
        self.sock.sendto(message, self.host)
        return self.sock.recv(1024)
