import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.claims.router import router as claims_router
from app.core.config import get_settings
from app.core.errors import DomainError

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper())

app = FastAPI(
    title="ExpenseFlow Core API",
    version="0.1.0",
    description="Phase 1 Expense Reimbursement Core API",
)
app.include_router(claims_router)


@app.exception_handler(DomainError)
async def handle_domain_error(_request: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    details = [
        {"location": list(error["loc"]), "message": error["msg"], "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": details,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def handle_database_error(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"code": "DATABASE_ERROR", "message": "A database operation failed"},
    )
