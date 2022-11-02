import glob
from hashlib import md5

hashes = {}

for f in glob.glob("cache/*.input"):
    h = md5(open(f, "rb").read()).hexdigest()
    if h in hashes:
        print(f"Clash between {f} and {hashes[h]}")
    else:
        hashes[h] = f
