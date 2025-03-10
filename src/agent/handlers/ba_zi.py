import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction
from ...database.models import SessionLocal
from ...database import crud
from ..conversation_states import BA_ZI_ASSESSMENT, BA_ZI_BIRTHDATE

logger = logging.getLogger(__name__)

# Function to get AI service safely
def get_ai_service():
    from ..telegram_bot import ai_service
    return ai_service

async def ba_zi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /bazi command."""
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
    
    # Set the current topic
    context.user_data['current_topic'] = 'bazi'
    
    # Show initial information message based on language
    if language == 'zh':
        response_text = (
            "🔮 <b>八字命理</b> 🔮\n\n"
            "八字（四柱命理）是一种古老的中国命理学，基于您的出生年、月、日、时分析您的命运。\n\n"
            "我可以帮您：\n"
            "• 解释您的天干地支组合\n"
            "• 分析您的五行平衡\n"
            "• 探讨命运中的强弱方面\n"
            "• 提供与职业、关系和财富相关的洞见\n\n"
            "如需个性化的八字解读，请使用 /assess 并选择八字。"
        )
    else:
        response_text = (
            "🔮 <b>BaZi (Four Pillars of Destiny)</b> 🔮\n\n"
            "BaZi is an ancient Chinese metaphysical system that analyzes your destiny based on your birth "
            "year, month, day, and hour.\n\n"
            "I can help you with:\n"
            "• Understanding your Heavenly Stems and Earthly Branches\n"
            "• Analyzing your Five Elements balance\n"
            "• Exploring strengths and weaknesses in your chart\n"
            "• Providing insights related to career, relationships, and wealth\n\n"
            "For a personalized BaZi reading, use /assess and select BaZi."
        )
    
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
    """Handle the BaZi user name input."""
    user_name = update.message.text
    context.user_data['assessment'] = {
        'name': user_name,
        'topic': 'bazi'
    }
    
    # Get language from assessment data or user data
    language = context.user_data.get('assessment', {}).get('language', None)
    
    if not language:
        language = context.user_data.get('language', 'en')
        # Store language in assessment data for later use
        context.user_data['assessment']['language'] = language
    
    if language == 'zh':
        await update.message.reply_text(
            f"谢谢，{user_name}。为了生成您的八字命盘，我需要您的出生日期。\n\n"
            f"请按照此格式输入您的出生日期：YYYY-MM-DD（例如，1990-05-15）"
        )
    else:
        await update.message.reply_text(
            f"Thank you, {user_name}. To generate your BaZi chart, I need your birth date.\n\n"
            f"Please enter your birth date in this format: YYYY-MM-DD (e.g., 1990-05-15)"
        )
    
    return BA_ZI_BIRTHDATE

async def ba_zi_birthdate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's birthdate and generate BaZi chart."""
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
        
        # Show typing indicator
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        if language == 'zh':
            await update.message.reply_text(
                f"谢谢。我正在根据您的出生日期（{birth_date.year}年{birth_date.month}月{birth_date.day}日）生成八字分析...\n\n"
                f"这可能需要一点时间。"
            )
        else:
            await update.message.reply_text(
                f"Thank you. I'm generating your BaZi analysis based on your birth date "
                f"({birth_date.month}/{birth_date.day}/{birth_date.year})...\n\n"
                f"This might take a moment."
            )
        
        # Generate personalized results
        return await generate_ba_zi_results(update, context)
        
    except ValueError:
        if language == 'zh':
            await update.message.reply_text(
                "抱歉，我无法理解该日期格式。请使用YYYY-MM-DD格式（例如，1990-05-15）。"
            )
        else:
            await update.message.reply_text(
                "Sorry, I couldn't understand that date format. Please use YYYY-MM-DD (e.g., 1990-05-15)."
            )
        return BA_ZI_BIRTHDATE

# Chinese lunar calendar mapping tables (simplified)
HEAVENLY_STEMS = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
HEAVENLY_STEMS_EN = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]

EARTHLY_BRANCHES = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
EARTHLY_BRANCHES_EN = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
ZODIAC_ANIMALS_EN = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
ZODIAC_ANIMALS_ZH = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]

FIVE_ELEMENTS_EN = ["Wood", "Fire", "Earth", "Metal", "Water"]
FIVE_ELEMENTS_ZH = ["木", "火", "土", "金", "水"]

def get_heavenly_stem(year):
    """Get the heavenly stem for a given year."""
    stem_index = (year - 4) % 10
    return stem_index

def get_earthly_branch(year):
    """Get the earthly branch for a given year."""
    branch_index = (year - 4) % 12
    return branch_index

def get_zodiac_animal(year):
    """Get the zodiac animal for a given year."""
    return get_earthly_branch(year)

def get_element(stem_index):
    """Get the five element for a given stem."""
    # The stem order determines the element: Wood (0,1), Fire (2,3), Earth (4,5), Metal (6,7), Water (8,9)
    return stem_index // 2

