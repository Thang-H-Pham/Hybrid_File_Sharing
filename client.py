import os
import socket
import threading

P2P_PORT = 11227
HOST = "100.105.143.67"
PORT = 11226
BUFFER_SIZE = 4096

# ------------------------------------ SEND AND RECEIVE DATA ------------------------------------

# Send data/msg
def send_line(sock, line):
    sock.sendall((line + "\n").encode())

# Retrieve data/msg
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

# ------------------------------------ COMMANDS ------------------------------------

# Send help to the client
def print_help():
    print('Commands: transfer "path" (upload a file) | list (show shared files) | register | download | help (show commands) | quit (disconnect)')

# Transfer file into the main/central server
def register_file_to_server(sock, path):
    path = path.strip().strip('"').strip("'")
    if not os.path.isfile(path):
        return "ERROR File not found: " + path

    filename = os.path.basename(path)
    if " " in filename:
        return "ERROR Filenames with spaces are not supported"

    size = os.path.getsize(path)
    
    # Notice we no longer open the file or send chunks here
    send_line(sock, f"REGISTER {filename}: {size}")
    return recv_line(sock)

# ------------------------------------ P2P Listener Thread ------------------------------------

def p2p_listener():
    listener= socket.socket(socket.AF_INET, socket.sock_STREAM)
    listener.bind(("0.0.0.0", P2P_PORT))
    listener.listen(5)
    
    while True:
        conn, addr = listener.accept()
        try:
            requested_file = recv_line(conn)
            if os.path.isfile(requested_file):
                with open(requested_file, "rb") as f:
                    while True:
                        chunk = f.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        conn.sendall(chunk)
        except (ConnectionError, OSError):
            pass
        finally:
            conn.close()


# ------------------------------------ Direct Download Logic ------------------------------------
def download_file(sock, filename):
    # Ask server for the IP
    send_line(sock, "GET_IP " + filename)
    response = recv_line(sock)
    
    if response.startswith("IP "):
        peer_ip = response[3:]
        print(f"Connecting to peer at {peer_ip}...")
        
        # Connect directly to the peer
        peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            peer_sock.connect((peer_ip, P2P_PORT))
            send_line(peer_sock, filename)
            
            # Receive and save the file chunks
            with open("downloaded_" + filename, "wb") as f:
                while True:
                    chunk = peer_sock.recv(BUFFER_SIZE)
                    if not chunk:
                        break
                    f.write(chunk)
            peer_sock.close()
            return f"Successfully downloaded: {filename}"
        except OSError:
            return "ERROR Could not connect to the peer."
    return response

# ------------------------------------ MAIN ------------------------------------

# Main program
def main():
    # Starts the background listener
    threading.Thread(target=p2p_listener, daemon=True).start()

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

            # ----- list -----
            if cmd == "list":
                send_line(sock, "LIST")
                print(recv_line(sock))

            # ----- register -----
            elif cmd == "register" and arg != "":
                print(register_file_to_server(sock, arg))

             # ----- download -----
            elif cmd == "download" and arg != "":
                print(download_file(sock, arg))


            # ----- help -----
            elif cmd == "help":
                print_help()

            # ----- quit -----
            elif cmd == "quit":
                send_line(sock, "QUIT")
                print(recv_line(sock))
                break

            # ----- transfer <path> -----
            elif cmd == "transfer" and arg != "":
                print(transfer_file_to_server(sock, arg))

            else:
                print("Unknown command. Type 'help'.")
    except ConnectionError as e:
        print("Error:", e)
    except (KeyboardInterrupt, EOFError):
        print()

    sock.close()
    print("Disconnected from the server.")


if __name__ == "__main__":
    main()

