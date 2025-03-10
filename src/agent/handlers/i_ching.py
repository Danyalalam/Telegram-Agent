from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction
from ...database.models import SessionLocal
from ...database import crud
import logging
import random

# Import conversation states
from ..conversation_states import I_CHING_ASSESSMENT, I_CHING_QUESTION
from telegram.ext import ConversationHandler
logger = logging.getLogger(__name__)

# Function to get AI service safely
def get_ai_service():
    from ..telegram_bot import ai_service
    return ai_service

async def i_ching_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /iching command."""
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
            language = 'en'  # Default to English
        finally:
            db.close()
    
    # Set the current topic
    context.user_data['current_topic'] = 'iching'
    
    # Show initial information message based on language
    if language == 'zh':
        response_text = """🔮 <b>易经</b> 🔮

    《易经》或"变化之书"是古代中国占卜文献。

    我可以基于卦象提供解读和诠释。

    您可以问我这样的问题：
    - 乾卦（第一卦）代表什么？
    - 可以解释一下井卦吗？
    - 易经如何看待变化和转化？

    如需个性化解读，请使用 /assess 并选择易经。"""
        
    else:
        response_text = (
            "🔮 <b>I-Ching Oracle</b> 🔮\n\n"
            "The I-Ching or 'Book of Changes' is an ancient Chinese divination text.\n\n"
            "I can provide readings and interpretations based on hexagrams.\n\n"
            "Ask me questions like:\n"
            "- What does hexagram 1 (The Creative) mean?\n"
            "- Can you interpret the hexagram 'The Well'?\n"
            "- How does the I-Ching view change and transformation?\n\n"
            "For a personalized reading, use /assess and select I-Ching."
        )
    
    # Log this interaction
    db = SessionLocal()
    try:
        crud.log_conversation(
            db, 
            user_id, 
            "/iching", 
            response_text,
            'iching'
        )
    finally:
        db.close()
    
    await update.message.reply_text(
        response_text,
        parse_mode="HTML"
    )

async def i_ching_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the I-Ching user name input."""
    user_name = update.message.text
    context.user_data['assessment'] = {
        'name': user_name,
        'topic': 'iching'
    }
    
    # Get language from assessment data or user data
    language = context.user_data.get('assessment', {}).get('language', None)
    
    if not language:
        language = context.user_data.get('language', 'en')
        # Store language in assessment data for later use
        context.user_data['assessment']['language'] = language
    
    if language == 'zh':
        await update.message.reply_text(
            f"谢谢，{user_name}。易经可以为任何问题或情况提供指引。\n\n"
            f"请提出您的问题或描述您需要指引的情况。"
        )
    else:
        await update.message.reply_text(
            f"Thank you, {user_name}. The I-Ching can provide guidance for any question or situation.\n\n"
            f"Please ask your question or describe the situation you seek guidance for."
        )
    
    return I_CHING_QUESTION

