from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ConversationHandler, CallbackQueryHandler
import logging
import asyncio


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
        
        # Check language preference
        db_user = crud.get_user(db, telegram_id=user_id)
        language = db_user.language if hasattr(db_user, 'language') else 'en'
        context.user_data['language'] = language
        
    finally:
        db.close()
    
    if language == 'zh':
        await update.message.reply_text(
            f"您好，{user.first_name}！我是您的AI伙伴，为您提供个性化的玄学见解。\n\n"
            f"我可以为您提供量身定制的建议！\n\n"
            f"使用这些命令与我互动：\n"
            f"/assess - 开始个性化评估\n"
            f"/fengshui - 获取风水建议\n"
            f"/mbti - 获取MBTI人格见解\n"
            f"/iching - 获取易经占卜\n"
            f"/bazi - 获取中国四柱分析\n"
            f"/ziwei - 获取紫微斗数星盘解读\n"
            f"/language - 切换语言（中文/英文）\n"
            f"/history - 查看您最近的对话\n"
            f"/help - 显示此帮助信息"
        )
    else:
        await update.message.reply_text(
            f"Hello {user.first_name}! I'm your AI companion for personalized metaphysical insights.\n\n"
            f"I can provide advice tailored just for you!\n\n"
            f"Use these commands to interact with me:\n"
            f"/assess - Start a personalized assessment\n"
            f"/fengshui - Get Feng Shui advice\n"
            f"/mbti - Get MBTI personality insights\n"
            f"/iching - Get I-Ching divination\n"
            f"/bazi - Get Chinese Four Pillars analysis\n"
            f"/ziwei - Get Zi Wei Dou Shu chart reading\n"
            f"/language - Switch language (English/Chinese)\n"
            f"/history - View your recent conversations\n"
            f"/help - Show this help message"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    # Determine language for help text
    language = context.user_data.get('language', None)
    
    if not language:
        db = SessionLocal()
        try:
            db_user = crud.get_user(db, telegram_id=update.effective_user.id)
            if db_user and hasattr(db_user, 'language'):
                language = db_user.language
                # Cache it in context
                context.user_data['language'] = language
            else:
                language = 'en'  # Default to English
        except Exception:
            language = 'en'  # Default on error
        finally:
            db.close()
    
    if language == 'zh':
        await update.message.reply_text(
            "我可以为您提供个性化的评估和见解：\n\n"
            "✨ /assess - 开始个性化评估\n"
            "🏠 /fengshui - 为您的家居提供风水建议\n"
            "🧠 /mbti - MBTI人格分析\n"
            "🔮 /iching - 易经占卜和卦象解读\n"
            "🌙 /bazi - 中国八字（四柱）命运分析\n"
            "⭐ /ziwei - 紫微斗数星盘解读\n"
            "📜 /history - 查看您最近的对话历史\n"
            "🔄 /reset - 重置我们的对话记忆\n"
            "🔀 /topic <name> - 更改特定话题\n"
            "🌐 /language - 切换语言（中文/英文）\n"
            "📬 /subscribe - 查看每日提示订阅状态\n"
            "   /subscribe on - 订阅每日提示\n"
            "   /subscribe off - 取消订阅每日提示\n"
            "❓ 您可以直接询问任何与这些主题相关的问题！"
        )
    else:
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
            "🌐 /language - Switch language (English/Chinese)\n"
            "📬 /subscribe - Check subscription status for daily tips\n"
            "   /subscribe on - Subscribe to daily tips\n"
            "   /subscribe off - Unsubscribe from daily tips\n"
            "❓ Just ask me any question related to these topics!"
        )

