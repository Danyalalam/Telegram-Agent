from sqlalchemy.orm import Session
from . import models
import datetime
from typing import List, Optional

def get_user(db: Session, telegram_id: int) -> Optional[models.User]:
    """Get a user by their Telegram ID."""
    return db.query(models.User).filter(models.User.telegram_id == telegram_id).first()

def get_or_create_user(db: Session, telegram_id: int, username: Optional[str] = None, 
                       first_name: Optional[str] = None, last_name: Optional[str] = None) -> models.User:
    """Get a user by Telegram ID or create if not exists."""
    user = get_user(db, telegram_id)
    
    if user:
        # Update user details if they've changed
        if username is not None:
            user.username = username
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        
        # Update last interaction time
        user.last_interaction = datetime.datetime.utcnow()
        db.commit()
        return user
    
    # Create new user
    new_user = models.User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def log_conversation(db: Session, telegram_id: int, message: str, response: str, topic: str) -> models.Conversation:
    """Log a conversation between the user and the bot."""
    user = get_user(db, telegram_id)
    
    if not user:
        # If user doesn't exist, create them
        user = get_or_create_user(db, telegram_id)
    
    # Update last interaction time
    user.last_interaction = datetime.datetime.utcnow()
    
    # Create the conversation record
    new_conversation = models.Conversation(
        user_id=user.id,
        message=message,
        response=response,
        topic=topic
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    return new_conversation

def get_user_conversations(db: Session, telegram_id: int, limit: int = 10) -> List[models.Conversation]:
    """Get recent conversations for a specific user."""
    user = get_user(db, telegram_id)
    
    if not user:
        return []
    
    return db.query(models.Conversation).filter(
        models.Conversation.user_id == user.id
    ).order_by(
        models.Conversation.created_at.desc()
    ).limit(limit).all()

def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> List[models.User]:
    """Get all users with pagination."""
    return db.query(models.User).offset(skip).limit(limit).all()

def get_all_conversations(db: Session, skip: int = 0, limit: int = 100) -> List[models.Conversation]:
    """Get all conversations with pagination."""
    return db.query(models.Conversation).order_by(
        models.Conversation.created_at.desc()
    ).offset(skip).limit(limit).all()
    
def update_user_subscription(db: Session, telegram_id: int, subscribed: bool) -> models.User:
    """Update a user's subscription status."""
    user = get_user(db, telegram_id)
    
    if not user:
        raise ValueError(f"User with telegram_id {telegram_id} not found")
    
    user.subscribed_to_tips = subscribed
    db.commit()
    db.refresh(user)
    return user

def get_subscribed_users(db: Session) -> List[models.User]:
    """Get all users who are subscribed to daily tips."""
    return db.query(models.User).filter(models.User.subscribed_to_tips == True).all()