from filesystem import *

fs = FileSystemUDPServer("localhost", 5432)
fs.start()
