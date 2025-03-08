from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction
from ...database.models import SessionLocal
from ...database import crud
import logging

# Import conversation states
from ..conversation_states import FENG_SHUI_ROOM, FENG_SHUI_DIRECTIONS

logger = logging.getLogger(__name__)

# Function to get AI service safely
def get_ai_service():
    from ..telegram_bot import ai_service
    return ai_service

async def fengshui_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /fengshui command."""
    user_id = update.effective_user.id
    
    response_text = (
        "🏠 *Feng Shui Consultation* 🏠\n\n"
        "Feng Shui is an ancient Chinese practice of arranging your environment to enhance energy flow.\n\n"
        "I can provide advice for optimizing your space. Ask me questions like:\n"
        "- How should I arrange my bedroom for better sleep?\n"
        "- What colors are best for my home office?\n"
        "- How can I improve the energy in my living room?\n"
        "- What are my lucky directions based on my Kua number?\n\n"
        "For a personalized assessment, use the /assess command and select Feng Shui."
    )
    
    # Set the current topic in user data
    context.user_data['current_topic'] = 'feng_shui'
    
    # Log this interaction
    db = SessionLocal()
    try:
        crud.log_conversation(
            db, 
            user_id, 
            "/fengshui", 
            response_text,
            'feng_shui'
        )
    finally:
        db.close()
    
    await update.message.reply_text(
        response_text,
        parse_mode="Markdown"
    )

async def feng_shui_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the feng shui user name input."""
    user_name = update.message.text
    context.user_data['assessment']['name'] = user_name
    
    keyboard = [
        [
            InlineKeyboardButton("Bedroom", callback_data='bedroom'),
            InlineKeyboardButton("Living Room", callback_data='living_room'),
        ],
        [
            InlineKeyboardButton("Kitchen", callback_data='kitchen'),
            InlineKeyboardButton("Home Office", callback_data='office'),
        ],
        [
            InlineKeyboardButton("Entire Home", callback_data='entire_home'),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Nice to meet you, {user_name}! Which area would you like to focus on?",
        reply_markup=reply_markup
    )
    
    return FENG_SHUI_ROOM

async def feng_shui_room(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the room selection."""
    query = update.callback_query
    await query.answer()
    
    room = query.data
    context.user_data['assessment']['room'] = room
    
    if 'birth_info' not in context.user_data['assessment']:
        await query.edit_message_text(
            f"Great! To provide personalized Feng Shui advice for your {room}, "
            f"when were you born? (Format: YYYY-MM-DD, e.g. 1990-05-15)\n\n"
            f"This helps me calculate your personal Kua number and lucky directions."
        )
        return FENG_SHUI_DIRECTIONS
    else:
        # Skip to results if birth info was already collected
        return await generate_feng_shui_results(update, context)

async def feng_shui_directions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the birth date for direction calculation."""
    try:
        birth_date = update.message.text
        # Parse the birth date (with basic validation)
        year, month, day = map(int, birth_date.split('-'))
        
        # Store birth info
        context.user_data['assessment']['birth_info'] = {
            'year': year,
            'month': month,
            'day': day
        }
        
        # Show typing indicator
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        # Generate personalized results
        return await generate_feng_shui_results(update, context)
        
    except Exception as e:
        logger.error(f"Error processing birth date: {e}")
        await update.message.reply_text(
            "I couldn't understand that date format. Please use YYYY-MM-DD (e.g., 1990-05-15)."
        )
        return FENG_SHUI_DIRECTIONS

async def generate_feng_shui_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate personalized Feng Shui results."""
    assessment = context.user_data['assessment']
    user_name = assessment['name']
    room = assessment['room']
    
    # Calculate Kua number if birth info is available
    kua_info = ""
    lucky_directions = ""
    if 'birth_info' in assessment:
        birth = assessment['birth_info']
        # Simple Kua number calculation (simplified for example)
        last_digit_of_year = birth['year'] % 10
        kua_base = last_digit_of_year + birth['month'] + birth['day']
        kua_number = kua_base % 9 or 9  # If remainder is 0, use 9
        
        # Determine lucky directions based on Kua number
        east_group = [1, 3, 4, 9]
        west_group = [2, 5, 6, 7, 8]
        
        if kua_number in east_group:
            lucky_directions = "East, Southeast, North, South"
        else:
            lucky_directions = "West, Northwest, Southwest, Northeast"
            
        kua_info = f"Based on your birth date, your Kua number is {kua_number}.\n\n"
        
    # Create a personalized query for the AI
    user_query = (
        f"Create a personalized Feng Shui analysis for {user_name}'s {room}. "
        f"Include specific recommendations for furniture placement, colors, and elements. "
        f"Their lucky directions are {lucky_directions}. Keep it concise but personal."
    )
    
    # Show typing indicator
    method = update.callback_query.edit_message_text if update.callback_query else update.message.reply_text
    
    try:
        # Generate AI response
        ai_service = get_ai_service()
        response = await ai_service.generate_response('feng_shui', user_query, update.effective_user.id)
        
        # Store the assessment context for follow-up questions
        context_summary = (
            f"Feng Shui assessment for {user_name}'s {room}. "
            f"Kua number: {kua_number if 'birth_info' in assessment else 'Not calculated'}. "
            f"Lucky directions: {lucky_directions or 'Not calculated'}."
        )
        ai_service.store_assessment_result(update.effective_user.id, 'feng_shui', context_summary)
        
        # Add personal touches to the response
        personalized_response = (
            f"✨ <b>{user_name}'s Personalized Feng Shui Analysis</b> ✨\n\n"
            f"{kua_info}"
            f"{response}\n\n"
            f"Would you like more specific advice about colors, furniture placement, or another room?"
        )
        
        # Store this assessment in the database
        db = SessionLocal()
        try:
            crud.log_conversation(
                db, update.effective_user.id, 
                f"Feng Shui assessment for {room}", 
                personalized_response, 
                'feng_shui'
            )
        finally:
            db.close()
        
        # Send the response
        if update.callback_query:
            await update.callback_query.edit_message_text(personalized_response, parse_mode="HTML")
        else:
            await update.message.reply_text(personalized_response, parse_mode="HTML")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error generating Feng Shui results: {e}")
        error_msg = "I'm having trouble creating your personalized Feng Shui analysis. Please try again later."
        
        if update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)
        
        return ConversationHandler.END