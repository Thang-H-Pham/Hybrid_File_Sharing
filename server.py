
import os
import csv
import socket
from _thread import start_new_thread
import threading
from datetime import datetime
import json 
import hashlib
import secrets
import time

lock = threading.Lock()

FOLDER = "server_files"
CSV_FILE = "files.csv"
USERS_FILE = "users.json"
SESSION_TIME = 60 * 60   # An amount of valid time (here is set of 1 hour)

sessions = {}            # session ID -> {"user": name, "expires": time}
file_cache = set()       # non-duplicated names of files stored on the server (transfer).
peer_files = {}          # P2P index: file name -> {"ip": owner IP, "user": owner name, "conn": owner connection}

# ------------------------------------ SEND DATA ------------------------------------

# Send one reply line to the client
def send_line(c, line):
    c.sendall((line + "\n").encode())

# ------------------------------------ SHARED FILES' DATA (THE CENTRAL SERVER) ------------------------------------

# Save user's file into files.csv
def save_file(f, header):
    name, size = header.rsplit(": ", 1)
    name = os.path.basename(name)
    size = int(size)

    data = f.read(size)
    if len(data) < size:
        return "ERROR Upload incomplete"

    with lock:
        with open(os.path.join(FOLDER, name), "wb") as out:
            out.write(data)
        with open(CSV_FILE, "a", newline="") as out:
            csv.writer(out).writerow([name, size, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        file_cache.add(name)   # keep the cache up to date

    print("Saved", name, "(" + str(size), "bytes)")
    return "OK Received " + name

# List all available files, labelled by where they are (read from memory, not from files.csv)
def list_files():
    with lock:
        server_names = sorted(file_cache)
        peer_names = sorted(name + " (" + info["user"] + ")" for name, info in peer_files.items())
    if not server_names and not peer_names:
        return "No files available"
    return ("On server: " + (", ".join(server_names) or "none")
            + " | Shared by peers (use download): " + (", ".join(peer_names) or "none"))

# Clear files.csv for new server
def clear_csv():
    with lock:
        open(CSV_FILE, "w").close()
        file_cache.clear()   # the cache starts empty too
        peer_files.clear()

# ------------------------------------ P2P INDEXING ------------------------------------

# Record that a peer shares a file (the file itself stays on the peer)
def share_file(header, owner_ip, user, conn):
    name, size = header.rsplit(": ", 1)
    name = os.path.basename(name)
    size = int(size)

    with lock:
        with open(CSV_FILE, "a", newline="") as out:
            csv.writer(out).writerow([name, size, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), owner_ip])
        peer_files[name] = {"ip": owner_ip, "user": user, "conn": conn}

    print("Shared (P2P)", name, "from", user, "at", owner_ip)
    return "OK Shared " + name

# Tell the downloader which peer has the file
def get_file_ip(filename):
    with lock:
        info = peer_files.get(filename)
        on_server = filename in file_cache
    if info is not None:
        return "IP " + info["ip"]
    if on_server:
        return "ERROR " + filename + " is stored on the server, not shared by a peer"
    return "ERROR File not found"

# Remove every file a peer shared once that peer disconnects
def remove_peer_files(conn):
    with lock:
        gone = [name for name, info in peer_files.items() if info["conn"] == conn]
        for name in gone:
            del peer_files[name]
    if gone:
        print("Removed offline peer files:", ", ".join(gone))

# ------------------------------------ SESSION ID (COOKIE) ------------------------------------

# Make a new random session ID for a logged-in user
def create_session(name):
    token = secrets.token_hex(16)
    with lock:
        sessions[token] = {"user": name, "expires": time.time() + SESSION_TIME}
    return token

# Return the user name for a session ID, or None if it is unknown or expired
def check_session(token):
    with lock:
        session = sessions.get(token)
        if session is None:
            return None
        if time.time() > session["expires"]:
            del sessions[token]
            return None
        return session["user"]

# Remove a session ID so it cannot be used again
def delete_session(token):
    with lock:
        sessions.pop(token, None)

# ------------------------------------ USER REGISTERATION ------------------------------------

# Create the file if it is not exist
def init_users():
    with lock:
        if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) == 0:
            with open(USERS_FILE, "w") as out:
                json.dump({}, out)

# Read the file and store in dictionary. It will helps to see if the user is already registered or not. 
def load_users():
    with open(USERS_FILE) as f:
        return json.load(f)
    
# Updated the users.json with new and current users as well
def save_users(users):
    with open(USERS_FILE, "w") as out:
        json.dump(users, out, indent=2)

