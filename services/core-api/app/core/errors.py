class DomainError(Exception):
    code = "DOMAIN_ERROR"
    message = "A domain error occurred"
    status_code = 400

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.message
        super().__init__(self.message)


class ClaimNotFound(DomainError):
    code = "CLAIM_NOT_FOUND"
    message = "Expense claim was not found"
    status_code = 404


class InvalidClaimTransition(DomainError):
    code = "INVALID_CLAIM_TRANSITION"
    message = "The requested claim status transition is not allowed"
    status_code = 409


class ClaimItemsRequired(DomainError):
    code = "CLAIM_ITEMS_REQUIRED"
    message = "At least one expense item is required before submission"
    status_code = 422