async def i_ching_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's question and generate I-Ching hexagram."""
    user_question = update.message.text
    context.user_data['assessment']['question'] = user_question
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    # Show typing indicator
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Generate the hexagram - simulating the coin toss method
    lines = []
    for _ in range(6):
        # Simulate 3 coin tosses (heads=3, tails=2)
        coins = [random.choice([2, 3]) for _ in range(3)]
        total = sum(coins)
        
        # Determine line type based on the sum
        if total == 6:  # All tails (yin changing)
            lines.append('x')
        elif total == 7:  # 2 heads 1 tail (yang stable)
            lines.append('-')
        elif total == 8:  # 1 head 2 tails (yin stable)
            lines.append('--')
        elif total == 9:  # All heads (yang changing)
            lines.append('o')
    
    # Convert to primary and secondary hexagrams
    primary_hexagram = []
    secondary_hexagram = []
    
    for line in lines:
        if line == '-':  # Yang stable
            primary_hexagram.append('yang')
            secondary_hexagram.append('yang')
        elif line == '--':  # Yin stable
            primary_hexagram.append('yin')
            secondary_hexagram.append('yin')
        elif line == 'o':  # Yang changing to Yin
            primary_hexagram.append('yang')
            secondary_hexagram.append('yin')
        elif line == 'x':  # Yin changing to Yang
            primary_hexagram.append('yin')
            secondary_hexagram.append('yang')
    
    # Determine the hexagram numbers (simplified mapping - would be more complex in real implementation)
    hex_types = {
        ('yang', 'yang', 'yang', 'yang', 'yang', 'yang'): 1,  # The Creative / 乾
        ('yin', 'yin', 'yin', 'yin', 'yin', 'yin'): 2,  # The Receptive / 坤
        ('yin', 'yang', 'yin', 'yin', 'yang', 'yin'): 3,  # Difficulty at the Beginning / 屯
        ('yin', 'yin', 'yang', 'yin', 'yin', 'yin'): 4,  # Youthful Folly / 蒙
        # ... more hexagrams would be defined here
    }
    
    # Get the hexagram number or use a default
    primary_num = hex_types.get(tuple(primary_hexagram), random.randint(1, 64))
    secondary_num = hex_types.get(tuple(secondary_hexagram), random.randint(1, 64))
    
    # Store hexagram info
    context.user_data['assessment']['hexagrams'] = {
        'primary': primary_num,
        'secondary': secondary_num,
        'changing_lines': [i for i, line in enumerate(lines, 1) if line in ['o', 'x']]
    }
    
    # Create a visual representation of the hexagram
    hexagram_visual = ''
    for line in reversed(lines):  # Display bottom to top as is traditional
        if line == '-':
            hexagram_visual += '▅▅▅▅▅\n'
        elif line == '--':
            hexagram_visual += '▅▅ ▅▅\n'
        elif line == 'o':
            hexagram_visual += '▅▅▅▅▅ (changing)\n' if language == 'en' else '▅▅▅▅▅ (变爻)\n'
        elif line == 'x':
            hexagram_visual += '▅▅ ▅▅ (changing)\n' if language == 'en' else '▅▅ ▅▅ (变爻)\n'
    
    # Show the hexagram to the user
    if language == 'zh':
        await update.message.reply_text(
            f"*您的易经卦象*\n\n"
            f"```\n{hexagram_visual}```\n"
            f"主卦: *第{primary_num}卦*\n"
            f"{'有变爻' if context.user_data['assessment']['hexagrams']['changing_lines'] else ''}\n\n"
            f"请稍候，我正在为您的问题解读这个卦象...",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"*Your I-Ching Hexagram*\n\n"
            f"```\n{hexagram_visual}```\n"
            f"Primary Hexagram: *#{primary_num}*\n"
            f"{'with changing lines' if context.user_data['assessment']['hexagrams']['changing_lines'] else ''}\n\n"
            f"Please wait while I interpret this reading for your question...",
            parse_mode="Markdown"
        )
    
    return await generate_i_ching_results(update, context)

