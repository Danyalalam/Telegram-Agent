from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction
from ...database.models import SessionLocal
from ...database import crud
import logging
import datetime

# Import conversation states
from ..conversation_states import BA_ZI_ASSESSMENT, BA_ZI_BIRTHDATE

logger = logging.getLogger(__name__)

# Function to get AI service safely
def get_ai_service():
    from ..telegram_bot import ai_service
    return ai_service

async def ba_zi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /bazi command."""
    user_id = update.effective_user.id
    
    response_text = (
        "🌙 *Ba Zi Four Pillars* 🌙\n\n"
        "Ba Zi (八字) or 'Four Pillars of Destiny' is a Chinese metaphysical concept "
        "that analyzes a person's fate based on birth time elements.\n\n"
        "I can explain concepts like:\n"
        "- What the Day Master element means\n"
        "- How the Five Elements influence your life\n"
        "- What your Lucky and Unlucky Elements are\n"
        "- How Heavenly Stems and Earthly Branches work\n\n"
        "For a personalized Ba Zi chart reading, use /assess and select Ba Zi."
    )
    
    # Set the current topic in user data
    context.user_data['current_topic'] = 'bazi'
    
    # Log this interaction
    db = SessionLocal()
    try:
        crud.log_conversation(
            db, 
            user_id, 
            "/bazi", 
            response_text,
            'bazi'
        )
    finally:
        db.close()
    
    await update.message.reply_text(
        response_text,
        parse_mode="HTML"
    )

async def ba_zi_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the Ba Zi user name input."""
    user_name = update.message.text
    context.user_data['assessment'] = {
        'name': user_name,
        'topic': 'bazi'
    }
    
    await update.message.reply_text(
        f"Thank you, {user_name}. To generate your Ba Zi chart, I need your birth date.\n\n"
        f"Please enter your birth date in this format: YYYY-MM-DD (e.g., 1990-05-15)"
    )
    
    return BA_ZI_BIRTHDATE

async def ba_zi_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's birthdate and generate Ba Zi chart."""
    try:
        birth_date_text = update.message.text
        birth_date = datetime.datetime.strptime(birth_date_text, "%Y-%m-%d")
        
        context.user_data['assessment']['birth_info'] = {
            'year': birth_date.year,
            'month': birth_date.month,
            'day': birth_date.day,
        }
        
        # Show typing indicator
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        # Calculate basic Ba Zi elements based on birth date
        await update.message.reply_text(
            f"Thank you. Generating your Ba Zi chart based on birth date: {birth_date_text}...\n\n"
            f"For a more accurate reading, I would typically need your birth time as well, "
            f"but I can create a basic chart with just the date."
        )
        
        # Generate personalized results
        return await generate_ba_zi_results(update, context)
        
    except ValueError:
        await update.message.reply_text(
            "Sorry, I couldn't understand that date format. Please use YYYY-MM-DD (e.g., 1990-05-15)."
        )
        return BA_ZI_BIRTHDATE

# Chinese calendar mapping tables
HEAVENLY_STEMS = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
EARTHLY_BRANCHES = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
STEM_ELEMENTS = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]
BRANCH_ANIMALS = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
BRANCH_ELEMENTS = ["Water", "Earth", "Wood", "Wood", "Earth", "Fire", "Fire", "Earth", "Metal", "Metal", "Earth", "Water"]

def get_year_pillar(year):
    """Calculate year pillar based on Chinese calendar."""
    stem_index = (year - 4) % 10
    branch_index = (year - 4) % 12
    return {
        'stem': HEAVENLY_STEMS[stem_index],
        'branch': EARTHLY_BRANCHES[branch_index],
        'stem_element': STEM_ELEMENTS[stem_index],
        'branch_element': BRANCH_ELEMENTS[branch_index],
        'animal': BRANCH_ANIMALS[branch_index]
    }

def get_month_pillar(year, month):
    """Calculate month pillar based on Chinese calendar (simplified)."""
    # Simplified calculation - actual would depend on solar terms
    stem_index = ((year - 4) * 12 + month) % 10
    
    # The problem is in this line - the calculation can produce values > 11
    # branch_index = (month + 2) % 12 if month > 2 else (month + 10)
    
    # Fixed calculation to ensure branch_index is between 0-11
    if month > 2:
        branch_index = (month + 2) % 12
    else:
        branch_index = (month + 10) % 12
    
    return {
        'stem': HEAVENLY_STEMS[stem_index],
        'branch': EARTHLY_BRANCHES[branch_index],
        'stem_element': STEM_ELEMENTS[stem_index],
        'branch_element': BRANCH_ELEMENTS[branch_index]
    }

def get_day_pillar(year, month, day):
    """Calculate day pillar based on Chinese calendar (simplified)."""
    # Simplified calculation - actual would involve complex formula
    base_date = datetime.datetime(1900, 1, 1)
    birth_date = datetime.datetime(year, month, day)
    days_diff = (birth_date - base_date).days
    stem_index = (days_diff + 10) % 10  # Starting from Geng
    branch_index = (days_diff + 12) % 12  # Starting from Zi
    return {
        'stem': HEAVENLY_STEMS[stem_index],
        'branch': EARTHLY_BRANCHES[branch_index],
        'stem_element': STEM_ELEMENTS[stem_index],
        'branch_element': BRANCH_ELEMENTS[branch_index]
    }