# Update the history_command function to support language selection
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display recent conversation history."""
    user_id = update.effective_user.id
    
    # Get user language preference
    language = context.user_data.get('language', None)
    
    if not language:
        db = SessionLocal()
        try:
            db_user = crud.get_user(db, telegram_id=user_id)
            if db_user and hasattr(db_user, 'language'):
                language = db_user.language
                # Cache it in context
                context.user_data['language'] = language
            else:
                language = 'en'  # Default to English
        except Exception as e:
            logger.error(f"Error fetching user language: {e}")
            language = 'en'  # Default to English on error
        finally:
            db.close()
    
    db = SessionLocal()
    try:
        # Get recent conversations
        conversations = crud.get_user_conversations(db, telegram_id=user_id, limit=5)
        
        if not conversations:
            if language == 'zh':
                await update.message.reply_text("您还没有任何对话历史记录。")
            else:
                await update.message.reply_text("You don't have any conversation history yet.")
            return
            
        # Format and send history without Markdown
        if language == 'zh':
            history_text = "📜 您最近的对话:\n\n"
        else:
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
            
            # Topic names in Chinese if necessary
            if language == 'zh':
                topic_name = {
                    "feng_shui": "风水",
                    "mbti": "MBTI人格",
                    "iching": "易经",
                    "bazi": "八字",
                    "ziwei": "紫微斗数",
                    "general": "一般"
                }.get(conv.topic, conv.topic.title())
            else:
                topic_name = conv.topic.title()
            
            # Add topic emoji and timestamp
            history_text += f"{i}. {topic_emoji} {topic_name} · {timestamp}\n"
            
            # Label messages according to language
            if language == 'zh':
                history_text += f"您: {conv.message[:50]}{'...' if len(conv.message) > 50 else ''}\n"
                history_text += f"机器人: {conv.response[:50]}{'...' if len(conv.response) > 50 else ''}\n\n"
            else:
                history_text += f"You: {conv.message[:50]}{'...' if len(conv.message) > 50 else ''}\n"
                history_text += f"Bot: {conv.response[:50]}{'...' if len(conv.response) > 50 else ''}\n\n"
        
        # Send without specifying parse_mode
        await update.message.reply_text(history_text)
        
    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        if language == 'zh':
            await update.message.reply_text("我现在无法检索您的对话历史记录。")
        else:
            await update.message.reply_text("I couldn't retrieve your conversation history right now.")
    finally:
        db.close()
        
async def topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Change the current topic."""
    args = context.args
    
    # Get user language preference
    language = context.user_data.get('language', None)
    
    if not language:
        db = SessionLocal()
        try:
            db_user = crud.get_user(db, telegram_id=update.effective_user.id)
            if db_user and hasattr(db_user, 'language'):
                language = db_user.language
                # Cache it in context
                context.user_data['language'] = language
            else:
                language = 'en'  # Default to English
        except Exception as e:
            logger.error(f"Error fetching user language: {e}")
            language = 'en'
        finally:
            db.close()
    
    if not args:
        if language == 'zh':
            await update.message.reply_text(
                "请指定一个话题: /topic feng_shui, /topic mbti, /topic iching, /topic bazi, 或 /topic ziwei"
            )
        else:
            await update.message.reply_text(
                "Please specify a topic: /topic feng_shui, /topic mbti, /topic iching, /topic bazi, or /topic ziwei"
            )
        return
        
    topic = args[0].lower()
    if topic not in ["feng_shui", "mbti", "iching", "bazi", "ziwei"]:
        if language == 'zh':
            await update.message.reply_text(
                "可用的话题有: feng_shui, mbti, iching, bazi, ziwei"
            )
        else:
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
    
    # Topic names in Chinese if necessary
    if language == 'zh':
        topic_name = {
            "feng_shui": "风水",
            "mbti": "MBTI人格",
            "iching": "易经",
            "bazi": "八字",
            "ziwei": "紫微斗数"
        }.get(topic, topic.replace('_', ' ').title())
        
        await update.message.reply_text(
            f"{emoji} 话题已更改为 *{topic_name}*。您现在可以询问有关这个话题的问题了。",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"{emoji} Topic changed to *{topic.replace('_', ' ').title()}*. You can now ask questions about this topic.",
            parse_mode="Markdown"
        )

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process messages not caught by other handlers."""
    user_message = update.message.text
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Get user language preference
    language = context.user_data.get('language', None)
    
    if not language:
        db = SessionLocal()
        try:
            db_user = crud.get_user(db, telegram_id=user_id)
            if db_user and hasattr(db_user, 'language'):
                language = db_user.language
                # Cache it in context
                context.user_data['language'] = language
            else:
                language = 'en'  # Default to English
        except Exception as e:
            logger.error(f"Error fetching user language: {e}")
            language = 'en'  # Default to English on error
        finally:
            db.close()
    
    # Determine the topic based on message content or use 'general'
    topic = 'general'
    
    # Simple keyword detection to guess the topic - now includes Chinese keywords
    keywords = {
        'feng_shui': ['feng', 'shui', 'home', 'house', 'room', 'space', 'color', 'direction', 'energy',
                     '风水', '家居', '房间', '空间', '颜色', '方向', '能量'],
        'mbti': ['mbti', 'personality', 'introvert', 'extrovert', 'intuitive', 'sensing', 'thinking', 
                'feeling', 'judging', 'perceiving', 'infp', 'entj', 
                '人格', '性格', '内向', '外向', '直觉', '感觉', '思考', '情感', '判断', '感知'],
        'iching': ['iching', 'i-ching', 'divination', 'hexagram', 'oracle', 'book of changes',
                  '易经', '占卜', '卦象', '六爻', '预测', '变卦'],
        'bazi': ['bazi', 'ba-zi', 'four pillars', 'chinese horoscope', 'eight characters',
                '八字', '四柱', '命盘', '生辰', '命理', '天干地支'],
        'ziwei': ['ziwei', 'zi wei', 'purple star', 'dou shu', 'astrology',
                 '紫微', '斗数', '星盘', '宫位', '命宫', '星曜']
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
    
    # Keep typing indicator visible for longer responses
    typing_task = asyncio.create_task(
        send_sustained_typing(update.effective_chat.id, context.bot)
    )
    
    try:
        # Generate AI response with user_id to maintain chat history and language preference
        response = await ai_service.generate_response(topic, user_message, user_id, language)
        
        # Store the conversation in the database
        db = SessionLocal()
        try:
            crud.log_conversation(db, user_id, user_message, response, topic)
        finally:
            db.close()
        
        # Cancel the typing indicator task since we're ready to send the response
        typing_task.cancel()
            
        await update.message.reply_text(response)
        
    except Exception as e:
        # Cancel typing indicator on error
        typing_task.cancel()
        
        logger.error(f"Error generating response: {e}")
        # Error message in the appropriate language
        if language == 'zh':
            await update.message.reply_text(
                "我暂时无法处理您的请求。请稍后再试。"
            )
        else:
            await update.message.reply_text(
                "I'm having trouble processing your request right now. Please try again later."
            )
    finally:
        # Ensure the typing indicator task is cancelled if it exists
        if 'typing_task' in locals() and not typing_task.done():
            typing_task.cancel()

# Helper function for sustained typing indicator
async def send_sustained_typing(chat_id, bot):
    """Send typing indicator repeatedly to keep it visible during long operations."""
    try:
        # Keep showing typing for up to 30 seconds (or until task is cancelled)
        for _ in range(8):  # Each typing action lasts ~4 seconds
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(3.5)  # Sleep just under 4 seconds to keep it continuous
    except Exception as e:
        logger.debug(f"Typing indicator stopped: {e}")
        
async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset the conversation history."""
    user_id = update.effective_user.id
    
    # Get user language preference
    language = context.user_data.get('language', None)
    
    if not language:
        db = SessionLocal()
        try:
            db_user = crud.get_user(db, telegram_id=user_id)
            if db_user and hasattr(db_user, 'language'):
                language = db_user.language
                # Cache it in context
                context.user_data['language'] = language
            else:
                language = 'en'  # Default to English
        except Exception as e:
            logger.error(f"Error fetching user language: {e}")
            language = 'en'
        finally:
            db.close()
    
    # Clear the chat session
    if hasattr(ai_service, 'chat_sessions') and user_id in ai_service.chat_sessions:
        del ai_service.chat_sessions[user_id]
        
        if language == 'zh':
            await update.message.reply_text("🔄 我已重置我们的对话。您现在想谈论什么？")
        else:
            await update.message.reply_text("🔄 I've reset our conversation. What would you like to talk about now?")
    else:
        if language == 'zh':
            await update.message.reply_text("我们还没有活跃的对话。请随时向我提问！")
        else:
            await update.message.reply_text("We don't have an active conversation yet. Feel free to ask me something!")
        
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Subscribe or unsubscribe from daily tips."""
    user_id = update.effective_user.id
    
    # Get user language preference
    language = context.user_data.get('language', None)
    
    if not language:
        db = SessionLocal()
        try:
            db_user = crud.get_user(db, telegram_id=user_id)
            if db_user and hasattr(db_user, 'language'):
                language = db_user.language
                # Cache it in context
                context.user_data['language'] = language
            else:
                language = 'en'  # Default to English
        except Exception as e:
            logger.error(f"Error fetching user language: {e}")
            language = 'en'
        finally:
            db.close()
    
    db = SessionLocal()
    try:
        # Get current user
        user = crud.get_user(db, telegram_id=user_id)
        if not user:
            if language == 'zh':
                await update.message.reply_text(
                    "⚠️ 我找不到您的用户资料。请使用 /start 先设置您的资料。"
                )
            else:
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
                    if language == 'zh':
                        await update.message.reply_text(
                            "📬 您已经订阅了每日提示！您将继续在每天早上9点收到见解。"
                        )
                    else:
                        await update.message.reply_text(
                            "📬 You're already subscribed to daily tips! You'll continue receiving insights each day at 9:00 AM."
                        )
                    return
                new_status = True
            elif arg in ['off', 'no', 'false', '0']:
                # User explicitly wants to unsubscribe
                if not current_status:
                    if language == 'zh':
                        await update.message.reply_text(
                            "📭 您已经取消订阅了每日提示。"
                        )
                    else:
                        await update.message.reply_text(
                            "📭 You're already unsubscribed from daily tips."
                        )
                    return
                new_status = False
            else:
                # Invalid argument
                if language == 'zh':
                    await update.message.reply_text(
                        "⚠️ 无效选项。使用 /subscribe on 订阅或 /subscribe off 取消订阅。"
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ Invalid option. Use /subscribe on to subscribe or /subscribe off to unsubscribe."
                    )
                return
        else:
            # No arguments, so just check the status
            if current_status:
                if language == 'zh':
                    await update.message.reply_text(
                        "📬 您当前已订阅每日提示。\n\n"
                        "要取消订阅，请使用 /subscribe off"
                    )
                else:
                    await update.message.reply_text(
                        "📬 You're currently subscribed to daily tips.\n\n"
                        "To unsubscribe, use /subscribe off"
                    )
                return
            else:
                if language == 'zh':
                    await update.message.reply_text(
                        "📭 您当前未订阅每日提示。\n\n"
                        "要订阅，请使用 /subscribe on"
                    )
                else:
                    await update.message.reply_text(
                        "📭 You're currently not subscribed to daily tips.\n\n"
                        "To subscribe, use /subscribe on"
                    )
                return
        
        # Update user subscription status
        crud.update_user_subscription(db, telegram_id=user_id, subscribed=new_status)
        
        if new_status:
            if language == 'zh':
                await update.message.reply_text(
                    "✅ 您已成功订阅每日提示！每天早上9点，您将收到有关风水、MBTI、易经、八字和紫微斗数的见解。"
                )
            else:
                await update.message.reply_text(
                    "✅ You've successfully subscribed to daily tips! You'll receive insights about "
                    "Feng Shui, MBTI, I-Ching, Ba Zi, and Zi Wei Dou Shu once a day at 9:00 AM."
                )
        else:
            if language == 'zh':
                await update.message.reply_text(
                    "❌ 您已取消订阅每日提示。您将不再收到自动消息。"
                )
            else:
                await update.message.reply_text(
                    "❌ You've unsubscribed from daily tips. You'll no longer receive automated messages."
                )
    except Exception as e:
        logger.error(f"Error handling subscription: {e}")
        if language == 'zh':
            await update.message.reply_text(
                "⚠️ 处理您的订阅时出错。请稍后再试。"
            )
        else:
            await update.message.reply_text(
                "⚠️ There was an error processing your subscription. Please try again later."
            )
    finally:
        db.close()

async def start_assessment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start a personalized assessment."""
    # Get user language preference
    language = context.user_data.get('language', None)
    
    if not language:
        db = SessionLocal()
        try:
            db_user = crud.get_user(db, telegram_id=update.effective_user.id)
            if db_user and hasattr(db_user, 'language'):
                language = db_user.language
                # Cache it in context
                context.user_data['language'] = language
            else:
                language = 'en'  # Default to English
        finally:
            db.close()
    
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
    
    if language == 'zh':
        await update.message.reply_text(
            "您好！我是您的个人中国玄学和人格分析顾问。"
            "我想更好地了解您，以提供个性化的见解。\n\n"
            "今天您想让我帮您什么？",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Hi! I'm your personal consultant for Chinese metaphysics and personality analysis. "
            "I'd like to get to know you better to provide personalized insights.\n\n"
            "What would you like me to help you with today?",
            reply_markup=reply_markup
        )
    
    # Initialize the assessment data structure
    context.user_data['assessment'] = {}
    # Store the language in the assessment data
    context.user_data['assessment']['language'] = language
    
    return SELECTING_TOPIC

