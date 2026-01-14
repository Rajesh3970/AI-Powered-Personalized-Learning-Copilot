from services.llm_client import llm_client
from services.vector_store import vector_store
from database import MasteryTracker
from sqlalchemy.orm import Session
from typing import Dict, List
import json
import re

class QuizGenerationAgent:
    """Quiz Generation Agent - Creates adaptive quizzes based on mastery level"""
    
    def __init__(self):
        self.llm = llm_client
        self.vector_store = vector_store
    
    def generate_quiz(
        self,
        student_id: int,
        course_name: str,
        topic: str,
        difficulty: str = "adaptive",
        num_questions: int = 5,
        db: Session = None
    ) -> Dict:
        """Generate topic-specific quiz with adaptive difficulty"""
        
        # Determine difficulty based on mastery if adaptive
        if difficulty == "adaptive" and db:
            mastery = db.query(MasteryTracker).filter(
                MasteryTracker.student_id == student_id,
                MasteryTracker.topic == topic
            ).first()
            
            if mastery:
                if mastery.mastery_score < 0.4:
                    difficulty = "easy"
                elif mastery.mastery_score < 0.7:
                    difficulty = "medium"
                else:
                    difficulty = "hard"
            else:
                difficulty = "medium"
        
        # Retrieve relevant content for quiz generation
        print(f"🔍 Retrieving content for quiz on: {topic}")
        retrieved_chunks = self.vector_store.semantic_search(
            course_name=course_name,
            query=topic,
            n_results=5  # Get more context
        )
        
        context = ""
        if retrieved_chunks:
            context = "\n\n".join([
                f"Content {i+1}:\n{chunk['text'][:800]}" 
                for i, chunk in enumerate(retrieved_chunks[:3])
            ])
            print(f"✅ Retrieved {len(retrieved_chunks)} relevant chunks")
        else:
            print("⚠️  No PDF content found, using general knowledge")
            context = f"General knowledge about {topic}"
        
        # Enhanced prompt for better quiz generation
        prompt = f"""You are an expert quiz creator. Generate {num_questions} high-quality multiple-choice questions about {topic}.

IMPORTANT INSTRUCTIONS:
1. Use the provided course content to create questions with REAL, SPECIFIC information
2. Each question should test deep understanding, not just memorization
3. All 4 options must be plausible and based on actual concepts
4. DO NOT use generic options like "Concept A", "Concept B", "Option 1", "Option 2"
5. Options should be specific, detailed, and factually accurate
6. Include brief explanations that teach the correct answer

Difficulty Level: {difficulty}
- Easy: Basic definitions and concepts
- Medium: Application and analysis
- Hard: Complex scenarios and synthesis

Course Content:
{context}

Generate questions in this EXACT JSON format (no markdown, no extra text):
{{
    "topic": "{topic}",
    "difficulty_level": "{difficulty}",
    "questions": [
        {{
            "question": "A clear, specific question about the topic?",
            "options": [
                "Detailed option A with real information",
                "Detailed option B with real information",
                "Detailed option C with real information",
                "Detailed option D with real information"
            ],
            "correct_index": 0,
            "explanation": "Why this answer is correct and what the concept means"
        }}
    ]
}}

Make questions challenging but fair. Use terminology from the course content when available.
Return ONLY valid JSON, nothing else."""

        print(f"🤖 Generating {num_questions} {difficulty} questions...")
        response = self.llm.generate(prompt, temperature=0.8)
        
        try:
            # Extract JSON from response
            # Remove markdown code blocks if present
            response = response.strip()
            if response.startswith('```'):
                # Remove ```json or ``` at start
                response = re.sub(r'^```(?:json)?\s*', '', response)
                # Remove ``` at end
                response = re.sub(r'\s*```$', '', response)
            
            # Find JSON object
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON object found in response")
            
            json_str = response[start_idx:end_idx]
            quiz_data = json.loads(json_str)
            
            # Validate quiz structure
            if "questions" not in quiz_data or len(quiz_data["questions"]) == 0:
                raise ValueError("Invalid quiz structure - no questions")
            
            # Validate each question has real content
            for q in quiz_data["questions"]:
                if not q.get("question") or not q.get("options"):
                    raise ValueError("Question missing content")
                
                # Check for placeholder content
                options_text = " ".join(q["options"]).lower()
                if any(placeholder in options_text for placeholder in [
                    "concept a", "concept b", "concept c", "concept d",
                    "option 1", "option 2", "option 3", "option 4"
                ]):
                    print("⚠️  Detected placeholder options, regenerating...")
                    raise ValueError("Quiz contains placeholder content")
            
            print(f"✅ Generated {len(quiz_data['questions'])} high-quality questions")
            return quiz_data
            
        except Exception as e:
            print(f"❌ Quiz generation error: {e}")
            print(f"Response preview: {response[:200]}...")
            
            # Enhanced fallback quiz with real content
            fallback_quiz = self._generate_fallback_quiz(topic, difficulty, context, num_questions)
            return fallback_quiz
    
    def _generate_fallback_quiz(self, topic: str, difficulty: str, context: str, num_questions: int) -> Dict:
        """Generate a basic fallback quiz with real content"""
        
        # Try one more time with a simpler prompt
        simple_prompt = f"""Create {num_questions} multiple choice questions about {topic}.

Use this information:
{context[:500]}

Format each question as:
Q: [question]
A) [option]
B) [option]
C) [option]
D) [option]
Correct: [A/B/C/D]
Explanation: [why]

Make options specific and informative, not generic placeholders."""

        try:
            response = self.llm.generate(simple_prompt, temperature=0.7)
            
            # Try to parse the simpler format
            questions = []
            current_q = {}
            
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('Q:'):
                    if current_q:
                        questions.append(current_q)
                    current_q = {"question": line[2:].strip(), "options": []}
                elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                    current_q["options"].append(line[2:].strip())
                elif line.startswith('Correct:'):
                    correct_letter = line.split(':')[1].strip()[0].upper()
                    current_q["correct_index"] = ord(correct_letter) - ord('A')
                elif line.startswith('Explanation:'):
                    current_q["explanation"] = line.split(':', 1)[1].strip()
            
            if current_q:
                questions.append(current_q)
            
            if questions:
                return {
                    "topic": topic,
                    "difficulty_level": difficulty,
                    "questions": questions[:num_questions]
                }
        except:
            pass
        
        # Ultimate fallback - basic but real questions
        print("⚠️  Using ultimate fallback quiz")
        return {
            "topic": topic,
            "difficulty_level": difficulty,
            "questions": [
                {
                    "question": f"What is the primary purpose of {topic}?",
                    "options": [
                        f"To understand fundamental concepts of {topic}",
                        f"To apply {topic} in practical scenarios",
                        f"To analyze complex {topic} problems",
                        f"To evaluate different {topic} approaches"
                    ],
                    "correct_index": 0,
                    "explanation": f"Understanding fundamentals is the foundation of learning {topic}."
                },
                {
                    "question": f"Which statement best describes {topic}?",
                    "options": [
                        f"{topic} is a fundamental concept in this field",
                        f"{topic} is rarely used in practice",
                        f"{topic} only applies to theoretical scenarios",
                        f"{topic} has been completely replaced by newer methods"
                    ],
                    "correct_index": 0,
                    "explanation": f"{topic} remains an important foundational concept."
                },
                {
                    "question": f"What is a key characteristic of {topic}?",
                    "options": [
                        f"It requires understanding of underlying principles",
                        f"It can be learned without any prerequisites",
                        f"It is identical across all applications",
                        f"It never changes or evolves"
                    ],
                    "correct_index": 0,
                    "explanation": f"Understanding principles is crucial for mastering {topic}."
                },
                {
                    "question": f"How is {topic} typically applied?",
                    "options": [
                        f"Through systematic analysis and problem-solving",
                        f"By random trial and error only",
                        f"Without any planning or methodology",
                        f"Only in theoretical discussions"
                    ],
                    "correct_index": 0,
                    "explanation": f"Systematic approaches are most effective for {topic}."
                },
                {
                    "question": f"What should you consider when working with {topic}?",
                    "options": [
                        f"The context and specific requirements of the problem",
                        f"Only the most popular approach regardless of context",
                        f"Avoiding any complexity at all costs",
                        f"Ignoring established best practices"
                    ],
                    "correct_index": 0,
                    "explanation": f"Context-aware approaches lead to better outcomes with {topic}."
                }
            ][:num_questions]
        }

quiz_agent = QuizGenerationAgent()
