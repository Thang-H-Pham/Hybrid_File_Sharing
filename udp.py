import socket

UDP_PORT= 11228
BROADCAST_IP = "255.255.255.255"
SERVICE_TYPE = "urn:hybrid-file-sharing:peer:1"

ssdp_request = (
    'M-SEARCH * HTTP/1.1\r\n'
    'HOST: 239.255.255.250:1900\r\n'
    'MAN: "ssdp:discover"\r\n'
    'MX: 2\r\n'
    'ST: ssdp:all\r\n'
    '\r\n'
)

"HTTP/1.1 200 OK\r\n"
"CACHE-CONTROL: max-age=1800\r\n"
"EXT:\r\n"
"LOCATION: http://192.168.1\r\n"
"SERVER: Linux/5.15 UPnP/1.1 CustomDevice/1.0\r\n"
"ST: upnp:rootdevice\r\n"
"USN: uuid:12345678-1234-1234-1234-123456789abc::upnp:rootdevice\r\n"
"\r\n"

