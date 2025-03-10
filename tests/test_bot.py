import os
import asyncio
import json
from openai import AsyncOpenAI
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GPT4o-Test")

# Load the OpenAI API key from environment variables or set it directly
# For testing, we'll set it directly, but in production use environment variables
API_KEY = "your_openai_api_key"  # Replace with your actual API key

class GPT4oTester:
    def __init__(self, api_key=None):
        self.api_key = api_key or API_KEY
        
        # Initialize the OpenAI client
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # Track token usage for cost estimation
        self.total_tokens_used = 0
        self.total_api_calls = 0
        self.start_time = time.time()
    
    async def test_basic_query(self, query="Hello, tell me a short joke"):
        """Test a basic query to ensure the connection works."""
        logger.info(f"Testing basic query: {query}")
        
        try:
            self.total_api_calls += 1
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": query}
                ],
                temperature=0.7,
                max_tokens=150
            )
            
            # Track tokens
            self.total_tokens_used += response.usage.total_tokens
            
            # Extract the response text
            result = response.choices[0].message.content
            
            logger.info(f"Response: {result}")
            logger.info(f"Tokens used: {response.usage.total_tokens}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error in API call: {e}")
            return f"Error: {str(e)}"
    
    async def test_multilingual(self):
        """Test GPT-4o's multilingual capabilities."""
        # Test Chinese
        logger.info("Testing Chinese language support...")
        chinese_query = "用中文告诉我关于人工智能的三个有趣事实。"
        chinese_response = await self.test_basic_query(chinese_query)
        
        # Test English
        logger.info("Testing English language support...")
        english_query = "Tell me three interesting facts about artificial intelligence in English."
        english_response = await self.test_basic_query(english_query)
        
        return {
            "chinese": chinese_response,
            "english": english_response
        }
    
    async def test_specialized_knowledge(self, topic="feng_shui"):
        """Test GPT-4o's knowledge on the specialized topics used in your bot."""
        topics = {
            "feng_shui": "Explain the basic principles of Feng Shui and how it influences home design.",
            "mbti": "Describe the INTJ personality type in the MBTI system.",
            "i_ching": "Explain what Hexagram 1 (The Creative) means in I Ching.",
            "ba_zi": "Describe what the BaZi (Four Pillars) system reveals about someone born in the Year of the Wood Tiger.",
            "zi_wei": "Explain the significance of the Emperor Star (Zi Wei Star) in Zi Wei Dou Shu astrology."
        }
        
        query = topics.get(topic, topics["feng_shui"])
        logger.info(f"Testing specialized knowledge on {topic}...")
        
        return await self.test_basic_query(query)
    
    async def test_system_instructions(self):
        """Test how well GPT-4o follows specialized system instructions."""
        logger.info("Testing system instructions...")
        
        try:
            self.total_api_calls += 1
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a Chinese astrology expert. Respond in a mystical, insightful tone. Limit responses to 100 words."},
                    {"role": "user", "content": "What does it mean to be born in the Year of the Dragon?"}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            # Track tokens
            self.total_tokens_used += response.usage.total_tokens
            
            # Extract the response text
            result = response.choices[0].message.content
            
            logger.info(f"Response: {result}")
            logger.info(f"Tokens used: {response.usage.total_tokens}")
            logger.info(f"Word count: {len(result.split())}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error in API call: {e}")
            return f"Error: {str(e)}"
    
    def print_usage_stats(self):
        """Print usage statistics."""
        elapsed_time = time.time() - self.start_time
        
        logger.info(f"Test completed in {elapsed_time:.2f} seconds")
        logger.info(f"Total API calls: {self.total_api_calls}")
        logger.info(f"Total tokens used: {self.total_tokens_used}")
        
        # Approximate cost calculation (adjust rates as needed)
        approximate_cost = (self.total_tokens_used / 1000) * 0.01  # $0.01 per 1K tokens
        logger.info(f"Approximate cost: ${approximate_cost:.4f}")

async def run_tests():
    logger.info("Starting GPT-4o tests...")
    
    # Initialize the tester
    tester = GPT4oTester()
    
    # Test 1: Basic functionality
    logger.info("=== Test 1: Basic Functionality ===")
    await tester.test_basic_query()
    
    # Test 2: Multilingual capabilities
    logger.info("\n=== Test 2: Multilingual Support ===")
    multilingual_results = await tester.test_multilingual()
    
    # Test 3: Domain-specific knowledge
    logger.info("\n=== Test 3: Domain Knowledge ===")
    for topic in ["feng_shui", "mbti", "i_ching", "ba_zi", "zi_wei"]:
        logger.info(f"\nTesting {topic}...")
        await tester.test_specialized_knowledge(topic)
    
    # Test 4: System instructions
    logger.info("\n=== Test 4: System Instructions ===")
    await tester.test_system_instructions()
    
    # Print final usage statistics
    logger.info("\n=== Usage Statistics ===")
    tester.print_usage_stats()
    
    logger.info("All tests completed successfully.")

if __name__ == "__main__":
    # Replace with your actual OpenAI API key before running
    os.environ["OPENAI_API_KEY"] = API_KEY  # As a fallback - better to set in environment
    
    # Run the tests
    asyncio.run(run_tests())