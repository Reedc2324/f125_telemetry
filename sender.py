import socket

# Configuration
target_ip = "127.0.0.1"
target_port = 5005
message = b"UDP Test Packet"

# 1. Create the socket (AF_INET = IPv4, SOCK_DGRAM = UDP)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 2. Send the packet
sock.sendto(message, (target_ip, target_port))
print(f"Sent message to {target_ip}:{target_port}")