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
from telegram.ext import ConversationHandler
logger = logging.getLogger(__name__)

# Function to get AI service safely
def get_ai_service():
    from ..telegram_bot import ai_service
    return ai_service

async def zi_wei_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /ziwei command."""
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
    context.user_data['current_topic'] = 'ziwei'
    
    # Show initial information message based on language
    if language == 'zh':
        response_text = (
            "⭐ *紫微斗数* ⭐\n\n"
            "紫微斗数是古老的中国命理学体系，根据您的出生日期和时间创建详细的命盘。\n\n"
            "我可以解释以下概念：\n"
            "- 十二宫（命宫）及其含义\n"
            "- 主要星曜如紫微星、天府星和帝星\n"
            "- 如何解读星曜组合和宫位影响\n"
            "- 基于您命盘的不同生活方面的预测\n\n"
            "如需个人化的紫微斗数命盘解读，请使用 /assess 并选择紫微斗数。"
        )
    else:
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
    
    # Get language from assessment data or user data
    language = context.user_data.get('assessment', {}).get('language', None)
    
    if not language:
        language = context.user_data.get('language', 'en')
        # Store language in assessment data for later use
        context.user_data['assessment']['language'] = language
    
    if language == 'zh':
        await update.message.reply_text(
            f"谢谢，{user_name}。为了创建您的紫微斗数命盘，我需要您的出生日期。\n\n"
            f"请按照此格式输入您的出生日期：YYYY-MM-DD（例如，1990-05-15）"
        )
    else:
        await update.message.reply_text(
            f"Thank you, {user_name}. To create your Zi Wei Dou Shu chart, I need your birth date.\n\n"
            f"Please enter your birth date in this format: YYYY-MM-DD (e.g., 1990-05-15)"
        )
    
    return ZI_WEI_BIRTHDATE

async def zi_wei_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's birthdate input."""
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    try:
        birth_date_text = update.message.text
        birth_date = datetime.datetime.strptime(birth_date_text, "%Y-%m-%d")
        
        context.user_data['assessment']['birth_info'] = {
            'year': birth_date.year,
            'month': birth_date.month,
            'day': birth_date.day
        }
        
        if language == 'zh':
            await update.message.reply_text(
                f"很好！现在我需要您的出生时间来完成命盘。\n\n"
                f"请按24小时制输入您的出生时间：HH:MM（例如，14:30表示下午2:30）"
            )
        else:
            await update.message.reply_text(
                f"Great! Now I need your birth time to complete the chart.\n\n"
                f"Please enter your birth time in 24-hour format: HH:MM (e.g., 14:30 for 2:30 PM)"
            )
        
        return ZI_WEI_BIRTHTIME
        
    except ValueError:
        if language == 'zh':
            await update.message.reply_text(
                "抱歉，我无法理解该日期格式。请使用YYYY-MM-DD格式（例如，1990-05-15）。"
            )
        else:
            await update.message.reply_text(
                "Sorry, I couldn't understand that date format. Please use YYYY-MM-DD (e.g., 1990-05-15)."
            )
        return ZI_WEI_BIRTHDATE

async def zi_wei_birthtime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's birthtime and generate Zi Wei chart."""
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    try:
        birth_time_text = update.message.text
        birth_time = datetime.datetime.strptime(birth_time_text, "%H:%M")
        
        # Add birth time to existing birth info
        context.user_data['assessment']['birth_info']['hour'] = birth_time.hour
        context.user_data['assessment']['birth_info']['minute'] = birth_time.minute
        
        # Show typing indicator
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        if language == 'zh':
            await update.message.reply_text(
                f"谢谢。我正在根据您的出生信息生成紫微斗数命盘...\n\n"
                f"这可能需要一点时间，因为计算相当复杂。"
            )
        else:
            await update.message.reply_text(
                f"Thank you. I'm generating your Zi Wei Dou Shu chart based on your birth information...\n\n"
                f"This might take a moment as the calculations are quite complex."
            )
        
        # Generate personalized results
        return await generate_zi_wei_results(update, context)
        
    except ValueError:
        if language == 'zh':
            await update.message.reply_text(
                "抱歉，我无法理解该时间格式。请使用24小时制的HH:MM格式（例如，14:30）。"
            )
        else:
            await update.message.reply_text(
                "Sorry, I couldn't understand that time format. Please use HH:MM in 24-hour format (e.g., 14:30)."
            )
        return ZI_WEI_BIRTHTIME

