from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ChatAction
from ...database.models import SessionLocal
from ...database import crud
import logging
import random

# Import conversation states
from ..conversation_states import I_CHING_ASSESSMENT, I_CHING_QUESTION

logger = logging.getLogger(__name__)

# Function to get AI service safely
def get_ai_service():
    from ..telegram_bot import ai_service
    return ai_service

async def i_ching_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /iching command."""
    user_id = update.effective_user.id
    
    response_text = (
        "🔮 *I-Ching Oracle* 🔮\n\n"
        "The I-Ching or 'Book of Changes' is an ancient Chinese divination text.\n\n"
        "I can provide readings and interpretations based on hexagrams.\n\n"
        "Ask me questions like:\n"
        "- What does hexagram 1 (The Creative) mean?\n"
        "- Can you interpret the hexagram 'The Well'?\n"
        "- How does the I-Ching view change and transformation?\n\n"
        "For a personalized reading, use /assess and select I-Ching."
    )
    
    # Set the current topic in user data
    context.user_data['current_topic'] = 'iching'
    
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
        parse_mode="Markdown"
    )

async def i_ching_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the I-Ching user name input."""
    user_name = update.message.text
    context.user_data['assessment'] = {
        'name': user_name,
        'topic': 'iching'
    }
    
    await update.message.reply_text(
        f"Thank you, {user_name}. The I-Ching can provide guidance for any question or situation.\n\n"
        f"Please ask your question or describe the situation you seek guidance for."
    )
    
    return I_CHING_QUESTION

async def i_ching_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's question and generate I-Ching hexagram."""
    user_question = update.message.text
    context.user_data['assessment']['question'] = user_question
    
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
        ('yang', 'yang', 'yang', 'yang', 'yang', 'yang'): 1,  # The Creative
        ('yin', 'yin', 'yin', 'yin', 'yin', 'yin'): 2,  # The Receptive
        ('yin', 'yang', 'yin', 'yin', 'yang', 'yin'): 3,  # Difficulty at the Beginning
        ('yin', 'yin', 'yang', 'yin', 'yin', 'yin'): 4,  # Youthful Folly
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
            hexagram_visual += '▅▅▅▅▅ (changing)\n'
        elif line == 'x':
            hexagram_visual += '▅▅ ▅▅ (changing)\n'
    
    # Show the hexagram to the user
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
    
    primary = hexagrams['primary']
    secondary = hexagrams['secondary']
    changing_lines = hexagrams['changing_lines']
    
    # Show typing indicator
    await update.message.chat.send_action(action=ChatAction.TYPING)
    
    # Create a personalized query for the AI
    user_query = (
        f"Create a personalized I-Ching reading for {user_name} who asked: '{question}'. "
        f"They received hexagram #{primary}"
        f"{f' changing to #{secondary}' if changing_lines else ''}. "
        f"The changing lines are {changing_lines if changing_lines else 'none'}. "
        f"Provide an interpretation that's personal and relevant to their question. "
        f"Include both general hexagram meaning and specific advice for their situation."
    )
    
    try:
        # Generate AI response
        ai_service = get_ai_service()
        response = await ai_service.generate_response('iching', user_query, update.effective_user.id)
        
        # Add personal touches to the response
        personalized_response = (
            f"🔮 *{user_name}'s I-Ching Reading* 🔮\n\n"
            f"*Your Question:* {question}\n\n"
            f"*Primary Hexagram:* #{primary}\n"
            f"{f'*Changing to:* #{secondary}' if changing_lines else ''}\n"
            f"*Changing Lines:* {', '.join(map(str, changing_lines)) if changing_lines else 'None'}\n\n"
            f"{response}\n\n"
            f"Would you like to ask another question or learn more about this hexagram?"
        )
        
        # Store this assessment in the database
        db = SessionLocal()
        try:
            crud.log_conversation(
                db, update.effective_user.id, 
                f"I-Ching reading: Hexagram {primary}", 
                personalized_response, 
                'iching'
            )
        finally:
            db.close()
        
        # Send the response
        await update.message.reply_text(personalized_response, parse_mode="Markdown")
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error generating I-Ching results: {e}")
        await update.message.reply_text(
            "I'm having trouble interpreting your I-Ching reading. Please try again later."
        )
        
        return ConversationHandler.END