from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction
from ...database.models import SessionLocal
from ...database import crud
import logging

# Import conversation states
from ..conversation_states import MBTI_QUESTION_1, MBTI_QUESTION_2, MBTI_QUESTION_3, MBTI_QUESTION_4

logger = logging.getLogger(__name__)

# Function to get AI service safely
def get_ai_service():
    from ..telegram_bot import ai_service
    return ai_service

async def mbti_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /mbti command."""
    user_id = update.effective_user.id
    
    response_text = (
        "🧠 *MBTI Personality Analysis* 🧠\n\n"
        "The Myers-Briggs Type Indicator (MBTI) is a personality assessment that helps understand "
        "how people perceive the world and make decisions.\n\n"
        "I can provide insights about the 16 personality types. Ask me questions like:\n"
        "- What does INFJ mean?\n"
        "- What careers suit an ENTJ?\n"
        "- How do INTPs and ESFJs get along?\n"
        "- What are the cognitive functions of ISFP?\n\n"
        "For a personalized assessment to find your type, use /assess and select MBTI."
    )
    
    # Set the current topic in user data
    context.user_data['current_topic'] = 'mbti'
    
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
        parse_mode="Markdown"
    )

async def mbti_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the MBTI user name input."""
    user_name = update.message.text
    context.user_data['assessment']['name'] = user_name
    context.user_data['assessment']['mbti_answers'] = []
    
    # First MBTI question - Stack buttons vertically
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
    
    # Second MBTI question - Stack buttons vertically
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
    
    # Third MBTI question - Stack buttons vertically
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
    
    # Fourth MBTI question - Stack buttons vertically
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
    
    # Show typing indicator
    await query.message.chat.send_action(action=ChatAction.TYPING)
    
    # Generate personalized results
    return await generate_mbti_results(update, context)

async def generate_mbti_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate personalized MBTI results."""
    assessment = context.user_data['assessment']
    user_name = assessment['name']
    mbti_type = assessment['mbti_type']
    
    # Create a personalized query for the AI
    user_query = (
        f"Create a personalized MBTI analysis for {user_name} who has the type {mbti_type}. "
        f"Include strengths, weaknesses, career recommendations, and relationship compatibility. "
        f"Make it feel personal and specific to them. Keep it concise but detailed."
    )
    
    try:
        # Generate AI response
        ai_service = get_ai_service()
        response = await ai_service.generate_response('mbti', user_query, update.effective_user.id)
        
        # Store the assessment context for follow-up questions
        context_summary = f"MBTI assessment for {user_name} with personality type {mbti_type}."
        ai_service.store_assessment_result(update.effective_user.id, 'mbti', context_summary)
        
        # Add personal touches to the response
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
                personalized_response, 
                'mbti'
            )
        finally:
            db.close()
        
        # Send the response
        await update.callback_query.edit_message_text(personalized_response, parse_mode="HTML")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error generating MBTI results: {e}")
        await update.callback_query.edit_message_text(
            "I'm having trouble creating your personalized MBTI analysis. Please try again later."
        )
        
        return ConversationHandler.END