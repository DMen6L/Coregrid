from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.models import User
from app.schemas import TokenResponse, UserCreate, UserLogin, UserResponse
from helpers.auth import create_access_token, hash_password, verify_password
from helpers.dependencies import DbSession

from helpers.transactions import commit_or_raise
from helpers.update_helpers import check_unique_constraints


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_user(db: DbSession, user_data: UserCreate):
    hashed = hash_password(user_data.password)

    user_schema = {
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": hashed,
    }

    check_unique_constraints(
        db=db,
        model=User,
        constraint_name="uq_users_email",
        values=user_schema,
    )

    user = User(
        **user_schema,
    )

    db.add(user)
    commit_or_raise(db)
    db.refresh(user)

    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
)
def login(db: DbSession, login_data: UserLogin):
    user = db.scalar(select(User).where(User.email == login_data.email))

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User email or password is wrong",
        )

    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User email or password is wrong",
        )

    return TokenResponse(access_token=create_access_token(user.id))
