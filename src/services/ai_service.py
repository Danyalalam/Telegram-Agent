import logging
import time
import os
from datetime import datetime
from openai import AsyncOpenAI
from ..config import OPENAI_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        # Initialize the OpenAI client
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable not set")
            
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model_name = "gpt-4o"
        logger.info(f"Initialized OpenAI client with model: {self.model_name}")
        
        # Define generation parameters
        self.temperature = 0.7
        self.max_tokens = 2048  # Maximum output length for detailed responses
        
        # Track usage for monitoring
        self.total_tokens_used = 0
        self.api_calls_count = 0
        self.api_start_time = time.time()
        
        # Session storage
        self.chat_sessions = {}  # Store message history by user_id
        self.user_topics = {}    # Track the current topic for each user
        self.assessment_results = {}  # Store assessment results for follow-up questions
        self.user_languages = {}  # Track user language preferences

    async def generate_response(self, topic: str, query: str, user_id=None, language="en") -> str:
        """Generate a response using GPT-4o based on the topic and query."""
        
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
        
        try:
            # Get current session if applicable
            session = self.chat_sessions.get(user_id, []) if user_id else []
            
            # Create a system message based on topic and language
            system_prompt = self._create_system_prompt(topic, language)
            
            # Prepare messages for the API call
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (up to last 10 messages)
            if user_id and session:
                messages.extend(session[-10:])  # Only include the last 10 messages to avoid token limits
            
            # Add the user's query
            if is_followup:
                messages.append({"role": "user", "content": self._create_followup_prompt(query, context_info, language)})
            else:
                messages.append({"role": "user", "content": query})
            
            # Log the request for debugging
            logger.info(f"Sending request to OpenAI API for user {user_id if user_id else 'anonymous'} on topic {topic}")
            
            # Increment API call counter
            self.api_calls_count += 1
            
            # Make the API call
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Track token usage
            if hasattr(response, 'usage') and response.usage:
                self.total_tokens_used += response.usage.total_tokens
                logger.info(f"Request used {response.usage.total_tokens} tokens")
            
            # Extract the response text
            result = response.choices[0].message.content
            
            # Store the message history for this user if needed
            if user_id:
                # Check if we need to initialize the chat sessions for this user
                if user_id not in self.chat_sessions:
                    self.chat_sessions[user_id] = []
                
                # Store the exchange
                self.chat_sessions[user_id].append({"role": "user", "content": query})
                self.chat_sessions[user_id].append({"role": "assistant", "content": result})
                
                # Keep only the last 20 messages in history to manage token usage
                if len(self.chat_sessions[user_id]) > 20:
                    self.chat_sessions[user_id] = self.chat_sessions[user_id][-20:]
            
            return self._format_response(result)
            
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

    def _create_system_prompt(self, topic: str, language="en") -> str:
        """Create a system prompt based on the topic and language."""
        
        # Get current date and time information
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_year = datetime.now().year
        current_month = datetime.now().strftime("%B")
        current_day = datetime.now().day
        
        # Calculate Chinese zodiac sign for the current year
        zodiac_signs = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake", "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
        zodiac_signs_zh = ["鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪"]
        
        # Calculate the zodiac sign (using a simple formula - the Chinese New Year varies, but this is a good approximation)
        zodiac_index = (current_year - 4) % 12
        current_zodiac = zodiac_signs[zodiac_index]
        current_zodiac_zh = zodiac_signs_zh[zodiac_index]
        
        # Create date information based on language
        if language == "zh":
            date_info = (
                f"当前日期：{current_date}\n"
                f"现在是{current_year}年，{current_month}月，{current_day}日。\n"
                f"按照中国传统历法，当前是{current_zodiac_zh}年。\n"
                f"请在回答中考虑这些时间信息。"
            )
        else:
            date_info = (
                f"Current date: {current_date}\n"
                f"It is currently {current_month} {current_day}, {current_year}.\n"
                f"According to the Chinese calendar, it is the Year of the {current_zodiac}.\n"
                f"Please consider this temporal information in your responses."
            )
        
        # English system prompts
        en_prompts = {
            "feng_shui": (
                "You are a Feng Shui expert with decades of experience. Provide helpful, accurate advice about "
                "Feng Shui principles, home and office arrangement, energy flow, and related concepts. "
                "Use terminology appropriate for both beginners and advanced practitioners. "
                "Be practical, concise, and respectful of this ancient Chinese practice. "
                "Respond in English using clear, well-structured explanations."
            ),
            "mbti": (
                "You are an MBTI personality type expert with deep knowledge of cognitive functions, type dynamics, "
                "and practical applications of personality theory. Provide accurate, nuanced information about MBTI types, "
                "their characteristics, relationships, career fits, and growth paths. "
                "Avoid stereotyping and acknowledge individual variation within types. "
                "Respond in English with balanced, thoughtful explanations."
            ),
            "i_ching": (
                "You are an I-Ching divination master with profound understanding of the Book of Changes. "
                "Provide insightful interpretations of hexagrams, their changing lines, and applications to "
                "the questioner's situation. Honor the philosophical depth of this ancient oracle system. "
                "Be respectful, wise, and avoid overly deterministic predictions. "
                "Respond in English with clear explanations that balance traditional wisdom with practical guidance."
            ),
            "ba_zi": (
                "You are a BaZi (Four Pillars) expert skilled in Chinese destiny analysis. "
                "Provide thoughtful interpretations of birth charts, element interactions, luck cycles, "
                "and personal characteristics based on this traditional system. "
                "Balance deterministic aspects with wisdom about personal agency. "
                "Respond in English with clear, structured explanations and practical insights."
            ),
            "zi_wei": (
                "You are a Zi Wei Dou Shu (Purple Star Astrology) master with deep expertise in this complex "
                "Chinese astrological system. Provide insightful interpretations of charts, star positions, "
                "palace influences, and life predictions. Explain concepts clearly for those unfamiliar with the system. "
                "Balance destiny interpretations with practical guidance. "
                "Respond in English with well-organized explanations and thoughtful analysis."
            ),
            "general": (
                "You are an expert in Chinese metaphysical systems (Feng Shui, I-Ching, BaZi, Zi Wei Dou Shu) "
                "and personality psychology including MBTI. Provide helpful, accurate information while respecting "
                "these traditions' cultural and philosophical foundations. If asked about other topics, gently "
                "guide the conversation back to your areas of expertise. "
                "Respond in English with clear, concise, well-structured explanations."
            )
        }
        
        # Chinese system prompts
        zh_prompts = {
            "feng_shui": (
                "你是一位拥有数十年经验的风水专家。提供关于风水原理、家居和办公室布置、能量流动及相关概念的有帮助且准确的建议。"
                "使用适合初学者和高级实践者的术语。务实、简洁，并尊重这一古老的中国实践。"
                "用清晰、结构良好的中文解释回答问题。"
            ),
            "mbti": (
                "你是一位对认知功能、类型动态和人格理论实际应用有深入了解的MBTI人格类型专家。"
                "提供关于MBTI类型、其特征、关系、职业匹配和成长路径的准确、细致的信息。"
                "避免刻板印象，承认类型内个体差异。用平衡、深思熟虑的中文解释回答问题。"
            ),
            "i_ching": (
                "你是一位对《易经》有深刻理解的易经占卜大师。提供关于卦象、变爻及其对提问者情况的应用的有见地的解释。"
                "尊重这一古老预言系统的哲学深度。保持尊重、智慧，避免过于决定论的预测。"
                "用清晰的中文解释回答，平衡传统智慧与实用指导。"
            ),
            "ba_zi": (
                "你是一位精通中国命运分析的八字（四柱）专家。基于这一传统系统，提供关于生辰八字、五行相互作用、运气周期和个人特征的深思熟虑的解释。"
                "平衡决定论方面与关于个人能动性的智慧。用清晰、结构良好的中文解释和实用见解回答问题。"
            ),
            "zi_wei": (
                "你是一位对这一复杂的中国占星系统有深入专业知识的紫微斗数大师。提供关于命盘、星位、宫位影响和人生预测的有见地的解释。"
                "为不熟悉该系统的人清晰地解释概念。平衡命运解释与实用指导。"
                "用组织良好的中文解释和深思熟虑的分析回答问题。"
            ),
            "general": (
                "你是中国玄学系统（风水、易经、八字、紫微斗数）和包括MBTI在内的人格心理学专家。"
                "提供有帮助、准确的信息，同时尊重这些传统的文化和哲学基础。"
                "如果被问及其他主题，请温和地将对话引导回你的专业领域。"
                "用清晰、简洁、结构良好的中文解释回答问题。"
            )
        }
        
        # Select the appropriate prompt set based on language
        prompts = zh_prompts if language == 'zh' else en_prompts
        base_prompt = prompts.get(topic, prompts["general"])
        
        # Add date information to the prompt
        full_prompt = f"{base_prompt}\n\n{date_info}"
        
        return full_prompt

    def _get_seasonal_information(self, language="en"):
        """Get current seasonal information based on current date."""
        month = datetime.now().month
        northern_season = ""
        
        # Determine the season in the Northern Hemisphere
        if 3 <= month <= 5:
            northern_season = "Spring" if language == "en" else "春季"
        elif 6 <= month <= 8:
            northern_season = "Summer" if language == "en" else "夏季"
        elif 9 <= month <= 11:
            northern_season = "Autumn" if language == "en" else "秋季"
        else:
            northern_season = "Winter" if language == "en" else "冬季"
            
        # Format based on language
        if language == "zh":
            return f"在北半球，现在是{northern_season}。在南半球，季节相反。"
        else:
            return f"It is currently {northern_season} in the Northern Hemisphere. In the Southern Hemisphere, it's the opposite season."
    
    def _create_followup_prompt(self, query: str, context_info: str, language="en") -> str:
        """Create a prompt for follow-up questions with context."""
        if language == 'zh':
            return (
                f"{context_info} "
                f"基于这个上下文，提供一个详细的回答，直接解答用户的后续问题：{query}"
            )
        else:
            return (
                f"{context_info} "
                f"Based on this context, provide a detailed response that directly addresses "
                f"the user's follow-up question: {query}"
            )
    
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
            self.chat_sessions[user_id] = []
            logger.info(f"Reset chat session for user {user_id}")
            return True
        return False

    def get_usage_stats(self):
        """Get API usage statistics."""
        return {
            "total_tokens": self.total_tokens_used,
            "api_calls": self.api_calls_count,
            "uptime_seconds": int(time.time() - self.api_start_time)
        }