async def generate_ba_zi_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate personalized Ba Zi results."""
    assessment = context.user_data['assessment']
    user_name = assessment['name']
    birth = assessment['birth_info']
    
    # Calculate Ba Zi chart
    year_pillar = get_year_pillar(birth['year'])
    month_pillar = get_month_pillar(birth['year'], birth['month'])
    day_pillar = get_day_pillar(birth['year'], birth['month'], birth['day'])
    
    # Day Master (Day Stem Element)
    day_master = day_pillar['stem_element']
    
    # Store Ba Zi chart data
    context.user_data['assessment']['ba_zi'] = {
        'year_pillar': year_pillar,
        'month_pillar': month_pillar,
        'day_pillar': day_pillar,
        'day_master': day_master
    }
    
    # Format the chart for display - more compact format
    chart = (
        f"Year: {year_pillar['stem']} ({year_pillar['stem_element']}) {year_pillar['branch']} ({year_pillar['branch_element']}) - {year_pillar['animal']}\n"
        f"Month: {month_pillar['stem']} ({month_pillar['stem_element']}) {month_pillar['branch']} ({month_pillar['branch_element']})\n"
        f"Day: {day_pillar['stem']} ({day_pillar['stem_element']}) {day_pillar['branch']} ({day_pillar['branch_element']})\n"
        f"Day Master: {day_master}"
    )
    
    # Count elements for basic analysis
    elements = {
        'Wood': 0,
        'Fire': 0,
        'Earth': 0,
        'Metal': 0,
        'Water': 0
    }
    
    # Count elements from stems and branches
    for pillar in [year_pillar, month_pillar, day_pillar]:
        elements[pillar['stem_element']] += 1
        elements[pillar['branch_element']] += 1
    
    # Show typing indicator
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Create a personalized query for the AI - request a SHORTER response
    user_query = (
        f"Create a concise personalized Ba Zi (Four Pillars) reading for {user_name}, born on "
        f"{birth['year']}-{birth['month']}-{birth['day']}.\n\n"
        f"Their Ba Zi chart is:\n{chart}\n\n"
        f"Day Master: {day_master}\n"
        f"Element counts: Wood ({elements['Wood']}), Fire ({elements['Fire']}), "
        f"Earth ({elements['Earth']}), Metal ({elements['Metal']}), Water ({elements['Water']})\n\n"
        f"Provide brief insights about their personality, strengths, challenges, and favorable elements. "
        f"Keep your response under 1000 characters total."
    )
    
    try:
        # Generate AI response
        ai_service = get_ai_service()
        response = await ai_service.generate_response('bazi', user_query, update.effective_user.id)
        
        # Store the assessment context for follow-up questions
        context_summary = (
            f"Ba Zi reading for {user_name}, born on {birth['year']}-{birth['month']}-{birth['day']}. "
            f"Day Master: {day_master}. Chart shows: {elements['Wood']} Wood, {elements['Fire']} Fire, "
            f"{elements['Earth']} Earth, {elements['Metal']} Metal, {elements['Water']} Water."
        )
        ai_service.store_assessment_result(update.effective_user.id, 'bazi', context_summary)
        
        # Limit response length
        if len(response) > 2000:
            response = response[:1997] + "..."
        
        # Add personal touches to the response - more compact format
        personalized_response = (
            f"🌙 <b>{user_name}'s Ba Zi Chart</b> 🌙\n\n"
            f"<b>Chart:</b>\n{chart}\n\n"
            f"<b>Elements:</b> Wood: {elements['Wood']}, Fire: {elements['Fire']}, Earth: {elements['Earth']}, "
            f"Metal: {elements['Metal']}, Water: {elements['Water']}\n\n"
            f"<b>Your Reading:</b>\n\n"
            f"{response}\n\n"
            f"Would you like more information about your favorable elements or specific life aspects?"
        )
        
        # Ensure the total message is within Telegram limits
        if len(personalized_response) > 4000:
            # Further trim if still too long
            excess = len(personalized_response) - 3950
            response = response[:-excess] + "..."
            personalized_response = (
                f"🌙 <b>{user_name}'s Ba Zi Chart</b> 🌙\n\n"
                f"<b>Chart:</b>\n{chart}\n\n"
                f"<b>Elements:</b> Wood: {elements['Wood']}, Fire: {elements['Fire']}, Earth: {elements['Earth']}, "
                f"Metal: {elements['Metal']}, Water: {elements['Water']}\n\n"
                f"<b>Your Reading:</b>\n\n"
                f"{response}\n\n"
                f"Would you like more information about your favorable elements or specific life aspects?"
            )
        
        # Store this assessment in the database
        db = SessionLocal()
        try:
            crud.log_conversation(
                db, update.effective_user.id, 
                f"Ba Zi reading: Day Master {day_master}", 
                personalized_response[:500] + "...",  # Store a truncated version in the database
                'bazi'
            )
        finally:
            db.close()
        
        # Send the response
        await update.message.reply_text(personalized_response, parse_mode="HTML")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error generating Ba Zi results: {e}")
        await update.message.reply_text(
            "I'm having trouble creating your Ba Zi chart analysis. Please try again later."
        )
        
        return ConversationHandler.END