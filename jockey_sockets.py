import socket
import struct
import logging

def create_server_socket(name: str):
    # Define the abstract socket path.
    # IMPORTANT: It MUST start with a null byte (b'\0') to indicate an abstract namespace socket.
    # The rest of the string is the name within that namespace.
    socket_path = b'\0' + name.encode("ascii")
    
    # Create a Unix Domain Socket (AF_UNIX) for streaming (SOCK_STREAM)
    server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    
    # Set socket options to reuse the address immediately after closing,
    # which is useful for rapid restarts, though less critical for abstract sockets.
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # Bind the socket to the abstract namespace path.
    # The path must be bytes.
    server_socket.bind(socket_path)

    # Listen for incoming connections. The argument is the backlog (max pending connections).
    server_socket.listen(0)

    return server_socket

def connect_to_socket(name: str):
    # Define the abstract socket path.
    # IMPORTANT: It MUST start with a null byte (b'\0') to indicate an abstract namespace socket.
    # The rest of the string is the name within that namespace.
    socket_path = b'\0' + name.encode("ascii")
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(socket_path)
    return s

def send_object(obj, s: socket.socket):
    # The paradigm is:
    # <4 byte network order integer of JSON UTF-8 string length>
    # <UTF-8 encoded JSON string of dataclass>
    json_bytes = obj.to_json().encode("utf-8")
    length: int = len(json_bytes)
    logging.debug("Writing %d bytes out to socket...", length)
    packed_integer = struct.pack('!I', length)
    assert len(packed_integer) == 4, "Network-order integer must be 4 bytes"
    num_bytes = s.send(packed_integer)
    assert num_bytes == 4, "Less data sent than expected. Socket closed?"
    num_bytes = s.send(json_bytes)
    assert num_bytes == length, "Less data sent than expected. Socket closed?"

def receive_object(cls, s: socket.socket):
    from_json = getattr(cls, "from_json")
    assert callable(from_json)

    data = s.recv(4)
    assert data, "Socket has disconnected"
    assert len(data) == 4, "Received less bytes than expected"

    length = struct.unpack('!I', data)[0]
    logging.debug("Reading %d bytes from socket...", length)
    
    data = s.recv(length)
    assert data, "Socket has disconnected"

    json_str = data.decode("utf-8")
    obj = from_json(json_str)
    return obj