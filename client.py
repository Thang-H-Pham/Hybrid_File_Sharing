import os
import socket
import threading

HOST = "100.105.143.67"
PORT = 11226
BUFFER_SIZE = 4096
DOWNLOAD_DIR = "downloads"

def send_line(sock, line):
    sock.sendall((line + "\n").encode())


def recv_line(sock):
    data = b""
    while True:
        byte = sock.recv(1)
        if not byte:
            raise ConnectionError("Server closed the connection")
        if byte == b"\n":
            break
        data += byte
    return data.decode()


def print_help():
    print("Commands:")
    print("  msg <text>          send a message")
    print("  upload <path>       upload a file")
    print("  download <filename> download a file")
    print("  list                list files on the server")
    print("  quit                exit")


def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect((HOST, PORT))
    except OSError:
        print("Could not connect to server. Is it running?")
        return
    sock.settimeout(None)
    print("Connected to", HOST, PORT)
    print_help()

    try:
        while True:
            line = input("> ").strip()
            if line == "":
                continue

            parts = line.split(" ", 1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""

            # ----- msg <text> -----
            if cmd == "msg" and arg != "":
                send_line(sock, "MSG " + arg)
                print(recv_line(sock))

            # ----- list -----
            elif cmd == "list":
                send_line(sock, "LIST")
                print(recv_line(sock))

            # ----- help -----
            elif cmd == "help":
                print_help()

            # ----- quit -----
            elif cmd == "quit":
                send_line(sock, "QUIT")
                print(recv_line(sock))
                break

            else:
                print("Unknown command. Type 'help'.")
    except ConnectionError as e:
        print("Error:", e)
    except KeyboardInterrupt:
        print()

    sock.close()
    print("Disconnected")


if __name__ == "__main__":
    main()
