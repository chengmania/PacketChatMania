# 📡 PacketChat4 – AX.25 Acoustic Packet Chat Application

**Author**: Greg (KC3SMW)  
**License**: MIT  
**Platform**: Cross-platform (Linux, Windows)  
**Interface**: `ttkbootstrap` GUI (Tkinter)  
**Transport**: AX.25 over KISS TCP (e.g. Direwolf)

---

## 🧭 Overview

**PacketChat4** is a modern, lightweight ham radio packet chat application for acoustic and TNC-based communication using the AX.25 protocol. Designed for real-time messaging and file sharing, it offers a clean GUI and robust features including:

- ✅ Real-time AX.25 chat over Direwolf or compatible KISS TNC
- ✅ Unproto support and digipeater routing
- ✅ File transfers with ACK/NACK, progress bar, and retry logic
- ✅ Acoustic modem compatibility (mic/speaker-based)
- ✅ Heard stations list with clickable callsigns
- ✅ Auto-ACK and mailbox (in development)
- ✅ CQ calling and multi-operator support
- ✅ Modern `ttkbootstrap`-based GUI

---

## 🚀 Getting Started

### Requirements

- Python 3.10+
- Tkinter (comes with Python)
- `ttkbootstrap`
- A KISS-compatible TNC (e.g., **Direwolf**, `kissattach`, etc.)

### Installation

1. Clone the repository:

```bash
git clone https://github.com/yourusername/PacketChat.git
cd PacketChat
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python3 main.py
```

---

## 🖥️ Features

| Feature                        | Status      | Notes |
|-------------------------------|-------------|-------|
| AX.25 message chat            | ✅ Complete |       |
| File transfer (chunked w/ ACK)| ✅ Complete | `[REQFILE]`, `[DATA]`, `[ACK]`, `[EOF]` |
| Heard Stations List           | ✅ Complete | Auto-updated, sorted |
| CQ calling                    | ✅ Basic    | Sends `CQ` broadcast |
| Unproto mode                  | ✅ Complete | Requires `Unproto` checkbox |
| Auto-ACK                      | ✅ Optional | Toggle in GUI settings |
| Mailbox system                | 🚧 Planned  | One-to-one offline message store |
| Settings persistence          | 🚧 Planned  | `config.ini` for callsign, theme, etc. |
| CQ / Net control tools        | 🧪 Experimental | Multi-user interaction |

---

## 📁 File Structure

```
src/
├── main.py          # Launches the app
├── gui.py           # GUI layout (Tkinter + ttkbootstrap)
├── receiver.py      # KISS/AX.25 receive loop and decoding
├── ax25.py          # AX.25 frame construction/decoding
├── filetransfer.py  # File sending logic with ACK/NACK
├── config.py        # User config management (coming soon)
├── utils.py         # Utility functions (optional)
└── README.md
```

---

## 🔧 Configuration

Callsign must be set before transmitting or connecting to a TNC.  
Additional settings will be saved in `config.ini` (coming soon).

---

## 🗃️ File Transfer Protocol

1. Sender sends `[REQFILE] filename.ext`
2. Receiver replies with `[ACKFILE]` or `[NACKFILE]`
3. File is sent in `[DATA]{chunk_id}:{hex}` chunks
4. Each chunk must be acknowledged with `[ACK]{chunk_id}:{percent}`  
5. `[EOF]` marks the end of file

---

## 🛠️ Roadmap

- [x] Heard stations tracking
- [x] Reliable file transfers
- [x] Unproto/digipeater routing
- [ ] Config.ini support
- [ ] Mailbox (local-only)
- [ ] Multi-op CQ/Nets
- [ ] Offline message history view

---

## 📜 License

MIT License. See `LICENSE` file.
