import os
import csv
import socket
from _thread import start_new_thread
import threading
from datetime import datetime

lock = threading.Lock()


# ------------------------------------ SEND DATA ------------------------------------

# Send one reply line to the client
def send_line(c, line):
    c.sendall((line + "\n").encode())

# ------------------------------------ REGISTRATION FUNCTION (TO REPLACE SAVE_FILE) ------------------------------------

# Save user's file registration into files.csv (NO BINARY STORAGE)
def register_file(header,owner_ip):
    name,size=header.rsplit(": ", 1)
    name = os.path.basename(name)
    size=int(size)

    with lock:
        with open(CSV_FILE, "a", newline="") as out:
            #append the owner_ip to the csv row
            csv.writer(out).writerow([name,size,datetime.now().strftime("%Y-%m-%d %H:%M:%S"), owner_ip])
    print ("Registered", name, "from", owner_ip)
    return "OK Registered " + name

def get_file_ip(filename):
    with lock:
        with open (CSV_FILE, newline="") as f:
            for row in csv.reader(f):
                if row and row[0] == filename:
                    return "IP"+row[3]
        return 'ERROR File not found'

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

# ------------------------------------ MULTITHREADING (HANDLE ONE BY ONE) ------------------------------------

# Read commands from one client and reply to each one
def client_handler(c, addr):
    f = c.makefile("rb")
    try:
        while True:
            line = f.readline()
            if not line:
                break
            line = line.decode().strip()

            if line == "LIST":
                send_line(c, list_files())
            elif line.startswith("REGISTER "):
                # Route to the new register function, passing the client's IP
                send_line(c, register_file(line[9:], addr[0]))
            elif line.startswith("GET_IP "):
                # Route to the new IP lookup function
                send_line(c, get_file_ip(line[7:]))
            elif line == "QUIT":
                send_line(c, "BYE")
                break
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
