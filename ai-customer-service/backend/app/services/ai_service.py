import openai
import time
from typing import List, Dict
from app.core.config import settings

class AIService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
        self.max_tokens = settings.MAX_TOKENS
        self.temperature = settings.TEMPERATURE
        
        # System prompts for different contexts
        self.system_prompts = {
            "customer_service": """You are a helpful AI customer service assistant. 
            You should be polite, professional, and helpful. 
            If you don't know something, admit it and offer to escalate to a human agent.
            Always maintain a friendly and supportive tone.""",
            
            "troubleshooting": """You are a technical support specialist. 
            Help users troubleshoot issues step by step. 
            Ask clarifying questions when needed and provide clear, actionable solutions.
            If the issue is complex, recommend escalation to technical support.""",
            
            "faq": """You are answering frequently asked questions. 
            Provide clear, concise answers based on the knowledge base.
            If the question isn't in your knowledge base, suggest contacting support."""
        }
    
    async def generate_response(
        self, 
        message: str, 
        conversation_history: List[Dict] = None,
        context_type: str = "customer_service",
        additional_context: str = None
    ) -> Dict:
        """Generate AI response with timing and token tracking."""
        
        start_time = time.time()
        
        # Build messages for the API
        messages = [{"role": "system", "content": self.system_prompts.get(context_type)}]
        
        # Add additional context if provided
        if additional_context:
            messages.append({
                "role": "system", 
                "content": f"Additional context: {additional_context}"
            })
        
        # Add conversation history
        if conversation_history:
            messages.extend(conversation_history[-10:])  # Keep last 10 messages for context
        
        # Add current user message
        messages.append({"role": "user", "content": message})
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            end_time = time.time()
            response_time = int((end_time - start_time) * 1000)  # Convert to milliseconds
            
            return {
                "response": response.choices[0].message.content,
                "tokens_used": response.usage.total_tokens,
                "response_time": response_time,
                "success": True
            }
            
        except Exception as e:
            end_time = time.time()
            response_time = int((end_time - start_time) * 1000)
            
            return {
                "response": "I'm sorry, I'm experiencing technical difficulties. Please try again later or contact support.",
                "tokens_used": 0,
                "response_time": response_time,
                "success": False,
                "error": str(e)
            }
    
    async def analyze_customer_intent(self, message: str) -> Dict:
        """Analyze customer message to determine intent and urgency."""
        
        analysis_prompt = f"""
        Analyze the following customer message and provide:
        1. Intent (question, complaint, request, technical_issue, billing, etc.)
        2. Urgency level (low, medium, high, urgent)
        3. Category (technical, billing, general, product_info, etc.)
        4. Sentiment (positive, neutral, negative, frustrated)
        
        Customer message: "{message}"
        
        Respond in JSON format:
        {{
            "intent": "...",
            "urgency": "...",
            "category": "...",
            "sentiment": "..."
        }}
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": analysis_prompt}],
                max_tokens=200,
                temperature=0.3
            )
            
            import json
            analysis = json.loads(response.choices[0].message.content)
            return analysis
            
        except Exception:
            return {
                "intent": "general",
                "urgency": "medium", 
                "category": "general",
                "sentiment": "neutral"
            }
    
    def search_knowledge_base(self, query: str, knowledge_base: List[Dict]) -> List[Dict]:
        """Simple keyword-based search through knowledge base."""
        
        query_words = query.lower().split()
        results = []
        
        for item in knowledge_base:
            content = f"{item.get('title', '')} {item.get('content', '')}".lower()
            score = sum(1 for word in query_words if word in content)
            
            if score > 0:
                results.append({
                    **item,
                    "relevance_score": score
                })
        
        # Sort by relevance score
        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        return results[:5]  # Return top 5 results

# Global AI service instance
ai_service = AIService()
