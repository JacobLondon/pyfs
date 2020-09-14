from filesystem import *

fs = FileSystemTCPClient("localhost", 5432)
fd = fs.open("out.txt", "TextFile")

fd2 = fs.open("out.txt", "TextFile")

fs.write(fd, "Hello, World!")
print(fs.read(fd2))
fs.write(fd2, "next line?")

m = fs.open("tmp", "TestFile", "testlib")
fs.close(m)

fs.close(fd)
fs.close(fd2)
