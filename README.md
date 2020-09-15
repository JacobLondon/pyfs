# Python Filesystem
Concept of having a server that can really really easily share state between many clients including managing disconnects

## Example
The idea is to define a file similar to a Linux kernel module, but the file operations are open, close, read, and write. After defining the file class extension, the file system client can open a named (create if doesn't exist, else get back the same file descriptor back) and used.
```python
# --- myserver.py ---
from filesystem import FileSystemTCPServer
from filetypes import File

someglobaldata = {}

class MyFile(File):
    def __init__(self):
        super().__init__()
        someglobaldata[self.name] = None

    def write(self, val) -> int:
        # each file instance can have a different name
        someglobaldata[self.name] = val

    # many clients can open different MyFiles, or the same one and
    # easily manage global state
    def read(self) -> str:
        return str(someglobaldata)

    def close(self) -> None:
        del someglobaldata[self.name]

fs = FileSystemTCPServer("localhost", 5432)
fs.start()

# --- myclient.py ---
from filesystem import FileSystemTcpClient

fs = FileSystemTcpClient("localhost", 5432)

# note that this will do a relative import from the __main__ module
fd = fs.open("make_up_name", fileclass="MyFile", filemodule="myserver")
fs.write(fd, "Hello!")
fs.read(fd)
# {'make_up_name': 'Hello!'}

# open the file with another user, can be a different client, but fd2 == fd
fd2 = fs.open("make_up_name", "MyFile", "myserver")
fs.read(fd2)
# {'make_up_name': 'Hello!'}

fd3 = fs.open("different_name","MyFile", "myserver")
fs.write(fd3, "World!")
fs.read(fd3)
# {'make_up_name': 'Hello!', 'different_name': 'World!'}

# remove entries in the example
fs.close(fd3)
fs.read(fd)
# {'make_up_name': 'Hello!'}

fs.close(fd2)
fs.close(fd)
```

## Built-in File Classes
Note that there are built in file classes such as File, no operations, and TextFile, writing and reading to text files on the hard disk.
```python
from filetypes import TextFile, File

# no op file
fd = fs.open("noop")
fd = fs.open("noop", File)

# examples
fd = fs.open("myfile.txt", TextFile)
```
