from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.claims.repository import SqlAlchemyExpenseClaimRepository
from app.claims.service import ExpenseClaimService
from app.db.session import get_db_session

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_claim_service(session: DbSession) -> ExpenseClaimService:
    repository = SqlAlchemyExpenseClaimRepository(session)
    return ExpenseClaimService(repository)


ClaimService = Annotated[ExpenseClaimService, Depends(get_claim_service)]
