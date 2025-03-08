import google.generativeai as genai
import logging
from ..config import GEMINI_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

# Configure the Gemini API
genai.configure(api_key=GEMINI_API_KEY)

class AIService:
    def __init__(self):
        # Define generation config for more context retention
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40
        }
        
        # Configure model with custom settings for better responses
        self.model = genai.GenerativeModel(
            'gemini-1.5-pro',
            generation_config=generation_config
        )
        
        self.chat_sessions = {}  # Store chat sessions by user_id
        self.user_topics = {}    # Track the current topic for each user

    async def generate_response(self, topic: str, query: str, user_id=None) -> str:
        """Generate a response using Gemini based on the topic and query."""
        prompt = self._create_prompt(topic, query)
        
        try:
            # If user_id is provided, maintain a chat session
            if user_id:
                # Check if topic has changed for this user
                if user_id in self.user_topics and self.user_topics[user_id] != topic:
                    # Topic changed, create a new chat session
                    self.chat_sessions[user_id] = self.model.start_chat(history=[])
                
                # Update current topic
                self.user_topics[user_id] = topic
                
                # Create new chat session if needed
                if user_id not in self.chat_sessions:
                    self.chat_sessions[user_id] = self.model.start_chat(history=[])
                
                # Use the existing chat session
                chat = self.chat_sessions[user_id]
                response = await chat.send_message_async(prompt)
            else:
                # One-off generation
                response = await self.model.generate_content_async(prompt)
                
            return self._format_response(response.text)
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm sorry, I couldn't generate a response at the moment. Please try again later."

    def _create_prompt(self, topic: str, query: str) -> str:
        """Create a prompt based on the topic."""
        prompts = {
            "feng_shui": (
                f"You are a Feng Shui expert. Provide helpful, accurate advice about Feng Shui "
                f"in response to this query. Keep your response concise and to the point: {query}"
            ),
            "mbti": (
                f"You are an MBTI personality type expert. Provide helpful, accurate information "
                f"about MBTI personality types in response to this query. Keep your response concise: {query}"
            ),
            "iching": (
                f"You are an I-Ching oracle expert. Provide helpful, accurate interpretation of "
                f"hexagrams and I-Ching wisdom in response to this query. Keep your response concise: {query}"
            ),
            "bazi": (
                f"You are a Ba Zi (Four Pillars) expert. Provide helpful, accurate Chinese birth chart "
                f"analysis and interpretations in response to this query. Keep your response concise: {query}"
            ),
            "ziwei": (
                f"You are a Zi Wei Dou Shu (Purple Star Astrology) expert. Provide helpful, accurate "
                f"interpretations of star positions and palace influences in response to this query. "
                f"Keep your response concise: {query}"
            ),
            "general": (
                f"You are an AI assistant specializing in Chinese metaphysics (Feng Shui, I-Ching, Ba Zi, "
                f"Zi Wei Dou Shu) and MBTI personality types. If this query relates to one of these topics, "
                f"provide relevant information. If not, politely explain that you focus on these domains. "
                f"Keep responses concise: {query}"
            )
        }
        
        return prompts.get(topic, prompts["general"])
    
    def _format_response(self, text: str) -> str:
        """Format the response text to be suitable for Telegram."""
        # Limit to 4000 characters (Telegram's message limit)
        if len(text) > 4000:
            text = text[:3997] + "..."
        return text