# Chinese lunar calendar mapping tables (simplified)
# Bilingual version for each entry
EARTHLY_BRANCHES = [
    "Zi (Rat) / 子（鼠）", 
    "Chou (Ox) / 丑（牛）", 
    "Yin (Tiger) / 寅（虎）", 
    "Mao (Rabbit) / 卯（兔）",
    "Chen (Dragon) / 辰（龙）", 
    "Si (Snake) / 巳（蛇）", 
    "Wu (Horse) / 午（马）", 
    "Wei (Goat) / 未（羊）",
    "Shen (Monkey) / 申（猴）", 
    "You (Rooster) / 酉（鸡）", 
    "Xu (Dog) / 戌（狗）", 
    "Hai (Pig) / 亥（猪）"
]

# Bilingual version for Heavenly Stems
HEAVENLY_STEMS = [
    "Jia / 甲", "Yi / 乙", "Bing / 丙", "Ding / 丁", "Wu / 戊", 
    "Ji / 己", "Geng / 庚", "Xin / 辛", "Ren / 壬", "Gui / 癸"
]

# Bilingual palace names
PALACES_EN = ["Life", "Wealth", "Career", "Travel", "Friends", "Health", 
           "Children", "Spouse", "Property", "Reputation", "Happiness", "Parents"]

PALACES_ZH = ["命宫", "财帛", "兄弟", "田宅", "男女", "奴仆", 
           "迁移", "疾厄", "财神", "官禄", "福德", "父母"]

# Combined for backward compatibility
PALACES = PALACES_EN

# Major stars (bilingual)
MAJOR_STARS_EN = ["Zi Wei (Emperor)", "Tian Ji (Advisory)", "Tai Yang (Sun)", "Wu Qu (General)", 
               "Tian Tong (Communication)", "Lian Zhen (Chastity)", "Tian Fu (Civil Servant)", 
               "Tai Yin (Moon)", "Tan Lang (Greedy Wolf)", "Ju Men (Giant Gate)", 
               "Tian Xiang (Minister)", "Tian Liang (Clarity)", "Qi Sha (Seven Killings)", 
               "Po Jun (Defeated Army)"]

