# Keka live-coding starter (FastAPI)

Meets every item in the pre-interview checklist:

| Checklist item | Where |
|---|---|
| Sample POST: JSON body → object → JSON response | `POST /api/accounts` in `app/api/routes.py` |
| Logger printing to console | `app/logging_config.py` + request-logging middleware in `app/main.py` |
| No boilerplate | Pydantic models + `@dataclass` in `app/schemas.py` |
| Way to call endpoints | `requests.http` (VS Code REST Client / PyCharm) or curl below; Swagger UI at `/docs` |
| In-memory storage | `app/repository/in_memory.py` |

## Run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://localhost:8000/docs
pytest -q                              # 7 tests
```

```bash
curl -X POST localhost:8000/api/accounts -H 'Content-Type: application/json' \
     -d '{"owner_name":"Abd","initial_balance":500}'
```

## Layout: say this out loud in the interview

```
app/
  api/routes.py          HTTP layer: parse, call service, shape response. Thin.
  services/*_service.py  Business rules. No FastAPI imports, so it's testable alone.
  repository/in_memory.py Storage. Dict + lock. Swappable for a DB.
  schemas.py             Request/response models (validation) + domain model
  errors.py              Domain exceptions → mapped to HTTP codes in main.py
  main.py                App wiring, logging middleware, error handlers
```

Error contract (every error looks the same):
```json
{"error": {"code": "NOT_FOUND", "message": "Account 'x' not found"}}
```
| Situation | Status |
|---|---|
| Malformed JSON / wrong type / missing field | 400 `VALIDATION_ERROR` |
| Resource doesn't exist | 404 `NOT_FOUND` |
| Duplicate / state clash | 409 `CONFLICT` |
| Well-formed but breaks a rule (insufficient balance) | 422 `BUSINESS_RULE_VIOLATION` |
| Bug | 500 `INTERNAL_ERROR` (logged with stack trace) |

## Adding a new endpoint in the interview (the 4-step loop)

1. `schemas.py` – request model with constraints (`Field(gt=0)`, `min_length`, validators)
2. `errors.py` – reuse existing errors; add one only if needed
3. `services/` – the business rule, raising domain errors, logging decisions
4. `routes.py` – 3-line endpoint calling the service

Then hit it with `requests.http`, happy path first, then each edge case.

---

## 60-minute game plan

| Time | Do |
|---|---|
| 5 min before | Read the problem. Write down endpoints, rules, edge cases in a comment block. |
| 0–8 | **Restate the problem and ask questions.** Agree on request/response shapes and status codes. Don't code yet. |
| 8–12 | Design out loud: models, storage structure (which dict, keyed by what), which errors. |
| 12–30 | Endpoint 1 end to end: schema, service, route, then call it. |
| 30–48 | Endpoint 2 end to end. |
| 48–55 | Walk the edge-case list, fix what fails. |
| 55–60 | Summarise: what's done, what you'd add next (tests, persistence, idempotency, auth). |

**Questions worth asking upfront** (pick the ones that apply):
- Uniqueness: can two X have the same name? Case-insensitive?
- Amounts: decimals allowed? Max value? Currency?
- Dates: inclusive ranges? Past dates allowed? Time zones?
- State: what transitions are legal (pending → approved, but approved → pending)?
- Concurrency: should I worry about two simultaneous requests? (Say yes and use the lock.)
- Repeat requests: should a retried POST be idempotent?

**Edge-case checklist** to run through for any endpoint:
- Missing / null / empty / whitespace-only fields
- Zero, negative, huge numbers; wrong types (`"abc"` for a number)
- IDs that don't exist; referencing yourself (transfer to same account)
- Duplicates; operating on something in the wrong state (approving twice)
- Boundaries: exactly at the limit (balance == amount), date start == end
- Concurrent requests racing on the same resource

**Logging rules they're grading:**
- INFO for business events (`Created leave request id=.. employee=.. days=..`)
- WARNING for rejected requests (`Insufficient balance account=.. needed=.. had=..`)
- ERROR / `log.exception` only for real failures (has stack trace)
- Use `%s` placeholders, not f-strings, and log IDs, not whole objects
- Never log secrets or personal data

**Debugging out loud:** "I expected 201 but got 422. Let me read the response body… the field name is `ownerName` in my request but `owner_name` in the model. Fixing." Read the error, form a hypothesis, check the log, change one thing, re-run.

**Python traps:**
- Use `Decimal` for money, never `float` (`0.1 + 0.2 != 0.3`)
- Storage must be created once at module level, not per request
- Read-check-write sequences must hold `repo.lock` for the whole sequence
- `datetime.now(timezone.utc)`, not naive `datetime.now()`

---

## Practice problems (do each in ≤ 45 min, timed, no AI)

### P1: Wallet transfer
Keep `POST /api/accounts`. Add:
- `POST /api/transfers` `{from_account_id, to_account_id, amount}`
- `GET /api/accounts/{id}/transactions` → list of debits and credits, newest first

Rules: both accounts exist (404), from ≠ to (400), amount > 0 with max 2 decimals (400),
sufficient balance (422), transfer is atomic (both balances change or neither),
two concurrent transfers must not overdraw. Bonus: `Idempotency-Key` header.

### P2: Leave requests (very Keka)
Seed employees in memory with balances `{"CASUAL": 12, "SICK": 6}` and a manager.
- `POST /api/leave-requests` `{employee_id, leave_type, start_date, end_date, reason}`
- `POST /api/leave-requests/{id}/decision` `{approver_id, decision: APPROVED|REJECTED}`

Rules: start ≤ end; no past dates; count weekdays only; no overlap with an existing
PENDING/APPROVED request (409); enough balance (422), reserved at apply time;
only the employee's manager can decide (403); only PENDING can be decided (409);
on approve deduct from balance, on reject release the reserved days.
