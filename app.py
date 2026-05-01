import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-super-secret-key-change-in-production'  # Change this!
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# ====================== USER MODEL ======================
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# ====================== HELPER AI FUNCTION ======================
def get_ai_response(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an experienced startup advisor and venture capitalist."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI Error: {str(e)}"

# ====================== PROMPTS (Same as before) ======================
def validate_idea_prompt(idea): 
    return f"""Analyze this startup idea... (same as previous version)"""  # Keep your full prompt here

def market_research_prompt(idea): 
    return f"""Do quick market research... (same as previous)"""

def generate_pitch_prompt(idea): 
    return f"""Create a compelling investor pitch... (same as previous)"""

# ====================== AUTH ROUTES ======================
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

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
        username = request.form.get('username')
        password = request.form.get('password')

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


# ====================== MAIN APP ROUTES (Protected) ======================
@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/validate-idea', methods=['POST'])
@login_required
def validate_idea():
    data = request.get_json()
    idea = data.get('idea', '').strip()
    if not idea:
        return jsonify({"error": "Idea is required"}), 400

    prompt = validate_idea_prompt(idea)   # Use your full prompt
    result = get_ai_response(prompt)
    return jsonify({"result": result})


@app.route('/market-research', methods=['POST'])
@login_required
def market_research():
    data = request.get_json()
    idea = data.get('idea', '').strip()
    if not idea:
        return jsonify({"error": "Idea is required"}), 400

    prompt = market_research_prompt(idea)
    result = get_ai_response(prompt)
    return jsonify({"result": result})


@app.route('/generate-pitch', methods=['POST'])
@login_required
def generate_pitch():
    data = request.get_json()
    idea = data.get('idea', '').strip()
    if not idea:
        return jsonify({"error": "Idea is required"}), 400

    prompt = generate_pitch_prompt(idea)
    result = get_ai_response(prompt)
    return jsonify({"result": result})


if __name__ == '__main__':
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  WARNING: OPENAI_API_KEY not found in .env")
    app.run(debug=True)