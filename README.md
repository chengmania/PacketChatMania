# 📡 Packet ChatMania – AX.25 Acoustic Packet Chat Application

**Author**: Greg (KC3SMW)  
**License**: MIT  
**Platform**: Linux- currently
**Interface**: `ttkbootstrap` GUI (Tkinter)  
**Transport**: AX.25 over KISS TCP (e.g. Direwolf)

---

## 🧭 Overview

**PacketChat4** is a modern, lightweight ham radio packet chat application for acoustic and TNC-based communication using the AX.25 protocol. Designed for real-time messaging and file sharing(not implemented yet), it offers a clean GUI and robust features including:

- ✅ Real-time AX.25 chat over Direwolf or compatible KISS TNC
- ✅ Unproto support and digipeater routing
- ✅ Acoustic modem compatibility (mic/speaker-based)
- ✅ Heard stations list with clickable callsigns
- ✅ Auto-ACK and mailbox (in development)
- ✅ CQ calling and multi-operator support
- ✅ Modern `ttkbootstrap`-based GUI

---

## 🚀 Getting Started

### Requirements

- Python 3.10+
- `Tkinter` (comes with Python)
- `ttkbootstrap` (install via pip)
- A KISS-compatible TNC such as:
  - [Direwolf](https://github.com/wb2osz/direwolf)

```bash
pip install ttkbootstrap
```

## 🖥️ Features

| Feature                        | Status      | Notes |
|-------------------------------|-------------|-------|
| AX.25 message chat            | ✅ Complete |       |
| File transfer (chunked w/ ACK)| 🚧 Planned  | `[REQFILE]`, `[DATA]`, `[ACK]`, `[EOF]` |
| Heard Stations List           | ✅ Complete | Auto-updated, sorted |
| CQ calling                    | ✅ Basic    | Sends `CQ` broadcast |
| Settings persistence          | ✅ Complete | `config.ini` for callsign, theme, etc. |
| Unproto mode                  | ✅ Complete | Requires `Unproto` checkbox |
| Mailbox system                | 🚧 Planned  | One-to-one offline message store |
| CQ / Net control tools        | 🧪 Experimental | Multi-user interaction |

---

## 🔧 Configuration

Callsign must be set before transmitting or connecting to a TNC.  
Additional settings will be saved in `config.ini` (coming soon).

---

## 🛠️ Roadmap

- [x] Heard stations tracking
- [x] Reliable file transfers
- [x] Unproto/digipeater routing
- [X] Config.ini support
- [ ] Mailbox (local-only)
- [ ] Multi-op CQ/Nets

---

## 📜 License

MIT License. See `LICENSE` file.


## ▶️ Running the App (Linux & Windows)

You can run **PacketChat4** using a virtual environment (`venv`) for clean and isolated dependencies.

```bash
# 1. Clone the repository
git clone https://github.com/chengmania/PacketChatMania.git
cd PacketChatMania/src

# 2. Create a virtual environment
python3 -m venv .

# 3. Activate the virtual environment
# 🐧 Linux/macOS:
source ./bin/activate

# 🪟 Windows (Command Prompt):
# \Scripts\activate.bat

# 🪟 Windows (PowerShell):
# \Scripts\Activate.ps1

# 4. Install required packages
pip install -r requirements.txt

# 5. Run the application in Linux
python3 ./main.py

To Run the application in Windows
python main.py
```

💡 *To deactivate the virtual environment when you're done:*

```bash
deactivate
```