async def topic_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the topic selection."""
    query = update.callback_query
    await query.answer()
    
    topic = query.data
    context.user_data['assessment']['topic'] = topic
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    if topic == 'feng_shui':
        if language == 'zh':
            message = "我将帮您用个性化的风水建议优化您的居住空间。首先，您的名字是什么？（这有助于我为您提供个性化的建议）"
        else:
            message = "I'll help you optimize your living space with personalized Feng Shui advice. First, what's your name? (This helps me personalize your recommendations)"
        
        await query.edit_message_text(message)
        return FENG_SHUI_ASSESSMENT
    
    elif topic == 'mbti':
        if language == 'zh':
            message = "我将帮您发现您的MBTI人格类型。首先，您的名字是什么？（这有助于我为您提供个性化的分析）"
        else:
            message = "I'll help you discover your MBTI personality type. First, what's your name? (This helps me personalize your analysis)"
        
        await query.edit_message_text(message)
        return MBTI_ASSESSMENT
    
    elif topic == 'i_ching':
        if language == 'zh':
            message = "我将为您提供个性化的易经解读。首先，您的名字是什么？（这有助于我为您提供个性化的解读）"
        else:
            message = "I'll provide you with a personalized I-Ching reading. First, what's your name? (This helps me personalize your reading)"
        
        await query.edit_message_text(message)
        return I_CHING_ASSESSMENT
    
    elif topic == 'ba_zi':
        if language == 'zh':
            message = "我将为您创建八字（四柱）分析。首先，您的名字是什么？（这有助于我为您提供个性化的解读）"
        else:
            message = "I'll create a Ba Zi (Four Pillars) analysis for you. First, what's your name? (This helps me personalize your reading)"
        
        await query.edit_message_text(message)
        return BA_ZI_ASSESSMENT
    
    elif topic == 'zi_wei':
        if language == 'zh':
            message = "我将为您生成紫微斗数星盘解读。首先，您的名字是什么？（这有助于我为您提供个性化的解读）"
        else:
            message = "I'll generate a Zi Wei Dou Shu chart interpretation for you. First, what's your name? (This helps me personalize your reading)"
        
        await query.edit_message_text(message)
        return ZI_WEI_ASSESSMENT

async def cancel_assessment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the assessment conversation."""
    # Get language from assessment data or user data
    language = context.user_data.get('assessment', {}).get('language', None)
    
    if not language:
        language = context.user_data.get('language', 'en')
    
    if language == 'zh':
        await update.message.reply_text(
            "评估已取消。您可以随时使用 /assess 开始新的评估！"
        )
    else:
        await update.message.reply_text(
            "Assessment canceled. You can start a new one anytime with /assess!"
        )
    
    return ConversationHandler.END

