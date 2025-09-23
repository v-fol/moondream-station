import json
import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

from .core.config import SERVICE_PORT


class SessionState:
    def __init__(self):
        self.session_dir = Path.home() / ".moondream-station" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.session_file = self.session_dir / "current.json"
        self.history_file = self.session_dir / "history.json"
        self.state = self._load_session()
        self.command_history = self._load_history()

    def _load_session(self) -> Dict[str, Any]:
        previous_session = {}
        if self.session_file.exists():
            try:
                with open(self.session_file) as f:
                    previous_session = json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        # Always create a new session on app launch, but preserve some data
        return {
            "started_at": datetime.now().isoformat(),
            "requests_processed": 0,
            "last_model": previous_session.get("last_model"),
            "last_port": previous_session.get("last_port", SERVICE_PORT),
            "session_id": str(int(time.time())),
        }

    def _load_history(self) -> list:
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def _save_session(self):
        try:
            with open(self.session_file, "w") as f:
                json.dump(self.state, f, indent=2)
        except IOError:
            pass

    def _save_history(self):
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.command_history[-1000:], f, indent=2)
        except IOError:
            pass

    def record_request(self, request_path: str):
        entry = {
            "request": request_path,
            "timestamp": datetime.now().isoformat(),
            "session_id": self.state["session_id"],
        }

        self.command_history.append(entry)
        self.state["requests_processed"] += 1

        if len(self.command_history) > 1000:
            self.command_history = self.command_history[-1000:]

        self._save_history()
        self._save_session()

    def set_last_model(self, model: str):
        self.state["last_model"] = model
        self._save_session()

    def set_last_port(self, port: int):
        self.state["last_port"] = port
        self._save_session()

    def get_recent_requests(self, limit: int = 10) -> list:
        return self.command_history[-limit:] if self.command_history else []

    def get_requests_last_24h(self) -> int:
        from datetime import datetime, timedelta

        if not self.command_history:
            return 0

        cutoff = datetime.now() - timedelta(hours=24)
        count = 0

        for entry in self.command_history:
            try:
                entry_time = datetime.fromisoformat(entry["timestamp"])
                if entry_time > cutoff:
                    count += 1
            except (ValueError, KeyError):
                continue

        return count


    def get_session_info(self) -> Dict[str, Any]:
        started = datetime.fromisoformat(self.state["started_at"])
        duration = datetime.now() - started

        return {
            "session_id": self.state["session_id"],
            "started_at": self.state["started_at"],
            "duration": str(duration).split(".")[0],
            "requests_processed": self.state["requests_processed"],
            "last_model": self.state["last_model"],
            "last_port": self.state["last_port"],
        }

    def clear_history(self):
        self.command_history = []
        self._save_history()
