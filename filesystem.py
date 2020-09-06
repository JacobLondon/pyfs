import json
import signal
import socket
import socketserver
import sys
from threading import Semaphore
from typing import Dict, List

import filetypes
from filetypes import File

_MAX_DESCRIPTORS = 128

class FileSystem:
    def __init__(self):
        self._files: Dict[int, File] = {}
        self._available_fds = iter(range(_MAX_DESCRIPTORS))
        self._reusable_fds: List[int] = []
        self._lock: Semaphore = Semaphore(1)

    def _file_or_none(self, fd: int) -> File:
        if fd in self._files:
            return self._files[fd]
        return None

    def _next_fd(self) -> int:
        if self._reusable_fds:
            return self._reusable_fds.pop(0)
        try:
            return next(self._available_fds)
        except StopIteration:
            print(f"FileSystem: _next_fd: File descriptor limit reached: {_MAX_DESCRIPTORS}", file=sys.stderr)
            exit(1)

    def open(self, name: str, fileclass: str="File", filemodule: str="filetypes") -> int:
        try:
            file = getattr(sys.modules[filemodule], fileclass)
        except:
            return None

        # already in it
        for i, file in enumerate(self._files.values()):
            if file.name == name:
                self._files[i]._incref()
                return i

        # not in it
        self._lock.acquire()
        fd = self._next_fd()
        self._files[fd] = file(name, fd)
        self._lock.release()
        return fd

    def close(self, fd: int):
        if fd in self._files:
            if self._files[fd]._decref():
                self._lock.acquire()
                del self._files[fd]
                self._reusable_fds.append(fd)
                self._lock.release()

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

    def format(self):
        return bytes(json.dumps(self.__dict__), "utf-8")

class FileSystemUDPServer(FileSystem):
    # to connect to a FSUDPServer, you need a FSUDPClient
    # alternatively, standard writes/reads/close/open will work from this end
    # so local programs can just use as a normal FS
    def __init__(self, port: int):
        super().__init__()
        self.port = port

        class Handler(socketserver.BaseRequestHandler):
            server = self
            def handle(self):
                try:
                    message = json.loads(self.request[0])
                except:
                    pass
                socket = self.request[1]

                # this is insane and crazy, but look up the func name from the network,
                # call it from the server and pass the network args
                try:
                    resp = str(getattr(Handler.server, message["func"])(*message["args"]))
                except:
                    resp = str(None)
                print(message, bytes(resp, "utf-8"))
                # EACCES????? WHY?
                ret = socket.sendto(bytes(resp, "utf-8"), self.client_address)
                print(ret)
        self.handler = Handler

    def start(self):
        signal.signal(signal.SIGINT, lambda sig, frame: exit(0))
        with socketserver.UDPServer(("localhost", self.port), self.handler) as server:
            server.serve_forever()

class FileSystemUDPClient:
    def __init__(self, ip: str, port: int):
        self.host = (ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def open(self, name: str, fileclass: str="File", filemodule: str="filetypes"):
        message = Message("open", (name, fileclass, filemodule)).format()
        self.sock.sendto(message, self.host)

        # if this is gonna except, the user needs to catch it because the user defines the read func
        fd = int(self.sock.recv(32))
        return fd

    def close(self, fd: int):
        message = Message("close", (fd,)).format()
        self.sock.sendto(message, self.host)

    def write(self, fd: int, val):
        message = Message("write", (fd, val)).format()
        self.sock.sendto(message, self.host)

    def read(self, fd: int):
        message = Message("read", (fd,)).format()
        self.sock.sendto(message, self.host)

        resp = str(self.sock.recv(1024), encoding="utf-8")
        return resp
