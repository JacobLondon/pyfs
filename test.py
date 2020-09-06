from filesystem import *

fs = FileSystemUDPClient("localhost", 5432)
fd = fs.open("coolio")

print(fs.read(fd))

fd2 = fs.open("coolio")
print(fs.read(fd2))
fs.close(fd)
fs.close(fd2)
