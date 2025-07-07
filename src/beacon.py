# beacon.py

import time
import threading

class BeaconManager:
    def __init__(self, send_fn, get_callsign_fn, get_enabled_fn, get_interval_fn, get_message_fn, get_digipeater_fn):
        """
        send_fn(src, dest, msg, digi) → callable to send AX.25 frame
        get_callsign_fn() → returns current station callsign
        get_enabled_fn() → returns True/False if beaconing is enabled
        get_interval_fn() → returns interval in minutes
        get_message_fn() → returns beacon message string
        """
        self.send_fn = send_fn
        self.get_callsign = get_callsign_fn
        self.get_enabled = get_enabled_fn
        self.get_interval = get_interval_fn
        self.get_message = get_message_fn
        self.get_digipeater = get_digipeater_fn

        self._last_tx_time = time.time()
        self._thread = None
        self._stop_event = threading.Event()

    def start(self):
        self._stop_event.clear()
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self._stop_event.set()

    def reset_idle_timer(self):
        self._last_tx_time = time.time()

    def _run_loop(self):
        while not self._stop_event.is_set():
            if not self.get_enabled():
                time.sleep(10)
                continue

            idle_time = time.time() - self._last_tx_time
            interval = self.get_interval() * 60  # convert minutes to seconds

            if idle_time >= interval:
                self._send_beacon()
                self._last_tx_time = time.time()

            time.sleep(5)

    def _send_beacon(self):
        callsign = self.get_callsign()
        message = self.get_message()
        if callsign and message:
            print(f"📡 Sending beacon: {callsign}>BEACON: {message}")
            digi = self.get_digipeater()
            self.send_fn(callsign, "BEACON", message, digi=digi)
