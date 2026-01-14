# AI-Powered-Personalized-Learning-Copilot
The Personalized Learning Copilot for Core Courses is an AI-driven assistant that helps students plan and track study progress in core engineering subjects. It generates weekly study plans, answers questions using RAG with citations, creates adaptive quizzes, and updates learning paths based on mastery.

#Make sure you have:
-Python 3.11+
-PostgreSQL 15+ (running)
-Git
--------------------------------------------------------------------------------------------------------------------------------------------
#1. Clone & Set Up Project
```bash
mkdir learning-copilot
git clone AI-Powered-Personalized-Learning-Copilot
```
#2. Install Backend Dependencies
```py
python3 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
#3. Create Database
```psql
createdb learning_copilot
```
#4. Configure Environment
Create .env:
- Get API key from makersuite Google Gemini
- Create the Secret Key for jwt using openssl
- Provide the correct username and password for psql
```bash
GEMINI_API_KEY=your_api_key
DATABASE_URL=postgresql://postgres:password@localhost:5432/learning_copilot
SECRET_KEY=your_secret_key
UPLOAD_DIR=./data/uploads
CHROMA_DIR=./data/chroma_db
```
#5. Run the App
Backend:
```py
python main.py
```
API available at: http://localhost:8000
Frontend:
```py
python3 -m http.server 3000
```
Open: http://localhost:3000
```bash
start index.html
```
