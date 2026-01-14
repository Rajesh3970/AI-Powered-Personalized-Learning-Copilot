from services.llm_client import llm_client
from sqlalchemy.orm import Session
from database import StudyPlan
from typing import List, Dict
import json

class PlanningAgent:
    """Planning Agent - Breaks syllabus into weekly learning units (per documentation)"""
    
    def __init__(self):
        self.llm = llm_client
    
    def generate_study_plan(
        self,
        student_id: int,
        course_name: str,
        study_hours_per_week: int,
        syllabus_content: str = None,
        exam_timeline: str = None,
        db: Session = None
    ) -> Dict:
        """Generate personalized 4-week study plan"""
        
        template = """You are an expert educational planner. Create a detailed 4-week study plan.

Course: {course_name}
Available Study Hours per Week: {hours}
{syllabus_section}
{exam_section}

Create a JSON response with this structure:
{{
    "weeks": [
        {{
            "week_number": 1,
            "topics": "Comma-separated list of topics",
            "allocated_hours": <hours for this week>
        }}
    ]
}}

Make the plan:
1. Realistic given the time constraint
2. Progressive (building concepts week by week)
3. Aligned with exam timeline if provided
4. Covering all major syllabus topics

Return ONLY valid JSON."""

        variables = {
            "course_name": course_name,
            "hours": study_hours_per_week,
            "syllabus_section": f"\nSyllabus:\n{syllabus_content}" if syllabus_content else "",
            "exam_section": f"\nExam Timeline:\n{exam_timeline}" if exam_timeline else ""
        }
        
        response = self.llm.generate_with_template(template, variables)
        
        try:
            # Parse JSON response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            json_str = response[start_idx:end_idx]
            plan_data = json.loads(json_str)
            
            # Save to database if db session provided
            if db:
                for week in plan_data['weeks']:
                    study_plan = StudyPlan(
                        student_id=student_id,
                        course_name=course_name,
                        week_number=week['week_number'],
                        topics=week['topics'],
                        allocated_hours=week['allocated_hours']
                    )
                    db.add(study_plan)
                db.commit()
                print(f"✅ Study plan saved to database")
            
            return plan_data
            
        except Exception as e:
            print(f"❌ Plan generation error: {e}")
            # Return fallback plan
            return self._fallback_plan(course_name, study_hours_per_week)
    
    def _fallback_plan(self, course_name: str, hours: int) -> Dict:
        """Fallback plan if LLM fails"""
        return {
            "weeks": [
                {
                    "week_number": 1,
                    "topics": f"Introduction to {course_name}, foundational concepts",
                    "allocated_hours": hours
                },
                {
                    "week_number": 2,
                    "topics": "Core concepts and principles",
                    "allocated_hours": hours
                },
                {
                    "week_number": 3,
                    "topics": "Advanced topics and applications",
                    "allocated_hours": hours
                },
                {
                    "week_number": 4,
                    "topics": "Review, practice problems, exam preparation",
                    "allocated_hours": hours
                }
            ]
        }

planning_agent = PlanningAgent()