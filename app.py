import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-super-secret-key-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ✅ Groq Client (Free!)
client = Groq(api_key=os.getenv('GROQ_API_KEY'))


# ====================== MODELS ======================

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    ideas = db.relationship('IdeaHistory', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class IdeaHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    idea = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(50), nullable=False)
    result = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


with app.app_context():
    db.create_all()


# ====================== AI HELPER (Groq) ======================

def get_ai_response(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",   # Free Llama 3 model on Groq
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an experienced startup advisor, venture capitalist, and business strategist "
                        "with 20+ years of experience evaluating startups. You give sharp, structured, and "
                        "actionable advice. Always respond in clean structured format using the exact sections requested."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=1024,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "invalid_api_key" in error_msg.lower():
            return "AI Error: Invalid Groq API key. Please check your GROQ_API_KEY in .env file."
        elif "429" in error_msg or "rate_limit" in error_msg.lower():
            return "AI Error: Rate limit reached. Please wait a moment and try again."
        elif "model" in error_msg.lower():
            return "AI Error: Model not available. Please check Groq model name."
        else:
            return f"AI Error: {error_msg}"


# ====================== PROMPTS ======================

def validate_idea_prompt(idea: str) -> str:
    return f"""
Analyze the following startup idea and provide a structured evaluation.

Startup Idea: "{idea}"

Respond EXACTLY in this format (use these exact headings):

PROBLEM IT SOLVES:
[Describe clearly what real problem this idea addresses]

TARGET AUDIENCE:
[Who are the primary users/customers? Be specific about demographics and segments]

MARKET DEMAND:
[Rate as High / Medium / Low and explain why in 2-3 sentences]

RISKS:
[List 3-5 key risks this startup faces]

SUGGESTIONS:
[Give 3-5 actionable suggestions to improve or strengthen this idea]
"""


def market_research_prompt(idea: str) -> str:
    return f"""
Perform a quick but thorough market analysis for the following startup idea.

Startup Idea: "{idea}"

Respond EXACTLY in this format (use these exact headings):

COMPETITORS:
[List 3-5 real or likely competitors with their names]

WHAT THEY DO:
[For each competitor, briefly describe what they offer and their strength]

MARKET GAP:
[Identify the gap or underserved need that this startup idea can fill]

OPPORTUNITIES:
[List 3-5 specific opportunities this startup can capitalize on]
"""


def generate_pitch_prompt(idea: str) -> str:
    return f"""
Create a compelling investor pitch for the following idea.

Startup Idea: "{idea}"

Respond EXACTLY in this format (use these exact headings):

PROBLEM:
[Describe the core problem in a compelling, relatable way]

SOLUTION:
[How does this startup solve the problem? Be clear and exciting]

BUSINESS MODEL:
[How does this startup make money? Describe revenue streams]

TARGET MARKET:
[Define the total addressable market and the initial target segment]

WHY IT WILL SUCCEED:
[Give 3-5 strong reasons why this startup has a competitive advantage and will win]
"""


# ====================== SAVE TO HISTORY ======================

def save_to_history(idea: str, module: str, result: str):
    try:
        entry = IdeaHistory(
            user_id=current_user.id,
            idea=idea,
            module=module,
            result=result
        )
        db.session.add(entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"History save error: {e}")


# ====================== AUTH ROUTES ======================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not email or not password:
            flash('All fields are required!', 'danger')
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('signup'))

        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('index'))

        flash('Invalid username or password!', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ====================== MAIN ROUTES ======================

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=current_user.username)


@app.route('/history')
@login_required
def history():
    entries = IdeaHistory.query.filter_by(user_id=current_user.id)\
        .order_by(IdeaHistory.created_at.desc()).all()
    return jsonify([
        {
            "id": e.id,
            "idea": e.idea,
            "module": e.module,
            "result": e.result,
            "created_at": e.created_at.strftime("%b %d, %Y %I:%M %p")
        }
        for e in entries
    ])


@app.route('/history/delete/<int:entry_id>', methods=['DELETE'])
@login_required
def delete_history(entry_id):
    entry = IdeaHistory.query.filter_by(id=entry_id, user_id=current_user.id).first()
    if not entry:
        return jsonify({"error": "Entry not found"}), 404
    db.session.delete(entry)
    db.session.commit()
    return jsonify({"message": "Deleted successfully"})


# ====================== AI API ROUTES ======================

@app.route('/validate-idea', methods=['POST'])
@login_required
def validate_idea():
    data = request.get_json()
    idea = data.get('idea', '').strip()

    if not idea:
        return jsonify({"error": "Please enter a startup idea."}), 400
    if len(idea) < 10:
        return jsonify({"error": "Please describe your idea in more detail."}), 400

    result = get_ai_response(validate_idea_prompt(idea))

    if result.startswith("AI Error:"):
        return jsonify({"error": result}), 500

    save_to_history(idea, "validate", result)
    return jsonify({"result": result})


@app.route('/market-research', methods=['POST'])
@login_required
def market_research():
    data = request.get_json()
    idea = data.get('idea', '').strip()

    if not idea:
        return jsonify({"error": "Please enter a startup idea."}), 400
    if len(idea) < 10:
        return jsonify({"error": "Please describe your idea in more detail."}), 400

    result = get_ai_response(market_research_prompt(idea))

    if result.startswith("AI Error:"):
        return jsonify({"error": result}), 500

    save_to_history(idea, "market", result)
    return jsonify({"result": result})


@app.route('/generate-pitch', methods=['POST'])
@login_required
def generate_pitch():
    data = request.get_json()
    idea = data.get('idea', '').strip()

    if not idea:
        return jsonify({"error": "Please enter a startup idea."}), 400
    if len(idea) < 10:
        return jsonify({"error": "Please describe your idea in more detail."}), 400

    result = get_ai_response(generate_pitch_prompt(idea))

    if result.startswith("AI Error:"):
        return jsonify({"error": result}), 500

    save_to_history(idea, "pitch", result)
    return jsonify({"result": result})

# ====================== CHATBOT ROUTE ======================
# Add this to your existing app.py

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    messages = data.get('messages', [])

    if not messages:
        return jsonify({"error": "No messages provided."}), 400

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a highly intelligent and friendly AI assistant. "
                        "You can answer any question on any topic — technology, science, history, math, "
                        "coding, business, startups, health, culture, and more. "
                        "You give clear, helpful, and accurate responses. "
                        "When relevant, you can also give startup and business advice. "
                        "Be conversational, concise, and engaging."
                    )
                },
                *messages  # Full conversation history for memory
            ],
            max_tokens=1024,
            temperature=0.7
        )
        reply = response.choices[0].message.content.strip()
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": f"AI Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True)
else:
    # For production (Render / Gunicorn)
    if not os.getenv('GROQ_API_KEY'):
        print("⚠️ WARNING: GROQ_API_KEY is missing!")