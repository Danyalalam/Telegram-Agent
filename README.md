# Chinese Metaphysics AI Companion Bot

A Telegram bot that acts as an AI companion specializing in Chinese metaphysics (Feng Shui, I-Ching, Ba Zi, Zi Wei Dou Shu) and MBTI personality analysis. The bot provides insights, answers questions, and offers daily tips based on these topics.

## Features

- **Feng Shui Expert**: Provides insights on home layout, colors, lucky directions based on general Feng Shui principles
- **MBTI Advisor**: Analyzes user personality types and provides compatibility insights
- **I-Ching Oracle**: Interprets hexagrams from the ancient Chinese Book of Changes for divination
- **Ba Zi (Four Pillars)**: Analyzes Chinese birth charts to provide insights on personality and destiny
- **Zi Wei Dou Shu**: Creates and interprets Purple Star Astrology charts for comprehensive life readings
- **Daily Tips**: Sends automated push notifications with relevant insights
- **User Memory**: Stores user preferences and past interactions for personalized responses

## Setup

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Copy `.env.example` to `.env` and fill in your API keys
4. Run the bot: `python main.py`

## Commands

- `/start` - Start the bot and get welcome message
- `/help` - Display help information
- `/assess` - Begin a personalized assessment in any topic
- `/fengshui` - Get Feng Shui advice
- `/mbti` - Get MBTI personality insights
- `/iching` - Receive I-Ching divination and insights
- `/bazi` - Get Ba Zi (Four Pillars) birth chart analysis
- `/ziwei` - Get Zi Wei Dou Shu astrological chart reading
- `/history` - View your recent conversation history
- `/reset` - Clear conversation memory
- `/topic` - Change the current topic of discussion
- `/subscribe` - Subscribe or unsubscribe from daily tips

## Development

This project uses:
- python-telegram-bot for Telegram integration
- FastAPI for the backend API
- Gemini AI for generating responses
- SQLAlchemy for database operations