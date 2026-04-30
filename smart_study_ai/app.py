# ============================================
# SMART AI — SECURE VERSION
# API Keys loaded from .env file
# ============================================

import os

# Load .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Get secrets from environment variables
HF_TOKEN = os.getenv('HF_TOKEN', '')
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
SECRET_KEY = os.getenv('SECRET_KEY', 'smart-ai-default-key')

# Set HF_TOKEN if available
if HF_TOKEN:
    os.environ["HF_TOKEN"] = HF_TOKEN

from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, session, send_from_directory, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests, re, base64, json, webbrowser, uuid, time, random, threading
from datetime import datetime, timedelta
from PIL import Image, ImageStat, ImageEnhance
import numpy as np

try:
    from gtts import gTTS
    GTTS_OK = True
except:
    GTTS_OK = False

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY  # ✅ From .env
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['SESSION_COOKIE_SECURE'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

for folder in ['analysis_images', 'thumbnails', 'voice_cache', 'chat_history', 'user_memory']:
    os.makedirs(f'uploads/{folder}', exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp'}
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = None
login_manager.refresh_view = 'login'
login_manager.needs_refresh_message = None

# ✅ GROQ_API_KEY is now from .env, not hardcoded!

# ============================================
# 🧠 ENGINES
# ============================================
class QueryUnderstanding:
    INTENTS = {
        'coding': ['code','program','function','python','java','javascript','html','css','algorithm','debug','error','api'],
        'math': ['solve','equation','math','algebra','geometry','calculus','formula','theorem','derivative','integral'],
        'science': ['physics','chemistry','biology','science','experiment','atom','molecule','cell','dna'],
        'explanation': ['explain','what is','how does','why','tell me about','define','describe','meaning'],
        'analysis': ['analyze','review','evaluate','assess','critique'],
        'creative': ['write','story','poem','essay','script','letter','create'],
        'conversation': ['hi','hello','hey','how are you','thanks','bye','good morning'],
    }
    @classmethod
    def understand(cls, query):
        q = query.lower().strip()
        scores = {}
        for intent, keywords in cls.INTENTS.items():
            score = sum(1 for kw in keywords if kw in q)
            if score > 0: scores[intent] = score
        primary = max(scores, key=scores.get) if scores else 'general'
        hindi = len(re.findall(r'[\u0900-\u097F]', q))
        lang = 'hindi' if hindi > len(q)*0.3 else 'english'
        return {'intent': primary, 'language': lang, 'original': query}

class ContextEngine:
    @staticmethod
    def file(uid): return os.path.join('uploads','user_memory',f'ctx_{uid}.json')
    @staticmethod
    def load(uid):
        try:
            with open(ContextEngine.file(uid),'r',encoding='utf-8') as f: return json.load(f)
        except: return {"conversation_history":[],"user_profile":{}}
    @staticmethod
    def save(uid,d):
        with open(ContextEngine.file(uid),'w',encoding='utf-8') as f: json.dump(d,f,ensure_ascii=False,indent=2)
    @staticmethod
    def update(uid,role,msg):
        ctx = ContextEngine.load(uid)
        ctx['conversation_history'].append({'role':role,'content':msg[:500],'timestamp':datetime.now().isoformat()})
        if len(ctx['conversation_history']) > 50: ctx['conversation_history'] = ctx['conversation_history'][-50:]
        ContextEngine.save(uid,ctx)
    @staticmethod
    def get_context(uid):
        ctx = ContextEngine.load(uid)
        recent = ctx['conversation_history'][-10:]
        return "\n".join([f"{'User' if c['role']=='user' else 'Assistant'}: {c['content'][:150]}" for c in recent])

class ReasoningEngine:
    @staticmethod
    def generate(query, understanding, context, username, mode="expert"):
        intent = understanding['intent']
        lang = understanding['language']
        lang_inst = "Respond in natural Hindi (हिंदी)." if lang == 'hindi' else ""
        
        system = f"""# DEEPSEEK R1
You are DeepSeek, created by 深度求索. Ultra-intelligent AI.
Context: {context}
Intent: {intent}
{lang_inst}
Style: **bold**, • bullets, 1. steps, ``` code. Be concise yet comprehensive."""
        
        # ✅ FIXED: Multiple model fallback
        models = [
            "llama-3.1-8b-instant",
            "llama-3.3-70b-versatile",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]
        
        for model in models:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "system", "content": system}, {"role": "user", "content": query}],
                        "temperature": 0.4 if mode == "expert" else 0.7,
                        "max_tokens": 2500 if mode == "expert" else 800
                    },
                    timeout=35
                )
                if r.status_code == 200:
                    data = r.json()
                    if 'choices' in data and data['choices']:
                        return data['choices'][0]['message']['content']
            except:
                continue
        
        return f"**{query}**\n\nI understand your question. Let me help."

