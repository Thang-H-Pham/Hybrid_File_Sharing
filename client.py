import os
import threading
import socket

HOST = "100.105.143.67"
PORT = 11226
BUFFER_SIZE = 4096
SESSION_FILE = "session.txt"   # where the client keeps its session ID (cookie)

P2P_PORT = 11926
shared_files = {}   # maps filename -> full local path so p2p_listener can find it

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
def print_help(is_register):
    if is_register == True: 
        print("register <Name>: <Password> | login <Name>: <Password>")
    else: 
        print('Welcome. Here are the commands: transfer "path" (upload a file) | list (show shared files) | help (show commands) | share "path" | download <filename> logout (forget saved login) | quit (disconnect)')

# Transfer file into the main/central server
def transfer_file_to_server(sock, path):
    path = path.strip().strip('"').strip("'")
    if not os.path.isfile(path):    
        return "ERROR File not found: " + path

    filename = os.path.basename(path)
    if " " in filename:
        return "ERROR Filenames with spaces are not supported"

    size = os.path.getsize(path)

    send_line(sock, "TRANSFER " + filename + ": " + str(size))

    with open(path, "rb") as f:
        chunk = f.read(BUFFER_SIZE)
        while chunk:
            sock.sendall(chunk)
            chunk = f.read(BUFFER_SIZE)

    return recv_line(sock)

# ------------------------------------ P2P FUNCTIONS ------------------------------------

def share_file_to_server(sock, path):
    path = path.strip().strip('"').strip("'")
    if not os.path.isfile(path):
        return "ERROR File not found: " + path

    filename = os.path.basename(path)
    if " " in filename:
        return "ERROR Filenames with spaces are not supported"

    size = os.path.getsize(path)
    shared_files[filename] = path

    send_line(sock, f"SHARE {filename}: {size}")
    return recv_line(sock)

def p2p_listener():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("0.0.0.0", P2P_PORT))
    listener.listen(5)

    while True:
        conn, addr = listener.accept()
        try:
            requested_file = recv_line(conn)
            filepath = shared_files.get(requested_file, requested_file)
            if os.path.isfile(filepath):
                with open(filepath, "rb") as f:
                    while True:
                        chunk = f.read(BUFFER_SIZE)
                        if not chunk:
                            break
                        conn.sendall(chunk)
        except (ConnectionError, OSError):
            pass
        finally:
            conn.close()

def download_file(sock, filename):
    send_line(sock, "GET_IP " + filename)
    response = recv_line(sock)

    if response.startswith("IP "):
        peer_ip = response[3:]
        print(f"Connecting to peer at {peer_ip}...")

        peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            peer_sock.connect((peer_ip, P2P_PORT))
            send_line(peer_sock, filename)

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


# ------------------------------------ USER REGISTERATION HANDLE ------------------------------------

# User registeration / Login in 
def user_registeration(sock, cmd, name, pwd):
    send_line(sock, cmd.upper() + " " + name + ": " + pwd)
    response = recv_line(sock)
    print(response)
    if response.startswith("OK"):
        session_line = recv_line(sock)      # "SESSION <id>"
        save_session(session_line[8:])
        return True
    return False

# ------------------------------------ SESSION ID (COOKIE) ------------------------------------

# Save the session ID in a file for next time
def save_session(token):
    with open(SESSION_FILE, "w") as out:
        out.write(token)

# Read the saved session ID, or None if there is none
def load_session():
    if not os.path.isfile(SESSION_FILE):
        return None
    with open(SESSION_FILE) as f:
        return f.read().strip() or None

# Delete the saved session ID
def delete_session():
    if os.path.isfile(SESSION_FILE):
        os.remove(SESSION_FILE)

# Try to log in with the saved session ID. Returns True if it worked.
def resume_session(sock):
    token = load_session()
    if token is None:
        return False
    send_line(sock, "SESSION " + token)
    response = recv_line(sock)
    print(response)
    if response.startswith("OK"):
        return True
    delete_session()   # the saved ID no longer works
    return False


# ------------------------------------ MAIN ------------------------------------

# Main program
def main():

    threading.Thread(target=p2p_listener, daemon=True).start() # start background listener

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)
    try:
        sock.connect((HOST, PORT))
    except OSError:
        print("Could not connect to server. Is it running?")
        return
    
    sock.settimeout(None)
    print("Connected to", HOST, PORT)
    is_register = True

    try:
        # Use the saved session ID (cookie) if there is one
        if resume_session(sock):
            is_register = False
        print_help(is_register)

        while True:
            line = input("> ").strip()
            if line == "":
                continue

            parts = line.split(" ", 1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""
            
            
            # ----- Registeration / Login -----
            if cmd == "register" or cmd == "login":
                if not is_register: 
                    print("You are already logged in.")
                    continue
                if ": " not in arg: 
                    print("Wrong command. Usage: " + cmd + " <Name>: <Password>")
                    continue
                
                name, pwd = arg.split(": ", 1)
                name = name.strip()
                pwd = pwd.strip()
                
                if name == "" or " " in name: 
                    print("Name must not be empty or contain spaces")
                    continue
                if pwd == "" or " " in pwd: 
                    print("Password must not be empty or contain spaces")
                    continue
                
                if user_registeration(sock, cmd, name, pwd):
                    is_register = False;
                    print_help(is_register)
            
            # ----- list -----
            elif cmd == "list":
                send_line(sock, "LIST")
                print(recv_line(sock))

            # ----- help -----
            elif cmd == "help":
                print_help(is_register)

            # ----- logout -----
            elif cmd == "logout":
                if is_register:
                    print("You are not logged in.")
                    continue
                send_line(sock, "LOGOUT")
                print(recv_line(sock))
                delete_session()
                is_register = True
                print_help(is_register)

            # ----- quit -----
            elif cmd == "quit":
                send_line(sock, "QUIT")
                print(recv_line(sock))
                break

            # ----- transfer <path> -----
            elif cmd == "transfer" and arg != "":
                print(transfer_file_to_server(sock, arg))

            # ----- share <path> (P2P register) -----
            elif cmd == "share" and arg != "":
                print(share_file_to_server(sock, arg))

            # ----- download <filename> (P2P direct download) -----
            elif cmd == "download" and arg != "":
                print(download_file(sock, arg))
            
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
