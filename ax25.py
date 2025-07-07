# ax25.py

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

def ax25_ui_frame(dest, src, msg, digipeater=None):
    frame = bytearray()

    # Correct last-field logic
    frame += encode_call(dest, last=False)
    frame += encode_call(src, last=(digipeater is None))

    if digipeater:
        digis = digipeater.split(",") if isinstance(digipeater, str) else [digipeater]
        for i, digi in enumerate(digis):
            last = i == len(digis) - 1
            frame += encode_call(digi.strip(), last=last)

    frame += b'\x03'  # UI Frame
    frame += b'\xf0'  # No Layer 3
    frame += msg.encode('ascii')

    print(f"📤 Building AX.25 frame: SRC={src}, DEST={dest}, DIGI={digipeater}, MSG={msg}")
    return frame


def wrap_kiss(ax25_bytes):
    return b'\xC0\x00' + ax25_bytes + b'\xC0'

def decode_callsign(data):
    call = ''.join([chr(b >> 1) for b in data[:6]]).strip()
    ssid = (data[6] >> 1) & 0x0F
    if ssid:
        return f"{call}-{ssid}"
    return call
