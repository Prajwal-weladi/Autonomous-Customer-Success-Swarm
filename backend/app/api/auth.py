from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from app.agents.database.db_service import get_user_by_email, create_user, get_chat_history_by_email
from app.core.auth import get_password_hash, verify_password, create_access_token
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/v1/auth", tags=["auth"])

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    full_name: str = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    email: str
    full_name: str = None

@router.post("/signup", response_model=TokenResponse)
async def signup(user_data: UserSignup):
    """Register a new user"""
    logger.info(f"Auth: Signup request for {user_data.email}")
    
    # Check if user exists
    existing_user = get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Hash password and create user
    hashed_pass = get_password_hash(user_data.password)
    new_user = create_user(
        email=user_data.email,
        hashed_password=hashed_pass,
        full_name=user_data.full_name
    )
    
    if not new_user:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": new_user.email})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        email=new_user.email,
        full_name=new_user.full_name
    )

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Authenticate user and return token"""
    logger.info(f"Auth: Login request for {credentials.email}")
    
    user = get_user_by_email(credentials.email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        email=user.email,
        full_name=user.full_name
    )

@router.get("/history", response_model=list[dict])
async def get_user_history(email: str):
    """Retrieve chat history for a user"""
    logger.info(f"Auth: History request for {email}")
    history = get_chat_history_by_email(email)
    
    # Simple grouping by conversation_id could be done here if needed
    # For now, returning flat list or grouped list
    return history
