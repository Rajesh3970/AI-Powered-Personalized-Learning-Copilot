from services.llm_client import llm_client
from database import MasteryTracker, StudyPlan, QuizHistory
from sqlalchemy.orm import Session
from typing import Dict, List
import json

class ReflectionAgent:
    """Reflection Agent - Evaluates performance and updates mastery scores"""
    
    def __init__(self):
        self.llm = llm_client
    
    def update_mastery(
        self,
        student_id: int,
        topic: str,
        score: float,
        total_questions: int,
        correct_answers: int,
        db: Session
    ):
        """Update mastery score after quiz attempt"""
        
        # Get existing mastery or create new
        mastery = db.query(MasteryTracker).filter(
            MasteryTracker.student_id == student_id,
            MasteryTracker.topic == topic
        ).first()
        
        if mastery:
            # Update using weighted average (recent performance weighted more)
            new_score = (mastery.mastery_score * 0.7) + (score * 0.3)
            mastery.mastery_score = new_score
            mastery.attempts += 1
        else:
            # Create new mastery entry
            mastery = MasteryTracker(
                student_id=student_id,
                topic=topic,
                mastery_score=score,
                attempts=1
            )
            db.add(mastery)
        
        db.commit()
        print(f"✅ Updated mastery for {topic}: {mastery.mastery_score:.2f}")
        
        return mastery.mastery_score
    
    def suggest_plan_modifications(
        self,
        student_id: int,
        course_name: str,
        db: Session
    ) -> Dict:
        """Analyze mastery and suggest study plan adjustments"""
        
        # Get all mastery scores for student
        mastery_records = db.query(MasteryTracker).filter(
            MasteryTracker.student_id == student_id
        ).all()
        
        if not mastery_records:
            return {"recommendation": "Complete more quizzes to get personalized recommendations"}
        
        # Identify weak and strong topics
        weak_topics = [m.topic for m in mastery_records if m.mastery_score < 0.5]
        strong_topics = [m.topic for m in mastery_records if m.mastery_score >= 0.8]
        
        template = """Analyze student performance and suggest study plan modifications.

Weak Topics (mastery < 50%): {weak_topics}
Strong Topics (mastery >= 80%): {strong_topics}

Overall Mastery Scores:
{mastery_details}

Provide recommendations in JSON format:
{{
    "recommendation": "Overall assessment and advice",
    "focus_areas": ["Topic 1", "Topic 2"],
    "reduce_time_on": ["Topic A"],
    "suggested_actions": ["Action 1", "Action 2"]
}}"""

        mastery_details = "\n".join([
            f"- {m.topic}: {m.mastery_score:.1%} ({m.attempts} attempts)"
            for m in mastery_records
        ])
        
        variables = {
            "weak_topics": ", ".join(weak_topics) if weak_topics else "None",
            "strong_topics": ", ".join(strong_topics) if strong_topics else "None",
            "mastery_details": mastery_details
        }
        
        response = self.llm.generate_with_template(template, variables)
        
        try:
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            suggestions = json.loads(response[start_idx:end_idx])
            return suggestions
        except:
            return {}
reflection_agent = ReflectionAgent()
