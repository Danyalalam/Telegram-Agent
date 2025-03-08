from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction
from ...database.models import SessionLocal
from ...database import crud
import logging
import datetime
from math import floor

# Import conversation states
from ..conversation_states import ZI_WEI_ASSESSMENT, ZI_WEI_BIRTHDATE, ZI_WEI_BIRTHTIME

logger = logging.getLogger(__name__)

# Function to get AI service safely
def get_ai_service():
    from ..telegram_bot import ai_service
    return ai_service

async def zi_wei_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /ziwei command."""
    user_id = update.effective_user.id
    
    response_text = (
        "⭐ *Zi Wei Dou Shu Purple Star Astrology* ⭐\n\n"
        "Zi Wei Dou Shu is an ancient Chinese astrological system that creates a detailed chart "
        "based on your birth date and time.\n\n"
        "I can explain concepts like:\n"
        "- The 12 Houses (Life Palaces) and their meanings\n"
        "- The major stars like Zi Wei, Tian Fu, and Emperor stars\n"
        "- How to interpret star combinations and palace influences\n"
        "- Predictions about different life aspects based on your chart\n\n"
        "For a personalized Zi Wei chart reading, use /assess and select Zi Wei Dou Shu."
    )
    
    # Set the current topic in user data
    context.user_data['current_topic'] = 'ziwei'
    
    # Log this interaction
    db = SessionLocal()
    try:
        crud.log_conversation(
            db, 
            user_id, 
            "/ziwei", 
            response_text,
            'ziwei'
        )
    finally:
        db.close()
    
    await update.message.reply_text(
        response_text,
        parse_mode="Markdown"
    )

async def zi_wei_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the Zi Wei user name input."""
    user_name = update.message.text
    context.user_data['assessment'] = {
        'name': user_name,
        'topic': 'ziwei'
    }
    
    await update.message.reply_text(
        f"Thank you, {user_name}. To create your Zi Wei Dou Shu chart, I need your birth date.\n\n"
        f"Please enter your birth date in this format: YYYY-MM-DD (e.g., 1990-05-15)"
    )
    
    return ZI_WEI_BIRTHDATE

async def zi_wei_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's birthdate input."""
    try:
        birth_date_text = update.message.text
        birth_date = datetime.datetime.strptime(birth_date_text, "%Y-%m-%d")
        
        context.user_data['assessment']['birth_info'] = {
            'year': birth_date.year,
            'month': birth_date.month,
            'day': birth_date.day
        }
        
        await update.message.reply_text(
            f"Great! Now I need your birth time to complete the chart.\n\n"
            f"Please enter your birth time in 24-hour format: HH:MM (e.g., 14:30 for 2:30 PM)"
        )
        
        return ZI_WEI_BIRTHTIME
        
    except ValueError:
        await update.message.reply_text(
            "Sorry, I couldn't understand that date format. Please use YYYY-MM-DD (e.g., 1990-05-15)."
        )
        return ZI_WEI_BIRTHDATE

async def zi_wei_birthtime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's birthtime and generate Zi Wei chart."""
    try:
        birth_time_text = update.message.text
        birth_time = datetime.datetime.strptime(birth_time_text, "%H:%M")
        
        # Add birth time to existing birth info
        context.user_data['assessment']['birth_info']['hour'] = birth_time.hour
        context.user_data['assessment']['birth_info']['minute'] = birth_time.minute
        
        # Show typing indicator
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        await update.message.reply_text(
            f"Thank you. I'm generating your Zi Wei Dou Shu chart based on your birth information...\n\n"
            f"This might take a moment as the calculations are quite complex."
        )
        
        # Generate personalized results
        return await generate_zi_wei_results(update, context)
        
    except ValueError:
        await update.message.reply_text(
            "Sorry, I couldn't understand that time format. Please use HH:MM in 24-hour format (e.g., 14:30)."
        )
        return ZI_WEI_BIRTHTIME

