# FastAPI Interview Reference

Nov 25, 2026 · @Abd

## 1. How a request flows

Every request passes through four layers: HTTP (routes), business rules (service), storage (repository), and error mapping (main). Each layer only talks to the one below it.

&#91;embedded content: request flow · 5 layers, 2 error exits\]

Bad input never reaches the route body; a raised domain error skips straight to its handler in main.py.

| File | Layer | What it does | Say this out loud |
| --- | --- | --- | --- |
| `app/main.py` | Wiring | Creates `app`, attaches the router, logging middleware, exception handlers | "main maps domain errors to HTTP codes, so the service never knows about HTTP" |
| `app/api/routes.py` | HTTP | Parses the request, calls the service, shapes the response. Thin. | "Routes are 2–3 lines: no business logic here" |
| `app/services/*_service.py` | Business rules | Checks rules, raises domain errors, logs decisions. No FastAPI imports. | "The rules are plain Python, so they're testable without HTTP" |
| `app/repository/in_memory.py` | Storage | Dict + lock. Only stores and fetches. | "Swappable for a database without touching the service" |
| `app/schemas.py` | Contract | Pydantic request/response models (validated) + dataclass domain model | "Validation happens before my code runs" |
| `app/errors.py` | Errors | `DomainError` subclasses, each with a status code | "One handler covers every error type" |
| `app/logging_config.py` | Logging | Console logs: time, level, module, message |  |

Run it: `uvicorn app.main:app --reload` means "in `app/main.py`, find the variable `app`". Swagger UI is free at http://localhost:8000/docs.

## 2. FastAPI cheat sheet

FastAPI decides where each parameter comes from by its type and name. That one rule explains most surprises.

### Where parameters come from

| Parameter looks like | FastAPI reads it from | Example |
| --- | --- | --- |
| Name matches `{...}` in the path | Path | `def get(account_id: str)` on `/accounts/{account_id}` |
| Type is a Pydantic `BaseModel` | JSON body | `def create(req: CreateAccountRequest)` |
| Plain `int` / `float` / `str` / `bool` | Query string (`?x=1`) | `def list(limit: int = 10)` |
| `Header()` | Request header | `idempotency_key: str \| None = Header(None)` |
| `Depends(fn)` | FastAPI calls `fn()` and passes the result | `service: AccountService = Depends(get_service)` |

Trap: `amount: float` as a plain parameter is a **query** param, not the body. Wrap it in a model.

### A route

```python
router = APIRouter(prefix="/api")

@router.post("/accounts", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(req: CreateAccountRequest, service: AccountService = Depends(get_service)):
    return service.create_account(req).to_response()

@router.get("/accounts/{account_id}", response_model=AccountResponse)
def get_account(account_id: str, service: AccountService = Depends(get_service)):
    return service.get_account(account_id).to_response()

@router.get("/accounts", response_model=list[AccountResponse])
def list_accounts(service: AccountService = Depends(get_service)):
    return [a.to_response() for a in service.list_accounts()]
```

- `response_model` filters and serialises the return value to JSON.
- `status_code` sets the success code (default 200; use 201 for create).
- Use plain `def` for routes. FastAPI runs them in a thread pool, which is why storage needs a lock.

### Status codes to use

| Code | When |
| --- | --- |
| 200 OK | Read or update succeeded |
| 201 Created | POST created something |
| 204 No Content | DELETE succeeded, no body |
| 400 Bad Request | Malformed JSON, wrong type, missing or invalid field |
| 403 Forbidden | Known user, not allowed (e.g. not the manager) |
| 404 Not Found | ID doesn't exist |
| 409 Conflict | Duplicate, or wrong state (approving twice) |
| 422 Unprocessable | Valid input that breaks a business rule (insufficient balance) |
| 500 | A bug. Never return it on purpose. |

### Middleware and exception handlers (in main.py)

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)   # the route runs here
    log.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response

@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError):
    return JSONResponse(status_code=exc.status_code,
                        content={"error": {"code": exc.code, "message": exc.message}})
```

- Middleware wraps every request: code before `call_next` runs first, code after runs once the route finishes.
- Exception handlers turn a raised Python exception into an HTTP response. Three exist: `DomainError` (yours), `RequestValidationError` (Pydantic, mapped to 400), `Exception` (bugs, 500 + stack trace).

## 3. Pydantic cheat sheet

Put input validation in the schema. Bad input then never reaches your code and comes back as 400 automatically.

### Request model

```python
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator, model_validator

