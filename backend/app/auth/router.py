from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.auth.cookies import (
    clear_authentication_cookies,
    set_authentication_cookies,
    set_csrf_cookie,
)
from app.auth.dependencies import (
    AuthenticatedCsrfSession,
    CurrentUser,
    require_csrf_tokens,
)
from app.auth.google import (
    GoogleVerificationUnavailableError,
    InvalidGoogleTokenError,
    verify_google_id_token,
)
from app.auth.schemas import GoogleLoginRequest, LoginRequest, RegistrationRequest, UserResponse
from app.auth.service import (
    GoogleAccountConflictError,
    InvalidCredentialsError,
    InvalidEmailError,
    InvalidPasswordError,
    RegistrationConflictError,
    login_user,
    register_user,
    revoke_session,
    sign_in_with_google,
)
from app.auth.tokens import generate_token
from app.database import DatabaseSession
from app.dependencies import ApplicationSettings

router = APIRouter(prefix="/auth", tags=["authentication"])


def _user_response(user_id: UUID, email: str) -> UserResponse:
    return UserResponse(id=user_id, email=email)


@router.get("/csrf", status_code=status.HTTP_204_NO_CONTENT)
def csrf(response: Response, settings: ApplicationSettings) -> None:
    """Bootstrap the double-submit token required by state-changing auth requests."""
    set_csrf_cookie(response, generate_token(), settings)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegistrationRequest,
    response: Response,
    database_session: DatabaseSession,
    settings: ApplicationSettings,
    _csrf_token_hash: bytes = Depends(require_csrf_tokens),
) -> UserResponse:
    try:
        issued_session = register_user(
            database_session,
            payload.email,
            payload.password,
            settings.session_lifetime_seconds,
        )
    except (InvalidEmailError, InvalidPasswordError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error))
    except RegistrationConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to create an account with those credentials.",
        ) from error

    set_authentication_cookies(response, issued_session, settings)
    return _user_response(issued_session.user.id, issued_session.user.normalized_email)


@router.post("/google", response_model=UserResponse)
def google_login(
    payload: GoogleLoginRequest,
    response: Response,
    database_session: DatabaseSession,
    settings: ApplicationSettings,
    _csrf_token_hash: bytes = Depends(require_csrf_tokens),
) -> UserResponse:
    if settings.google_client_id is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not configured.",
        )

    try:
        google_identity = verify_google_id_token(payload.id_token, settings.google_client_id)
    except InvalidGoogleTokenError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unable to authenticate with Google.",
        ) from error
    except GoogleVerificationUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is temporarily unavailable.",
        ) from error

    try:
        issued_session = sign_in_with_google(
            database_session,
            google_identity,
            settings.session_lifetime_seconds,
        )
    except GoogleAccountConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to sign in with Google.",
        ) from error

    set_authentication_cookies(response, issued_session, settings)
    return _user_response(issued_session.user.id, issued_session.user.normalized_email)


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    database_session: DatabaseSession,
    settings: ApplicationSettings,
    _csrf_token_hash: bytes = Depends(require_csrf_tokens),
) -> UserResponse:
    try:
        issued_session = login_user(
            database_session,
            payload.email,
            payload.password,
            settings.session_lifetime_seconds,
        )
    except InvalidCredentialsError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        ) from error

    set_authentication_cookies(response, issued_session, settings)
    return _user_response(issued_session.user.id, issued_session.user.normalized_email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    settings: ApplicationSettings,
    user_session: AuthenticatedCsrfSession,
) -> None:
    revoke_session(user_session)
    clear_authentication_cookies(response, settings)


@router.get("/me", response_model=UserResponse)
def current_user(
    user: CurrentUser,
) -> UserResponse:
    return _user_response(user.id, user.normalized_email)
