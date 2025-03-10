from openai import AsyncOpenAI
import logging
import time
from ..config import OPENAI_API_KEY

# Configure logging
logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        # Initialize the OpenAI client
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        self.model_name = "gpt-4o"
        
        # Define generation config
        self.temperature = 0.7
        self.max_tokens = 2048
        
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
            # If user_id is provided, maintain message history
            if user_id:
                # Check if topic or language has changed for this user
                if (user_id in self.user_topics and 
                    (self.user_topics[user_id] != topic or 
                     self.user_languages.get(user_id) != language) and 
                    not is_followup):
                    # Topic or language changed, reset message history
                    self.chat_sessions[user_id] = []
                
                # Update current topic and language
                self.user_topics[user_id] = topic
                self.user_languages[user_id] = language
                
                # Create new session if needed
                if user_id not in self.chat_sessions:
                    self.chat_sessions[user_id] = []
                
                # Get current session
                session = self.chat_sessions[user_id]
            else:
                # One-off generation with no history
                session = []
            
            # Create the system prompt based on topic and language
            system_prompt = self._create_system_prompt(topic, language)
            
            # Prepare messages for the API call
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (up to last 10 messages)
            if user_id and session:
                messages.extend(session[-10:])
            
            # Add the user's query or follow-up context
            if is_followup:
                messages.append({"role": "user", "content": self._create_followup_prompt(topic, query, context_info, language)})
            else:
                messages.append({"role": "user", "content": query})
            
            # Log the API call for monitoring
            self.api_calls_count += 1
            
            # Make the API call
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            # Track token usage
            self.total_tokens_used += response.usage.total_tokens
            
            # Extract the response text
            result = response.choices[0].message.content
            
            # Store the message history for this user if needed
            if user_id:
                # Only store the last message from user and assistant to save memory
                # (full context is sent in each request anyway)
                self.chat_sessions[user_id].append({"role": "user", "content": query})
                self.chat_sessions[user_id].append({"role": "assistant", "content": result})
                
                # Keep only the last 20 messages in history to manage memory
                if len(self.chat_sessions[user_id]) > 20:
                    self.chat_sessions[user_id] = self.chat_sessions[user_id][-20:]
            
            return self._format_response(result)
            
        except Exception as e:
            logger.error(f"Error generating response with GPT-4o: {e}")
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
                "You are an MBTI personality type expert with extensive knowledge of the 16 personality types, "
                "cognitive functions, and type dynamics. Provide accurate, nuanced information about MBTI, "
                "avoiding stereotypes and oversimplifications. Acknowledge both strengths and limitations of the system. "
                "Respond in English using clear, well-structured explanations."
            ),
            "iching": (
                "You are an I-Ching oracle expert with deep knowledge of the 64 hexagrams, their meanings, "
                "and traditional and modern interpretations. Provide thoughtful analysis that respects "
                "the wisdom and nuance of this ancient divination system. Be insightful but avoid making "
                "absolute predictions about the future. Respond in English using clear, well-structured explanations."
            ),
            "bazi": (
                "You are a Ba Zi (Four Pillars) expert with deep knowledge of Chinese birth charts, "
                "the interactions between the Ten Heavenly Stems and Twelve Earthly Branches, and "
                "Five Elements theory. Provide accurate interpretations that honor the complexity and "
                "cultural context of this ancient system. Respond in English using clear, well-structured explanations."
            ),
            "ziwei": (
                "You are a Zi Wei Dou Shu (Purple Star Astrology) expert with comprehensive knowledge of "
                "star positions, palace influences, and chart interpretation. Provide accurate analysis that "
                "respects this sophisticated Chinese astrological system. Balance technical details with "
                "practical insights. Respond in English using clear, well-structured explanations."
            ),
            "general": (
                "You are an expert in Chinese metaphysical systems (Feng Shui, I-Ching, Ba Zi, Zi Wei Dou Shu) "
                "and MBTI personality types. Respond to questions accurately and helpfully, showing respect for "
                "these traditions. If asked about topics outside these domains, politely explain that you "
                "specialize in these areas. Respond in English using clear, well-structured explanations."
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
                "你是一位MBTI人格类型专家，对16种人格类型、认知功能和类型动力学有深入了解。提供准确、细致的MBTI信息，"
                "避免刻板印象和过度简化。承认该系统的优势和局限性。"
                "用清晰、结构良好的中文解释回答问题。"
            ),
            "iching": (
                "你是一位易经专家，对64卦、卦义以及传统和现代解释有深入了解。提供尊重这一古老占卜系统智慧和细微差别的深思熟虑的分析。"
                "有见地但避免对未来作出绝对预测。"
                "用清晰、结构良好的中文解释回答问题。"
            ),
            "bazi": (
                "你是一位八字（四柱）专家，对中国生辰八字、十天干与十二地支的相互作用以及五行理论有深入了解。"
                "提供准确的解释，尊重这一古老系统的复杂性和文化背景。"
                "用清晰、结构良好的中文解释回答问题。"
            ),
            "ziwei": (
                "你是一位紫微斗数（紫星占星）专家，对星位、宫位影响和命盘解读有全面的了解。提供尊重这一复杂中国占星系统的准确分析。"
                "平衡技术细节与实用见解。"
                "用清晰、结构良好的中文解释回答问题。"
            ),
            "general": (
                "你是中国玄学系统（风水、易经、八字、紫微斗数）和MBTI人格类型的专家。准确且有帮助地回答问题，"
                "尊重这些传统。如果被问及这些领域之外的话题，请礼貌地解释你专注于这些领域。"
                "用清晰、结构良好的中文解释回答问题。"
            )
        }
        
        # Select the appropriate prompt set based on language
        prompts = zh_prompts if language == 'zh' else en_prompts
        
        return prompts.get(topic, prompts["general"])
    
    def _create_followup_prompt(self, topic: str, query: str, context_info: str, language="en") -> str:
        """Create a prompt for follow-up questions with context."""
        if language == 'zh':
            base = (
                f"{context_info} "
                f"基于这个上下文，提供一个详细的回答，直接解答用户的后续问题：{query}"
            )
        else:
            base = (
                f"{context_info} "
                f"Based on this context, provide a detailed response that directly addresses "
                f"the user's follow-up question: {query}"
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
            self.chat_sessions[user_id] = []
            return True
        return False
    
    def get_usage_stats(self):
        """Get usage statistics for monitoring."""
        elapsed_time = time.time() - self.api_start_time
        hours_elapsed = elapsed_time / 3600
        
        # Calculate running cost estimate (adjust pricing as needed)
        cost_estimate = (self.total_tokens_used / 1000) * 0.01  # $0.01 per 1K tokens
        
        stats = {
            "total_tokens": self.total_tokens_used,
            "api_calls": self.api_calls_count,
            "uptime_hours": round(hours_elapsed, 2),
            "tokens_per_hour": round(self.total_tokens_used / max(1, hours_elapsed)),
            "calls_per_hour": round(self.api_calls_count / max(1, hours_elapsed)),
            "estimated_cost": f"${cost_estimate:.4f}"
        }
        
        return stats