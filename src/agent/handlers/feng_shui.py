import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from ...database.models import SessionLocal
from ...database import crud
from ...services.ai_service import AIService
from ..conversation_states import FENG_SHUI_ROOM, FENG_SHUI_DIRECTIONS
from telegram.ext import ConversationHandler
logger = logging.getLogger(__name__)
ai_service = AIService()

async def fengshui_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Provide general feng shui information."""
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
    
    # Set the current topic
    context.user_data['current_topic'] = 'feng_shui'
    
    # Show initial information message based on language
    if language == 'zh':
        info_text = (
            "🏠 <b>风水</b>\n\n"
            "风水是古老的中国哲学，专注于人与环境的和谐，以促进健康、幸福和繁荣。\n\n"
            "我可以帮您：\n"
            "• 分析您家居的风水布局\n"
            "• 提供改善能量流动的建议\n"
            "• 推荐适合特定房间的颜色和装饰\n"
            "• 提供最佳家具摆放指南\n\n"
            "请告诉我您的具体问题，我将提供个性化建议。"
            "或者，使用 /assess 开始完整的风水评估。"
        )
    else:
        info_text = (
            "🏠 <b>Feng Shui</b>\n\n"
            "Feng Shui is an ancient Chinese philosophy focused on harmony between people and their environment "
            "to promote health, happiness, and prosperity.\n\n"
            "I can help you with:\n"
            "• Analysis of your home's energy layout\n"
            "• Recommendations for improving energy flow\n"
            "• Color and decor suggestions for specific rooms\n"
            "• Optimal furniture placement guidance\n\n"
            "Ask me specific questions and I'll provide personalized advice, "
            "or use /assess to start a complete Feng Shui assessment."
        )
    
    await update.message.reply_text(info_text, parse_mode="HTML")

async def feng_shui_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the user's name and ask about which room they want to focus on."""
    name = update.message.text
    context.user_data['assessment']['name'] = name
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    # Create room selection buttons
    keyboard = [
        [
            InlineKeyboardButton("🛋️ Living Room", callback_data='living_room'),
            InlineKeyboardButton("🛏️ Bedroom", callback_data='bedroom')
        ],
        [
            InlineKeyboardButton("🍽️ Kitchen", callback_data='kitchen'),
            InlineKeyboardButton("💼 Office", callback_data='office')
        ],
        [
            InlineKeyboardButton("🚪 Entrance", callback_data='entrance'),
            InlineKeyboardButton("🏠 Whole Home", callback_data='whole_home')
        ]
    ]
    
    # Chinese labels for buttons if needed
    if language == 'zh':
        keyboard = [
            [
                InlineKeyboardButton("🛋️ 客厅", callback_data='living_room'),
                InlineKeyboardButton("🛏️ 卧室", callback_data='bedroom')
            ],
            [
                InlineKeyboardButton("🍽️ 厨房", callback_data='kitchen'),
                InlineKeyboardButton("💼 办公室", callback_data='office')
            ],
            [
                InlineKeyboardButton("🚪 入口", callback_data='entrance'),
                InlineKeyboardButton("🏠 整个家", callback_data='whole_home')
            ]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if language == 'zh':
        await update.message.reply_text(
            f"谢谢，{name}！您想要关注哪个房间的风水？",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            f"Thanks, {name}! Which area of your home would you like to focus on for Feng Shui advice?",
            reply_markup=reply_markup
        )
    
    return FENG_SHUI_ROOM

async def feng_shui_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process the selected room and ask about the main directions."""
    query = update.callback_query
    await query.answer()
    
    room = query.data
    context.user_data['assessment']['room'] = room
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    # Room names in Chinese if necessary
    if language == 'zh':
        room_names = {
            'living_room': '客厅',
            'bedroom': '卧室',
            'kitchen': '厨房',
            'office': '办公室',
            'entrance': '入口',
            'whole_home': '整个家'
        }
        room_name = room_names.get(room, room)
        
        await query.edit_message_text(
            f"了解了！让我们为您的{room_name}提供风水建议。"
            f"请告诉我您家的主要朝向是什么？（例如：北、东南、西南等）"
        )
    else:
        room_name = room.replace('_', ' ').title()
        
        await query.edit_message_text(
            f"Great! Let's look at the Feng Shui for your {room_name}. "
            f"What's the main direction your home faces? (e.g., North, Southeast, Southwest, etc.)"
        )
    
    return FENG_SHUI_DIRECTIONS

async def feng_shui_directions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Process directions and provide a detailed Feng Shui analysis."""
    directions = update.message.text
    context.user_data['assessment']['directions'] = directions
    
    name = context.user_data['assessment']['name']
    room = context.user_data['assessment']['room']
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    # Show typing indicator
    await update.message.chat.send_action(action="typing")
    
    # Room names in Chinese if necessary
    if language == 'zh':
        room_names = {
            'living_room': '客厅',
            'bedroom': '卧室',
            'kitchen': '厨房',
            'office': '办公室',
            'entrance': '入口',
            'whole_home': '整个家'
        }
        room_name = room_names.get(room, room)
        
        # Create a detailed assessment prompt
        prompt = (
            f"为一个名叫{name}的人提供详细的风水分析和建议，针对他们的{room_name}，朝向为{directions}。"
            f"包括家具摆放、颜色选择、装饰物和元素平衡的具体建议。"
            f"首先给出整体评估，然后按类别提供3-5个可操作的具体建议。"
            f"使用传统风水原则，但以现代、实用的方式解释。以友好、专业的语气回答。"
            f"用中文回答，使用表情符号增加趣味性。限制在800个字以内。"
        )
    else:
        room_name = room.replace('_', ' ').title()
        
        # Create a detailed assessment prompt
        prompt = (
            f"Provide a detailed Feng Shui analysis and advice for {name}'s {room_name} that faces {directions}. "
            f"Include specific suggestions for furniture placement, color choices, decorative elements, and element balance. "
            f"Start with an overall assessment, then provide 3-5 actionable specific recommendations by category. "
            f"Use traditional Feng Shui principles but explain them in modern, practical terms. Answer in a friendly yet professional tone. "
            f"Include emojis for fun. Keep response under 800 words."
        )
    
    try:
        # Generate detailed response
        assessment_response = await ai_service.generate_response('feng_shui', prompt, language=language)
        
        # Store this assessment result for potential follow-ups
        assessment_context = f"{name}'s {room_name} facing {directions}"
        ai_service.store_assessment_result(update.effective_user.id, 'feng_shui', assessment_context)
        
        await update.message.reply_text(assessment_response)
        
        # Send a follow-up message asking if they want more information
        if language == 'zh':
            await update.message.reply_text(
                "我希望这些风水建议对您有帮助！如果您有任何后续问题，或者想了解特定方面的更多信息，请随时告诉我。"
            )
        else:
            await update.message.reply_text(
                "I hope these Feng Shui recommendations are helpful! If you have any follow-up questions or would like "
                "more information about specific aspects, feel free to ask me anytime."
            )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error generating Feng Shui assessment: {e}")
        if language == 'zh':
            await update.message.reply_text(
                "抱歉，生成您的风水评估时出现了问题。请稍后再试，或者尝试用不同的方式提问。"
            )
        else:
            await update.message.reply_text(
                "I'm sorry, there was an error generating your Feng Shui assessment. Please try again later or "
                "try asking in a different way."
            )
        
        return ConversationHandler.END