MAJOR_STARS_ZH = ["紫微星", "天机星", "太阳星", "武曲星", "天同星", "廉贞星", 
                "天府星", "太阴星", "贪狼星", "巨门星", "天相星", "天梁星", 
                "七杀星", "破军星"]

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
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    try:
        # Calculate Zi Wei chart (simplified)
        ming_gong_index = calculate_ming_gong(birth['year'], birth['month'], birth['day'], birth['hour'])
        stars = calculate_main_stars(ming_gong_index, birth['year'], birth['month'], birth['day'], birth['hour'])
        
        # Create chart representation
        chart = {}
        palace_list = PALACES_ZH if language == 'zh' else PALACES_EN
        
        for palace_idx, palace in enumerate(palace_list):
            chart[palace] = []
        
        # Place stars in palaces - use appropriate language for palace names
        star_names = {}
        for star_key, pos in stars.items():
            if language == 'zh':
                # Map English star names to Chinese versions
                if star_key == "Zi Wei":
                    star_names[MAJOR_STARS_ZH[0]] = pos
                elif star_key == "Tian Fu":
                    star_names[MAJOR_STARS_ZH[6]] = pos
                elif star_key == "Tai Yang":
                    star_names[MAJOR_STARS_ZH[2]] = pos
                elif star_key == "Tai Yin":
                    star_names[MAJOR_STARS_ZH[7]] = pos
                elif star_key == "Wu Qu":
                    star_names[MAJOR_STARS_ZH[3]] = pos
                elif star_key == "Tian Tong":
                    star_names[MAJOR_STARS_ZH[4]] = pos
            else:
                star_names[star_key] = pos
        
        # Place stars in palaces based on language
        if language == 'zh':
            for star, pos in star_names.items():
                chart[PALACES_ZH[pos]].append(star)
        else:
            for star, pos in stars.items():
                chart[PALACES_EN[pos]].append(star)
        
        # Format the chart for display - keep it shorter but with appropriate language
        if language == 'zh':
            chart_text = f"命宫：{EARTHLY_BRANCHES[ming_gong_index].split(' / ')[1]}\n\n"
            important_palaces = ["命宫", "财帛", "官禄", "田宅"]
        else:
            chart_text = f"Life Palace (Ming Gong): {EARTHLY_BRANCHES[ming_gong_index].split(' / ')[0]}\n\n"
            important_palaces = ["Life", "Wealth", "Career", "Property"]
        
        # Limit the number of palaces shown in detail to save space
        for palace, palace_stars in chart.items():
            if palace_stars and palace in important_palaces:
                chart_text += f"{palace}: {', '.join(palace_stars)}\n"
        
        # Show typing indicator
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        # Store Zi Wei chart data
        context.user_data['assessment']['zi_wei'] = {
            'ming_gong': EARTHLY_BRANCHES[ming_gong_index],
            'chart': chart
        }
        
        # Create a personalized query for the AI - request a SHORTER response
        if language == 'zh':
            user_query = (
                f"为{user_name}创建一个简明的紫微斗数解读，出生于"
                f"{birth['year']}年{birth['month']}月{birth['day']}日 {birth['hour']:02d}:{birth['minute']:02d}。\n\n"
                f"他们的紫微命盘有以下主要特点：\n"
                f"- 命宫在{EARTHLY_BRANCHES[ming_gong_index].split(' / ')[1]}\n"
                f"- 紫微星在{PALACES_ZH[stars['Zi Wei']]}宫\n"
                f"- 天府星在{PALACES_ZH[stars['Tian Fu']]}宫\n\n"
                f"请提供关于他们人生道路、性格和主要生活方面的简短见解。"
                f"请用中文回答，将总回复控制在1500字符以内。"
            )
        else:
            user_query = (
                f"Create a concise personalized Zi Wei Dou Shu reading for {user_name}, born on "
                f"{birth['year']}-{birth['month']}-{birth['day']} at {birth['hour']:02d}:{birth['minute']:02d}.\n\n"
                f"Their Zi Wei chart has the following key features:\n"
                f"- Life Palace (Ming Gong) is in {EARTHLY_BRANCHES[ming_gong_index].split(' / ')[0]}\n"
                f"- Zi Wei star is in {PALACES_EN[stars['Zi Wei']]} Palace\n"
                f"- Tian Fu star is in {PALACES_EN[stars['Tian Fu']]} Palace\n\n"
                f"Provide brief insights about their life path, personality, and main life aspects. "
                f"Keep the response under 1500 characters total."
            )
        
        # Generate AI response
        ai_service = get_ai_service()
        response = await ai_service.generate_response('ziwei', user_query, update.effective_user.id, language)
        
        # Store the assessment context for follow-up questions
        if language == 'zh':
            context_summary = (
                f"{user_name}的紫微斗数解读，出生于{birth['year']}年{birth['month']}月{birth['day']}日"
                f"{birth['hour']}时{birth['minute']}分。命宫在{EARTHLY_BRANCHES[ming_gong_index].split(' / ')[1]}。"
                f"紫微星在{PALACES_ZH[stars['Zi Wei']]}宫。"
            )
        else:
            context_summary = (
                f"Zi Wei Dou Shu reading for {user_name}, born on {birth['year']}-{birth['month']}-{birth['day']} "
                f"at {birth['hour']}:{birth['minute']}. Life Palace in {EARTHLY_BRANCHES[ming_gong_index].split(' / ')[0]}. "
                f"Zi Wei star in {PALACES_EN[stars['Zi Wei']]} Palace."
            )
        
        ai_service.store_assessment_result(update.effective_user.id, 'ziwei', context_summary)
        
        # Limit the AI response length
        if len(response) > 2000:
            response = response[:1997] + "..."
        
        # Add personal touches to the response - keep it shorter with language support
        if language == 'zh':
            personalized_response = (
                f"⭐ <b>{user_name}的紫微斗数命盘</b> ⭐\n\n"
                f"{chart_text}\n"
                f"<b>您的分析：</b>\n\n"
                f"{response}\n\n"
                f"您想了解关于您命盘中其他宫位的信息吗？"
            )
        else:
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
            
            if language == 'zh':
                personalized_response = (
                    f"⭐ <b>{user_name}的紫微斗数命盘</b> ⭐\n\n"
                    f"{chart_text}\n"
                    f"<b>您的分析：</b>\n\n"
                    f"{response}\n\n"
                    f"您想了解关于您命盘中其他宫位的信息吗？"
                )
            else:
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
        
        if language == 'zh':
            await update.message.reply_text(
                "我在创建您的紫微斗数命盘分析时遇到了问题。请稍后再试。"
            )
        else:
            await update.message.reply_text(
                "I'm having trouble creating your Zi Wei Dou Shu chart analysis. Please try again later."
            )
        
        return ConversationHandler.END