import socket
from _thread import start_new_thread
import threading 
from datetime import datetime

lock = threading.Lock()

def client_handler():
    while True:
        data=c.recv(1024)
        if not data:
            print('Not data')
            lock.release()
            break
        c.send(data[::-1])
    c.close()


def main():
    address=""
    port=""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(5)
    print("Server running on port", port)