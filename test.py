from filesystem import FileSystem

fs = FileSystem()
fd = fs.open("coolio")

print(fd, fs.read(fd))
fs.close(fd)

fd = fs.open("different")
print(fd, fs.read(fd))

next_fd = fs.open("second")
print(next_fd, fs.read(next_fd))

fs.close(next_fd)
next_fd = fs.open("third")
print(next_fd, fs.read(next_fd))

ffd = fs.open("fourth")
print(ffd, fs.read(ffd))

fs.close(next_fd)
next_fd = fs.open("fifth, should reuse")
print(next_fd, fs.read(next_fd))

