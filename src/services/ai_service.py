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
            "top_k": 40,
            "max_output_tokens": 2048  # Increased output length for more detailed responses
        }
        
        # Safety settings - keep the safe defaults
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
        ]
        
        # Configure model with custom settings for better responses
        self.model = genai.GenerativeModel(
            'gemini-1.5-pro',
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        
        self.chat_sessions = {}  # Store chat sessions by user_id
        self.user_topics = {}    # Track the current topic for each user
        self.assessment_results = {}  # Store assessment results for follow-up questions
        self.user_languages = {}  # Track user language preferences

    async def generate_response(self, topic: str, query: str, user_id=None, language="en") -> str:
        """Generate a response using Gemini based on the topic and query."""
        
        # Update user language preference if provided
        if user_id:
            self.user_languages[user_id] = language
        
        # Check if this is a follow-up question to an assessment
        is_followup = False
        context_info = ""
        
        # Define follow-up keywords for different languages
        followup_keywords = {
            "en": [
                "yes", "sure", "please", "tell me more", "more information", 
                "explain", "elaborate", "continue", "go on", "and", "what about",
                "could you", "can you", "i'd like", "i would", "give me", "show me"
            ],
            "zh": [
                "是的", "好", "请", "告诉我更多", "更多信息", 
                "解释", "详述", "继续", "接着说", "和", "那么",
                "你能", "你可以", "我想", "我希望", "给我", "展示"
            ]
        }
        
        # Get the appropriate keywords based on language
        current_keywords = followup_keywords.get(language, followup_keywords["en"])
        
        # Check if this is a short query that might be a follow-up
        if user_id in self.assessment_results and len(query.split()) < 10:
            # Check for follow-up indicators
            if any(keyword in query.lower() for keyword in current_keywords):
                is_followup = True
                last_assessment = self.assessment_results[user_id]
                context_info = (
                    f"The user is asking a follow-up question to their {last_assessment['topic']} "
                    f"assessment. Their previous context was: {last_assessment['context']}. "
                    f"The user is now asking: {query}. Provide more information related to their "
                    f"previous assessment. Respond in {'Chinese' if language == 'zh' else 'English'}."
                )
        
        # Create the prompt based on whether this is a follow-up
        if is_followup:
            prompt = self._create_followup_prompt(topic, query, context_info, language)
        else:
            prompt = self._create_prompt(topic, query, language)
        
        try:
            # If user_id is provided, maintain a chat session
            if user_id:
                # Check if topic or language has changed for this user
                if (user_id in self.user_topics and 
                    (self.user_topics[user_id] != topic or 
                     self.user_languages.get(user_id) != language) and 
                    not is_followup):
                    # Topic or language changed, create a new chat session
                    self.chat_sessions[user_id] = self.model.start_chat(history=[])
                
                # Update current topic and language
                self.user_topics[user_id] = topic
                self.user_languages[user_id] = language
                
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
            if language == 'zh':
                return "抱歉，我暂时无法生成回复。请稍后再试。"
            else:
                return "I'm sorry, I couldn't generate a response at the moment. Please try again later."

    def store_assessment_result(self, user_id, topic, context):
        """Store assessment result for potential follow-up questions."""
        self.assessment_results[user_id] = {
            'topic': topic,
            'context': context
        }

    def _create_prompt(self, topic: str, query: str, language="en") -> str:
        """Create a prompt based on the topic and language."""
        
        # English prompts
        en_prompts = {
            "feng_shui": (
                f"You are a Feng Shui expert. Provide helpful, accurate advice about Feng Shui "
                f"in response to this query. Keep your response concise but thorough. "
                f"Respond in English. Query: {query}"
            ),
            "mbti": (
                f"You are an MBTI personality type expert. Provide helpful, accurate information "
                f"about MBTI personality types in response to this query. "
                f"Keep your response concise but thorough. "
                f"Respond in English. Query: {query}"
            ),
            "iching": (
                f"You are an I-Ching oracle expert. Provide helpful, accurate interpretation of "
                f"hexagrams and I-Ching wisdom in response to this query. "
                f"Keep your response concise but thorough. "
                f"Respond in English. Query: {query}"
            ),
            "bazi": (
                f"You are a Ba Zi (Four Pillars) expert. Provide helpful, accurate Chinese birth chart "
                f"analysis and interpretations in response to this query. "
                f"Keep your response concise but thorough. "
                f"Respond in English. Query: {query}"
            ),
            "ziwei": (
                f"You are a Zi Wei Dou Shu (Purple Star Astrology) expert. Provide helpful, accurate "
                f"interpretations of star positions and palace influences in response to this query. "
                f"Keep your response concise but thorough. "
                f"Respond in English. Query: {query}"
            ),
            "general": (
                f"You are an AI assistant specializing in Chinese metaphysics (Feng Shui, I-Ching, Ba Zi, "
                f"Zi Wei Dou Shu) and MBTI personality types. If this query relates to one of these topics, "
                f"provide relevant information. If not, politely explain that you focus on these domains. "
                f"Keep your response concise but thorough. "
                f"Respond in English. Query: {query}"
            )
        }
        
        # Chinese prompts
        zh_prompts = {
            "feng_shui": (
                f"你是一位风水专家。请对这个问题提供有帮助、准确的风水建议。"
                f"请保持简洁但详细的回答。请用中文回答。问题：{query}"
            ),
            "mbti": (
                f"你是一位MBTI人格类型专家。请针对这个问题提供有关MBTI人格类型的有帮助、准确的信息。"
                f"请保持简洁但详细的回答。请用中文回答。问题：{query}"
            ),
            "iching": (
                f"你是一位易经专家。请提供有关卦象和易经智慧的有帮助、准确的解释，回应这个问题。"
                f"请保持简洁但详细的回答。请用中文回答。问题：{query}"
            ),
            "bazi": (
                f"你是一位八字（四柱）专家。请提供有关中国生辰八字分析和解释的有帮助、准确的信息，回应这个问题。"
                f"请保持简洁但详细的回答。请用中文回答。问题：{query}"
            ),
            "ziwei": (
                f"你是一位紫微斗数（紫星占星）专家。请针对这个问题提供有关星位和宫位影响的有帮助、准确的解释。"
                f"请保持简洁但详细的回答。请用中文回答。问题：{query}"
            ),
            "general": (
                f"你是一位专注于中国玄学（风水、易经、八字、紫微斗数）和MBTI人格类型的AI助手。"
                f"如果这个问题与这些主题相关，请提供相关信息。如果不相关，请礼貌地解释你专注于这些领域。"
                f"请保持简洁但详细的回答。请用中文回答。问题：{query}"
            )
        }
        
        # Select the appropriate prompt set based on language
        prompts = zh_prompts if language == 'zh' else en_prompts
        
        return prompts.get(topic, prompts["general"])
    
    def _create_followup_prompt(self, topic: str, query: str, context_info: str, language="en") -> str:
        """Create a prompt for follow-up questions with context."""
        if language == 'zh':
            base = (
                f"用户正在询问一个后续问题。{context_info} "
                f"基于这个上下文，提供一个详细的回答，直接解答他们的后续问题。请用中文回答。问题：{query}"
            )
        else:
            base = (
                f"The user is asking a follow-up question. {context_info} "
                f"Based on this context, provide a detailed response that directly addresses "
                f"their follow-up question. Respond in English. Query: {query}"
            )
        return base
    
    def _format_response(self, text: str) -> str:
        """Format the response text to be suitable for Telegram."""
        # Limit to 4000 characters (Telegram's message limit)
        if len(text) > 4000:
            text = text[:3997] + "..."
        return text
    
    def get_user_language(self, user_id):
        """Get the user's preferred language."""
        return self.user_languages.get(user_id, "en")
    
    def set_user_language(self, user_id, language):
        """Set the user's preferred language."""
        self.user_languages[user_id] = language
        
    def reset_chat_session(self, user_id):
        """Reset a user's chat session."""
        if user_id in self.chat_sessions:
            self.chat_sessions[user_id] = self.model.start_chat(history=[])
            return True
        return False