import socket
from _thread import start_new_thread
import threading 
from datetime import datetime

lock = threading.Lock()

def client_handler(c):
    while True:
        data=c.recv(1024)
        if not data:
            print('Not data')
            break
        c.send(data[::-1])
    c.close()


def main():
    host=""
    port=8080
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(5)
    print("Server running on port", port)

    # loop to keep server running to accept new clients
    while True:
        c, addr= s.accept()
        print('Connected to :', addr[0], ':', addr[1])

        start_new_thread(client_handler, (c,))

if __name__ == '__main__':
    main()
