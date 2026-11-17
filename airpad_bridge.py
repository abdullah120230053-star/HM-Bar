import json
import time
from contextlib import closing
from multiprocessing.shared_memory import SharedMemory
from pathlib import Path
from uuid import uuid4


AIRPAD_HOME = Path.home() / "RemoteHub"


class AirPadBridge:
    """Client for the installed AirPad companion's existing local desktop API."""

    def __init__(self, home=AIRPAD_HOME):
        self.home = home
        self.bridge = home / ".state" / "pairing"
        self.received = home / "Received"

    def request(self, command, timeout=1.3, **arguments):
        if not self.bridge.is_dir():
            return None
        key = uuid4()
        marker = self.bridge / f"pair-{key.hex}.request"
        payload = json.dumps({"command": command, **arguments}, ensure_ascii=False).encode("utf-8")
        if len(payload) >= 65536:
            raise ValueError("Too many files selected")
        with closing(SharedMemory(name=f"Local\\RemoteHub-{key.hex}", create=True, size=65536)) as reply:
            try:
                reply.buf[0] = 0
                reply.buf[1:len(payload) + 1] = payload
                marker.touch(exist_ok=False)
                until = time.monotonic() + timeout
                while reply.buf[0] != 1:
                    if time.monotonic() >= until:
                        return None
                    time.sleep(0.06)
                data = json.loads(bytes(reply.buf[1:]).partition(b"\x00")[0])
                if data.get("error"):
                    raise RuntimeError(data["error"])
                return data
            finally:
                marker.unlink(missing_ok=True)

    def phones(self):
        dashboard = self.request("dashboard")
        if dashboard is None:
            return None
        return {
            key: (info.get("name") or info.get("reported_name") or "Paired phone", tuple(info["routes"]))
            for key, info in dashboard.get("phones", {}).items() if info.get("routes")
        }

    def received_files(self):
        if not self.received.is_dir():
            return {}
        root = self.received.resolve()
        files = {}
        for path in root.iterdir():
            try:
                if path.is_file() and not path.is_symlink() and path.resolve().parent == root:
                    stat = path.stat()
                    files[path] = (stat.st_size, stat.st_mtime_ns)
            except OSError:
                continue
        return files
