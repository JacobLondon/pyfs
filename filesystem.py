import errno
import importlib
import json
import os
import signal
import socket
import socketserver
import sys
from threading import Semaphore
from typing import Dict, List

try:
    from .filetypes import File
except:
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
        classptr = None
        try:
            classptr = getattr(sys.modules[filemodule], fileclass)
        except:
            try:
                module = importlib.import_module(filemodule)
                #print(module, fileclass)
                classptr = getattr(module, fileclass)
            except:
                print(f"FileSystem: open: Failed to import {os.getcwd()}{os.sep}{filemodule}.{fileclass}", file=sys.stderr)
                return None

        # already in it
        for i, file in enumerate(self._files.values()):
            if file.name == name:
                self._files[i]._incref()
                return i

        # not in it
        self._lock.acquire()
        fd = self._next_fd()
        self._files[fd] = classptr(name, fd)
        self._lock.release()
        return fd

    def close(self, fd: int):
        file = self._file_or_none(fd)
        if file:
            file.close()
            if self._files[fd]._decref():
                self._lock.acquire()
                del self._files[fd]
                self._reusable_fds.append(fd)
                self._lock.release()
                return 0
            return 0
        return errno.ENOENT

    def write(self, fd: int, val):
        file = self._file_or_none(fd)
        if file:
            return file.write(val)

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

class FileSystemTCPServer(FileSystem):
    # to connect to a FSTCPServer, you need a FSTCPClient
    # alternatively, standard writes/reads/close/open will work from this end
    # so local programs can just use as a normal FS
    def __init__(self, host: str, port: int):
        super().__init__()
        self.port = port
        self.host = host

        class Handler(socketserver.BaseRequestHandler):
            server = self
            fd_info = {}
            def handle(self):
                self.timeout = 2
                print("Client connected:", self.request.getpeername())
                while True:
                    try:
                        self.data = self.request.recv(32768)
                        message = json.loads(self.data)
                    except:
                        print("Client timed out:", self.request.getpeername())
                        break

                    # this is insane and crazy, but look up the func name from the network,
                    # call it from the server and pass the network args
                    resp = str(getattr(Handler.server, message["func"])(*message["args"]))
                    try:
                        self.request.sendall(bytes(resp, "utf-8"))
                    except:
                        print("HANDLE ERROR", len(resp), "bytes /", resp)
                    
                    if message["func"] == "close":
                        print("Client disconnected:", self.request.getpeername)
                        break
        self.handler = Handler

    def start(self):
        signal.signal(signal.SIGINT, lambda sig, frame: exit(0))
        with socketserver.ThreadingTCPServer((self.host, self.port), self.handler) as server:
            server.serve_forever()

class FileSystemTCPClient:
    def __init__(self, ip: str, port: int):
        self.host = (ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    def open(self, name: str, fileclass: str="File", filemodule: str="filetypes"):
        message = Message("open", (name, fileclass, filemodule)).format()
        try:
            self.sock.connect(self.host)
            self.sock.sendall(message)
        except:
            print("OPEN", len(message), "bytes /", message)

        # if this is gonna except, the user needs to catch it because the user defines the read func
        return int(self.sock.recv(32)) # the file descriptor converted from bytes

    def close(self, fd: int):
        message = Message("close", (fd,)).format()
        try:
            self.sock.sendall(message)
        except:
            print("CLOSE ERROR", len(message), "bytes /", message)
        return str(self.sock.recv(32), encoding="utf-8")

    def write(self, fd: int, val):
        message = Message("write", (fd, val)).format()
        try:
            self.sock.sendall(message)
        except:
            print("WRITE ERROR", len(message), "bytes /", message)
        return str(self.sock.recv(32), encoding="utf-8")

    def read(self, fd: int):
        message = Message("read", (fd,)).format()
        try:
            self.sock.sendall(message)
        except:
            print("READ ERROR", len(message), "bytes /", message)
        return str(self.sock.recv(32768), encoding="utf-8")
