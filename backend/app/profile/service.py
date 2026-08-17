from sqlalchemy.orm import Session

from app.models import Profile, User
from app.profile.schemas import ProfileInput


def get_profile(database_session: Session, user: User) -> Profile | None:
    """Look up a profile using the authenticated user's database identity."""
    return database_session.get(Profile, user.id)


def save_profile(database_session: Session, user: User, payload: ProfileInput) -> Profile:
    """Create or replace the authenticated user's planning preferences."""
    profile = get_profile(database_session, user)
    values = payload.model_dump(mode="json")

    if profile is None:
        profile = Profile(user_id=user.id, **values)
        database_session.add(profile)
    else:
        for field_name, value in values.items():
            setattr(profile, field_name, value)

    database_session.flush()
    return profile
