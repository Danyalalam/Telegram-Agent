from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction
from ...database.models import SessionLocal
from ...database import crud
import logging

# Import conversation states
from ..conversation_states import MBTI_QUESTION_1, MBTI_QUESTION_2, MBTI_QUESTION_3, MBTI_QUESTION_4
from telegram.ext import ConversationHandler
logger = logging.getLogger(__name__)

# Function to get AI service safely
def get_ai_service():
    from ..telegram_bot import ai_service
    return ai_service

async def mbti_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /mbti command."""
    user_id = update.effective_user.id
    
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
    
    # Set the current topic in user data
    context.user_data['current_topic'] = 'mbti'
    
    # Show initial information message based on language
    if language == 'zh':
        response_text = (
            "🧠 <b>MBTI 人格类型分析</b> 🧠\n\n"
            "迈尔斯-布里格斯类型指标（MBTI）是一种人格测评工具，"
            "帮助理解人们如何感知世界和做出决策。\n\n"
            "我可以提供关于16种人格类型的见解。您可以问我这样的问题：\n"
            "- INFJ 是什么意思？\n"
            "- 什么职业适合ENTJ？\n"
            "- INTP 和 ESFJ 相处得如何？\n"
            "- ISFP 的认知功能是什么？\n\n"
            "如需个性化评估以找出您的类型，请使用 /assess 并选择 MBTI。"
        )
    else:
        response_text = (
            "🧠 <b>MBTI Personality Analysis</b> 🧠\n\n"
            "The Myers-Briggs Type Indicator (MBTI) is a personality assessment that helps understand "
            "how people perceive the world and make decisions.\n\n"
            "I can provide insights about the 16 personality types. Ask me questions like:\n"
            "- What does INFJ mean?\n"
            "- What careers suit an ENTJ?\n"
            "- How do INTPs and ESFJs get along?\n"
            "- What are the cognitive functions of ISFP?\n\n"
            "For a personalized assessment to find your type, use /assess and select MBTI."
        )
    
    # Log this interaction
    db = SessionLocal()
    try:
        crud.log_conversation(
            db, 
            user_id, 
            "/mbti", 
            response_text,
            'mbti'
        )
    finally:
        db.close()
    
    await update.message.reply_text(
        response_text,
        parse_mode="HTML"
    )

async def mbti_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the MBTI user name input."""
    user_name = update.message.text
    context.user_data['assessment']['name'] = user_name
    context.user_data['assessment']['mbti_answers'] = []
    
    # Get language from assessment data
    language = context.user_data.get('assessment', {}).get('language', None)
    
    if not language:
        language = context.user_data.get('language', 'en')
        # Store language in assessment data for later use
        context.user_data['assessment']['language'] = language
    
    # First MBTI question - Stack buttons vertically with language-specific text
    if language == 'zh':
        keyboard = [
            [InlineKeyboardButton("社交聚会会给我能量 (E)", callback_data='E')],
            [InlineKeyboardButton("我需要独处时间来恢复精力 (I)", callback_data='I')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"谢谢 {user_name}！让我们找出您的MBTI人格类型。\n\n"
            f"问题 1/4：哪个陈述更符合您的特点？",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("I'm energized by social gatherings (E)", callback_data='E')],
            [InlineKeyboardButton("I need alone time to recharge (I)", callback_data='I')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Thanks {user_name}! Let's find your MBTI personality type.\n\n"
            f"Question 1/4: Which statement describes you better?",
            reply_markup=reply_markup
        )
    
    return MBTI_QUESTION_1

async def mbti_question_1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the first MBTI question response."""
    query = update.callback_query
    await query.answer()
    
    # Save the answer
    answer = query.data
    context.user_data['assessment']['mbti_answers'].append(answer)
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    # Second MBTI question - Stack buttons vertically with language-specific text
    if language == 'zh':
        keyboard = [
            [InlineKeyboardButton("我关注具体事实和细节 (S)", callback_data='S')],
            [InlineKeyboardButton("我寻找模式和可能性 (N)", callback_data='N')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"问题 2/4：您如何处理信息？",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("I focus on concrete facts and details (S)", callback_data='S')],
            [InlineKeyboardButton("I look for patterns and possibilities (N)", callback_data='N')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"Question 2/4: How do you process information?",
            reply_markup=reply_markup
        )
    
    return MBTI_QUESTION_2

async def mbti_question_2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the second MBTI question response."""
    query = update.callback_query
    await query.answer()
    
    # Save the answer
    answer = query.data
    context.user_data['assessment']['mbti_answers'].append(answer)
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    # Third MBTI question - Stack buttons vertically with language-specific text
    if language == 'zh':
        keyboard = [
            [InlineKeyboardButton("我基于逻辑做决定 (T)", callback_data='T')],
            [InlineKeyboardButton("我首先考虑人的感受 (F)", callback_data='F')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"问题 3/4：您如何做决定？",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("I make decisions based on logic (T)", callback_data='T')],
            [InlineKeyboardButton("I consider people's feelings first (F)", callback_data='F')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"Question 3/4: How do you make decisions?",
            reply_markup=reply_markup
        )
    
    return MBTI_QUESTION_3

async def mbti_question_3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the third MBTI question response."""
    query = update.callback_query
    await query.answer()
    
    # Save the answer
    answer = query.data
    context.user_data['assessment']['mbti_answers'].append(answer)
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    # Fourth MBTI question - Stack buttons vertically with language-specific text
    if language == 'zh':
        keyboard = [
            [InlineKeyboardButton("我喜欢计划和结构 (J)", callback_data='J')],
            [InlineKeyboardButton("我喜欢灵活和自发 (P)", callback_data='P')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"问题 4/4：您如何对待生活？",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton("I prefer planning and structure (J)", callback_data='J')],
            [InlineKeyboardButton("I prefer flexibility and spontaneity (P)", callback_data='P')],
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"Question 4/4: How do you approach life?",
            reply_markup=reply_markup
        )
    
    return MBTI_QUESTION_4

async def mbti_question_4(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the fourth MBTI question response and generate results."""
    query = update.callback_query
    await query.answer()
    
    # Save the answer
    answer = query.data
    context.user_data['assessment']['mbti_answers'].append(answer)
    
    # Calculate the MBTI type
    mbti_type = ''.join(context.user_data['assessment']['mbti_answers'])
    context.user_data['assessment']['mbti_type'] = mbti_type
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    # Show typing indicator
    await query.message.chat.send_action(action=ChatAction.TYPING)
    
    # Inform user that we're generating results
    if language == 'zh':
        await query.edit_message_text(
            f"正在基于您的回答分析您的MBTI类型：{mbti_type}...\n\n"
            f"请稍候，我正在生成您的个性化人格分析..."
        )
    else:
        await query.edit_message_text(
            f"Analyzing your MBTI type based on your answers: {mbti_type}...\n\n"
            f"Please wait while I generate your personalized personality analysis..."
        )
    
    # Generate personalized results
    return await generate_mbti_results(update, context)

async def generate_mbti_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate personalized MBTI results."""
    assessment = context.user_data['assessment']
    user_name = assessment['name']
    mbti_type = assessment['mbti_type']
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    # Create a personalized query for the AI - specify maximum length with language preference
    if language == 'zh':
        user_query = (
            f"为{user_name}创建一个简洁的MBTI分析，他/她的类型是{mbti_type}。"
            f"包括主要优势、弱点、职业推荐和人际关系兼容性。"
            f"让内容个性化但将总回复控制在1000字符以内。请用中文回答。"
        )
    else:
        user_query = (
            f"Create a concise personalized MBTI analysis for {user_name} who has the type {mbti_type}. "
            f"Include key strengths, weaknesses, career recommendations, and relationship compatibility. "
            f"Make it feel personal but keep the total response under 1000 characters."
        )
    
    try:
        # Generate AI response with language preference
        ai_service = get_ai_service()
        response = await ai_service.generate_response('mbti', user_query, update.effective_user.id, language)
        
        # Store the assessment context for follow-up questions
        if language == 'zh':
            context_summary = f"{user_name}的MBTI评估，人格类型为{mbti_type}。"
        else:
            context_summary = f"MBTI assessment for {user_name} with personality type {mbti_type}."
            
        ai_service.store_assessment_result(update.effective_user.id, 'mbti', context_summary)
        
        # Limit the response length
        if len(response) > 1500:
            response = response[:1497] + "..."
        
        # Add personal touches to the response - keep it concise with language preference
        if language == 'zh':
            personalized_response = (
                f"🧠 <b>{user_name}的MBTI人格档案：{mbti_type}</b> 🧠\n\n"
                f"{response}\n\n"
                f"您想了解更多关于您的MBTI类型的优势、职业或人际关系方面的具体信息吗？"
            )
        else:
            personalized_response = (
                f"🧠 <b>{user_name}'s MBTI Personality Profile: {mbti_type}</b> 🧠\n\n"
                f"{response}\n\n"
                f"Would you like more specific information about your MBTI type's strengths, careers, or relationships?"
            )
        
        # Ensure the total message is within Telegram limits
        if len(personalized_response) > 4000:
            # Further trim if still too long
            excess = len(personalized_response) - 3950
            response = response[:-excess] + "..."
            
            if language == 'zh':
                personalized_response = (
                    f"🧠 <b>{user_name}的MBTI人格档案：{mbti_type}</b> 🧠\n\n"
                    f"{response}\n\n"
                    f"您想了解更多关于您的MBTI类型的优势、职业或人际关系方面的具体信息吗？"
                )
            else:
                personalized_response = (
                    f"🧠 <b>{user_name}'s MBTI Personality Profile: {mbti_type}</b> 🧠\n\n"
                    f"{response}\n\n"
                    f"Would you like more specific information about your MBTI type's strengths, careers, or relationships?"
                )
        
        # Store this assessment in the database
        db = SessionLocal()
        try:
            crud.log_conversation(
                db, update.effective_user.id, 
                f"MBTI assessment result: {mbti_type}", 
                personalized_response[:500] + "...",  # Store a truncated version in the database
                'mbti'
            )
        finally:
            db.close()
        
        # Send the response
        await update.callback_query.edit_message_text(personalized_response, parse_mode="HTML")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error generating MBTI results: {e}")
        
        if language == 'zh':
            await update.callback_query.edit_message_text(
                "我在创建您的个性化MBTI分析时遇到了问题。请稍后再试。"
            )
        else:
            await update.callback_query.edit_message_text(
                "I'm having trouble creating your personalized MBTI analysis. Please try again later."
            )
        
        return ConversationHandler.END