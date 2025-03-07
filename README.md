# Feng Shui AI Companion Bot

A Telegram bot that acts as an AI companion specializing in Feng Shui, MBTI personality analysis, and mythology. The bot provides insights, answers questions, and offers daily tips based on these topics.

## Features

- **Feng Shui Expert**: Provides insights on home layout, colors, lucky directions based on general Feng Shui principles
- **MBTI Advisor**: Analyzes user personality types and provides compatibility insights
- **Mythology Guide**: Explains mythological symbols and legends from various cultures
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
- `/fengshui` - Get Feng Shui advice
- `/mbti` - Get MBTI personality insights
- `/mythology` - Learn about mythology

## Development

This project uses:
- python-telegram-bot for Telegram integration
- FastAPI for the backend API
- Gemini AI for generating responses
- SQLAlchemy for database operations

## Todo

- [ ] Implement AI response generation for general queries
- [ ] Add daily tips functionality
- [ ] Enhance user memory and personalization