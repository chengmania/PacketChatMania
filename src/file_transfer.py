# file_transfer.py

import time
import os

class FileTransferManager:
    def __init__(self, send_fn, status_fn, append_fn, progress_fn, ack_mgr):
        self.send = send_fn
        self.set_status = status_fn
        self.append_text = append_fn
        self.set_progress = progress_fn
        self.ack_manager = ack_mgr  # ⬅️ New

        self.stop_transmit = False
        self.file_data = bytearray()
        self.expecting_chunks = False
        self.chunk_map = {}
        self.incoming_filename = "received_file.dat"

        # Ensure downloads folder exists
        self.download_dir = os.path.join(os.getcwd(), "downloads")
        os.makedirs(self.download_dir, exist_ok=True)


    def send_file(self, filepath, src, dest, digi=None):
        filename = os.path.basename(filepath)
        filesize = os.path.getsize(filepath)
        chunk_size = 200
        self.stop_transmit = False

        self.set_progress(0)
        self.append_text(f"Requesting to send file: {filename}", "sent")
        #self.set_status("Waiting for receiver to acknowledge...")

        # ➤ Track and send [REQFILE]
        self.ack_manager.track("REQFILE_INIT", src, dest, "[REQFILE]", digi=digi, msg_type="file")
        self.send(src, dest, "[REQFILE]", digi)
        log_raw_line(f"📤 Tracked REQFILE_INIT for {dest}")

        # 🕓 Wait for [ACKFILE] before continuing
        self.set_status("Waiting for receiver to approve file transfer...")
        for _ in range(25):  # Wait up to ~5 seconds (25 × 0.2s)
            if self.ack_manager.is_acknowledged("REQFILE_INIT"):
                break  # ACK received
            time.sleep(0.2)
        else:
            self.append_text("❌ File transfer request timed out or was denied.", "sent")
            self.set_status("File transfer canceled.")
            return

        time.sleep(1)  # Give receiver time to respond

        # ➤ Track and send [FILE]<filename>
        file_msg = f"[FILE]{filename}"
        self.ack_manager.track("FILE_INIT", src, dest, file_msg, digi=digi, msg_type="file")
        self.send(src, dest, file_msg, digi)
        self.append_text(f"Sending file: {filename} ({filesize} bytes)", "sent")

        # ➤ Send chunks
        sent_bytes = 0
        chunk_id = 0
        total_chunks = (filesize + chunk_size - 1) // chunk_size

        with open(filepath, 'rb') as f:
            while not self.stop_transmit:
                chunk = f.read(chunk_size)
                if not chunk:
                    break

                hex_chunk = chunk.hex()
                chunk_msg = f"[DATA]{chunk_id:04X}:{hex_chunk}"
                msg_id = f"FT_{chunk_id:04X}"
                self.ack_manager.track(msg_id, src, dest, chunk_msg, digi=digi, msg_type="file")
                self.send(src, dest, chunk_msg, digi)

                sent_bytes += len(chunk)
                self.set_progress((sent_bytes / filesize) * 100)
                self.append_text(f"➤ Chunk {chunk_id+1}/{total_chunks} sent ({sent_bytes}/{filesize} bytes)", "sent")
                chunk_id += 1

                time.sleep(0.2)  # prevent flooding

        if not self.stop_transmit:
            eof_msg = "[EOF]"
            self.ack_manager.track("EOF_FINAL", src, dest, eof_msg, digi=digi, msg_type="file")
            self.send(src, dest, eof_msg, digi)
            self.append_text("✅ File send complete.", "sent")
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
            self.append_text(f"{src} wants to send a file. Type YES to accept or NO to reject.", "recv")
            # No auto-reply here — wait for user input in main.py
            self.file_data = bytearray()
            self.expecting_chunks = True
            self.chunk_map = {}

        elif msg.startswith("[FILE]"):
            filename = msg[6:].strip()
            self.incoming_filename = os.path.join(self.download_dir, f"received_{filename}")
            self.append_text(f"📥 Receiving file: {filename}", "recv")

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
                rel_path = os.path.relpath(self.incoming_filename)
                self.append_text(f"💾 File saved as: {rel_path}", "recv")
                self.set_status("File transfer complete.")
            except Exception as e:
                self.append_text(f"❌ Error saving file: {e}", "recv")
            finally:
                self.expecting_chunks = False


