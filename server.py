import os
import csv
import socket
from _thread import start_new_thread
import threading
from datetime import datetime

lock = threading.Lock()

FOLDER = "server_files"
CSV_FILE = "files.csv"

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
            elif line.startswith("TRANSFER "):
                send_line(c, save_file(f, line[9:]))
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
