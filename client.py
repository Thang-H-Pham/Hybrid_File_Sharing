import os
import socket

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
def print_help(is_register):
    if is_register == True: 
        print("register <Name>: <Password> | login <Name>: <Password>")
    else: 
        print('Welcome. Here are the commands: transfer "path" (upload a file) | list (show shared files) | help (show commands) | quit (disconnect)')

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

# ------------------------------------ USER REGISTERATION HANDLE ------------------------------------

# User registeration / Login in 
def user_registeration(sock, cmd, name, pwd):
    send_line(sock, cmd.upper() + " " + name + ": " + pwd)
    response = recv_line(sock)
    print(response)
    return response.startswith("OK")  


# ------------------------------------ MAIN ------------------------------------

# Main program
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
    is_register = True
    print_help(is_register)
    
    try:
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
                if ": " not in arg: 
                    print("Wrong command, Usage: " + print_help(is_register))
                    continue
                
                name, pwd = arg.split(": ", 1)
                name = name.strip()
                pwd = pwd.strip()
                
                if name == " " or " " in name: 
                    print("Name must not be empty or contain spaces")
                    continue
                if pwd == " " or " " in pwd: 
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
