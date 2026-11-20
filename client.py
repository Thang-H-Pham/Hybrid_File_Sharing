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

# Print a reply for the user: "ERROR ..." -> "[Error] ...", "OK ..." -> "[Success]: ..."
# (the programs still send OK / ERROR to each other, only the screen text changes)
def show(message):
    if message.startswith("ERROR"):
        print("[Error] " + message[5:].lstrip(", "))
    elif message.startswith("OK"):
        print("[Success]: " + message[2:].lstrip(", "))
    else:
        print(message)

# ------------------------------------ COMMANDS ------------------------------------

# Send help to the client
def print_help(is_register):
    if is_register == True:
        print("Please log in or register:")
        print("  login <Name>: <Password>      log in to your account")
        print("  register <Name>: <Password>   create a new account")
        print("  help                          show this list")
        print("  quit                          close the program")
        print()
    else:
        print("You're logged in. What would you like to do?")
        print()
        print("  Files on other users' computers (P2P)")
        print('    - share "path"          let others download a file from your computer')
        # print("    - download <filename>   get a file from another user")
        print()
        print("  Files on the server")
        print('    - transfer "path"       upload a file to the server')
        print()
        print("  General")
        print("    - list                  show all files you can get")
        print("    - help                  show this list")
        print("    - logout                log out and forget the saved login")
        print("    - quit                  close the program")
        print()

# Transfer file into the main/central server
def transfer_file_to_server(sock, path):
    path = path.strip().strip('"').strip("'")
    if not os.path.isfile(path):    
        return "ERROR, File not found: " + path

    filename = os.path.basename(path)
    if " " in filename:
        return "ERROR, Filenames with spaces are not supported"

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
        return "ERROR, File not found: " + path

    filename = os.path.basename(path)
    if " " in filename:
        return "ERROR, Filenames with spaces are not supported"

    size = os.path.getsize(path)

    send_line(sock, f"SHARE {filename}: {size}")
    response = recv_line(sock)
    if response.startswith("OK"):
        shared_files[filename] = path   # remember the path only if the server accepted it
    return response

# Send ONE shared file to a peer that asks for it
def send_shared_file(conn):
    requested_file = recv_line(conn)
    filepath = shared_files.get(requested_file)   # only files this client shared
    if filepath is None or not os.path.isfile(filepath):
        send_line(conn, "ERROR, File is not shared by this peer")
        return
    send_line(conn, "OK " + str(os.path.getsize(filepath)))
    with open(filepath, "rb") as f:
        chunk = f.read(BUFFER_SIZE)
        while chunk:
            conn.sendall(chunk)
            chunk = f.read(BUFFER_SIZE)

# Background thread: wait for other peers to download from this client
def p2p_listener():
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("0.0.0.0", P2P_PORT))
    listener.listen(5)

    while True:
        conn, addr = listener.accept()
        try:
            send_shared_file(conn)
        except (ConnectionError, OSError):
            pass
        finally:
            conn.close()

# # Ask the server who has the file, then download it directly from that peer
# def download_file(sock, filename):
    # send_line(sock, "GET_IP " + filename)
    # response = recv_line(sock)
    # if not response.startswith("IP "):
        # return response

    # peer_ip = response[3:]
    # print(f"Connecting to peer at {peer_ip}...")
    # save_as = "downloaded_" + filename

    # peer_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # peer_sock.settimeout(10)
    # try:
        # peer_sock.connect((peer_ip, P2P_PORT))
        # send_line(peer_sock, filename)

        # answer = recv_line(peer_sock)          # "OK <size>" or "ERROR ..."
        # if not answer.startswith("OK "):
            # return answer
        # size = int(answer[3:])

        # received = 0
        # with open(save_as, "wb") as f:
            # while received < size:
                # chunk = peer_sock.recv(min(BUFFER_SIZE, size - received))
                # if not chunk:
                    # break
                # f.write(chunk)
                # received += len(chunk)

        # if received < size:
            # os.remove(save_as)                 # do not keep a broken file
            # return "ERROR Download incomplete (" + str(received) + " of " + str(size) + " bytes)"
        # return "OK Downloaded " + filename + " (" + str(size) + " bytes) as " + save_as
    # except (OSError, ConnectionError, ValueError):
        # return "ERROR Could not download from the peer."
    # finally:
        # peer_sock.close()


# ------------------------------------ USER REGISTERATION HANDLE ------------------------------------

# User registeration / Login in 
def user_registeration(sock, cmd, name, pwd):
    send_line(sock, cmd.upper() + " " + name + ": " + pwd)
    response = recv_line(sock)
    show(response)
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
    show(response)
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
    print("======== Welcome to our Hybrid File Sharing Services ========")
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
                show(recv_line(sock))

            # ----- help -----
            elif cmd == "help":
                print_help(is_register)

            # ----- logout -----
            elif cmd == "logout":
                if is_register:
                    print("You are not logged in.")
                    continue
                send_line(sock, "LOGOUT")
                show(recv_line(sock))
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
                show(transfer_file_to_server(sock, arg))

            # ----- share <path> (P2P register) -----
            elif cmd == "share" and arg != "":
                show(share_file_to_server(sock, arg))

            # # ----- download <filename> (P2P direct download) -----
            # elif cmd == "download" and arg != "":
                # show(download_file(sock, arg))
            
            else:
                print("Unknown command. Type 'help'.")
    except ConnectionError as e:
        print("[Error]", e)
    except (KeyboardInterrupt, EOFError):
        print()

    sock.close()
    print("Disconnected from the server.")


if __name__ == "__main__":
    main()
