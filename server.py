
import os
import csv
import socket
from _thread import start_new_thread
import threading
from datetime import datetime
import json 
import hashlib
import secrets

lock = threading.Lock()

FOLDER = "server_files"
CSV_FILE = "files.csv"
USERS_FILE = "users.json"

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

    print("Saved", name, "(" + str(size), "bytes)")
    return "OK Received " + name

# List all available shared files 
def list_files():
    with lock:
        with open(CSV_FILE, newline="") as f:
            names = sorted(set(row[0] for row in csv.reader(f) if row))
    if not names:
        return "No files available"
    return "Files: " + ", ".join(names)

# Clear files.csv for new server
def clear_csv():
    with lock:
        open(CSV_FILE, "w").close()


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

# Register for new user
def register_user(): 
    return 

# Login for existed user
def login_user(): 
    return 

# ------------------------------------ MULTITHREADING (HANDLE ONE BY ONE) ------------------------------------

# Read commands from one client and reply to each one
def client_handler(c, addr):
    f = c.makefile("rb")
    user = None
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

            # ----- quit (allowed without login) -----
            elif line == "QUIT":
                send_line(c, "BYE")
                break

            # ----- everything else needs a login -----
            elif user is None:
                if line.startswith("TRANSFER "):
                    f.read(int(line.rsplit(": ", 1)[1]))  
                send_line(c, "ERROR Please log in first")

            elif line == "LIST":
                send_line(c, list_files())
            elif line.startswith("TRANSFER "):
                send_line(c, save_file(f, line[9:]))
            else:
                send_line(c, "ERROR Unknown command")
    except (ConnectionError, ValueError):
        pass
    c.close()
    print('Disconnected from :', addr[0], ':', addr[1])
# ------------------------------------ MAIN ------------------------------------

# Main function
def main():
    host=""
    port=11226
    os.makedirs(FOLDER, exist_ok=True)
    clear_csv()
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
