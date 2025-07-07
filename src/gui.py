# gui.py
import tkinter as tk
from tkinter import scrolledtext, filedialog
import config
import ttkbootstrap as ttk
import time
from ttkbootstrap.constants import *
from chatlog import get_log

class PacketChatGUI:
    def __init__(self, root, on_beacon_toggle=None):
        self.root = root
        self.on_beacon_toggle = on_beacon_toggle
        self.root.title("Packet ChatMania")
        self.auto_ack_enabled_var = ttk.BooleanVar(value=False)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)



        # Menu
        menu = ttk.Menu(self.root)
        self.root.config(menu=menu)
        view_menu = ttk.Menu(menu, tearoff=0)
        menu.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show Raw TNC Data", command=self.open_raw_window)
        settings_menu = ttk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Settings", menu=settings_menu)
        settings_menu.add_command(label="Configure", command=self.open_configure_window)
        settings_menu.add_checkbutton(
            label="Auto ACK Incoming Messages",
            variable=self.auto_ack_enabled_var,
            onvalue=True,
            offvalue=False
        )

        self.raw_window = None
        self.raw_text_area = None

        # Top Frame
        #top_frame = ttk.Frame(self.root, padding=5)
        # --- Load config values ---
        config_data = config.load_config()
        tnc_config = config_data["TNC"]
        user_config = config_data["User"]

        # --- Top Container Frame ---
        top_container = ttk.Frame(self.root, padding=5)
        top_container.grid(row=0, column=0, sticky="ew")
        top_container.columnconfigure(0, weight=1)


        # --- Connection Info Frame ---
        connection_frame = ttk.Labelframe(top_container, text="TNC Info", padding=(10, 5))
        connection_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        connection_frame.columnconfigure((1, 3, 5), weight=1)

        self.host_label_var = tk.StringVar(value=tnc_config.get("host", "127.0.0.1"))
        self.port_label_var = tk.StringVar(value=tnc_config.get("port", "8001"))
        self.callsign_label_var = tk.StringVar(value=user_config.get("callsign", "N0CALL"))

        ttk.Label(connection_frame, text="Host:").grid(row=0, column=0, sticky="e", padx=(0, 5))
        ttk.Label(connection_frame, textvariable=self.host_label_var, width=14).grid(row=0, column=1, sticky="w")

        ttk.Label(connection_frame, text="Port:").grid(row=0, column=2, sticky="e", padx=(10, 5))
        ttk.Label(connection_frame, textvariable=self.port_label_var, width=6).grid(row=0, column=3, sticky="w")

        ttk.Label(connection_frame, text="Your Callsign:").grid(row=0, column=4, sticky="e", padx=(10, 5))
        ttk.Label(connection_frame, textvariable=self.callsign_label_var, width=10).grid(row=0, column=5, sticky="w")

        self.connect_button = ttk.Button(connection_frame, text="Connect TNC")
        self.connect_button.grid(row=0, column=6, padx=(10, 0), sticky="w")

        # --- Visual Separator ---
        ttk.Separator(top_container, orient='horizontal').grid(row=1, column=0, sticky="ew", pady=(5, 5))

        # --- Message Target Frame ---
        target_frame = ttk.Labelframe(top_container, text="Message Routing", padding=(10, 5))
        target_frame.grid(row=2, column=0, sticky="ew")
        target_frame.columnconfigure(5, weight=1)

        ttk.Label(target_frame, text="To:").grid(row=0, column=0, sticky='e', padx=(0, 5))
        self.dest_entry = ttk.Entry(target_frame, width=12)
        self.dest_entry.grid(row=0, column=1, sticky='w')

        ttk.Label(target_frame, text="Digi (optional):").grid(row=0, column=2, sticky='e', padx=(10, 5))
        self.digi_entry = ttk.Entry(target_frame, width=14)
        self.digi_entry.grid(row=0, column=3, sticky='w')

        self.cq_button = ttk.Button(target_frame, text="Send CQ", command=self.send_cq_message)
        self.cq_button.grid(row=0, column=6, padx=5, sticky="e")
        target_frame.columnconfigure(6, weight=1)  # Ensure rightward expansion for right-aligning

        # --- Another separator before the main text area ---
        ttk.Separator(self.root).grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        # --- Main Message + Heard Stations Frame ---
        message_container = ttk.Frame(self.root)
        message_container.grid(row=2, column=0, sticky="nsew")
        message_container.columnconfigure(0, weight=3)
        message_container.columnconfigure(1, weight=1)
        message_container.rowconfigure(0, weight=1)

        # --- Message Area (left side) ---
        self.text_area = scrolledtext.ScrolledText(message_container, state='disabled', font=("Courier", 10))
        self.text_area.grid(row=0, column=0, sticky="nsew", padx=(5, 2), pady=2)
        self.text_area.tag_config("sent", foreground="blue")
        self.text_area.tag_config("recv", foreground="green")

        # --- Heard Stations Panel (right side) ---
        heard_frame = ttk.Frame(message_container, padding=5)
        heard_frame.grid(row=0, column=1, sticky="nsew")

        ttk.Label(heard_frame, text="Heard Stations").pack(anchor="w")
        style = ttk.Style()
        style.configure("Treeview", font=("Courier", 10))
        style.configure("Treeview.Heading", font=("Courier", 10, "bold"))
        self.heard_tree = ttk.Treeview(heard_frame, columns=("when", "call", "type"), show="headings", height=15)

        style.map("Treeview", background=[("selected", "#cce5ff")])
        style.configure("Treeview", rowheight=22)
        self.heard_tree.heading("when", text="When")
        self.heard_tree.heading("call", text="Call")
        self.heard_tree.heading("type", text="Type")
        self.heard_tree.column("when", width=70, anchor="center", stretch=False)
        self.heard_tree.column("call", width=80, anchor="center", stretch=False)
        self.heard_tree.column("type", width=80, anchor="center", stretch=False)

        self.heard_tree.pack(fill="both", expand=True)

        # Click to route
        self.heard_tree.bind("<<TreeviewSelect>>", self.on_heard_click)

        # Store last heard times
        self.heard_dict = {}

        self.heard_messages = {}  # call -> message string
        self.tooltip = None       # Placeholder for tooltip window

        self.heard_tree.bind("<Motion>", self.on_heard_hover)
        self.heard_tree.bind("<Leave>", self.clear_tooltip)


        ttk.Separator(self.root).grid(row=3, column=0, sticky="ew", padx=5, pady=2)

        bottom_frame = ttk.Frame(self.root, padding=5)
        bottom_frame.grid(row=4, column=0, sticky="ew")
        bottom_frame.columnconfigure(0, weight=1)

        self.msg_entry = ttk.Entry(bottom_frame)
        self.msg_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))

        self.send_button = ttk.Button(bottom_frame, text="Send Msg")
        self.send_button.grid(row=0, column=1)

        self.send_file_button = ttk.Button(bottom_frame, text="Send File")
        self.send_file_button.grid(row=0, column=2, padx=(5, 0))

        self.progress_var = ttk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        # --- Status Bar Layout ---
        status_frame = ttk.Frame(self.root, padding=3)
        status_frame.grid(row=5, column=0, sticky="ew")

        # Left group (compact)
        left_group = ttk.Frame(status_frame)
        left_group.grid(row=0, column=0, sticky="w")
        ttk.Label(left_group, text="TNC").pack(side="left", padx=(2, 2))
        self.tnc_light = ttk.Canvas(left_group, width=16, height=16, highlightthickness=0)
        self.tnc_light.pack(side="left")
        self.tnc_circle = self.tnc_light.create_oval(2, 2, 14, 14, fill="red")

        ttk.Label(left_group, text=" RX/TX").pack(side="left", padx=(10, 2))
        self.rxtx_light = ttk.Canvas(left_group, width=16, height=16, highlightthickness=0)
        self.rxtx_light.pack(side="left")
        self.rxtx_circle = self.rxtx_light.create_oval(2, 2, 14, 14, fill="green")

        ttk.Label(left_group, text=" BCN").pack(side="left", padx=(10, 2))
        self.beacon_light = ttk.Canvas(left_group, width=16, height=16, highlightthickness=0)
        self.beacon_light.pack(side="left")
        self.beacon_circle = self.beacon_light.create_oval(2, 2, 14, 14, fill="gray")

        # Center (status text, fills remaining space)
        self.status_var = ttk.StringVar(value="Not connected")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor="center", justify="center")
        self.status_label.grid(row=0, column=1, sticky="ew", padx=10)
        status_frame.columnconfigure(1, weight=1)  # Center zone expands

        # Right group (Last heard)
        right_group = ttk.Frame(status_frame)
        right_group.grid(row=0, column=2, sticky="e", padx=(0, 10))
        ttk.Label(right_group, text="Last: ").pack(side="left", padx=(0, 2))
        self.last_heard_var = tk.StringVar(value="")
        self.last_heard_label = ttk.Label(right_group, textvariable=self.last_heard_var, anchor="w", justify="left", width=10)
        self.last_heard_label.pack(side="left")


        self.stop_button = ttk.Button(self.root, text="Stop Transmit", bootstyle=DANGER)
        self.stop_button.grid(row=7, column=0, sticky="ew", padx=5, pady=(0,5))
        self.stop_button.config(state='disabled')

        self.refresh_heard_times()

    def set_connection_light(self, color):
        self.tnc_light.itemconfig(self.tnc_circle, fill=color)

    def set_rx_tx_light(self, color):
        self.rxtx_light.itemconfig(self.rxtx_circle, fill=color)

    def set_beacon_light(self, color):
        self.beacon_light.itemconfig(self.beacon_circle, fill=color)


    def send_cq_message(self):
        msg = self.config.get("User", "cq_message", fallback=f"CQ CQ CQ de {self.callsign}")
        dest = "CQ"
        digi = self.digi_entry.get().strip() or None
        self.msg_entry.delete(0, "end")
        self.dest_entry.delete(0, "end")
        self.dest_entry.insert(0, dest)
        self.msg_entry.insert(0, msg)
        self.send_button.invoke()


    def append_text(self, text, tag=None):
        self.text_area.config(state='normal')
        self.text_area.insert('end', text + '\n', tag)
        self.text_area.config(state='disabled')
        self.text_area.yview('end')

    def open_raw_window(self):
        if self.raw_window is not None and tk.Toplevel.winfo_exists(self.raw_window):
            self.raw_window.lift()
            return

        self.raw_window = tk.Toplevel(self.root)
        self.raw_window.title("Raw TNC Data")
        self.raw_window.geometry("600x300")

        self.raw_text_area = scrolledtext.ScrolledText(self.raw_window, state='disabled', font=("Courier", 9))
        self.raw_text_area.pack(fill='both', expand=True)

        def on_close():
            self.raw_window.destroy()
            self.raw_window = None
            self.raw_text_area = None

        self.raw_window.protocol("WM_DELETE_WINDOW", on_close)

    def open_configure_window(self):
        config_data = config.load_config()
        tnc_config = config_data["TNC"]
        user_config = config_data["User"]
        beacon_config = config_data["Beacon"]


        config_win = tk.Toplevel(self.root)
        config_win.title("Configure")
        config_win.geometry("300x580")
        config_win.resizable(False, False)

        ttk.Label(config_win, text="TNC Host:").pack(pady=(10, 0))
        host_var = tk.StringVar(value=tnc_config.get("host", "127.0.0.1"))
        host_entry = ttk.Entry(config_win, textvariable=host_var)
        host_entry.pack(padx=10)

        ttk.Label(config_win, text="TNC Port:").pack(pady=(10, 0))
        port_var = tk.StringVar(value=tnc_config.get("port", "8001"))
        port_entry = ttk.Entry(config_win, textvariable=port_var)
        port_entry.pack(padx=10)

        ttk.Label(config_win, text="Your Callsign:").pack(pady=(10, 0))
        callsign_var = tk.StringVar(value=user_config.get("callsign", "N0CALL"))
        callsign_entry = ttk.Entry(config_win, textvariable=callsign_var)
        callsign_entry.pack(padx=10)

        ttk.Label(config_win, text="CQ Message:").pack(pady=(10, 0))
        cq_msg_var = tk.StringVar(value=user_config.get("cq_message", f"CQ CQ CQ de {callsign_var.get()}"))
        cq_msg_entry = ttk.Entry(config_win, textvariable=cq_msg_var)
        cq_msg_entry.pack(padx=10)

        beacon_enabled_var = tk.BooleanVar(value=beacon_config.get("enabled", "false").lower() == "true")
        beacon_interval_var = tk.StringVar(value=beacon_config.get("interval", "15"))
        beacon_message_var = tk.StringVar(value=beacon_config.get("message", "ChatMania App with mailbox"))
        beacon_digi_var = tk.StringVar(value=beacon_config.get("digipeater", ""))

        ttk.Label(config_win, text="Enable Beaconing:").pack(pady=(10, 0))
        ttk.Checkbutton(config_win, variable=beacon_enabled_var).pack()

        ttk.Label(config_win, text="Beacon Interval (min):").pack(pady=(10, 0))
        ttk.Entry(config_win, textvariable=beacon_interval_var).pack(padx=10)

        ttk.Label(config_win, text="Beacon Message:").pack(pady=(10, 0))
        ttk.Entry(config_win, textvariable=beacon_message_var).pack(padx=10)

        ttk.Label(config_win, text="Beacon Digipeater (optional):").pack(pady=(10, 0))
        ttk.Entry(config_win, textvariable=beacon_digi_var).pack(padx=10)

        def save_and_close():
            new_config = {
                "TNC": {
                    "host": host_var.get(),
                    "port": port_var.get()
                },
                "User": {
                    "callsign": callsign_var.get(),
                    "cq_message": cq_msg_var.get()
                },
                 "Beacon": {
                    "enabled": str(beacon_enabled_var.get()).lower(),
                    "interval": beacon_interval_var.get(),
                    "message": beacon_message_var.get(),
                    "digipeater": beacon_digi_var.get()
                }
            }
            old_enabled = self.config.getboolean("Beacon", "enabled", fallback=False)
            new_enabled = beacon_enabled_var.get()

            config.save_config(new_config)
            # Update main display if needed
            self.host_label_var.set(new_config["TNC"]["host"])
            self.port_label_var.set(new_config["TNC"]["port"])
            self.callsign_label_var.set(new_config["User"]["callsign"])
            self.config["User"]["cq_message"] = cq_msg_var.get()
            self.config["Beacon"]["enabled"] = str(beacon_enabled_var.get()).lower()
            self.config["Beacon"]["interval"] = beacon_interval_var.get()
            self.config["Beacon"]["message"] = beacon_message_var.get()
            self.config["Beacon"]["digipeater"] = beacon_digi_var.get()

            # Update beacon light
            self.set_beacon_light("green" if new_enabled else "gray")

            # ✅ Call main app to start/stop beacon manager
            if hasattr(self, "on_beacon_toggle") and callable(self.on_beacon_toggle):
                if old_enabled != new_enabled:
                    self.on_beacon_toggle(new_enabled)


            config_win.destroy()

        ttk.Button(config_win, text="Save", command=save_and_close).pack(pady=10)

    def on_heard_click(self, event):
        selected = self.heard_tree.selection()
        if not selected:
            return

        item = self.heard_tree.item(selected[0])
        callsign = item["values"][1]

        # Set destination field
        self.dest_entry.delete(0, "end")
        self.dest_entry.insert(0, callsign)

        # Load chat log
        log_text = get_log(callsign)

        # Display in receive window
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", "end")
        self.text_area.insert("end", f"Chat log with {callsign}:\n\n{log_text}")
        self.text_area.config(state="disabled")


    def update_heard_station(self, call, to_field, message=None, force_when=None):
        now = time.time()
        to_field = to_field.upper()
        my_call = self.callsign.upper()

        if to_field in {"CQ", "ALL", "QST", "BEACON", "ID"}:
            label_type = to_field
        elif to_field == my_call:
            label_type = f"→ {my_call}"
        else:
            label_type = f"→ {to_field}"  # Optional: show all routing
            # return  # ← Uncomment to strictly filter out other-to-other traffic

        if message:
            self.heard_messages[call] = message

        if not force_when:
            self.heard_dict[call] = (now, label_type)

        # Remove any existing entry for this call
        for iid in self.heard_tree.get_children():
            if self.heard_tree.item(iid)["values"][1] == call:
                self.heard_tree.delete(iid)

        if force_when:
            time_str = force_when
        else:
            minutes_ago = int((time.time() - now) / 60)
            time_str = f"{minutes_ago} min" if minutes_ago > 0 else "now"
        self.heard_tree.insert("", 0, values=(time_str, call, label_type))

    def refresh_heard_times(self):
        now = time.time()

        for iid in self.heard_tree.get_children():
            call = self.heard_tree.item(iid)["values"][1]  # callsign column
            if call in self.heard_dict:
                last_time, label_type = self.heard_dict[call]
                minutes_ago = int((now - last_time) / 60)
                time_str = f"{minutes_ago} min" if minutes_ago > 0 else "now"
                self.heard_tree.item(iid, values=(time_str, call, label_type))

        # Schedule again in 60 seconds
        self.root.after(60000, self.refresh_heard_times)

    def on_heard_hover(self, event):
        region = self.heard_tree.identify("region", event.x, event.y)
        if region != "cell":
            self.clear_tooltip()
            return

        row_id = self.heard_tree.identify_row(event.y)
        if not row_id:
            self.clear_tooltip()
            return

        call = self.heard_tree.item(row_id)["values"][1]
        msg = self.heard_messages.get(call)
        if not msg:
            self.clear_tooltip()
            return

        if self.tooltip:
            self.tooltip.destroy()

        self.tooltip = tk.Toplevel(self.heard_tree)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{event.x_root + 20}+{event.y_root + 10}")
        label = tk.Label(self.tooltip, text=msg, background="lightyellow", relief="solid", borderwidth=1, font=("Courier", 9), padx=5, pady=2)
        label.pack()

    def clear_tooltip(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

