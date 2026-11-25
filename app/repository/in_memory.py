"""In-memory storage. Swappable for a real DB later without touching the service."""
import threading
from typing import Optional

from app.schemas import Account


class AccountRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Account] = {}
        # RLock so the service can hold it across a read-check-write sequence
        self.lock = threading.RLock()

    def save(self, account: Account) -> Account:
        with self.lock:
            self._by_id[account.id] = account
            return account

    def find_by_id(self, account_id: str) -> Optional[Account]:
        with self.lock:
            return self._by_id.get(account_id)

    def find_by_owner(self, owner_name: str) -> Optional[Account]:
        with self.lock:
            key = owner_name.lower()
            return next(
                (a for a in self._by_id.values() if a.owner_name.lower() == key), None
            )

    def find_all(self) -> list[Account]:
        with self.lock:
            return list(self._by_id.values())

    def clear(self) -> None:
        with self.lock:
            self._by_id.clear()
