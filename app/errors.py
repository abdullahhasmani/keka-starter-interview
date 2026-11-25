"""Domain errors. The service layer raises these; main.py maps them to HTTP codes.

The service never imports FastAPI, so the business rules stay testable on their own.
"""


class DomainError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class NotFoundError(DomainError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(DomainError):
    status_code = 409
    code = "CONFLICT"


class BusinessRuleError(DomainError):
    """Input is well-formed but breaks a business rule (e.g. insufficient balance)."""
    status_code = 422
    code = "BUSINESS_RULE_VIOLATION"
