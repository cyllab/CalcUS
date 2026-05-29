import os
import glob

for inp in glob.glob("*.input"):
    name = os.path.splitext(inp)[0]
    if not os.path.isdir(name):
        os.remove(inp)
        print(inp)
