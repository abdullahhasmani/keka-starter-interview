import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.errors import DomainError
from app.logging_config import setup_logging

setup_logging()
log = logging.getLogger("app")

app = FastAPI(title="Keka interview service")
app.include_router(router)


# ---------- request logging ----------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = uuid.uuid4().hex[:8]
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    log.info("req=%s %s %s -> %s (%.1f ms)",
             request_id, request.method, request.url.path, response.status_code, ms)
    response.headers["X-Request-Id"] = request_id
    return response


# ---------- one consistent error shape: {"error": {"code", "message"}} ----------
@app.exception_handler(DomainError)
async def handle_domain_error(request: Request, exc: DomainError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(request: Request, exc: RequestValidationError):
    details = [
        {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
        for e in exc.errors()
    ]
    log.warning("Validation failed %s %s: %s", request.method, request.url.path, details)
    return JSONResponse(
        status_code=400,
        content={"error": {"code": "VALIDATION_ERROR", "message": "Invalid request", "details": details}},
    )


@app.exception_handler(Exception)
async def handle_unexpected(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_ERROR", "message": "Something went wrong"}},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
