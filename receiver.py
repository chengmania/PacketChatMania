from ax25 import decode_callsign
from chatlog import append_log

def parse_ax25_frame(data, my_callsign):
    if not (data.startswith(b'\xC0') and data.endswith(b'\xC0')):
        return None

    payload = data[2:-1]  # Remove KISS framing
    if len(payload) < 16:
        return None

    try:
        dest = decode_callsign(payload[0:7])
        src = decode_callsign(payload[7:14])

        digipeaters = []
        index = 14

        # Only parse digipeaters if the "last" bit is not set on the source field
        if not (payload[13] & 0x01):
            while index + 7 <= len(payload):
                addr = payload[index:index + 7]
                digipeaters.append(decode_callsign(addr))
                index += 7
                if addr[6] & 0x01:  # last address field
                    break

        if index + 2 > len(payload):
            return None

        control = payload[index]
        pid = payload[index + 1]
        info = payload[index + 2:].decode('ascii', errors='ignore')

        return {
            "src": src,
            "dest": dest,
            "digis": digipeaters,
            "info": info,
            "is_to_me": my_callsign == dest or my_callsign in digipeaters
        }
    except Exception as e:
        print(f"❌ Parse error: {e}")
        return None