async def generate_i_ching_results(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generate personalized I-Ching results."""
    assessment = context.user_data['assessment']
    user_name = assessment['name']
    question = assessment['question']
    hexagrams = assessment['hexagrams']
    
    # Get language from assessment data
    language = context.user_data['assessment'].get('language', 'en')
    
    primary = hexagrams['primary']
    secondary = hexagrams['secondary']
    changing_lines = hexagrams['changing_lines']
    
    # Show typing indicator
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Create a personalized query for the AI - request a SHORTER response
    if language == 'zh':
        user_query = (
            f"为{user_name}创建一个简明的易经解读，针对问题：'{question}'。"
            f"他们得到了第{primary}卦"
            f"{f'，变化为第{secondary}卦' if changing_lines else ''}。"
            f"变爻位置是{changing_lines if changing_lines else '无'}。"
            f"提供与他们问题相关的简短但有意义的解读。"
            f"包括卦象的含义和具体建议。请用中文回答，将回答控制在1500字符以内。"
        )
    else:
        user_query = (
            f"Create a concise personalized I-Ching reading for {user_name} who asked: '{question}'. "
            f"They received hexagram #{primary}"
            f"{f' changing to #{secondary}' if changing_lines else ''}. "
            f"The changing lines are {changing_lines if changing_lines else 'none'}. "
            f"Provide a brief but meaningful interpretation relevant to their question. "
            f"Include the hexagram meaning and specific advice. Keep the response under 1500 characters."
        )
    
    try:
        # Generate AI response
        ai_service = get_ai_service()
        response = await ai_service.generate_response('iching', user_query, update.effective_user.id, language)
        
        # Store the assessment context for follow-up questions
        if language == 'zh':
            context_summary = (
                f"{user_name}的易经解读，问题：'{question}'。"
                f"主卦第{primary}卦"
                f"{f'，变卦第{secondary}卦' if changing_lines else ''}。"
                f"变爻：{', '.join(map(str, changing_lines)) if changing_lines else '无'}。"
            )
        else:
            context_summary = (
                f"I-Ching reading for {user_name}'s question: '{question}'. "
                f"Primary hexagram #{primary}"
                f"{f', changing to #{secondary}' if changing_lines else ''}. "
                f"Changing lines: {', '.join(map(str, changing_lines)) if changing_lines else 'None'}."
            )
        ai_service.store_assessment_result(update.effective_user.id, 'iching', context_summary)
        
        # Limit the response length
        if len(response) > 2000:
            response = response[:1997] + "..."
        
        # Truncate question if it's too long
        if len(question) > 100:
            question = question[:97] + "..."
        
        # Add personal touches to the response - keep it short and concise
        if language == 'zh':
            personalized_response = (
                f"🔮 <b>{user_name}的易经解读</b> 🔮\n\n"
                f"<b>问题：</b> {question}\n\n"
                f"<b>卦象：</b> 第{primary}卦"
                f"{f' → 第{secondary}卦' if changing_lines else ''}\n"
                f"<b>变爻：</b> {', '.join(map(str, changing_lines)) if changing_lines else '无'}\n\n"
                f"{response}\n\n"
                f"您想了解更多关于这个解读的详情吗？"
            )
        else:
            personalized_response = (
                f"🔮 <b>{user_name}'s I-Ching Reading</b> 🔮\n\n"
                f"<b>Question:</b> {question}\n\n"
                f"<b>Hexagram:</b> #{primary}"
                f"{f' → #{secondary}' if changing_lines else ''}\n"
                f"<b>Lines:</b> {', '.join(map(str, changing_lines)) if changing_lines else 'None'}\n\n"
                f"{response}\n\n"
                f"Would you like more details about this reading?"
            )
        
        # Ensure the total message is within Telegram limits
        if len(personalized_response) > 4000:
            # Further trim if still too long
            excess = len(personalized_response) - 3950
            response = response[:-excess] + "..."
            
            if language == 'zh':
                personalized_response = (
                    f"🔮 <b>{user_name}的易经解读</b> 🔮\n\n"
                    f"<b>问题：</b> {question}\n\n"
                    f"<b>卦象：</b> 第{primary}卦"
                    f"{f' → 第{secondary}卦' if changing_lines else ''}\n"
                    f"<b>变爻：</b> {', '.join(map(str, changing_lines)) if changing_lines else '无'}\n\n"
                    f"{response}\n\n"
                    f"您想了解更多关于这个解读的详情吗？"
                )
            else:
                personalized_response = (
                    f"🔮 <b>{user_name}'s I-Ching Reading</b> 🔮\n\n"
                    f"<b>Question:</b> {question}\n\n"
                    f"<b>Hexagram:</b> #{primary}"
                    f"{f' → #{secondary}' if changing_lines else ''}\n"
                    f"<b>Lines:</b> {', '.join(map(str, changing_lines)) if changing_lines else 'None'}\n\n"
                    f"{response}\n\n"
                    f"Would you like more details about this reading?"
                )
        
        # Store this assessment in the database
        db = SessionLocal()
        try:
            crud.log_conversation(
                db, update.effective_user.id, 
                f"I-Ching reading: Hexagram {primary}", 
                personalized_response[:500] + "...",  # Store truncated version in database 
                'iching'
            )
        finally:
            db.close()
        
        # Send the response
        await update.message.reply_text(personalized_response, parse_mode="HTML")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error generating I-Ching results: {e}")
        
        if language == 'zh':
            await update.message.reply_text(
                "我在解读您的易经卦象时遇到了困难。请稍后再试。"
            )
        else:
            await update.message.reply_text(
                "I'm having trouble interpreting your I-Ching reading. Please try again later."
            )
        
        return ConversationHandler.END