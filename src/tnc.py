# tnc.py
import socket
import threading

class TNCClient:
    def __init__(self, on_data_received, on_status_update, set_connection_light):
        self.socket = None
        self.running = False
        self.thread = None
        self.on_data_received = on_data_received
        self.on_status_update = on_status_update
        self.set_connection_light = set_connection_light

    def connect(self, host, port, callsign):
        if self.running:
            return False

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.socket.settimeout(0.5)
            self.running = True
            self.set_connection_light("green")
            self.on_status_update(f"Connected to {host}:{port} as {callsign}")
            self.thread = threading.Thread(target=self.receive_loop, daemon=True)
            self.thread.start()
            return True
        except Exception as e:
            self.on_status_update(f"Connection failed: {e}")
            self.set_connection_light("red")
            return False

    def disconnect(self):
        self.running = False
        try:
            if self.socket:
                self.socket.shutdown(socket.SHUT_RDWR)
                self.socket.close()
            self.set_connection_light("red")
            self.on_status_update("Disconnected from TNC")
        except Exception as e:
            self.on_status_update(f"Error disconnecting: {e}")

    def receive_loop(self):
        while self.running:
            try:
                try:
                    data = self.socket.recv(1024)
                except socket.timeout:
                    continue
                if data:
                    self.on_data_received(data)
            except Exception as e:
                self.on_status_update(f"Receive error: {e}")
                break

    def send(self, data: bytes):
        if not self.socket:
            self.on_status_update("Send failed: not connected")
            return
        try:
            self.socket.send(data)
        except Exception as e:
            self.on_status_update(f"Send failed: {e}")
