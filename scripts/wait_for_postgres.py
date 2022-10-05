import socket
import time
import os

POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
while True:
    try:
        s.connect((POSTGRES_HOST, 5432))
        s.close()
        time.sleep(2)
        break
    except socket.error:
        time.sleep(1)
