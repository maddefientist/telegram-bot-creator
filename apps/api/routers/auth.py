"""Authentication routes."""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from core.auth import (
    create_access_token,
    get_current_active_user,
    get_password_hash,
    verify_password,
)
from core.security import generate_csrf_token
from database import get_db
from models.user import AuthMethod, User
from schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    Token,
    WalletNonceRequest,
    WalletNonceResponse,
    WalletRegister,
    WalletLogin,
)
from services.wallet_service import WalletService

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Register a new user."""
    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/login")
async def login(
    credentials: UserLogin,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Login and get access token."""
    # Find user
    result = await db.execute(select(User).where(User.email == credentials.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Generate CSRF token
    csrf_token = generate_csrf_token()

    # Create access token
    access_token = create_access_token(
        user_id=user.id,
        role=user.role.value,
        csrf_token=csrf_token,
        expires_delta=timedelta(hours=settings.jwt_expiration_hours),
    )

    # Set HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.debug,  # Secure in production
        samesite="lax",
        max_age=settings.jwt_expiration_hours * 3600,
        path="/",
    )

    return {
        "message": "Login successful",
        "csrf_token": csrf_token,
        "user": UserResponse.model_validate(user).model_dump(),
    }


@router.post("/logout")
async def logout(response: Response) -> dict:
    """Logout and clear cookies."""
    response.delete_cookie(
        key="access_token",
        path="/",
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
    )

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Get current user information."""
    return current_user


@router.post("/wallet/nonce", response_model=WalletNonceResponse)
async def request_wallet_nonce(
    request: WalletNonceRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Request a nonce for wallet signature verification."""
    wallet_service = WalletService()

    try:
        nonce, message = await wallet_service.generate_nonce(db, request.wallet_address)

        return {
            "nonce": nonce,
            "message": message,
            "expires_in": WalletService.NONCE_EXPIRY_MINUTES * 60,  # seconds
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/wallet/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_wallet(
    wallet_data: WalletRegister,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Register a new user with Solana wallet."""
    wallet_service = WalletService()

    # Verify signature
    is_valid = await wallet_service.verify_signature(
        db,
        wallet_data.wallet_address,
        wallet_data.signature,
        wallet_data.nonce,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature or expired nonce",
        )

    # Check if wallet already registered
    result = await db.execute(
        select(User).where(User.wallet_address == wallet_data.wallet_address)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet already registered",
        )

    # Check if email already exists (if provided)
    if wallet_data.email:
        result = await db.execute(select(User).where(User.email == wallet_data.email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

    # Create wallet user
    user = User(
        wallet_address=wallet_data.wallet_address,
        email=wallet_data.email,
        auth_method=AuthMethod.WALLET,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.post("/wallet/login")
async def login_wallet(
    credentials: WalletLogin,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Login with Solana wallet signature."""
    wallet_service = WalletService()

    # Verify signature
    is_valid = await wallet_service.verify_signature(
        db,
        credentials.wallet_address,
        credentials.signature,
        credentials.nonce,
    )

    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature or expired nonce",
        )

    # Find user
    result = await db.execute(
        select(User).where(User.wallet_address == credentials.wallet_address)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Wallet not registered",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    # Generate CSRF token
    csrf_token = generate_csrf_token()

    # Create access token
    access_token = create_access_token(
        user_id=user.id,
        role=user.role.value,
        csrf_token=csrf_token,
        expires_delta=timedelta(hours=settings.jwt_expiration_hours),
    )

    # Set HttpOnly cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.jwt_expiration_hours * 3600,
        path="/",
    )

    return {
        "message": "Login successful",
        "csrf_token": csrf_token,
        "user": UserResponse.model_validate(user).model_dump(),
    }


@router.post("/refresh")
async def refresh_token(
    response: Response,
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> dict:
    """Refresh access token."""
    # Generate new CSRF token
    csrf_token = generate_csrf_token()

    # Create new access token
    access_token = create_access_token(
        user_id=current_user.id,
        role=current_user.role.value,
        csrf_token=csrf_token,
        expires_delta=timedelta(hours=settings.jwt_expiration_hours),
    )

    # Set new cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=not settings.debug,
        samesite="lax",
        max_age=settings.jwt_expiration_hours * 3600,
        path="/",
    )

    return {
        "message": "Token refreshed",
        "csrf_token": csrf_token,
    }
