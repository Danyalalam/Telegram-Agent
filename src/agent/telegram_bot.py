from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler
import logging

from ..config import TELEGRAM_BOT_TOKEN
from .handlers import feng_shui, mbti, i_ching, ba_zi, zi_wei
from ..services.ai_service import AIService
from ..database.models import SessionLocal
from ..database import crud

# Import the conversation states
from .conversation_states import *

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Create AI service instance
ai_service = AIService()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_id = user.id
    
    # Store user in database
    db = SessionLocal()
    try:
        crud.get_or_create_user(
            db, 
            telegram_id=user_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
    finally:
        db.close()
    
    await update.message.reply_text(
        f"Hello {user.first_name}! I'm your AI companion for personalized metaphysical insights.\n\n"
        "I can provide advice tailored just for you!\n\n"
        "Use these commands to interact with me:\n"
        "/assess - Start a personalized assessment\n"
        "/fengshui - Get Feng Shui advice\n"
        "/mbti - Get MBTI personality insights\n"
        "/iching - Get I-Ching divination\n"
        "/bazi - Get Chinese Four Pillars analysis\n"
        "/ziwei - Get Zi Wei Dou Shu chart reading\n"
        "/history - View your recent conversations\n"
        "/help - Show this help message"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text(
        "I can help you with personalized assessments and insights:\n\n"
        "✨ /assess - Start a personalized assessment\n"
        "🏠 /fengshui - Feng Shui advice for your home\n"
        "🧠 /mbti - MBTI personality analysis\n"
        "🔮 /iching - I-Ching divination and hexagram readings\n"
        "🌙 /bazi - Chinese Four Pillars (Ba Zi) destiny analysis\n"
        "⭐ /ziwei - Zi Wei Dou Shu astrological chart reading\n"
        "📜 /history - View your recent conversation history\n"
        "🔄 /reset - Reset our conversation memory\n"
        "🔀 /topic <name> - Change to a specific topic\n"
        "📬 /subscribe - Check subscription status for daily tips\n"
        "   /subscribe on - Subscribe to daily tips\n"
        "   /subscribe off - Unsubscribe from daily tips\n"
        "❓ Just ask me any question related to these topics!"
    )

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display recent conversation history."""
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        # Get recent conversations
        conversations = crud.get_user_conversations(db, telegram_id=user_id, limit=5)
        
        if not conversations:
            await update.message.reply_text("You don't have any conversation history yet.")
            return
            
        # Format and send history without Markdown
        history_text = "📜 Your recent conversations:\n\n"
        
        for i, conv in enumerate(conversations, 1):
            # Format the timestamp
            timestamp = conv.created_at.strftime("%b %d, %H:%M")
            topic_emoji = {
                "feng_shui": "🏠", 
                "mbti": "🧠", 
                "iching": "🔮",
                "bazi": "🌙",
                "ziwei": "⭐",
                "general": "💬"
            }.get(conv.topic, "💬")
            
            # Add topic emoji and timestamp
            history_text += f"{i}. {topic_emoji} {conv.topic.title()} · {timestamp}\n"
            history_text += f"You: {conv.message[:50]}{'...' if len(conv.message) > 50 else ''}\n"
            history_text += f"Bot: {conv.response[:50]}{'...' if len(conv.response) > 50 else ''}\n\n"
        
        # Send without specifying parse_mode
        await update.message.reply_text(history_text)
        
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        await update.message.reply_text("I couldn't retrieve your conversation history right now.")
    finally:
        db.close()
        
async def topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change the current topic."""
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "Please specify a topic: /topic feng_shui, /topic mbti, /topic iching, /topic bazi, or /topic ziwei"
        )
        return
        
    topic = args[0].lower()
    if topic not in ["feng_shui", "mbti", "iching", "bazi", "ziwei"]:
        await update.message.reply_text(
            "Available topics are: feng_shui, mbti, iching, bazi, ziwei"
        )
        return
        
    # Update the current topic
    context.user_data['current_topic'] = topic
    
    # Reset the chat session for this user to start fresh with the new topic
    if hasattr(ai_service, 'chat_sessions') and update.effective_user.id in ai_service.chat_sessions:
        del ai_service.chat_sessions[update.effective_user.id]
    
    # Get topic emoji
    topic_emojis = {
        "feng_shui": "🏠", 
        "mbti": "🧠", 
        "iching": "🔮",
        "bazi": "🌙",
        "ziwei": "⭐"
    }
    emoji = topic_emojis.get(topic, "💬")
    
    await update.message.reply_text(
        f"{emoji} Topic changed to *{topic.replace('_', ' ').title()}*. You can now ask questions about this topic.",
        parse_mode="Markdown"
    )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process messages not caught by other handlers."""
    user_message = update.message.text
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Determine the topic based on message content or use 'general'
    topic = 'general'
    
    # Simple keyword detection to guess the topic
    keywords = {
        'feng_shui': ['feng', 'shui', 'home', 'house', 'room', 'space', 'color', 'direction', 'energy'],
        'mbti': ['mbti', 'personality', 'introvert', 'extrovert', 'intuitive', 'sensing', 'thinking', 'feeling', 'judging', 'perceiving', 'infp', 'entj'],
        'iching': ['iching', 'i-ching', 'divination', 'hexagram', 'oracle', 'book of changes'],
        'bazi': ['bazi', 'ba-zi', 'four pillars', 'chinese horoscope', 'eight characters'],
        'ziwei': ['ziwei', 'zi wei', 'purple star', 'dou shu', 'astrology']
    }
    
    for potential_topic, topic_keywords in keywords.items():
        if any(keyword in user_message.lower() for keyword in topic_keywords):
            topic = potential_topic
            break
    
    # Get topic from context if it exists
    if 'current_topic' in context.user_data:
        topic = context.user_data['current_topic']
    
    # Show typing indicator
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    try:
        # Generate AI response with user_id to maintain chat history
        response = await ai_service.generate_response(topic, user_message, update.effective_user.id)
        
        # Store the conversation in the database
        db = SessionLocal()
        try:
            crud.log_conversation(db, user_id, user_message, response, topic)
        finally:
            db.close()
            
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        await update.message.reply_text(
            "I'm having trouble processing your request right now. Please try again later."
        )
        
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset the conversation history."""
    user_id = update.effective_user.id
    
    # Clear the chat session
    if hasattr(ai_service, 'chat_sessions') and user_id in ai_service.chat_sessions:
        del ai_service.chat_sessions[user_id]
        await update.message.reply_text("🔄 I've reset our conversation. What would you like to talk about now?")
    else:
        await update.message.reply_text("We don't have an active conversation yet. Feel free to ask me something!")
        
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe or unsubscribe from daily tips."""
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        # Get current user
        user = crud.get_user(db, telegram_id=user_id)
        if not user:
            await update.message.reply_text(
                "⚠️ I couldn't find your user profile. Please use /start to set up your profile first."
            )
            return
        
        # Check current subscription status
        current_status = user.subscribed_to_tips
        
        # Handle subscription based on current status and command args
        if context.args and len(context.args) > 0:
            # If we have arguments, check if they're explicitly setting on/off
            arg = context.args[0].lower()
            
            if arg in ['on', 'yes', 'true', '1']:
                # User explicitly wants to subscribe
                if current_status:
                    await update.message.reply_text(
                        "📬 You're already subscribed to daily tips! You'll continue receiving insights each day at 9:00 AM."
                    )
                    return
                new_status = True
            elif arg in ['off', 'no', 'false', '0']:
                # User explicitly wants to unsubscribe
                if not current_status:
                    await update.message.reply_text(
                        "📭 You're already unsubscribed from daily tips."
                    )
                    return
                new_status = False
            else:
                # Invalid argument
                await update.message.reply_text(
                    "⚠️ Invalid option. Use /subscribe on to subscribe or /subscribe off to unsubscribe."
                )
                return
        else:
            # No arguments, so toggle the status
            if current_status:
                await update.message.reply_text(
                    "📬 You're currently subscribed to daily tips.\n\n"
                    "To unsubscribe, use /subscribe off"
                )
                return
            else:
                await update.message.reply_text(
                    "📭 You're currently not subscribed to daily tips.\n\n"
                    "To subscribe, use /subscribe on"
                )
                return
        
        # Update user subscription status
        crud.update_user_subscription(db, telegram_id=user_id, subscribed=new_status)
        
        if new_status:
            await update.message.reply_text(
                "✅ You've successfully subscribed to daily tips! You'll receive insights about "
                "Feng Shui, MBTI, I-Ching, Ba Zi, and Zi Wei Dou Shu once a day at 9:00 AM."
            )
        else:
            await update.message.reply_text(
                "❌ You've unsubscribed from daily tips. You'll no longer receive automated messages."
            )
    except Exception as e:
        logger.error(f"Error handling subscription: {e}")
        await update.message.reply_text(
            "⚠️ There was an error processing your subscription. Please try again later."
        )
    finally:
        db.close()

async def start_assessment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start a personalized assessment."""
    keyboard = [
        [
            InlineKeyboardButton("🏠 Feng Shui", callback_data='feng_shui'),
            InlineKeyboardButton("🧠 MBTI", callback_data='mbti'),
        ],
        [
            InlineKeyboardButton("🔮 I-Ching", callback_data='i_ching'),
            InlineKeyboardButton("🌙 Ba Zi", callback_data='ba_zi'),
        ],
        [
            InlineKeyboardButton("⭐ Zi Wei Dou Shu", callback_data='zi_wei'),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Hi! I'm your personal consultant for Chinese metaphysics and personality analysis. "
        "I'd like to get to know you better to provide personalized insights.\n\n"
        "What would you like me to help you with today?",
        reply_markup=reply_markup
    )
    
    # Initialize the assessment data structure
    context.user_data['assessment'] = {}
    
    return SELECTING_TOPIC

async def topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the topic selection."""
    query = update.callback_query
    await query.answer()
    
    topic = query.data
    context.user_data['assessment']['topic'] = topic
    
    if topic == 'feng_shui':
        await query.edit_message_text(
            "I'll help you optimize your living space with personalized Feng Shui advice. "
            "First, what's your name? (This helps me personalize your recommendations)"
        )
        return FENG_SHUI_ASSESSMENT
    
    elif topic == 'mbti':
        await query.edit_message_text(
            "I'll help you discover your MBTI personality type. "
            "First, what's your name? (This helps me personalize your analysis)"
        )
        return MBTI_ASSESSMENT
    
    elif topic == 'i_ching':
        await query.edit_message_text(
            "I'll provide you with a personalized I-Ching reading. "
            "First, what's your name? (This helps me personalize your reading)"
        )
        return I_CHING_ASSESSMENT
    
    elif topic == 'ba_zi':
        await query.edit_message_text(
            "I'll create a Ba Zi (Four Pillars) analysis for you. "
            "First, what's your name? (This helps me personalize your reading)"
        )
        return BA_ZI_ASSESSMENT
    
    elif topic == 'zi_wei':
        await query.edit_message_text(
            "I'll generate a Zi Wei Dou Shu chart interpretation for you. "
            "First, what's your name? (This helps me personalize your reading)"
        )
        return ZI_WEI_ASSESSMENT

async def cancel_assessment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the assessment conversation."""
    await update.message.reply_text(
        "Assessment canceled. You can start a new one anytime with /assess!"
    )
    return ConversationHandler.END

def create_application():
    """Create the Application and add handlers."""
    # Create the Application with longer timeouts for API calls
    builder = Application.builder()
    builder.token(TELEGRAM_BOT_TOKEN)
    builder.connect_timeout(30.0)
    builder.read_timeout(30.0)
    application = builder.build()

    # Add assessment conversation handler
    assessment_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("assess", start_assessment)],
        states={
            SELECTING_TOPIC: [CallbackQueryHandler(topic_selected)],
            
            # Feng Shui states
            FENG_SHUI_ASSESSMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, feng_shui.feng_shui_name)],
            FENG_SHUI_ROOM: [CallbackQueryHandler(feng_shui.feng_shui_room)],
            FENG_SHUI_DIRECTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, feng_shui.feng_shui_directions)],
            
            # MBTI states
            MBTI_ASSESSMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, mbti.mbti_name)],
            MBTI_QUESTION_1: [CallbackQueryHandler(mbti.mbti_question_1)],
            MBTI_QUESTION_2: [CallbackQueryHandler(mbti.mbti_question_2)],
            MBTI_QUESTION_3: [CallbackQueryHandler(mbti.mbti_question_3)],
            MBTI_QUESTION_4: [CallbackQueryHandler(mbti.mbti_question_4)],
            
            # I-Ching states
            I_CHING_ASSESSMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, i_ching.i_ching_name)],
            I_CHING_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, i_ching.i_ching_question)],
            
            # Ba Zi states
            BA_ZI_ASSESSMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, ba_zi.ba_zi_name)],
            BA_ZI_BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ba_zi.ba_zi_birthdate)],
            
            # Zi Wei states
            ZI_WEI_ASSESSMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, zi_wei.zi_wei_name)],
            ZI_WEI_BIRTHDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, zi_wei.zi_wei_birthdate)],
            ZI_WEI_BIRTHTIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, zi_wei.zi_wei_birthtime)],
        },
        fallbacks=[CommandHandler("cancel", cancel_assessment)],
    )
    
    application.add_handler(assessment_conv_handler)

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(CommandHandler("subscribe", subscribe_command))
    
    # Add specific topic handlers
    application.add_handler(CommandHandler("fengshui", feng_shui.fengshui_command))
    application.add_handler(CommandHandler("mbti", mbti.mbti_command))
    application.add_handler(CommandHandler("iching", i_ching.i_ching_command))
    application.add_handler(CommandHandler("bazi", ba_zi.ba_zi_command))
    application.add_handler(CommandHandler("ziwei", zi_wei.zi_wei_command))
    application.add_handler(CommandHandler("topic", topic_command))

    # Default handler for other messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    return application