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
            topics = ['feng_shui', 'mbti', 'mythology']
            topic = topics[day_of_week % len(topics)]
            
            # Generate tip using AI
            tip_prompt = f"Generate a short, insightful daily tip about {topic} that would be valuable to most people."
            tip = await self.ai_service.generate_response(topic, tip_prompt)
            
            # Format the tip with emojis
            topic_emojis = {"feng_shui": "🏠", "mbti": "🧠", "mythology": "🔮"}
            emoji = topic_emojis.get(topic, "💬")
            formatted_tip = f"{emoji} *Daily {topic.replace('_', ' ').title()} Tip* {emoji}\n\n{tip}"
            
            # Send to each subscribed user
            for user in subscribed_users:
                try:
                    await self.application.bot.send_message(
                        chat_id=user.telegram_id,
                        text=formatted_tip,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Sent daily tip to user {user.telegram_id}")
                except Exception as e:
                    logger.error(f"Failed to send tip to user {user.telegram_id}: {e}")
                
                # Add delay to avoid hitting rate limits
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Error in send_daily_tips: {e}")
        finally:
            db.close()