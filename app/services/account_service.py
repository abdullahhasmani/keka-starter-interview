"""Business rules live here. No HTTP, no FastAPI imports."""
import logging
import uuid
from decimal import Decimal

from app.errors import ConflictError, NotFoundError
from app.repository.in_memory import AccountRepository
from app.schemas import Account, CreateAccountRequest

log = logging.getLogger(__name__)


class AccountService:
    def __init__(self, repo: AccountRepository) -> None:
        self.repo = repo

    def create_account(self, req: CreateAccountRequest) -> Account:
        # check-then-write must be atomic, otherwise two concurrent requests
        # with the same name can both pass the duplicate check
        with self.repo.lock:
            if self.repo.find_by_owner(req.owner_name):
                log.warning("Rejected duplicate account for owner=%s", req.owner_name)
                raise ConflictError(f"Account for '{req.owner_name}' already exists")

            account = Account(
                id=str(uuid.uuid4()),
                owner_name=req.owner_name,
                balance=req.initial_balance,
            )
            self.repo.save(account)

        log.info("Created account id=%s owner=%s balance=%s",
                 account.id, account.owner_name, account.balance)
        return account

    def get_account(self, account_id: str) -> Account:
        account = self.repo.find_by_id(account_id)
        if account is None:
            log.info("Account not found id=%s", account_id)
            raise NotFoundError(f"Account '{account_id}' not found")
        return account

    def list_accounts(self) -> list[Account]:
        return self.repo.find_all()

    def deposit(self, account_id: str, amount: Decimal) -> Account:
        # amount > 0 is already enforced by DepositRequest.
        # read-modify-write under the lock so concurrent deposits can't lose an update
        with self.repo.lock:
            account = self.get_account(account_id)
            account.balance += amount
            self.repo.save(account)

        log.info("Deposited %s to account id=%s new_balance=%s",
                 amount, account.id, account.balance)
        return account
