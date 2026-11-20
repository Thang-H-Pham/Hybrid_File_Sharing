# -*- coding: utf-8 -*-
"""
Created on Wed Oct  7 10:12:00 2026

@author: thaot
"""

import socket 

serverPort = 9999

serverSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

serverSocket.bind(('', serverPort))

print ('The server is ready to receive')

while True: 
    message, clientAddress = serverSocket.recvfrom(2048)
    print('Connect with '+ clientAddress[0] + ":" + str(clientAddress[1]))
    modifiedMessage = message.decode().upper()
    serverSocket.sendto(modifiedMessage.encode(), clientAddress)
    
serverSocket.close()