# Add these new functions for language handling

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set user's preferred language."""
    user_id = update.effective_user.id
    
    # Create language selection buttons
    keyboard = [
        [
            InlineKeyboardButton("🇺🇸 English", callback_data='lang_en'),
            InlineKeyboardButton("🇨🇳 中文 (Chinese)", callback_data='lang_zh')
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Get current language
    db = SessionLocal()
    try:
        user = crud.get_user(db, telegram_id=user_id)
        current_lang = user.language if user and hasattr(user, 'language') else 'en'
        
        if current_lang == 'en':
            message = (
                "🌐 <b>Language Settings</b>\n\n"
                "Your current language is set to: <b>English</b>\n\n"
                "Select your preferred language:"
            )
        else:
            message = (
                "🌐 <b>语言设置</b>\n\n"
                "您当前的语言设置为: <b>中文</b>\n\n"
                "请选择您偏好的语言:"
            )
            
    except Exception as e:
        logger.error(f"Error checking language preference: {e}")
        message = "🌐 Select your preferred language:"
    finally:
        db.close()
    
    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode="HTML"
    )

async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection callback."""
    try:
        # Get the callback query
        query = update.callback_query
        user_id = update.effective_user.id
        
        # Log all information for debugging
        logger.info(f"Received language callback from user {user_id}")
        logger.info(f"Callback data: {query.data}")
        
        # Answer the callback query to stop the loading animation EARLY
        # This should immediately remove the "loading" indicator
        await query.answer()
        logger.info("Callback query answered")
        
        # Get selected language
        language = query.data.split('_')[1]  # lang_en or lang_zh
        logger.info(f"Selected language: {language}")
        
        # Set a temporary message to show progress
        try:
            await query.edit_message_text(
                text="Updating language preference..." if language == 'en' else "正在更新语言首选项...",
                parse_mode="HTML"
            )
            logger.info("Updated to temporary message")
        except Exception as edit_err:
            logger.error(f"Failed to edit message with temporary text: {edit_err}")
        
        # Store language preference in database
        db = None
        try:
            db = SessionLocal()
            logger.info("Database session created")
            
            # Update language in database
            crud.update_user_language(db, telegram_id=user_id, language=language)
            logger.info(f"Language updated in database for user {user_id}")
            
            # Close DB connection manually to ensure it doesn't block
            db.close()
            db = None
            logger.info("Database connection closed")
            
        except Exception as db_err:
            logger.error(f"Database error: {db_err}", exc_info=True)
            if db:
                db.close()
        
        # Store in context for immediate use
        context.user_data['language'] = language
        logger.info("Language set in context.user_data")
        
        # Also update the AI service's memory of user language
        try:
            ai_service.set_user_language(user_id, language)
            logger.info("Language set in AI service")
        except Exception as ai_err:
            logger.error(f"Error updating AI service language: {ai_err}")
        
        # Confirmation message based on language
        if language == 'en':
            message = (
                "✅ Your language has been set to English.\n\n"
                "You'll now receive responses in English."
            )
        else:
            message = (
                "✅ 您的语言已设置为中文。\n\n"
                "您现在将收到中文回复。"
            )
        
        # Send confirmation - wrap in try/except to catch any errors
        try:
            logger.info("Attempting to send final confirmation message")
            await query.edit_message_text(
                text=message,
                parse_mode="HTML"
            )
            logger.info("Final confirmation message sent successfully")
        except Exception as edit_err:
            logger.error(f"Failed to edit message with confirmation: {edit_err}", exc_info=True)
            # Try to send a new message if editing fails
            try:
                await context.bot.send_message(
                    chat_id=user_id, 
                    text=message + "\n\n(Could not update previous message)",
                    parse_mode="HTML"
                )
                logger.info("Sent confirmation as new message instead")
            except Exception as send_err:
                logger.error(f"Failed to send new message: {send_err}")
        
    except Exception as e:
        logger.error(f"Error in language_callback: {e}", exc_info=True)
        # Try to notify the user about the error
        try:
            if update.callback_query:
                await update.callback_query.answer("An error occurred")
                await update.callback_query.edit_message_text(
                    "⚠️ There was an error setting your language preference. "
                    "Please try again later."
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ There was an error setting your language preference. "
                        "Please try again later."
                )
        except Exception:
            # At this point we can't do much more
            pass
        
async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset the bot state for this user."""
    user_id = update.effective_user.id
    
    logger.info(f"User {user_id} requested a restart")
    
    # Get user language preference
    language = context.user_data.get('language', 'en')
    
    # Reset user data in context
    context.user_data.clear()
    # Restore language setting so we can still communicate properly
    context.user_data['language'] = language
    
    # Reset the AI session for this user
    try:
        if hasattr(ai_service, 'reset_chat_session'):
            ai_service.reset_chat_session(user_id)
            logger.info(f"AI chat session reset for user {user_id}")
        
        if hasattr(ai_service, 'chat_sessions') and user_id in ai_service.chat_sessions:
            del ai_service.chat_sessions[user_id]
            logger.info(f"AI chat session deleted for user {user_id}")
    except Exception as e:
        logger.error(f"Error resetting AI session: {e}")
    
    # Reset any active conversation
    if 'conversation_key' in context.chat_data:
        del context.chat_data['conversation_key']
        logger.info(f"Deleted conversation_key for user {user_id}")
    
    # Send confirmation
    if language == 'zh':
        message = (
            "🔄 机器人已重启！所有之前的对话已被重置。\n\n"
            "使用 /start 重新开始，或使用 /help 查看可用命令。"
        )
    else:
        message = (
            "🔄 Bot has been restarted! All previous conversations have been reset.\n\n"
            "Use /start to begin again or /help to see available commands."
        )
        
    await update.message.reply_text(message)
    logger.info(f"Sent restart confirmation to user {user_id}")
    
    # Return ConversationHandler.END to exit any active conversation
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
    
    # Add language handlers
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CallbackQueryHandler(language_callback, pattern=r'^lang_'))

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
    
    # Add restart command
    application.add_handler(CommandHandler("restart", restart_command))
    


    # Default handler for other messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    return application