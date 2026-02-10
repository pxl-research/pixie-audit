from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any


class _FakeAcquire:
    def __init__(self, conn: "FakeConnection") -> None:
        self._conn = conn

    async def __aenter__(self) -> "FakeConnection":
        return self._conn

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeTransaction:
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


@dataclass
class FakeConnection:
    fetch_results: list[list[dict[str, Any]]] = field(default_factory=list)
    executed: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)
    fetch_calls: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)

    async def execute(self, sql: str, *params: Any) -> str:
        self.executed.append((sql, params))
        return "OK"

    async def fetch(self, sql: str, *params: Any) -> list[dict[str, Any]]:
        self.fetch_calls.append((sql, params))
        if self.fetch_results:
            return self.fetch_results.pop(0)
        return []

    def transaction(self) -> _FakeTransaction:
        return _FakeTransaction()


@dataclass
class FakePool:
    conn: FakeConnection

    def acquire(self) -> _FakeAcquire:
        return _FakeAcquire(self.conn)


def make_request(pool: FakePool) -> Any:
    return SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(db=pool)))
