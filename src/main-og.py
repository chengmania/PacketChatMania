from gui import PacketChatGUI
from tnc import TNCClient
from ax25 import ax25_ui_frame, wrap_kiss
from receiver import parse_ax25_frame
from config import load_config
from time import time
from beacon import BeaconManager
from chatlog import append_log
from heardlog import load_heard_stations
from heardlog import save_heard_stations
from datetime import datetime, timezone

from file_transfer import FileTransferManager
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
        self.tnc = TNCClient(
            on_data_received=self.handle_incoming_data,
            on_status_update=self.gui.status_var.set,
            set_connection_light=self.gui.set_connection_light
        )

        # Bind GUI events
        self.gui.connect_button.config(command=self.toggle_connection)
        self.gui.send_button.config(command=self.send_message)
        self.gui.stop_button.config(command=self.stop_transmission)
        self.gui.msg_entry.bind("<Return>", lambda e: self.send_message())

        # File Transfer Manager
        self.ft = FileTransferManager(
            send_fn=self.send_ax25_frame,
            status_fn=self.gui.status_var.set,
            append_fn=self.gui.append_text,
            progress_fn=self.gui.progress_var.set
        )

        self.gui.send_file_button.config(command=self.send_file)

        self.sent_messages = []

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
        self.beacon.reset_idle_timer()

        msg = self.gui.msg_entry.get().strip()
        if not msg or not self.tnc.running:
            return

        src = self.gui.callsign_label_var.get().upper()
        dest = self.gui.dest_entry.get().strip().upper()

        # If Unproto Mode is ON and destination is blank, default to CQ
        if not dest:
            dest = "CQ"
        digi = self.gui.digi_entry.get().upper() if self.gui.digi_entry.get().strip() else None

        if digi and not digi.isalnum():
            print(f"⚠️ Invalid digipeater: {digi} — ignoring.")
            digi = None
        frame = ax25_ui_frame(dest, src, msg, digipeater=digi)
        kiss = wrap_kiss(frame)
        self.tnc.send(kiss)
        self.sent_messages.append((src, dest, msg))
        if len(self.sent_messages) > 20:  # Limit history to avoid memory buildup
            self.sent_messages.pop(0)


        line = f"{src}>{dest},{digi}: {msg}" if digi else f"{src}>{dest}: {msg}"
        self.gui.append_text(line, "sent")
        self.gui.msg_entry.delete(0, "end")
        self.gui.set_rx_tx_light("red")
        self.root.after(300, lambda: self.gui.set_rx_tx_light("green"))
        append_log(dest.upper(), self.callsign.upper(), msg)


    def stop_transmission(self):
        self.gui.status_var.set("Transmission stopped by user.")
        self.gui.append_text("Stopped transmission", "sent")


    def send_ax25_frame(self, src, dest, msg, digi):
        from ax25 import ax25_ui_frame, wrap_kiss

        frame = ax25_ui_frame(dest, src, msg, digipeater=digi)
        kiss = wrap_kiss(frame)
        print(f"📤 [AX.25 SEND] {src} > {dest} via {digi or 'direct'}: {msg}")
        self.tnc.send(kiss)

    def send_file(self):
        self.beacon.reset_idle_timer()

        from tkinter import filedialog
        filepath = filedialog.askopenfilename()
        if not filepath:
            return

        src = self.gui.callsign_label_var.get().upper()
        dest = self.gui.dest_entry.get().upper()
        digi = self.gui.digi_entry.get().upper() if self.gui.digi_entry.get().strip() else None
        self.ft.send_file(filepath, src, dest, digi)

    def handle_incoming_data(self, data):
        parsed = parse_ax25_frame(data, self.callsign)

        print("📥 Incoming KISS Frame:", data.hex())
        if not parsed:
            print("⚠️ parse_ax25_frame() returned None")
            return

        print("✅ AX.25 Parsed:", parsed)

        if not parsed:
            return

        src = parsed["src"]
        dest = parsed["dest"]
        info = parsed["info"]
        path_str = "," + ",".join(parsed["digis"]) if parsed["digis"] else ""

        if self.gui.raw_text_area:
            self.gui.raw_text_area.config(state='normal')
            self.gui.raw_text_area.insert('end', f"[RAW] {src}>{dest}{path_str}: {info}\n")
            self.gui.raw_text_area.config(state='disabled')
            self.gui.raw_text_area.yview('end')

        # 🟡 ROUTE FILE TRANSFER MESSAGES
        if info.startswith("[REQFILE]") or info.startswith("[FILE]") or info.startswith("[DATA]") or info.startswith("[EOF]"):
            self.ft.handle_incoming(info, src, dest, parsed["digis"])
            return

        # 🟢 Handle ACK/NACK messages
        if info.startswith("[ACK]") or info.startswith("[NACK]") or info.startswith("[ACKFILE]"):
            self.ft.handle_ack(info)
            return

        if src.upper() not in self.recalled_calls:
            self.gui.update_heard_station(src, dest, info)
        #log heard stations
        self.heard_stations[src.upper()] = datetime.now(timezone.utc).isoformat()
        save_heard_stations(self.heard_stations)
        # Once heard again live, stop treating as recalled
        self.recalled_calls.discard(src.upper())

        last_time, label_type = self.gui.heard_dict.get(src, (time(), ""))
        minutes_ago = int((time() - last_time) / 60)
        time_str = f"{minutes_ago} min ago" if minutes_ago > 0 else "just now"
        self.gui.last_heard_var.set(f"{src}")

        # Only suppress echo if it matches the exact last message *we* sent
        if self.sent_messages and (src, dest, info) == self.sent_messages[-1]:
            return

        current_chat_partner = self.gui.dest_entry.get().strip().upper()

        # Only show messages directed to us (not to someone else or broadcast noise)
        if dest.upper() != self.callsign.upper():
            print(f"🔕 Ignoring message to {dest} (not to me: {self.callsign})")
            return

        append_log(src.upper(), src.upper(), info)
        self.gui.append_text(f"{src}>{dest}{path_str}: {info}", "recv")

if __name__ == "__main__":
    app = PacketChatApp()
    app.root.mainloop()