async def generate_ba_zi_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate personalized BaZi results."""
    assessment = context.user_data['assessment']
    user_name = assessment['name']
    birth = assessment['birth_info']
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    try:
        # Calculate basic BaZi elements (simplified)
        year_stem_idx = get_heavenly_stem(birth['year'])
        year_branch_idx = get_earthly_branch(birth['year'])
        year_element_idx = get_element(year_stem_idx)
        
        # Create a simplified BaZi chart
        if language == 'zh':
            year_pillar = f"{HEAVENLY_STEMS[year_stem_idx]}{EARTHLY_BRANCHES[year_branch_idx]}"
            animal = ZODIAC_ANIMALS_ZH[year_branch_idx]
            element = FIVE_ELEMENTS_ZH[year_element_idx]
            chart = f"年柱：{year_pillar}（{element}{animal}）"
        else:
            year_pillar = f"{HEAVENLY_STEMS_EN[year_stem_idx]} {EARTHLY_BRANCHES_EN[year_branch_idx]}"
            animal = ZODIAC_ANIMALS_EN[year_branch_idx]
            element = FIVE_ELEMENTS_EN[year_element_idx]
            chart = f"Year Pillar: {year_pillar} ({element} {animal})"
        
        # Show typing indicator
        await update.message.chat.send_action(action=ChatAction.TYPING)
        
        # Create a personalized query for the AI - request a SHORTER response
        if language == 'zh':
            user_query = (
                f"为{user_name}（出生于{birth['year']}年{birth['month']}月{birth['day']}日）创建一个简明的八字命理分析。\n\n"
                f"基本信息：\n"
                f"- 年柱：{year_pillar}\n"
                f"- 五行：{element}\n"
                f"- 生肖：{animal}\n\n"
                f"请提供以下内容的简短分析：\n"
                f"1. 性格特点和天赋\n"
                f"2. 事业和财运前景\n"
                f"3. 人际关系和爱情\n"
                f"4. 健康与平衡建议\n\n"
                f"请用中文回答，保持简洁，控制在1500字符以内。"
            )
        else:
            user_query = (
                f"Create a concise BaZi (Four Pillars) analysis for {user_name}, born on "
                f"{birth['month']}/{birth['day']}/{birth['year']}.\n\n"
                f"Basic information:\n"
                f"- Year Pillar: {year_pillar}\n"
                f"- Element: {element}\n"
                f"- Zodiac Animal: {animal}\n\n"
                f"Please provide a brief analysis of:\n"
                f"1. Character traits and talents\n"
                f"2. Career and wealth prospects\n"
                f"3. Relationships and love\n"
                f"4. Health and balance recommendations\n\n"
                f"Keep your response under 1500 characters total."
            )
        
        # Generate AI response
        ai_service = get_ai_service()
        response = await ai_service.generate_response('bazi', user_query, update.effective_user.id, language)
        
        # Store the assessment context for follow-up questions
        if language == 'zh':
            context_summary = f"{user_name}的八字命理分析，出生于{birth['year']}年{birth['month']}月{birth['day']}日。年柱：{year_pillar}。"
        else:
            context_summary = f"BaZi analysis for {user_name}, born on {birth['month']}/{birth['day']}/{birth['year']}. Year Pillar: {year_pillar}."
            
        ai_service.store_assessment_result(update.effective_user.id, 'bazi', context_summary)
        
        # Limit the response length
        if len(response) > 2000:
            response = response[:1997] + "..."
        
        # Add personal touches to the response - keep it short
        if language == 'zh':
            personalized_response = (
                f"🔮 <b>{user_name}的八字命理分析</b> 🔮\n\n"
                f"<b>出生日期：</b> {birth['year']}年{birth['month']}月{birth['day']}日\n"
                f"<b>{chart}</b>\n\n"
                f"{response}\n\n"
                f"您想了解关于您命理中特定方面的更多信息吗？"
            )
        else:
            personalized_response = (
                f"🔮 <b>BaZi Analysis for {user_name}</b> 🔮\n\n"
                f"<b>Birth Date:</b> {birth['month']}/{birth['day']}/{birth['year']}\n"
                f"<b>{chart}</b>\n\n"
                f"{response}\n\n"
                f"Would you like to know more about any specific aspect of your reading?"
            )
        
        # Ensure the total message is within Telegram limits
        if len(personalized_response) > 4000:
            # Further trim if still too long
            excess = len(personalized_response) - 3950
            response = response[:-excess] + "..."
            
            if language == 'zh':
                personalized_response = (
                    f"🔮 <b>{user_name}的八字命理分析</b> 🔮\n\n"
                    f"<b>出生日期：</b> {birth['year']}年{birth['month']}月{birth['day']}日\n"
                    f"<b>{chart}</b>\n\n"
                    f"{response}\n\n"
                    f"您想了解关于您命理中特定方面的更多信息吗？"
                )
            else:
                personalized_response = (
                    f"🔮 <b>BaZi Analysis for {user_name}</b> 🔮\n\n"
                    f"<b>Birth Date:</b> {birth['month']}/{birth['day']}/{birth['year']}\n"
                    f"<b>{chart}</b>\n\n"
                    f"{response}\n\n"
                    f"Would you like to know more about any specific aspect of your reading?"
                )
        
        # Store this assessment in the database
        db = SessionLocal()
        try:
            crud.log_conversation(
                db, update.effective_user.id, 
                f"BaZi reading", 
                personalized_response[:500] + "...",  # Store truncated version
                'bazi'
            )
        finally:
            db.close()
        
        # Send the response
        await update.message.reply_text(personalized_response, parse_mode="HTML")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error generating BaZi results: {e}")
        
        if language == 'zh':
            await update.message.reply_text(
                "我在创建您的八字分析时遇到了问题。请稍后再试。"
            )
        else:
            await update.message.reply_text(
                "I'm having trouble creating your BaZi analysis. Please try again later."
            )
        
        return ConversationHandler.END