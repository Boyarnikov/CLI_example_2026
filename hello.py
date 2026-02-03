from sys import argv

name = "User" if len(argv) < 2 else argv[1]
print(f"hello {name}!")
print(argv, type(argv))