# Store a scrambled version instead of the real password
def hash_password(pwd, salt):
    return hashlib.pbkdf2_hmac("sha256", pwd.encode(), bytes.fromhex(salt), 100000).hex()

# Register for new user
def register_user(header): 
    if ": " not in header:
        return None, "ERROR Use: register <Name>: <Password>"
    
    name, pwd = header.split(": ", 1)
    
    if name == "" or " " in name or pwd == "":
        return None, "ERROR Name must not be empty or contain spaces, and password must not be empty"

    with lock:
        users = load_users()
        if name in users:
            return None, "ERROR Username taken"
        salt = secrets.token_hex(16)
        users[name] = {
            "salt": salt,
            "password": hash_password(pwd, salt),
            "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_users(users)

    print("Registered Successfully: ", name)
    return name, "OK, Registered successfully. Welcome, " + name + "! You are now logged in."
# Login for existed user
def login_user(header): 
    if ": " not in header:
        return None, "ERROR Use: login <Name>: <Password>"
    
    name, pwd = header.split(": ", 1)

    with lock:
        users = load_users()

    account = users.get(name)
    
    if account is None or hash_password(pwd, account["salt"]) != account["password"]:
        return None, "ERROR Invalid username or password"

    print(name +" just logged in.")
    return name, "OK, Welcome back: " + name 

# ------------------------------------ MULTITHREADING (HANDLE ONE BY ONE) ------------------------------------

# Read commands from one client and reply to each one
def client_handler(c, addr):
    f = c.makefile("rb")
    user = None
    token = None
    try:
        while True:
            line = f.readline()
            if not line:
                break
            line = line.decode().strip()

            # ----- register / login -----
            if line.startswith("REGISTER ") or line.startswith("LOGIN "):
                if user is not None:
                    send_line(c, "ERROR Already logged in as " + user)
                    continue
                cmd, header = line.split(" ", 1)
                if cmd == "REGISTER":
                    user, response = register_user(header)
                else:
                    user, response = login_user(header)
                send_line(c, response)
                # On success, also send a session ID (cookie) for next time
                if user is not None:
                    token = create_session(user)
                    send_line(c, "SESSION " + token)

            # ----- log in again with a saved session ID -----
            elif line.startswith("SESSION "):
                if user is not None:
                    send_line(c, "ERROR Already logged in as " + user)
                    continue
                name = check_session(line[8:])
                if name is None:
                    send_line(c, "ERROR Session expired, please log in")
                else:
                    user = name
                    token = line[8:]
                    print(name + " is back with a saved session.")
                    send_line(c, "OK, Welcome back: " + name + " (saved session)")

            # ----- quit (allowed without login) -----
            elif line == "QUIT":
                send_line(c, "BYE")
                break

            # ----- everything else needs a login -----
            elif user is None:
                if line.startswith("TRANSFER "):
                    f.read(int(line.rsplit(": ", 1)[1]))  
                send_line(c, "ERROR Please log in first")

            # ----- log out: forget the session ID -----
            elif line == "LOGOUT":
                delete_session(token)
                print(user + " logged out.")
                user = None
                token = None
                send_line(c, "OK, Logged out successfully.")

            elif line == "LIST":
                send_line(c, list_files())
            elif line.startswith("TRANSFER "):
                send_line(c, save_file(f, line[9:]))
            elif line.startswith("SHARE "):
                send_line(c, share_file(line[6:], addr[0], user, addr))
            elif line.startswith("GET_IP "):
                send_line(c, get_file_ip(line[7:]))
            else:
                send_line(c, "ERROR Unknown command")
    except (ConnectionError, ValueError):
        pass
    remove_peer_files(addr)   # this peer is offline now
    c.close()
    print('Disconnected from :', addr[0], ':', addr[1])
# ------------------------------------ MAIN ------------------------------------

# Main function
def main():
    host=""
    port=11226
    os.makedirs(FOLDER, exist_ok=True)
    clear_csv()
    init_users()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, port))
    s.listen(5)
    s.settimeout(1)
    print("Server running on port", port, "(press Ctrl+C to stop)")

    # loop to keep server running to accept new clients
    try:
        while True:
            try:
                c, addr= s.accept()
            except socket.timeout:
                continue
            c.settimeout(None)
            print('Connected to :', addr[0], ':', addr[1])

            start_new_thread(client_handler, (c, addr))
    except KeyboardInterrupt:
        print("Server stopped")
    finally:
        clear_csv()
        s.close()

if __name__ == '__main__':
    main()