class CreateAccountRequest(BaseModel):
    owner_name: str = Field(min_length=1, max_length=100)              # required (no default)
    initial_balance: Decimal = Field(default=Decimal("0"), ge=0, decimal_places=2)  # optional

    @field_validator("owner_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("owner_name must not be blank")   # OK here: Pydantic turns it into a 400
        return v
```

### Field constraints

| Type | Constraints |
| --- | --- |
| Numbers | `gt=0` (>), `ge=0` (>=), `lt`, `le`, `decimal_places=2`, `max_digits` |
| Strings | `min_length`, `max_length`, `pattern=r"^[A-Z]{3}$"` |
| Lists | `min_length`, `max_length` |
| Optional | `x: str \| None = None` |

### Cross-field rule (start <= end)

```python
from datetime import date

class LeaveRequest(BaseModel):
    start_date: date          # "2026-12-01" parses automatically
    end_date: date

    @model_validator(mode="after")
    def check_range(self):
        if self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self
```

### Fixed choices: Enum

```python
from enum import Enum

class Decision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

class DecisionRequest(BaseModel):
    approver_id: str = Field(min_length=1)
    decision: Decision        # anything else -> 400
```

### Three kinds of model

| Model | Tool | Purpose |
| --- | --- | --- |
| Request (`CreateAccountRequest`) | Pydantic `BaseModel` | What the client sends. Validated. No `id`, no `created_at`. |
| Domain (`Account`) | `@dataclass` | What you store. Can hold internal fields. Not validated. |
| Response (`AccountResponse`) | Pydantic `BaseModel` | What the client gets back. |

```python
@dataclass
class Account:
    id: str
    owner_name: str
    balance: Decimal
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

`default_factory` runs per object. Writing `= datetime.now()` would give every account the same timestamp.

## 4. Errors and status codes

The service raises a domain error; one handler in `main.py` turns it into JSON with the right status. Never raise a plain `ValueError` from the service: it becomes a 500.

```python
class DomainError(Exception):
    status_code = 400
    code = "BAD_REQUEST"
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

class NotFoundError(DomainError):     status_code, code = 404, "NOT_FOUND"
class ConflictError(DomainError):     status_code, code = 409, "CONFLICT"
class BusinessRuleError(DomainError): status_code, code = 422, "BUSINESS_RULE_VIOLATION"
```

Adding one takes three lines and no new handler:

```python
class ForbiddenError(DomainError):
    status_code = 403
    code = "FORBIDDEN"
```

Every error response has the same shape:

```json
{"error": {"code": "NOT_FOUND", "message": "Account 'x' not found"}}
```

| Situation | Who catches it | Status |
| --- | --- | --- |
| Malformed JSON, wrong type, missing field, failed `Field` constraint | Pydantic, before your code | 400 `VALIDATION_ERROR` |
| ID doesn't exist | Service raises `NotFoundError` | 404 |
| Not allowed (wrong approver) | Service raises `ForbiddenError` | 403 |
| Duplicate, or wrong state | Service raises `ConflictError` | 409 |
| Valid input, breaks a rule (insufficient balance) | Service raises `BusinessRuleError` | 422 |
| Anything else (`ValueError`, `TypeError`, ...) | Catch-all handler | 500 + stack trace in log |

Where does a check go? Shape of one field or one request (positive, not blank, start <= end) goes in the **schema**. Anything needing stored data (exists, balance, duplicate, state) goes in the **service**.

## 5. Service and storage patterns

Any read-check-write sequence must hold the lock from the first read to the last write. Otherwise two concurrent requests can both pass the check.

### Repository: only stores and fetches

```python
class AccountRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, Account] = {}
        self.lock = threading.RLock()     # RLock: same thread can take it again

    def save(self, account: Account) -> Account:
        with self.lock:
            self._by_id[account.id] = account
            return account

    def find_by_id(self, account_id: str) -> Account | None:
        with self.lock:
            return self._by_id.get(account_id)
```

No business rules here (no `balance += amount`). Pick the dict key by how you look things up; add a second dict as an index if you search by another field often.

### Service: rules under the lock

```python
class AccountService:
    def __init__(self, repo: AccountRepository) -> None:
        self.repo = repo                  # given, not created: tests can pass a fresh one

    def get_account(self, account_id: str) -> Account:
        account = self.repo.find_by_id(account_id)
        if account is None:
            log.info("Account not found id=%s", account_id)
            raise NotFoundError(f"Account '{account_id}' not found")
        return account

    def deposit(self, account_id: str, amount: Decimal) -> Account:
        with self.repo.lock:
            account = self.get_account(account_id)
            account.balance += amount
            self.repo.save(account)
        log.info("Deposited %s to account id=%s new_balance=%s", amount, account.id, account.balance)
        return account
```

### Transfer: check everything, then change everything

```python
def transfer(self, from_id: str, to_id: str, amount: Decimal) -> None:
    if from_id == to_id:
        raise BusinessRuleError("Cannot transfer to the same account")
    with self.repo.lock:
        src = self.get_account(from_id)
        dst = self.get_account(to_id)
        if src.balance < amount:
            log.warning("Insufficient balance account=%s needed=%s had=%s", src.id, amount, src.balance)
            raise BusinessRuleError("Insufficient balance")
        src.balance -= amount             # no raise possible after this point,
        dst.balance += amount             # so both change or neither does
    log.info("Transferred %s from=%s to=%s", amount, from_id, to_id)
```

### Singletons at module level

```python
# routes.py, created once when the module loads
_repo = AccountRepository()
_service = AccountService(_repo)

def get_service() -> AccountService:
    return _service
```

Creating them inside a route would give each request a new, empty dict.

### Why RLock and not Lock

The service holds the lock and then calls `repo.find_by_id`, which takes the same lock again. A plain `Lock` would wait on itself forever (deadlock). `RLock` lets the same thread re-enter.

## 6. Logging rules

Log business decisions in the service at the right level, with IDs and `%s` placeholders.

```python
import logging
log = logging.getLogger(__name__)     # top of every file; shows [app.services.account_service]
```

| Level | When | Example |
| --- | --- | --- |
| `log.info` | Business event succeeded | `log.info("Created leave request id=%s employee=%s days=%s", r.id, r.employee_id, days)` |
| `log.warning` | Request rejected by a rule | `log.warning("Insufficient balance account=%s needed=%s had=%s", a.id, amount, a.balance)` |
| `log.exception` | Real failure; prints the stack trace | Only in the catch-all handler |
| `log.debug` | Noisy detail, hidden at INFO | Rarely needed in the interview |

- Use `%s` placeholders, not f-strings: the string is only built if the line is printed.
- Log IDs, not whole objects. Never log passwords, tokens or personal data.
- The middleware already logs every request with method, path, status and time, so don't repeat that in routes.
- Pydantic validation failures are already logged as WARNING by the handler in `main.py`.

## 7. Adding an endpoint: the 4-step loop

Schema, error, service, route, then call it straight away. Worked example: `POST /api/accounts/{id}/deposit` with body `{"amount": 100}`.

1. **Schema** (`schemas.py`): request model with constraints.

   ```python
   class DepositRequest(BaseModel):
       amount: Decimal = Field(gt=0, decimal_places=2)
   ```
2. **Error** (`errors.py`): reuse what exists. Deposit needs only `NotFoundError`, so nothing new.
3. **Service** (`services/account_service.py`): the rule, under the lock, with a log line.

   ```python
   def deposit(self, account_id: str, amount: Decimal) -> Account:
       with self.repo.lock:
           account = self.get_account(account_id)   # 404 if missing
           account.balance += amount
           self.repo.save(account)
       log.info("Deposited %s to account id=%s new_balance=%s", amount, account.id, account.balance)
       return account
   ```
4. **Route** (`api/routes.py`): three lines; import the new schema.

   ```python
   @router.post("/accounts/{account_id}/deposit", response_model=AccountResponse)
   def deposit(account_id: str, req: DepositRequest, service: AccountService = Depends(get_service)):
       return service.deposit(account_id, req.amount).to_response()
   ```
5. **Call it** in `requests.http`: happy path first, then each edge case.

   ```http
   POST http://localhost:8000/api/accounts/REPLACE_ME/deposit
   Content-Type: application/json
   
   {"amount": 100}
   ```

The same endpoint by curl:

```bash
curl -X POST localhost:8000/api/accounts/<id>/deposit -H 'Content-Type: application/json' -d '{"amount": 100}'
```

| Deposit request | Result |
| --- | --- |
| `{"amount": 100}` | 200, balance 600 |
| `{"amount": "0.10"}` | 200, exact (Decimal) |
| `-5`, `0`, `"abc"`, `1.234`, `{}` | 400 `VALIDATION_ERROR` |
| Unknown account id | 404 `NOT_FOUND` |

## 8. 60-minute game plan

Plan for 12 minutes, build one endpoint end to end, then the second, then sweep edge cases. A working partial beats a broken whole.

| Time | Do |
| --- | --- |
| 5 min before | Read the problem. Write endpoints, rules, edge cases and questions in a comment block. No IDE yet. |
| 0–8 | Restate the problem. Ask questions. Agree request/response shapes and status codes. No code. |
| 8–12 | Design aloud: models, storage (which dict, keyed by what), which errors. |
| 12–30 | Endpoint 1: schema, service, route, call it. |
| 30–48 | Endpoint 2, the same way. |
| 48–55 | Run the edge-case list; fix what fails. |
| 55–60 | Summarise: done, not done, next (tests, DB, idempotency, auth, pagination). |

### Questions worth asking

- Uniqueness: can two have the same name? Case-insensitive?
- Amounts: decimals? Max value? Currency?
- Dates: inclusive ranges? Past dates allowed? Time zone?
- State: which transitions are legal? Can a decided request be decided again?
- Concurrency: should I handle simultaneous requests? (Say yes; use the lock.)
- Retries: should a repeated POST be idempotent?
- What should the response contain, and what status on success?

### Edge-case checklist

- [ ] Missing, null, empty, whitespace-only fields
- [ ] Zero, negative, huge numbers; wrong type (`"abc"`); too many decimals
- [ ] ID that doesn't exist; referencing yourself (transfer to same account)
- [ ] Duplicate; acting on the wrong state (approving twice)
- [ ] Boundaries: exactly at the limit (balance == amount), start == end
- [ ] Two requests racing on the same resource

### Think aloud lines

- "This check goes in the schema because it's about the shape of the input."
- "This one goes in the service because it needs stored data."
- "I'm holding the lock across the read and the write so two requests can't both pass."
- "I'll get endpoint 1 fully working before starting endpoint 2."

## 9. Debugging playbook

Read the response body and the console log first. They usually name the problem.

1. Read the response body: the `details` list names the failing field.
2. Read the uvicorn console: a `Traceback` ends with the real error and line number.
3. Say a hypothesis aloud: "I think X because Y."
4. Change one thing, re-send the same request.

Example aloud: "I expected 201 but got 400. The body says `owner_name: Field required`. My request sends `ownerName`. Fixing the request."

### Symptoms already seen

| Symptom | Cause | Fix |
| --- | --- | --- |
| 400 `query.amount: Field required` when sending a JSON body | Plain `amount: float` param is read from the query string | Put it in a Pydantic model: `req: DepositRequest` |
| 500 `TypeError: unsupported operand type(s) for +=: 'decimal.Decimal' and 'float'` | Mixed `float` with `Decimal` | Use `Decimal` everywhere for money |
| 500 `ValueError` from the service | Only `DomainError` maps to 4xx | Validate in the schema, or raise `BusinessRuleError` |
| `TypeError: 'type' object is not subscriptable` at startup | Python 3.8 venv; `dict[str, X]` needs 3.9+ | Rebuild venv with `python3.11` |
| Data disappears between requests | Repo created inside the route | Create it once at module level |
| `NameError` / import error on reload | New schema not imported in `routes.py` | Add it to the import line |
| Route returns 404 though code exists | Path typo, missing `/api` prefix, or router not included | Check `/docs` for the actual path |
| Server hangs on a request | Plain `Lock` re-acquired in the same thread | Use `RLock` |

## 10. Python traps and commands

| Trap | Do this |
| --- | --- |
| `0.1 + 0.2 != 0.3` with float | `Decimal` for money; `Decimal("0.10")` from a string, never from a float |
| Naive time | `datetime.now(timezone.utc)` |
| Same default for every object | `field(default_factory=...)` in dataclasses |
| Mutable default argument `def f(x=[])` | `def f(x=None)` then `x = x or []` |
| Check and write in separate lock blocks | One `with self.repo.lock:` around both |
| Weekdays between two dates | `sum(1 for i in range((end - start).days + 1) if (start + timedelta(days=i)).weekday() < 5)` |
| Date ranges overlap | `a.start <= b.end and b.start <= a.end` |
| Newest first | `sorted(items, key=lambda x: x.created_at, reverse=True)` |
| Case-insensitive match | Compare `.strip().lower()` on both sides |

### Commands

```bash
cd ~/Downloads/keka-starter
source .venv/bin/activate                 # must show Python 3.11: python --version
uvicorn app.main:app --reload             # http://localhost:8000/docs
pytest -q                                 # 7 tests

# rebuild venv if it breaks
rm -rf .venv && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### Before the call

- [ ] Venv on Python 3.11, app starts, tests pass
- [ ] Copilot and all AI extensions turned off in VS Code (including Claude)
- [ ] `requests.http` open, REST Client extension working
- [ ] Terminal with uvicorn visible next to the editor
- [ ] This doc open in a browser tab
