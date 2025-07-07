# file_transfer.py

import time
import os

class FileTransferManager:
    def __init__(self, send_fn, status_fn, append_fn, progress_fn):
        """
        send_fn(src, dest, msg, digi): callable to send AX.25 frame
        status_fn(text): set status message
        append_fn(line, tag): append text to chat
        progress_fn(percent): update progress bar
        """
        self.send = send_fn
        self.set_status = status_fn
        self.append_text = append_fn
        self.set_progress = progress_fn

        self.last_ack = None
        self.stop_transmit = False

         # Receiver state
        self.file_data = bytearray()
        self.expecting_chunks = False
        self.chunk_map = {}
        self.incoming_filename = "received_file.dat"

    def send_file(self, filepath, src, dest, digi=None):
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        chunk_size = 200
        retries_allowed = 3
        timeout_secs = 3

        self.stop_transmit = False
        self.set_progress(0)
        self.append_text(f"Requesting to send file: {filename}", "sent")

        self.send(dest, src, "[REQFILE]", digi)
        self.set_status("Waiting for receiver to acknowledge file request...")

        start_wait = time.time()
        while time.time() - start_wait < timeout_secs:
            if self.last_ack == "[ACKFILE]":
                break
            time.sleep(0.2)
        else:
            self.append_text("File transfer request timed out.", "sent")
            self.set_status("Transfer cancelled (timeout).")
            return

        self.append_text(f"Sending file: {filename} ({filesize} bytes)", "sent")
        self.send(src, dest, f"[FILE]{filename}", digi)

        sent_bytes = 0
        chunk_id = 0
        self.last_ack = None

        with open(filepath, 'rb') as f:
            while not self.stop_transmit:
                chunk = f.read(chunk_size)
                if not chunk:
                    break

                hex_chunk = chunk.hex()
                msg = f"[DATA]{chunk_id:04X}:{hex_chunk}"

                for attempt in range(retries_allowed):
                    self.send(src, dest,  msg, digi)
                    self.set_status(f"Waiting for ACK for chunk {chunk_id:04X}... (Attempt {attempt+1})")
                    self.last_ack = None
                    ack_wait_start = time.time()

                    while time.time() - ack_wait_start < timeout_secs:
                        if isinstance(self.last_ack, str):
                            if self.last_ack.startswith(f"[ACK]{chunk_id:04X}"):
                                break
                            elif self.last_ack.startswith(f"[NACK]{chunk_id:04X}"):
                                break
                        time.sleep(0.1)
                    else:
                        continue  # Retry

                    if self.last_ack.startswith(f"[ACK]{chunk_id:04X}"):
                        break
                else:
                    self.set_status(f"Failed to send chunk {chunk_id:04X} after {retries_allowed} attempts.")
                    self.append_text("Transmission aborted.", "sent")
                    return

                sent_bytes += len(chunk)
                self.set_progress((sent_bytes / filesize) * 100)
                chunk_id += 1

        if not self.stop_transmit:
            self.send(src, dest,  "[EOF]", digi)
            self.append_text("File send complete.", "sent")
            self.set_status("File transfer complete.")
        else:
            self.set_status("File transfer aborted by user.")
            self.append_text("Transmission stopped.", "sent")

    def stop(self):
        self.stop_transmit = True

    def handle_ack(self, msg):
        """Called from receive loop when [ACK...], [NACK...], or [ACKFILE] is received"""
        self.last_ack = msg
    def handle_incoming(self, msg, src, dest, digis):
        # Normalize to a single digipeater for reply path (first in list)
        digi = digis[0] if digis else None

        if msg.startswith("[REQFILE]"):
            self.append_text(f"{src} wants to send a file. Accepting...", "recv")
            self.send(src, dest, "[ACKFILE]", digi=digi)
            self.file_data = bytearray()
            self.expecting_chunks = True
            self.chunk_map = {}

        elif msg.startswith("[FILE]"):
            filename = msg[6:].strip()
            self.incoming_filename = f"received_{filename}"
            self.append_text(f"Receiving file: {filename}", "recv")

        elif msg.startswith("[DATA]") and self.expecting_chunks:
            try:
                header, hex_data = msg[6:].split(":")
                chunk_id = int(header, 16)
                chunk_bytes = bytes.fromhex(hex_data)

                self.chunk_map[chunk_id] = chunk_bytes
                percent = int((len(self.chunk_map) / 1000) * 100)  # Estimate
                self.send(src, dest, f"[ACK]{chunk_id:04X}:{percent}", digi=digi)
            except Exception as e:
                self.send(src, dest, f"[NACK]{chunk_id:04X}", digi=digi)

        elif msg == "[EOF]" and self.expecting_chunks:
            try:
                with open(self.incoming_filename, "wb") as f:
                    for chunk_id in sorted(self.chunk_map.keys()):
                        f.write(self.chunk_map[chunk_id])
                self.append_text(f"File saved as: {self.incoming_filename}", "recv")
                self.set_status("File transfer complete.")
            except Exception as e:
                self.append_text(f"Error saving file: {e}", "recv")
            finally:
                self.expecting_chunks = False


