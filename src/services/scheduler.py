import asyncio
import logging
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application
from ..database.models import SessionLocal
from ..database import crud
from .ai_service import AIService

logger = logging.getLogger(__name__)

class TipsScheduler:
    def __init__(self, application: Application, ai_service: AIService):
        self.application = application
        self.ai_service = ai_service
        self.scheduler = AsyncIOScheduler()
        
    def start(self):
        """Start the scheduler for daily tips."""
        # Schedule daily tips at 9:00 AM
        self.scheduler.add_job(
            self.send_daily_tips,
            CronTrigger(hour=9, minute=0),
            id='daily_tips',
            replace_existing=True
        )
        self.scheduler.start()
        logger.info("Scheduler started for daily tips")
        
    async def send_daily_tips(self):
        """Send daily tips to subscribed users."""
        logger.info("Sending daily tips to subscribers")
        db = SessionLocal()
        
        try:
            # Get all subscribed users
            subscribed_users = crud.get_subscribed_users(db)
            
            if not subscribed_users:
                logger.info("No subscribed users found")
                return
            
            # Determine which topic to use based on day of week
            day_of_week = datetime.now().weekday()
            topics = ['feng_shui', 'mbti', 'iching', 'bazi', 'ziwei']
            topic = topics[day_of_week % len(topics)]
            
            # Send to each subscribed user in their preferred language
            for user in subscribed_users:
                # Get user's preferred language
                language = user.language if hasattr(user, 'language') else 'en'
                
                # Generate tip using AI in the user's language
                tip_prompt = f"Generate a short, insightful daily tip about {topic} that would be valuable to most people."
                tip = await self.ai_service.generate_response(topic, tip_prompt, language=language)
                
                # Format the tip with emojis
                topic_emojis = {
                    "feng_shui": "🏠", 
                    "mbti": "🧠", 
                    "iching": "🔮",
                    "bazi": "🌙",
                    "ziwei": "⭐"
                }
                emoji = topic_emojis.get(topic, "💬")
                
                # Create topic title based on language
                if language == 'zh':
                    topic_title = topic.replace('_', ' ').title()
                    if topic == 'feng_shui':
                        topic_title = "风水"
                    elif topic == 'mbti':
                        topic_title = "MBTI人格"
                    elif topic == 'iching':
                        topic_title = "易经"
                    elif topic == 'bazi':
                        topic_title = "八字"
                    elif topic == 'ziwei':
                        topic_title = "紫微斗数"
                    
                    formatted_tip = f"{emoji} <b>每日{topic_title}提示</b> {emoji}\n\n{tip}"
                else:
                    formatted_tip = f"{emoji} <b>Daily {topic.replace('_', ' ').title()} Tip</b> {emoji}\n\n{tip}"
                
                try:
                    await self.application.bot.send_message(
                        chat_id=user.telegram_id,
                        text=formatted_tip,
                        parse_mode='HTML'
                    )
                    logger.info(f"Sent daily tip to user {user.telegram_id} in {language}")
                except Exception as e:
                    logger.error(f"Failed to send tip to user {user.telegram_id}: {e}")
                    
                    # Fallback to plain text if HTML parsing fails
                    try:
                        plain_text = formatted_tip.replace('<b>', '').replace('</b>', '')
                        await self.application.bot.send_message(
                            chat_id=user.telegram_id,
                            text=plain_text
                        )
                        logger.info(f"Sent fallback plain text tip to user {user.telegram_id}")
                    except Exception as e2:
                        logger.error(f"Failed to send fallback tip to user {user.telegram_id}: {e2}")
                
                # Add delay to avoid hitting rate limits
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in send_daily_tips: {e}")
        finally:
            db.close()