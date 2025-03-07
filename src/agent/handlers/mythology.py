from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from ...database.models import SessionLocal
from ...database import crud

async def mythology_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /mythology command."""
    user_id = update.effective_user.id
    user = update.effective_user
    
    response_text = (
        "🔮 *Mythology Guide* 🔮\n\n"
        "I can teach you about mythology from various cultures.\n\n"
        "Ask me questions like:\n"
        "- Who is Guan Yin in Chinese mythology?\n"
        "- Tell me about Greek gods and goddesses\n"
        "- What's the story of the Phoenix?"
    )
    
    # Set the current topic in user data
    context.user_data['current_topic'] = 'mythology'
    
    # Log this interaction
    db = SessionLocal()
    try:
        crud.log_conversation(
            db, 
            user_id, 
            "/mythology", 
            response_text,
            'mythology'
        )
    finally:
        db.close()
    
    await update.message.reply_text(
        response_text,
        parse_mode="Markdown"
    )