# Chinese lunar calendar mapping tables (simplified)
EARTHLY_BRANCHES = ["Zi (Rat)", "Chou (Ox)", "Yin (Tiger)", "Mao (Rabbit)", 
                    "Chen (Dragon)", "Si (Snake)", "Wu (Horse)", "Wei (Goat)", 
                    "Shen (Monkey)", "You (Rooster)", "Xu (Dog)", "Hai (Pig)"]

HEAVENLY_STEMS = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]

# Palace names
PALACES = ["Life", "Wealth", "Career", "Travel", "Friends", "Health", 
           "Children", "Spouse", "Property", "Reputation", "Happiness", "Parents"]

# Major stars
MAJOR_STARS = ["Zi Wei (Emperor)", "Tian Ji (Advisory)", "Tai Yang (Sun)", "Wu Qu (General)", 
               "Tian Tong (Communication)", "Lian Zhen (Chastity)", "Tian Fu (Civil Servant)", 
               "Tai Yin (Moon)", "Tan Lang (Greedy Wolf)", "Ju Men (Giant Gate)", 
               "Tian Xiang (Minister)", "Tian Liang (Clarity)", "Qi Sha (Seven Killings)", 
               "Po Jun (Defeated Army)"]

def calculate_ming_gong(year, month, day, hour):
    """Calculate the Ming Gong (Life Palace) position (simplified)."""
    # This is a simplified calculation - real Zi Wei uses Chinese lunar calendar
    # and complex astronomical calculations
    
    # Calculate a base value based on birth info
    lunar_month = month  # Simplified - should convert solar to lunar
    lunar_day = day      # Simplified - should convert solar to lunar
    
    # Calculate Ming Gong position
    ming_gong_index = (lunar_month + lunar_day // 3) % 12
    
    return ming_gong_index

def calculate_main_stars(ming_gong_index, year, month, day, hour):
    """Calculate positions of main stars based on Ming Gong (simplified)."""
    # This is a highly simplified calculation
    # Real Zi Wei calculations involve complex formulas for each star
    
    # Simulate star positions based on Ming Gong and birth info
    stars = {}
    
    # Zi Wei star calculation (simplified)
    birth_sum = year % 10 + month + day
    zi_wei_offset = birth_sum % 12
    zi_wei_pos = (ming_gong_index + zi_wei_offset) % 12
    stars["Zi Wei"] = zi_wei_pos
    
    # Tian Fu star calculation (simplified)
    tian_fu_pos = (12 - (zi_wei_pos - ming_gong_index)) % 12
    stars["Tian Fu"] = tian_fu_pos
    
    # Other star positions (simplified)
    stars["Tai Yang"] = (zi_wei_pos + 3) % 12
    stars["Tai Yin"] = (tian_fu_pos + 1) % 12
    stars["Wu Qu"] = (zi_wei_pos + 1) % 12
    stars["Tian Tong"] = (zi_wei_pos + 5) % 12
    
    return stars

def get_hour_branch(hour):
    """Convert hour to Chinese hour branch."""
    # Chinese hours are in 2-hour blocks
    if hour == 23 or hour < 1:
        return 0  # Zi (11pm-1am)
    else:
        return ((hour + 1) // 2) % 12

async def generate_zi_wei_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate personalized Zi Wei Dou Shu results."""
    assessment = context.user_data['assessment']
    user_name = assessment['name']
    birth = assessment['birth_info']
    
    try:
        # Calculate Zi Wei chart (simplified)
        ming_gong_index = calculate_ming_gong(birth['year'], birth['month'], birth['day'], birth['hour'])
        stars = calculate_main_stars(ming_gong_index, birth['year'], birth['month'], birth['day'], birth['hour'])
        
        # Create chart representation
        chart = {}
        for palace_idx, palace in enumerate(PALACES):
            chart[palace] = []
        
        # Place stars in palaces
        for star, pos in stars.items():
            chart[PALACES[pos]].append(star)
        
        # Format the chart for display - keep it shorter
        chart_text = "Life Palace (Ming Gong): " + EARTHLY_BRANCHES[ming_gong_index] + "\n\n"
        
        # Limit the number of palaces shown in detail to save space
        important_palaces = ["Life", "Wealth", "Career", "Spouse"]
        for palace, palace_stars in chart.items():
            if palace_stars and palace in important_palaces:
                chart_text += f"{palace} Palace: {', '.join(palace_stars)}\n"
        
        # Show typing indicator
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        # Store Zi Wei chart data
        context.user_data['assessment']['zi_wei'] = {
            'ming_gong': EARTHLY_BRANCHES[ming_gong_index],
            'chart': chart
        }
        
        # Create a personalized query for the AI - request a SHORTER response
        user_query = (
            f"Create a concise personalized Zi Wei Dou Shu reading for {user_name}, born on "
            f"{birth['year']}-{birth['month']}-{birth['day']} at {birth['hour']:02d}:{birth['minute']:02d}.\n\n"
            f"Their Zi Wei chart has the following key features:\n"
            f"- Life Palace (Ming Gong) is in {EARTHLY_BRANCHES[ming_gong_index]}\n"
            f"- Zi Wei star is in {PALACES[stars['Zi Wei']]} Palace\n"
            f"- Tian Fu star is in {PALACES[stars['Tian Fu']]} Palace\n\n"
            f"Provide brief insights about their life path, personality, and main life aspects. "
            f"Keep the response under 1500 characters total."
        )
        
        # Generate AI response
        ai_service = get_ai_service()
        response = await ai_service.generate_response('ziwei', user_query, update.effective_user.id)
        
        # Store the assessment context for follow-up questions
        context_summary = (
            f"Zi Wei Dou Shu reading for {user_name}, born on {birth['year']}-{birth['month']}-{birth['day']} "
            f"at {birth['hour']}:{birth['minute']}. Life Palace in {EARTHLY_BRANCHES[ming_gong_index]}. "
            f"Zi Wei star in {PALACES[stars['Zi Wei']]} Palace."
        )
        ai_service.store_assessment_result(update.effective_user.id, 'ziwei', context_summary)
        
        # Limit the AI response length
        if len(response) > 2000:
            response = response[:1997] + "..."
        
        # Add personal touches to the response - keep it shorter
        personalized_response = (
            f"⭐ <b>{user_name}'s Zi Wei Dou Shu Chart</b> ⭐\n\n"
            f"{chart_text}\n"
            f"<b>Your Analysis:</b>\n\n"
            f"{response}\n\n"
            f"Would you like information about other palaces in your chart?"
        )
        
        # Ensure the total message is within Telegram limits
        if len(personalized_response) > 4000:
            # Further trim if still too long
            excess = len(personalized_response) - 3950
            response = response[:-excess] + "..."
            personalized_response = (
                f"⭐ <b>{user_name}'s Zi Wei Dou Shu Chart</b> ⭐\n\n"
                f"{chart_text}\n"
                f"<b>Your Analysis:</b>\n\n"
                f"{response}\n\n"
                f"Would you like information about other palaces in your chart?"
            )
        
        # Store this assessment in the database
        db = SessionLocal()
        try:
            crud.log_conversation(
                db, update.effective_user.id, 
                f"Zi Wei Dou Shu reading", 
                personalized_response[:500] + "...",  # Store a truncated version in the database
                'ziwei'
            )
        finally:
            db.close()
        
        # Send the response
        await update.message.reply_text(personalized_response, parse_mode="HTML")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error generating Zi Wei results: {e}")
        await update.message.reply_text(
            "I'm having trouble creating your Zi Wei Dou Shu chart analysis. Please try again later."
        )
        
        return ConversationHandler.END