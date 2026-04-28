"""
Caching utility for intermediate agent results.
Avoids redundant API calls during the evaluation pipeline.
"""

import json
import hashlib
import os
import time
from typing import Any, Optional, Dict


class ResultCache:
    """In-memory + optional file-based cache for agent results."""

    def __init__(self, cache_dir: Optional[str] = None):
        self._memory: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self.cache_dir = cache_dir
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

    def _make_key(self, agent_name: str, input_hash: str) -> str:
        return f"{agent_name}_{input_hash}"

    def _hash_input(self, input_data: str) -> str:
        return hashlib.sha256(input_data.encode("utf-8")).hexdigest()[:16]

    def get(self, agent_name: str, input_data: str) -> Optional[Any]:
        """Retrieve cached result for an agent given input data."""
        key = self._make_key(agent_name, self._hash_input(input_data))

        # Check memory first
        if key in self._memory:
            return self._memory[key]

        # Check file cache
        if self.cache_dir:
            filepath = os.path.join(self.cache_dir, f"{key}.json")
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._memory[key] = data
                    return data
                except (json.JSONDecodeError, IOError):
                    pass

        return None

    def set(self, agent_name: str, input_data: str, result: Any) -> None:
        """Cache result for an agent."""
        key = self._make_key(agent_name, self._hash_input(input_data))
        self._memory[key] = result
        self._timestamps[key] = time.time()

        # Write to file cache
        if self.cache_dir:
            filepath = os.path.join(self.cache_dir, f"{key}.json")
            try:
                with open(filepath, "w", encoding="utf-8") as f:
                    if isinstance(result, str):
                        json.dump({"raw": result}, f, ensure_ascii=False, indent=2)
                    else:
                        json.dump(result, f, ensure_ascii=False, indent=2)
            except (IOError, TypeError):
                pass

    def clear(self) -> None:
        """Clear all cached data."""
        self._memory.clear()
        self._timestamps.clear()
        if self.cache_dir:
            for f in os.listdir(self.cache_dir):
                if f.endswith(".json"):
                    os.remove(os.path.join(self.cache_dir, f))

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        return {
            "entries": len(self._memory),
            "agents_cached": list(set(k.rsplit("_", 1)[0] for k in self._memory.keys())),
        }