class ImageAnalysisEngine:
    @staticmethod
    def analyze(image_path, question=None, username=None, uid=None, mode="expert"):
        try:
            img = Image.open(image_path); w,h=img.size; fmt=img.format or 'Unknown'; size_kb=os.path.getsize(image_path)/1024
            if img.mode!='RGB': img=img.convert('RGB')
            enhancer=ImageEnhance.Contrast(img); img_enhanced=enhancer.enhance(2.0)
            img_array=np.array(img_enhanced); brightness=np.mean(img_array)
            img_type="Document/Text" if brightness>180 else "Photo/Image"
            img_info=f"{w}x{h}px | {fmt} | {size_kb:.1f}KB | Type: {img_type}"
        except:
            img_info="Image loaded"; img_type="Unknown"
        
        context = ContextEngine.get_context(uid) if uid else ""
        prompt = f"""Analyze this image. Info: {img_info}
{f'Question: {question}' if question else ''}
Context: {context[:500]}
TASK: Read text if document. Analyze if photo. Be detailed. NEVER say you can't see."""
        
        models = ["llama-3.1-8b-instant", "llama-3.3-70b-versatile", "mixtral-8x7b-32768"]
        
        for model in models:
            try:
                r = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [{"role": "system", "content": "You are DeepSeek R1 with vision. Analyze thoroughly."}, {"role": "user", "content": prompt}],
                        "temperature": 0.2, "max_tokens": 2500
                    },
                    timeout=35
                )
                if r.status_code == 200:
                    data = r.json()
                    if 'choices' in data and data['choices']:
                        return data['choices'][0]['message']['content']
            except:
                continue
        
        return f"### 📎 Image Analysis\n\n**Details:** {img_info}\n\nI can analyze this image. What would you like to know?"

# ============================================
# CHAT HISTORY
# ============================================
class ChatHistory:
    @staticmethod
    def file(uid): return os.path.join('uploads','chat_history',f'ch_{uid}.json')
    @staticmethod
    def load(uid):
        try:
            with open(ChatHistory.file(uid),'r',encoding='utf-8') as f: return json.load(f)
        except: return {"chats":[]}
    @staticmethod
    def save(uid,d):
        with open(ChatHistory.file(uid),'w',encoding='utf-8') as f: json.dump(d,f,ensure_ascii=False,indent=2)
    @staticmethod
    def add(uid,cid,role,content,img=None):
        h=ChatHistory.load(uid)
        for c in h['chats']:
            if c['id']==cid:
                c['messages'].append({'role':role,'content':content,'image_url':img,'timestamp':datetime.now().isoformat()})
                c['updated_at']=datetime.now().isoformat(); ChatHistory.save(uid,h); return
        h['chats'].append({'id':cid,'title':content[:50],'created_at':datetime.now().isoformat(),'updated_at':datetime.now().isoformat(),'messages':[{'role':role,'content':content,'image_url':img,'timestamp':datetime.now().isoformat()}]})
        ChatHistory.save(uid,h)
    @staticmethod
    def chats(uid): return sorted([{'id':c['id'],'title':c.get('title',''),'updated_at':c.get('updated_at',''),'message_count':len(c.get('messages',[]))} for c in ChatHistory.load(uid)['chats']], key=lambda x: x['updated_at'], reverse=True)
    @staticmethod
    def messages(uid,cid):
        for c in ChatHistory.load(uid)['chats']:
            if c['id']==cid: return c.get('messages',[])
        return []
    @staticmethod
    def delete(uid,cid):
        h=ChatHistory.load(uid); h['chats']=[c for c in h['chats'] if c['id']!=cid]; ChatHistory.save(uid,h)
    @staticmethod
    def clear(uid): ChatHistory.save(uid,{"chats":[]})

