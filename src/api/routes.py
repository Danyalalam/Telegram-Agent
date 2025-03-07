from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database.models import SessionLocal, User, Conversation
from ..database import crud
from typing import List
from datetime import datetime, timedelta
from pydantic import BaseModel

app = FastAPI(title="Feng Shui Bot API")

# Pydantic models for API responses
class UserBase(BaseModel):
    telegram_id: int
    username: str = None
    first_name: str = None
    last_name: str = None
    
    class Config:
        orm_mode = True

class ConversationBase(BaseModel):
    id: int
    user_id: int
    message: str
    response: str
    topic: str = None
    created_at: datetime
    
    class Config:
        orm_mode = True

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
async def root():
    return {"message": "Feng Shui Bot API is running"}

@app.get("/users/", response_model=List[UserBase])
async def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_all_users(db, skip=skip, limit=limit)
    return users

@app.get("/user/{telegram_id}", response_model=UserBase)
async def get_user(telegram_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db, telegram_id=telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/conversations/", response_model=List[ConversationBase])
async def get_conversations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    conversations = crud.get_all_conversations(db, skip=skip, limit=limit)
    return conversations

@app.get("/user/{telegram_id}/conversations/", response_model=List[ConversationBase])
async def get_user_conversations(telegram_id: int, limit: int = 10, db: Session = Depends(get_db)):
    conversations = crud.get_user_conversations(db, telegram_id=telegram_id, limit=limit)
    return conversations

@app.get("/stats/")
async def get_stats(db: Session = Depends(get_db)):
    # Basic statistics
    total_users = db.query(User).count()
    total_conversations = db.query(Conversation).count()
    
    # Active users in the last 24 hours
    yesterday = datetime.utcnow() - timedelta(days=1)
    active_users = db.query(User).filter(User.last_interaction >= yesterday).count()
    
    # Conversations in the last 24 hours
    recent_conversations = db.query(Conversation).filter(Conversation.created_at >= yesterday).count()
    
    return {
        "total_users": total_users,
        "total_conversations": total_conversations,
        "active_users_24h": active_users,
        "conversations_24h": recent_conversations
    }