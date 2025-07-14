import time
from uuid import uuid4
from tnclog import log_raw_line

class AckManager:
    def __init__(self, send_fn, status_fn=None, debug_fn=None, alert_fn=None, my_call=None):

        self.send_fn = send_fn  # function(src, dest, msg, digi)
        self.status_fn = status_fn
        self.debug_fn = debug_fn or (lambda x: None)
        self.alert_fn = alert_fn or (lambda msg, tag=None: None)
        self.my_call = my_call or ""

        self.pending = {}  # msg_id -> metadata
        self.max_retries = 3
        self.timeout_sec = 10
        self.enabled = True  # global ACK control
        self.debug = False  # master debug toggle

    def generate_id(self):
        if not self.enabled:
            return None
        return str(uuid4())[:8]


    def ack_received(self, msg_id, from_call=None):
        if msg_id not in self.pending:
            msg = f"⚠️ Unknown ACK for {msg_id} — ignoring"
            self.debug_fn(msg)
            log_raw_line(msg)
            log_raw_line(f"⚠️ ACK for unknown or expired msg_id: {msg_id} (from {from_call})")

            return

        original = self.pending[msg_id]
        expected = original["dest"]

        # 🔒 Suppress self-heard ACK
        if from_call and from_call.upper() == self.my_call.upper():
            msg = f"❌ Ignoring ACK from self ({from_call})"
            self.debug_fn(msg)
            log_raw_line(f"[IGNORED ACK] {msg_id} from {from_call} (self-heard)")
            return

        # ❌ Suppress ACKs from unexpected stations
        if from_call and from_call.upper() != expected.upper():
            msg = f"❌ [IGNORED ACK] {msg_id} from {from_call} (expected {expected})"
            self.debug_fn(msg)
            log_raw_line(msg)
            return

        self.debug_fn(f"✅ ACK received for {msg_id} from {from_call or 'unknown'}")
        log_raw_line(f"[ACK] {msg_id} received from {from_call or 'unknown'}")

        self.pending[msg_id]["acknowledged"] = True


        if hasattr(self, "gui_ref") and hasattr(self.gui_ref, "sent_line_tags"):
            tag = self.gui_ref.sent_line_tags.get(msg_id)
            if tag and hasattr(self.gui_ref.gui, "mark_ack_received"):
                self.gui_ref.gui.mark_ack_received(tag, "✓")

        #del self.pending[msg_id]



    def tick(self):
        print(f"🔄 TICK: {len(self.pending)} pending messages")
        #for msg_id, info in self.pending.items():
        #    self.debug_fn(f"⏳ {msg_id}: age={time.time() - info['timestamp']:.2f}s, retries={info['retries']}")

        #for msg_id in list(self.pending):
        #   self.debug_fn(f"🕵️ Before tick: {msg_id} -> {self.pending[msg_id]}")

        now = time.time()
        expired_ids = []

        for msg_id, info in list(self.pending.items()):
            age = now - info["timestamp"]

            if age > self.timeout_sec:
                if info["retries"] >= self.max_retries:
                    if self.status_fn:
                        self.status_fn(f"❌ No ACK for {msg_id} after {info['retries']} retries")
                    self.alert_fn(f"[NOT DELIVERED] {info['src']} to {info['dest']}: {info['msg']}", "sent")
                    self.debug_fn(f"❌ Final fail for {msg_id} → {info['msg']}")
                    log_raw_line(f"[NOT DELIVERED] {info['src']} to {info['dest']}: {info['msg']}")
                    expired_ids.append(msg_id)
                else:
                    self.pending[msg_id]["retries"] += 1
                    msg_str = self.pending[msg_id]['msg']
                    retry_num = self.pending[msg_id]['retries']
                    self.debug_fn(f"🔁 Retry {retry_num}/{self.max_retries} for {msg_id} → {msg_str}")
                    log_raw_line(f"🔁 Retry {retry_num}/{self.max_retries} for {msg_id} → {msg_str}")

                    try:
                        self.send_fn(info["src"], info["dest"], info["msg"], info["digi"])
                        self.pending[msg_id]["timestamp"] = now
                        if self.status_fn:
                            self.status_fn(f"🔁 Retrying {msg_id} (attempt {self.pending[msg_id]['retries']} of {self.max_retries})")
                    except Exception as e:
                        if self.status_fn:
                            self.status_fn(f"⚠️ Retry for {msg_id} failed: {e}")

                    #self.debug_fn(f"🔍 Pending after retry for {msg_id}: {self.pending[msg_id]}")


        for msg_id in expired_ids:
            if self.pending.get(msg_id, {}).get("acknowledged"):
                self.debug_fn(f"✅ Skipping deletion for {msg_id}, already acknowledged")
                continue
            del self.pending[msg_id]


    def track(self, msg_id, src, dest, msg, digi=None, msg_type="msg", force=False):
        if self.debug:
            self.debug_fn(f"⏳ Tracking new message {msg_id}: {msg}")

        if not self.enabled and not force:
            return

        if msg_id in self.pending:
            self.debug_fn(f"⚠️ Overwriting existing pending msg_id: {msg_id}")

        self.pending[msg_id] = {
            "src": src,
            "dest": dest,
            "msg": msg,
            "digi": digi,
            "retries": 0,
            "timestamp": time.time(),
            "type": msg_type,
            "acknowledged": False  # ✅ This was missing!
        }


    def is_acknowledged(self, msg_id):
        if msg_id in self.pending:
            status = self.pending[msg_id].get("acknowledged", False)
            log_raw_line(f"🔍 Checking if {msg_id} is acknowledged → {status}")
            return status
        log_raw_line(f"🔍 is_acknowledged({msg_id}) → False (not tracked)")
        return False
        """Return True if message was ACK'd (and removed from retry queue)."""
        return msg_id not in self.tracked