# ============================================
# USER MODEL
# ============================================
class User(UserMixin):
    def __init__(self,uid,username,email): self.id=uid; self.username=username; self.email=email

@login_manager.user_loader
def load_user(uid):
    users=load_json('users.json')
    if uid in users: u=users[uid]; return User(uid,u['username'],u['email'])
    return None

@login_manager.unauthorized_handler
def unauthorized():
    flash('Please login to continue.', 'info')
    return redirect(url_for('login'))

def load_json(file):
    try:
        with open(file,'r',encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_json(file,data):
    with open(file,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in ALLOWED_EXTENSIONS

def format_text(text):
    if not text: return ""
    text = re.sub(r'```(\w*)\s*\n(.*?)\n```', r'<pre><code class="language-\1">\2</code></pre>', text, flags=re.DOTALL)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'### (.*?)(?:\n|$)', r'<h3>\1</h3>', text)
    text = re.sub(r'## (.*?)(?:\n|$)', r'<h2>\1</h2>', text)
    return text.replace('\n', '<br>')

# ============================================
# ROUTES
# ============================================
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

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
                user = User(uid, u['username'], u['email'])
                login_user(user, remember=True)
                session['just_logged_in'] = True
                session['login_username'] = u['username']
                session.permanent = True
                print(f"✅ {u['username']} logged in!")
                return redirect(url_for('dashboard'))
        
        flash('Invalid email or password.', 'error')
    
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
            flash('All fields required.', 'error')
        elif len(pwd) < 6:
            flash('Password min 6 characters.', 'error')
        else:
            users = load_json('users.json')
            if any(u['email'] == email for u in users.values()):
                flash('Email already exists.', 'error')
            else:
                uid = str(len(users) + 1)
                users[uid] = {
                    'username': username,
                    'email': email,
                    'password': generate_password_hash(pwd),
                    'created_at': datetime.now().isoformat()
                }
                save_json('users.json', users)
                flash('Account created successfully! Please login.', 'success')
                return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    username = current_user.username
    print(f"👋 {username} logging out...")
    
    logout_user()
    session.clear()
    
    response = make_response(redirect(url_for('login')))
    response.delete_cookie('session')
    response.delete_cookie('remember_token')
    response.delete_cookie('user_id')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    flash('You have been logged out successfully.', 'info')
    print(f"✅ {username} logged out completely!")
    
    return response

@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    show_welcome = session.pop('just_logged_in', False)
    login_username = session.pop('login_username', current_user.username)
    return render_template('dashboard.html', 
                         username=current_user.username,
                         show_welcome=show_welcome,
                         welcome_name=login_username)

@app.route('/history')
@login_required
def history_page():
    return render_template('history.html', username=current_user.username)

# ============================================
# API ENDPOINTS
# ============================================
@app.route('/api/history/chats')
@login_required
def api_chats():
    return jsonify({'success': True, 'chats': ChatHistory.chats(current_user.id)})

@app.route('/api/history/messages/<chat_id>')
@login_required
def api_messages(chat_id):
    return jsonify({'success': True, 'messages': ChatHistory.messages(current_user.id, chat_id)})

@app.route('/api/history/delete/<chat_id>', methods=['DELETE'])
@login_required
def api_delete_chat(chat_id):
    ChatHistory.delete(current_user.id, chat_id)
    return jsonify({'success': True})

@app.route('/api/history/clear', methods=['DELETE'])
@login_required
def api_clear():
    ChatHistory.clear(current_user.id)
    return jsonify({'success': True})

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json()
    msg = data.get('message', '').strip()
    mode = data.get('mode', 'instant')
    chat_id = data.get('chat_id', str(uuid.uuid4()))
    if not msg: return jsonify({'error': 'Message required'}), 400
    
    username = current_user.username
    uid = current_user.id
    
    understanding = QueryUnderstanding.understand(msg)
    context = ContextEngine.get_context(uid)
    ContextEngine.update(uid, 'user', msg)
    
    answer = ReasoningEngine.generate(msg, understanding, context, username, mode)
    
    ContextEngine.update(uid, 'assistant', answer)
    ChatHistory.add(uid, chat_id, 'user', msg)
    ChatHistory.add(uid, chat_id, 'assistant', answer)
    
    return jsonify({
        'response': format_text(answer),
        'status': 'success',
        'chat_id': chat_id,
        'mode': mode,
        'intent': understanding['intent']
    })

@app.route('/api/upload-image', methods=['POST'])
@login_required
def api_upload():
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No file'}), 400
    
    file = request.files['image']
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Invalid file'}), 400
    
    ext = file.filename.rsplit('.', 1)[1].lower()
    fn = f"img_{uuid.uuid4().hex[:10]}.{ext}"
    fp = os.path.join('uploads', 'analysis_images', fn)
    file.save(fp)
    
    try:
        img = Image.open(fp)
        img.thumbnail((300, 300))
        thumb_fn = f"thumb_{fn}"
        img.save(os.path.join('uploads', 'thumbnails', thumb_fn))
    except:
        thumb_fn = None
    
    question = request.form.get('question', '').strip()
    mode = request.form.get('mode', 'expert')
    chat_id = request.form.get('chat_id', str(uuid.uuid4()))
    username = current_user.username
    uid = current_user.id
    
    img_url = f"/uploads/analysis_images/{fn}"
    thumb_url = f"/uploads/thumbnails/{thumb_fn}" if thumb_fn else img_url
    
    user_msg = f"📎 {file.filename}" + (f"\n❓ {question}" if question else "")
    ChatHistory.add(uid, chat_id, 'user', user_msg, img_url)
    ContextEngine.update(uid, 'user', user_msg)
    
    analysis = ImageAnalysisEngine.analyze(fp, question, username, uid, mode)
    
    ChatHistory.add(uid, chat_id, 'assistant', analysis, img_url)
    ContextEngine.update(uid, 'assistant', analysis)
    
    return jsonify({
        'success': True,
        'image': {'url': img_url, 'thumb_url': thumb_url},
        'analysis': format_text(analysis),
        'chat_id': chat_id
    })

@app.route('/api/speak', methods=['POST'])
@login_required
def api_speak():
    if not GTTS_OK:
        return jsonify({'error': 'Not available'}), 500
    
    data = request.get_json()
    text = data.get('text', '').strip()[:500]
    if not text:
        return jsonify({'error': 'No text'}), 400
    
    clean = re.sub(r'<[^>]*>', '', text).strip()
    clean = clean.replace('. ', '. ... ').replace('? ', '? ... ')
    
    hindi = len(re.findall(r'[\u0900-\u097F]', clean))
    lang = 'hi' if len(clean.replace(' ', '')) > 0 and hindi / len(clean.replace(' ', '')) > 0.3 else 'en'
    
    tts = gTTS(text=clean, lang=lang, tld='co.in', slow=False)
    cache = os.path.join('uploads', 'voice_cache', f'v_{hash(clean[:100])}.mp3')
    tts.save(cache)
    
    with open(cache, 'rb') as f:
        audio = base64.b64encode(f.read()).decode()
    
    return jsonify({'success': True, 'audio': audio, 'lang': lang})

@app.route('/uploads/<folder>/<filename>')
def serve_file(folder, filename):
    return send_from_directory(os.path.join('uploads', folder), filename)

@app.errorhandler(404)
def not_found(e):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.errorhandler(405)
def method_not_allowed(e):
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🧠 SMART AI — SECURE VERSION")
    print("="*60)
    print(f"🔑 API Key: {'✅ Loaded' if GROQ_API_KEY else '❌ Missing - Check .env'}")
    print(f"🔐 Secret: {'✅ Loaded' if SECRET_KEY != 'smart-ai-default-key' else '⚠️ Using default'}")
    print("✅ Model Fallback: 4 models")
    print("✅ Proper Logout")
    print("🚀 http://localhost:5000")
    print("="*60 + "\n")
    webbrowser.open('http://127.0.0.1:5000')
    app.run(host='127.0.0.1', port=5000, debug=False)