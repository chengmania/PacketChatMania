import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from tkinter import messagebox, scrolledtext
import socket
import threading

class PacketChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AX.25 Packet ChatMania")
        self.socket = None
        self.connected = False

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        # Menu Bar
        menu = ttk.Menu(self.root)
        self.root.config(menu=menu)
        view_menu = ttk.Menu(menu, tearoff=0)
        menu.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show Raw Data", command=self.open_raw_window)

        self.raw_window = None
        self.raw_text_area = None

        # Top Frame
        top_frame = ttk.Frame(root, padding=5)
        top_frame.grid(row=0, column=0, sticky="ew")
        for i in range(8):
            top_frame.columnconfigure(i, weight=1)

        ttk.Label(top_frame, text="Host:").grid(row=0, column=0, sticky='e')
        self.host_entry = ttk.Entry(top_frame, width=12)
        self.host_entry.insert(0, "127.0.0.1")
        self.host_entry.grid(row=0, column=1, sticky='w')

        ttk.Label(top_frame, text="Port:").grid(row=0, column=2, sticky='e')
        self.port_entry = ttk.Entry(top_frame, width=6)
        self.port_entry.insert(0, "8001")
        self.port_entry.grid(row=0, column=3, sticky='w')

        ttk.Label(top_frame, text="Your Callsign:").grid(row=0, column=4, sticky='e')
        self.callsign_entry = ttk.Entry(top_frame, width=10)
        self.callsign_entry.grid(row=0, column=5, sticky='w')

        self.connect_button = ttk.Button(top_frame, text="Connect", bootstyle=SUCCESS, command=self.connect_to_direwolf)
        self.connect_button.grid(row=0, column=6, padx=10, sticky='w')

        ttk.Label(top_frame, text="To:").grid(row=1, column=0, sticky='e')
        self.dest_entry = ttk.Entry(top_frame, width=10)
        self.dest_entry.grid(row=1, column=1, sticky='w')

        ttk.Label(top_frame, text="Digi (optional):").grid(row=1, column=2, sticky='e')
        self.digi_entry = ttk.Entry(top_frame, width=12)
        self.digi_entry.grid(row=1, column=3, sticky='w')

        # Separator
        ttk.Separator(root).grid(row=1, column=0, sticky="ew", padx=5, pady=2)

        # Chat Text Area
        self.text_area = scrolledtext.ScrolledText(root, state='disabled', font=("Courier", 10))
        self.text_area.grid(row=2, column=0, sticky="nsew", padx=5, pady=2)
        self.text_area.tag_config("sent", foreground="blue")
        self.text_area.tag_config("recv", foreground="green")

        # Separator
        ttk.Separator(root).grid(row=3, column=0, sticky="ew", padx=5, pady=2)

        # Bottom Frame
        bottom_frame = ttk.Frame(root, padding=5)
        bottom_frame.grid(row=4, column=0, sticky="ew")
        bottom_frame.columnconfigure(0, weight=1)

        self.msg_entry = ttk.Entry(bottom_frame)
        self.msg_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.msg_entry.bind("<Return>", self.send_message)

        self.send_button = ttk.Button(bottom_frame, text="Send", bootstyle=PRIMARY, command=self.send_message)
        self.send_button.grid(row=0, column=1)

        # Status Bar
        self.status_var = ttk.StringVar(value="Not connected")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, anchor='w', bootstyle=INVERSE)
        self.status_bar.grid(row=5, column=0, sticky="ew")

    def connect_to_direwolf(self):
        if self.connected:
            return
        host = self.host_entry.get()
        port = int(self.port_entry.get())
        self.callsign = self.callsign_entry.get().upper()

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            self.connected = True
            self.status_var.set(f"Connected to {host}:{port} as {self.callsign}")
            threading.Thread(target=self.receive_loop, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))
            self.status_var.set("Connection failed")

    def receive_loop(self):
        while self.connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    continue

                # --- Raw window output ---
                if self.raw_text_area:
                    if data.startswith(b'\xC0') and data.endswith(b'\xC0'):
                        payload = data[2:-1]

                        if len(payload) >= 16:
                            dest = self.decode_callsign(payload[0:7])
                            src = self.decode_callsign(payload[7:14])
                            control = payload[14]
                            pid = payload[15]
                            info = payload[16:].decode(errors='ignore')

                            # Extract digipeater path
                            path = []
                            index = 14
                            while index + 7 <= len(payload):
                                addr = payload[index:index + 7]
                                if not addr:
                                    break
                                call = self.decode_callsign(addr)
                                path.append(call)
                                if addr[6] & 0x01:
                                    break
                                index += 7

                            path_str = f",{','.join(path)}" if path else ""
                            line = f"[RAW] {src}>{dest}{path_str}: {info}"
                        else:
                            line = f"[RAW] Short frame: {data.hex()}"
                    else:
                        line = f"[RAW] Non-UI Frame: {data.hex()}"

                    self.raw_text_area.config(state='normal')
                    self.raw_text_area.insert('end', line + '\n')
                    self.raw_text_area.config(state='disabled')
                    self.raw_text_area.yview('end')

                # --- Normal Chat Decode ---
                if data.startswith(b'\xC0') and data.endswith(b'\xC0'):
                    payload = data[2:-1]

                    if len(payload) >= 16:
                        dest = self.decode_callsign(payload[0:7])
                        src = self.decode_callsign(payload[7:14])
                        control = payload[14]
                        pid = payload[15]
                        info = payload[16:].decode(errors='ignore')

                        if self.callsign in (src, dest):
                            digipeater = ""
                            addr_end = 14
                            while addr_end + 7 <= len(payload) and not (payload[addr_end + 6] & 0x01):
                                addr_end += 7
                            if addr_end + 7 <= len(payload):
                                digi = self.decode_callsign(payload[addr_end:addr_end + 7])
                                digipeater = f",{digi}"

                            self.append_text(f"{src}>{dest}{digipeater}: {info}", "recv")

            except Exception as e:
                self.status_var.set(f"Receive error: {e}")
                break


    def send_message(self, event=None):
        if not self.connected:
            return
        msg = self.msg_entry.get().strip()
        if not msg:
            return

        src = self.callsign_entry.get().upper()
        dest = self.dest_entry.get().upper()
        digi = self.digi_entry.get().upper() if self.digi_entry.get().strip() else None

        ax25_frame = self.ax25_ui_frame(dest, src, msg, digipeater=digi)
        kiss_frame = b'\xC0\x00' + ax25_frame + b'\xC0'

        try:
            self.socket.send(kiss_frame)
            if digi:
                self.append_text(f"{src}>{dest},{digi}: {msg}", "sent")
            else:
                self.append_text(f"{src}>{dest}: {msg}", "sent")
        except Exception as e:
            self.status_var.set(f"Send failed: {e}")
        self.msg_entry.delete(0, 'end')

    def append_text(self, text, tag=None):
        self.text_area.config(state='normal')
        self.text_area.insert('end', text + '\n', tag)
        self.text_area.config(state='disabled')
        self.text_area.yview('end')

    def open_raw_window(self):
        import tkinter as tk  # ensure tk.Toplevel is available

        if self.raw_window is not None and tk.Toplevel.winfo_exists(self.raw_window):
            self.raw_window.lift()
            return

        self.raw_window = tk.Toplevel(self.root)
        self.raw_window.title("Raw Direwolf KISS Data")
        self.raw_window.geometry("600x300")

        self.raw_text_area = scrolledtext.ScrolledText(self.raw_window, state='disabled', font=("Courier", 9))
        self.raw_text_area.pack(fill='both', expand=True)

        def on_close():
            self.raw_window.destroy()
            self.raw_window = None
            self.raw_text_area = None

        self.raw_window.protocol("WM_DELETE_WINDOW", on_close)


    def decode_callsign(self, data):
        call = ''.join([chr(b >> 1) for b in data[:6]]).strip()
        ssid = (data[6] >> 1) & 0x0F
        if ssid:
            return f"{call}-{ssid}"
        return call

    def ax25_ui_frame(self, dest, src, msg, digipeater=None):
        def encode_call(call, last=False, repeated=False):
            call = call.ljust(6).upper()
            encoded = bytearray((ord(c) << 1) for c in call[:6])
            ssid = 0x60
            if last:
                ssid |= 0x01
            if repeated:
                ssid |= 0x80
            encoded.append(ssid)
            return encoded

        frame = bytearray()
        frame += encode_call(dest, last=False)
        frame += encode_call(src, last=False)

        if digipeater:
            frame += encode_call(digipeater, last=True)
        else:
            frame[-1] |= 0x01

        frame += b'\x03'
        frame += b'\xf0'
        frame += msg.encode('ascii')
        return frame

if __name__ == "__main__":
    app = PacketChatApp(ttk.Window(themename="journal"))
    app.root.mainloop()
