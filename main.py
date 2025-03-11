import asyncio
import uvicorn
from src.agent.telegram_bot import create_application, ai_service
from src.api.routes import app as fastapi_app
from src.database.models import init_db
from src.services.scheduler import TipsScheduler
from src.services.keep_alive import KeepAliveService
import threading
import logging
import os

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def run_bot():
    """Run the bot."""
    application = create_application()
    await application.initialize()
    
    # Create and start scheduler for daily tips
    try:
        scheduler = TipsScheduler(application, ai_service)
        scheduler.start()
        logger.info("Tip scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
    
    # Start the bot
    await application.start()
    await application.updater.start_polling()
    logger.info("Telegram bot started successfully")
    
    try:
        # Just hang tight for now
        await asyncio.Event().wait()
    finally:
        # Clean shutdown
        logger.info("Shutting down bot...")
        await application.stop()

# Update this function to use the PORT environment variable
def run_api():
    """Run the FastAPI server."""
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting API server on port {port}")
    uvicorn.run(fastapi_app, host="0.0.0.0", port=port)

async def main():
    """Run both the bot and API server."""
    # Initialize the database
    logger.info("Initializing database...")
    init_db()
    
    # Start the keep-alive service
    logger.info("Starting keep-alive service...")
    keep_alive = KeepAliveService(interval_minutes=10)  # Ping every 10 minutes
    keep_alive.start()
    
    # Start the API server in a separate thread
    logger.info("Starting API server...")
    api_thread = threading.Thread(target=run_api)
    api_thread.daemon = True
    api_thread.start()
    
    # Run the bot in the main thread
    logger.info("Starting Telegram bot...")
    await run_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}", exc_info=True)