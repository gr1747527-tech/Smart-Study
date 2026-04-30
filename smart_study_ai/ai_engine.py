import random
import json
import re
from datetime import datetime

class SmartAIEngine:
    def __init__(self):
        self.load_knowledge_base()
        self.user_sessions = {}
        
    def load_knowledge_base(self):
        """Load domain-specific knowledge"""
        with open('data/knowledge_base.json', 'r', encoding='utf-8') as f:
            self.knowledge = json.load(f)
    
    def generate_response(self, message, domain='general', language='english', user_context=''):
        """Main response generation pipeline"""
        
        # Detect intention
        intention = self.detect_intention(message)
        
        # Route to appropriate handler
        if intention == 'greeting':
            return self.handle_greeting(language)
        elif intention == 'coding':
            return self.handle_coding_request(message, language)
        elif intention == 'concept':
            return self.handle_concept_request(message, domain, language)
        elif intention == 'poetry':
            return self.generate_poetry(message, language)
        elif intention == 'math':
            return self.solve_math(message, language)
        else:
            return self.general_response(message, domain, language)
    
    def detect_intention(self, message):
        """Detect user's intention from message"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'namaste', 'नमस्ते']):
            return 'greeting'
        elif any(word in message_lower for word in ['code', 'program', 'debug', 'function', 'algorithm']):
            return 'coding'
        elif any(word in message_lower for word in ['explain', 'what is', 'concept', 'define']):
            return 'concept'
        elif any(word in message_lower for word in ['poem', 'poetry', 'kavita', 'कविता', 'story']):
            return 'poetry'
        elif any(char.isdigit() for char in message) and any(op in message_lower for op in ['+', '-', '*', '/', 'solve', 'calculate']):
            return 'math'
        else:
            return 'general'
    
    def handle_greeting(self, language):
        """Handle greeting messages"""
        greetings = {
            'english': [
                "Hey! How can I help you with your studies today? 📚",
                "Hello! Ready to dive into some learning? 🚀",
                "Hi there! What would you like to explore today?"
            ],
            'hindi': [
                "नमस्ते! आज किस विषय में मदद चाहिए? 🙏",
                "हैलो! सीखने के लिए तैयार हैं? चलिए शुरू करते हैं! ✨",
                "नमस्कार! आज हम क्या सीखेंगे?"
            ]
        }
        return random.choice(greetings.get(language, greetings['english']))
    
    def handle_coding_request(self, message, language):
        """Handle programming related queries"""
        # Detect programming language
        languages = ['python', 'java', 'c++', 'javascript', 'dart', 'flutter']
        detected_lang = 'python'  # default
        
        for lang in languages:
            if lang in message.lower():
                detected_lang = lang
                break
        
        # Generate sample code based on request
        if 'sort' in message.lower():
            code = self.generate_sorting_code(detected_lang)
            explanation = self.get_code_explanation('sorting', language)
        elif 'api' in message.lower():
            code = self.generate_api_example(detected_lang)
            explanation = self.get_code_explanation('api', language)
        else:
            code = self.generate_hello_world(detected_lang)
            explanation = self.get_code_explanation('basic', language)
        
        response = f"**{explanation}**\n\n```{detected_lang}\n{code}\n```\n\n💡 **Tip:** You can optimize this further by..."
        return response
    
    def generate_sorting_code(self, language):
        """Generate sorting algorithm code"""
        if language == 'python':
            return '''def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quick_sort(left) + middle + quick_sort(right)

# Example usage
numbers = [64, 34, 25, 12, 22, 11, 90]
sorted_numbers = quick_sort(numbers)
print(f"Sorted array: {sorted_numbers}")'''
        # Add more languages...
    
    def handle_concept_request(self, message, domain, language):
        """Handle conceptual explanation requests"""
        # Extract key terms
        words = message.lower().split()
        
        for topic in self.knowledge.get(domain, {}):
            if topic.lower() in words:
                concept_data = self.knowledge[domain][topic]
                return self.format_concept(concept_data, language)
        
        return "Let me explain this concept step by step... [Detailed explanation]"
    
    def generate_poetry(self, message, language):
        """Generate poetry/stories"""
        if language == 'hindi':
            poems = [
                "सीखने की राह पर चलते हैं हम,\nज्ञान के दीप जलाते हैं हम।\nहर सवाल का जवाब ढूंढते,\nSmart Study AI बन जाते हैं हम।",
                # Add more poems
            ]
            return random.choice(poems)
        else:
            poems = [
                "In the realm of code and light,\nWhere knowledge takes its flight,\nSmart Study AI guides the way,\nMaking learning bright as day.",
                # Add more poems
            ]
            return random.choice(poems)
    
    def solve_math(self, message, language):
        """Solve mathematical problems"""
        try:
            # Extract mathematical expression
            expression = re.findall(r'[\d\+\-\*\/\(\)\.]+', message)
            if expression:
                result = eval(expression[0])
                return f"**Solution:** {expression[0]} = {result}\n\n**Step-by-step:**\n1. ..."
        except:
            pass
        return "Please provide a clear mathematical expression to solve."
    
    def format_concept(self, concept_data, language):
        """Format concept explanation"""
        if language == 'hindi':
            return f"""
**{concept_data['title_hi']}**

📖 **परिभाषा:** {concept_data['definition_hi']}

🔍 **विस्तृत व्याख्या:**
{concept_data['explanation_hi']}

💡 **उदाहरण:**
{concept_data['example_hi']}

🎯 **महत्वपूर्ण बिंदु:**
{concept_data['key_points_hi']}
"""
        else:
            return f"""
**{concept_data['title']}**

📖 **Definition:** {concept_data['definition']}

🔍 **Detailed Explanation:**
{concept_data['explanation']}

💡 **Example:**
{concept_data['example']}

🎯 **Key Points:**
{concept_data['key_points']}
"""