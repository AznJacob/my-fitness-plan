from sqlalchemy.orm import Session

from app.account.schemas import AccountDetailsInput
from app.models import AccountDetails, User


def get_account_details(database_session: Session, user: User) -> AccountDetails | None:
    """Look up private details using only the authenticated database identity."""
    return database_session.get(AccountDetails, user.id)


def save_account_details(
    database_session: Session,
    user: User,
    payload: AccountDetailsInput,
) -> AccountDetails:
    details = get_account_details(database_session, user)
    values = payload.model_dump()
    if details is None:
        details = AccountDetails(user_id=user.id, **values)
        database_session.add(details)
    else:
        for field_name, value in values.items():
            setattr(details, field_name, value)
    database_session.flush()
    return details
