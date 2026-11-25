"""HTTP layer: parse request -> call service -> shape response. Keep it thin."""
from fastapi import APIRouter, Depends, status

from app.repository.in_memory import AccountRepository
from app.schemas import AccountResponse, CreateAccountRequest, DepositRequest
from app.services.account_service import AccountService

router = APIRouter(prefix="/api")

# single shared instances (in-memory storage must outlive each request)
_repo = AccountRepository()
_service = AccountService(_repo)


def get_service() -> AccountService:
    return _service


@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(req: CreateAccountRequest, service: AccountService = Depends(get_service)):
    return service.create_account(req).to_response()


# @router.get("/accounts/{account_id}", response_model=AccountResponse)
# def get_account(account_id: str, service: AccountService = Depends(get_service)):
#     return service.get_account(account_id).to_response()


# @router.get("/accounts", response_model=list[AccountResponse])
# def list_accounts(service: AccountService = Depends(get_service)):
#     return [account.to_response() for account in service.list_accounts()]


# @router.post("/accounts/{account_id}/deposit", response_model=AccountResponse)
# def deposit(account_id: str, req: DepositRequest, service: AccountService = Depends(get_service)):
#     return service.deposit(account_id, req.amount).to_response()
