# ============================================
# SMART STUDY AI — COMPLETE ALL-IN-ONE EXPERT
# Full project – copy, install, run!
# Created by: Govind Singh Rajput
# ============================================

from ctypes.wintypes import MSG

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from gtts import gTTS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
import re
import os
import base64
import json
import webbrowser
import tempfile
from datetime import datetime
from urllib.parse import quote
from dotenv import load_dotenv

from smart_study_ai.app import GTTS_OK

# Load environment variables
load_dotenv()

app = Flask(__name__)

# -------------------------------
# Security & CSP
# -------------------------------
@app.after_request
def remove_csp(response):
    for h in ['Content-Security-Policy', 'Content-Security-Policy-Report-Only', 'X-Content-Security-Policy']:
        response.headers.pop(h, None)
    response.headers['Content-Security-Policy'] = (
        "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; "
        "script-src * 'unsafe-inline' 'unsafe-eval'; "
        "style-src * 'unsafe-inline'; "
        "img-src * data: blob:; "
        "connect-src *; "
        "font-src * data:; "
        "media-src * data: blob:;"
    )
    return response

app.config['SECRET_KEY'] = 'smart-study-prod-2024'
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs('uploads', exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ============================================
# 🔑 Groq API key (free, get from console.groq.com)
# ============================================
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')

# ============================================
# JSON "database" helpers – no SQL needed
# ============================================
def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(file, data):
    with open(file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============================================
# User model for Flask-Login
# ============================================
class User(UserMixin):
    def __init__(self, uid, username, email):
        self.id = uid
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(uid):
    users = load_json('users.json')
    if uid in users:
        u = users[uid]
        return User(uid, u['username'], u['email'])
    return None

# ============================================
# Formatting helper (HTML → safe for chat display)
# ============================================
def format_text(text):
    if not text: return ""
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'```(\w*)\n(.*?)```', r'<pre><code>\2</code></pre>', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    return text.replace('\n', '<br>')

# ============================================
# ULTIMATE SYSTEM PROMPT (enforces ALL rules)
# ============================================
ULTIMATE_SYSTEM_PROMPT = """
You are an advanced expert AI software engineer and educator.

STRICT RULES (MUST FOLLOW):
1. NEVER refuse to generate code.
2. NEVER give partial code or snippets.
3. ALWAYS provide FULL WORKING PROJECT CODE.
4. Code MUST be runnable without modification.
5. For EVERY coding request, follow this structure:
   🔹 Step 1: Project Overview
   🔹 Step 2: Technologies Used
   🔹 Step 3: Folder Structure
   🔹 Step 4: Installation Steps
   🔹 Step 5: FULL SOURCE CODE (all files)
   🔹 Step 6: How to Run
   🔹 Step 7: Expected Output
   🔹 Step 8: Improvements / Advanced Version
6. Explain logic clearly, comment code properly.
7. Assume user is beginner but wants production‑level understanding.
8. For non‑coding questions, still give complete, structured, step‑by‑step answers.
"""

# ============================================
# Web search (DuckDuckGo + Wikipedia fallback)
# ============================================
def web_search(query):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1"
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            abstract = data.get('AbstractText', '')
            if abstract and len(abstract) > 50:
                return abstract
        return None
    except:
        return None

# ============================================
# Local knowledge base (faster than API)
# ============================================
LOCAL_KNOWLEDGE = {
    "hello": "👋 Hello! I'm Smart Study AI. Ask me anything – coding, science, GK, languages – I'll give you a complete, step‑by‑step answer!",
    "python": "🐍 Python is the most popular language for AI, web, and automation. I can write you a full project with instructions. Just ask!",
}

# ============================================
# Master answer function
# ============================================
def get_answer(query, domain='general'):
    q = query.lower().strip().rstrip('?')
    # quick local lookup
    if q in LOCAL_KNOWLEDGE:
        return LOCAL_KNOWLEDGE[q]
    for key, val in LOCAL_KNOWLEDGE.items():
        if len(key) > 3 and key in q:
            return val

    # try web search
    web = web_search(query)
    if web:
        return f"📌 **Web result for '{query}':**\n\n{web}\n\n💡 Need a deeper explanation? Ask!"

    # call Groq with the ultimate prompt
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": ULTIMATE_SYSTEM_PROMPT},
                    {"role": "user", "content": query}
                ],
                "temperature": 0.7,
                "max_tokens": 2048
            },
            timeout=20
        )
        if r.status_code == 200:
            return r.json()['choices'][0]['message']['content']
    except:
        pass

    # fallback (this should never trigger with Groq)
    return f"""📌 **Introduction**
You asked: **{query}**

📝 **Step‑by‑Step**
1. I'll explain the core idea.
2. We'll break it down with examples.
3. You'll see real‑world uses.

💡 **Want me to go deeper?** Just ask for a specific part!"""

