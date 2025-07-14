# main.py (excerpt with unified ACK system)
from gui import PacketChatGUI
from tnc import TNCClient
from ax25 import ax25_ui_frame, wrap_kiss
from receiver import parse_ax25_frame
from config import load_config
from time import time
from beacon import BeaconManager
from chatlog import append_log
from heardlog import load_heard_stations, save_heard_stations
from tnclog import log_raw_line

from datetime import datetime, timezone
from file_transfer import FileTransferManager
from ack_manager import AckManager
import ttkbootstrap as ttk
import os

if not os.path.exists("config.ini"):
    from config import save_config, default_config
    save_config(default_config)
os.makedirs("logs", exist_ok=True)

class PacketChatApp:
    def __init__(self):
        self.root = ttk.Window(themename="flatly")
        self.config = load_config()
        self.heard_stations = load_heard_stations()
        self.gui = PacketChatGUI(self.root, on_beacon_toggle=self.handle_beacon_toggle)
        self.callsign = self.config.get("User", "callsign", fallback="N0CALL")
        self.gui.callsign = self.callsign  # ✅ this is the missing line

        self.channel_busy = False
        self.last_heard_time = time()

        # For file acceptance logic
        self.awaiting_file_request = None  # e.g., {"from": "KC3SMW", "filename": "example.txt", "digi": "W3SK"}


        #load Heard stations
        self.recalled_calls = set()
        for call, iso_time in self.heard_stations.items():
            try:
                last_seen = datetime.fromisoformat(iso_time)
                age_minutes = int((datetime.now(timezone.utc) - last_seen).total_seconds() / 60)
                time_str = "0m" if age_minutes == 0 else f"*{age_minutes}" if age_minutes < 100 else "*99"
                self.recalled_calls.add(call.upper())
            except Exception:
                time_str = "*--"

            self.gui.update_heard_station(call, self.callsign, force_when=time_str)


        #Beacon Manager
        if self.config.getboolean("Beacon", "enabled", fallback=False):
            self.gui.set_beacon_light("green")
        else:
            self.gui.set_beacon_light("gray")

        get_digi = lambda: self.config.get("Beacon", "digipeater", fallback=None)
        self.beacon = BeaconManager(
            send_fn=self.send_ax25_frame,
            get_callsign_fn=lambda: self.callsign,
            get_enabled_fn=lambda: self.config.getboolean("Beacon", "enabled", fallback=False),
            get_interval_fn=lambda: self.config.getint("Beacon", "interval", fallback=15),
            get_message_fn=lambda: self.config.get("Beacon", "message", fallback="ChatMania App with mailbox"),
            get_digipeater_fn=get_digi
        )
        self.beacon.start()

        self.gui.config = self.config

        self.gui.send_message = self.send_message

        # Setup TNC client
        def update_status_and_log(msg):
            self.gui.status_var.set(msg)
            log_raw_line(f"[STATUS] {msg}")
        self.tnc = TNCClient(
            on_data_received=self.handle_incoming_data,
            on_status_update=update_status_and_log,
            set_connection_light=self.gui.set_connection_light
        )

        # Bind GUI events
        self.gui.connect_button.config(command=self.toggle_connection)
        self.gui.send_button.config(command=self.send_message)
        self.gui.stop_button.config(command=self.stop_transmission)
        self.gui.msg_entry.bind("<Return>", lambda e: self.send_message())

        # ACK Manager
        self.ack_manager = AckManager(
            send_fn=self.send_ax25_frame,
            status_fn=self.gui.status_var.set,
            debug_fn=self.gui.log_raw,
            alert_fn=self.gui.append_text,
            my_call=self.callsign.upper()
        )
        self.ack_manager.debug = True  # Turn on for now, off later
        self.ack_manager.max_retries = 3
        self.root.after(5000, self.poll_ack_manager)
        self.ack_manager.gui_ref = self


        # File Transfer Manager
        self.ft = FileTransferManager(
            send_fn=self.send_ax25_frame,
            status_fn=self.gui.status_var.set,
            append_fn=self.gui.append_text,
            progress_fn=self.gui.progress_var.set,
            ack_mgr=self.ack_manager
        )

        self.gui.send_file_button.config(command=self.send_file)

        self.sent_messages = []
        self.sent_line_tags = {}  # msg_id -> line tag

    def toggle_connection(self):
        if self.tnc.running:
            self.tnc.disconnect()
            self.gui.connect_button.config(text="Connect TNC")
        else:
            host = self.gui.host_label_var.get()
            port = int(self.gui.port_label_var.get())
            self.callsign = self.gui.callsign_label_var.get().upper()
            success = self.tnc.connect(host, port, self.callsign)
            if success:
                self.gui.connect_button.config(text="Disconnect TNC")

    def handle_beacon_toggle(self, enabled):
        if enabled:
            self.beacon.start()
            self.gui.set_beacon_light("green")
        else:
            self.beacon.stop()
            self.gui.set_beacon_light("gray")

    def send_message(self):
        if self.channel_busy:
            self.gui.log_raw("⚠️ Channel busy. Delaying transmit...")
            self.root.after(500, self.send_message)  # Retry in 0.5 seconds
            return

        self.beacon.reset_idle_timer()

        msg = self.gui.msg_entry.get().strip()
        # 🧠 Check for YES/NO reply to incoming file transfer request
        if self.awaiting_file_request and msg.upper() in ("YES", "NO"):
            req = self.awaiting_file_request
            response = msg.upper()
            self.awaiting_file_request = None
            self.gui.msg_entry.delete(0, "end")

            if response == "YES":
                self.gui.append_text(f"✅ Accepted file: {req['filename']}", "sent")
                log_raw_line(f"[ACKFILE] sent to {req['from']}")
                ack_msg = "[ACKFILE]"
                #msg_id = f"REQ_{req['filename']}"
                #self.ack_manager.track(msg_id, self.callsign, req["from"], ack_msg, digi=req["digi"], msg_type="file")
            else:
                self.gui.append_text(f"❌ Declined file: {req['filename']}", "sent")
                log_raw_line(f"[NACKFILE] sent to {req['from']}")
                ack_msg = "[NACKFILE]"

            self.send_ax25_frame(
                self.callsign,
                req["from"],
                ack_msg,
                digi=req["digi"]
            )
            return

        if not msg or not self.tnc.running:
            return

        src = self.gui.callsign_label_var.get().upper()
        dest = self.gui.dest_entry.get().strip().upper()
        if not dest:
            dest = "CQ"
        digi = self.gui.digi_entry.get().upper() if self.gui.digi_entry.get().strip() else None

        if digi and not digi.isalnum():
            print(f"⚠️ Invalid digipeater: {digi} — ignoring.")
            digi = None

        # Determine if this message should be tracked for ACK
        track_ack = False
        msg_id = None
        line_tag = None

        if dest in ("CQ", "BEACON", "ALL", "QST", "ID"):
            full_msg = msg
        elif self.gui.acks_enabled_var.get():
            msg_id = self.ack_manager.generate_id()
            full_msg = f"[MSGID]{msg_id}|{msg}"
            self.ack_manager.track(msg_id, src, dest, full_msg, digi)
            line_tag = f"msg_{msg_id}"
            self.sent_line_tags[msg_id] = line_tag
        else:
            full_msg = msg


        frame = ax25_ui_frame(dest, src, full_msg, digipeater=digi)
        self.tnc.send(wrap_kiss(frame))
        # ✅ Log outgoing message to Raw window
        path_str = f",{digi}" if digi else ""
        # Strip [MSGID] for readability if present
        display_msg = msg
        if full_msg.startswith("[MSGID]") and "|" in full_msg:
            display_msg = full_msg.split("|", 1)[1]
        if hasattr(self.gui, "log_raw"):
            self.gui.log_raw(f"[TX] {src}>{dest}{path_str}: {display_msg}")
            log_raw_line(f"[TX] {src}>{dest}{path_str}: {display_msg}")  # line is the raw message being printed


        self.sent_messages.append((src, dest, msg))
        if len(self.sent_messages) > 20:
            self.sent_messages.pop(0)

        line = f"{src}>{dest},{digi}: {msg}" if digi else f"{src}>{dest}: {msg}"
        self.gui.append_text(line, "sent", custom_tag=line_tag)
        self.gui.msg_entry.delete(0, "end")
        self.gui.set_rx_tx_light("red")
        self.root.after(300, lambda: self.gui.set_rx_tx_light("green"))
        append_log(dest.upper(), self.callsign.upper(), msg)



    def send_ax25_frame(self, src, dest, msg, digi=None, request_ack=False):
        """
        Send an AX.25 frame to the TNC. If request_ack is True and the message doesn't
        already include a [MSGID], one will be added. This function does NOT handle ACK tracking.
        """
        if not self.tnc.running:
            raise RuntimeError("TNC is not connected")

        full_msg = msg

        # Append a [MSGID] only if requested and not already present
        if request_ack and "[MSGID]" not in msg:
            msg_id = self.ack_manager.generate_id()
            full_msg = f"[MSGID]{msg_id}|{msg}"
            # Note: CALLER must track it separately if needed

        frame = ax25_ui_frame(dest, src, full_msg, digipeater=digi)
        self.tnc.send(wrap_kiss(frame))


    def handle_incoming_data(self, data):

        parsed = parse_ax25_frame(data, self.callsign)
        #if channel is busy
        self.channel_busy = True
        self.last_heard_time = time()
        self.root.after(2000, self.check_channel_clear)  # 2-second grace

        print("📥 Incoming KISS Frame:", data.hex())
        if not parsed:
            print("⚠️ parse_ax25_frame() returned None")
            return

        print("✅ AX.25 Parsed:", parsed)

        src = parsed["src"]
        dest = parsed["dest"]
        info = parsed["info"]
        path_str = "," + ",".join(parsed["digis"]) if parsed["digis"] else ""

        raw_line = f"[RAW] {src}>{dest}{path_str}: {info}"
        if hasattr(self.gui, "log_raw"):
            self.gui.log_raw(raw_line)
            log_raw_line(raw_line)  # line is the raw message being printed

        else:
            print(raw_line)



        # 🟢 Handle file transfer messages and ACKs
        if info.startswith("[REQFILE]"):
            filename = f"{src}_{int(time())}.dat"
            self.awaiting_file_request = {
                "from": src,
                "to": dest,
                "filename": filename,
                "digi": parsed["digis"][0] if parsed["digis"] else None
            }
            self.gui.append_text(f"📥 {src} wants to send a file: \"{filename}\"\nType YES to accept or NO to reject.", "recv")
            log_raw_line(f"[REQFILE] from {src}: {filename}")
            return

        elif info.startswith("[FILE]"):
            msg_id = f"FILE_{info[6:].strip()}"
            self.ack_manager.ack_received(msg_id, from_call=src)
            self.ft.handle_incoming(info, src, dest, parsed["digis"])
            return

        elif info.startswith("[DATA]"):
            try:
                chunk_id = info[6:].split(":")[0]
                msg_id = f"FT_{chunk_id}"
                self.ack_manager.ack_received(msg_id, from_call=src)
            except Exception:
                pass
            self.ft.handle_incoming(info, src, dest, parsed["digis"])
            return

        elif info.startswith("[EOF]"):
            self.ack_manager.ack_received("EOF_FINAL", from_call=src)
            self.ft.handle_incoming(info, src, dest, parsed["digis"])
            return

        elif info.startswith("[ACKFILE]"):
            log_raw_line(f"🟢 Received [ACKFILE] from {src}")
            if self.ack_manager.has("REQFILE_INIT"):
                self.ack_manager.ack_received("REQFILE_INIT", from_call=src)
                log_raw_line(f"✅ Marked REQFILE_INIT acknowledged from {src}")

            else:
                log_raw_line(f"⚠️ REQFILE_INIT not found in pending at time of ACKFILE from {src}")

            self.ft.handle_ack(info)
            return

        elif info.startswith("[ACK]"):
            ack_payload = info[5:].strip()

            if ":" in ack_payload:
                # It's a file chunk ACK like [ACK]0001:45
                chunk_id = ack_payload.split(":")[0]
                self.ack_manager.ack_received(f"FT_{chunk_id}", from_call=src)
            elif ack_payload == "FILE_INIT":
                self.ack_manager.ack_received("FILE_INIT", from_call=src)
            elif ack_payload == "EOF_FINAL":
                self.ack_manager.ack_received("EOF_FINAL", from_call=src)
            else:
                # It's a message ACK like [ACK]abc12345
                self.ack_manager.ack_received(ack_payload, from_call=src)

            self.ft.handle_ack(info)
            return


        elif info.startswith("[NACK]") or info.startswith("[NACKFILE]"):
            nack_id = info[6:].strip()
            self.ack_manager.ack_received(nack_id, from_call=src)
            self.gui.append_text(f"❌ Transfer failed or was declined: {nack_id}", "recv")
            return


        # 🟡 Auto reply with ACK (only if enabled)
        if "[MSGID]" in info and "|" in info and self.gui.acks_enabled_var.get():
            try:
                msg_id = info.split("[MSGID]")[1].split("|")[0]

                # 🛑 Don't ACK if we are the original sender
                if src.upper() == self.callsign.upper():
                    print(f"🛑 Skipping ACK to myself for msg_id {msg_id}")
                    return

                ack_line = f"[ACK]{msg_id}"
                self.send_ax25_frame(self.callsign, src, ack_line, ",".join(parsed["digis"]) if parsed["digis"] else None)
            except Exception as e:
                print("Auto ACK failed:", e)

        if src.upper() not in self.recalled_calls:
            self.gui.update_heard_station(src, dest, info)

        self.heard_stations[src.upper()] = datetime.now(timezone.utc).isoformat()
        save_heard_stations(self.heard_stations)

        self.recalled_calls.discard(src.upper())

        last_time, label_type = self.gui.heard_dict.get(src, (time(), ""))
        minutes_ago = int((time() - last_time) / 60)
        time_str = f"{minutes_ago} min ago" if minutes_ago > 0 else "just now"
        self.gui.last_heard_var.set(f"{src}")

        # Suppress echo
        if self.sent_messages and (src, dest, info) == self.sent_messages[-1]:
            return

        current_chat_partner = self.gui.dest_entry.get().strip().upper()


        # Only show messages directed to us (not to someone else or broadcast noise)
        if dest.upper() != self.callsign.upper():
            print(f"🔕 Ignoring message to {dest} (not to me: {self.callsign})")
            return

        # Log and display
        append_log(src.upper(), src.upper(), info)
        # 🧹 Strip [MSGID] from incoming messages for clean display
        if info.startswith("[MSGID]") and "|" in info:
            info = info.split("|", 1)[1]
        self.gui.append_text(f"{src}>{dest}{path_str}: {info}", "recv")

    def check_channel_clear(self):
        if time() - self.last_heard_time > 2:
            self.channel_busy = False


    def poll_ack_manager(self):
        self.ack_manager.tick()
        self.root.after(5000, self.poll_ack_manager)

    def send_file(self):
        from tkinter import filedialog
        filepath = filedialog.askopenfilename()
        if filepath:
            src = self.gui.callsign_label_var.get().upper()
            dest = self.gui.dest_entry.get().strip().upper()
            digi = self.gui.digi_entry.get().strip().upper() if self.gui.digi_entry.get().strip() else None
            self.ft.send_file(filepath, src, dest, digi)

    def stop_transmission(self):
        self.ft.stop()
        self.gui.status_var.set("Transmission stopped.")
        self.gui.append_text("Transmission stopped", "sent")


if __name__ == "__main__":
    app = PacketChatApp()
    app.root.mainloop()
