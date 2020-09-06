from filesystem import *

fs = FileSystemUDPClient("localhost", 5432)
fd = fs.open("out.txt", "TextFile")

fd2 = fs.open("out.txt", "TextFile")

fs.write(fd, "Hello, World!")
print(fs.read(fd2))

fs.close(fd)
fs.close(fd2)