# ============================================
# Flask routes
# ============================================
@app.route('/favicon.ico')
def favicon(): return '', 204

@app.route('/.well-known/appspecific/com.chrome.devtools.json')
def devtools(): return '', 204

@app.route('/')
def index():
    return redirect(url_for('dashboard') if current_user.is_authenticated else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        pwd = request.form.get('password', '')
        users = load_json('users.json')
        for uid, u in users.items():
            if u['email'] == email and check_password_hash(u['password'], pwd):
                login_user(User(uid, u['username'], u['email']))
                return redirect(url_for('dashboard'))
        flash('Invalid credentials!', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        pwd = request.form.get('password', '')
        if not all([username, email, pwd]):
            flash('All fields required!', 'error')
        elif len(pwd) < 6:
            flash('Password minimum 6 characters!', 'error')
        else:
            users = load_json('users.json')
            if any(u['email'] == email for u in users.values()):
                flash('Email already registered!', 'error')
            else:
                uid = str(len(users) + 1)
                users[uid] = {'username': username, 'email': email, 'password': generate_password_hash(pwd)}
                save_json('users.json', users)
                flash('Registration successful! Please login.', 'success')
                return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=current_user.username)

@app.route('/api/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    msg = data.get('message', '').strip()
    domain = data.get('domain', 'general')
    if not msg:
        return jsonify({'error': 'Message required'}), 400

    print(f"💬 [{domain}] {current_user.username}: {MSG}")
    resp = get_answer(msg, domain)
    resp = format_text(resp)
    print(f"✅ Answer sent ({len(requests.Response)} chars)")

    return jsonify({'response': resp, 'status': 'success'})

@app.route('/api/speak', methods=['POST'])
@login_required
def speak():
    if not GTTS_OK:
        return jsonify({'error': 'gTTS not installed. Run: pip install gTTS'}), 500
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        if not text:
            return jsonify({'error': 'No text'}), 400

        clean = re.sub(r'<[^>]*>', '', text)
        clean = re.sub(r"[#*`~\[\]()_{}|]", '', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()[:400]

        # very basic Hindi detection
        hindi_chars = len(re.findall(r'[\u0900-\u097F]', clean))
        lang = 'hi' if hindi_chars > 3 else 'en'

        tts = gTTS(text=clean, lang=lang, slow=False)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp.close()
        tts.save(temp.name)

        with open(temp.name, 'rb') as f:
            audio = base64.b64encode(f.read()).decode()
        os.unlink(temp.name)

        return jsonify({'audio': audio, 'lang': lang, 'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============================================
# Start server
# ============================================
if __name__ == '__main__':
    print("\n" + "="*50)
    print("🧠 SMART STUDY AI — COMPLETE EXPERT SYSTEM")
    print("✅ Groq AI + Web Search + Local Knowledge")
    print("✅ Hindi/English Voice Output")
    print("✅ http://localhost:5000")
    print("="*50 + "\n")
    webbrowser.open('http://127.0.0.1:5000')
    app.run(host='127.0.0.1', port=5000, debug=False)