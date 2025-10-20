import os
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'project_briefings'
app.config['LEADS_FOLDER'] = 'leads'

if not os.path.exists(app.config['LEADS_FOLDER']):
    os.makedirs(app.config['LEADS_FOLDER'])

# --- MUDANÇAS AQUI ---
# Conecta aos outros containers usando os nomes dos serviços
db_user = os.getenv('POSTGRES_USER')
db_password = os.getenv('POSTGRES_PASSWORD')
db_name = os.getenv('POSTGRES_DB')
db_host = 'db' # Nome do serviço do banco de dados no docker-compose

database_uri = f'postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}'
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth'

# ... (O resto do seu código, como os Modelos do DB, permanece igual) ...
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    projects = db.relationship('Project', backref='owner', lazy=True)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='draft')
    summary_file_path = db.Column(db.String(300), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    chat_messages = db.relationship('ChatMessage', backref='project', lazy=True, cascade="all, delete-orphan")

class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')
# ... (outras rotas como auth, logout, etc., permanecem iguais) ...
@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if 'register' in request.form:
            username = request.form['username']
            password = request.form['password']
            if User.query.filter_by(username=username).first():
                flash('Usuário já existe.', 'error')
                return redirect(url_for('auth'))
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('dashboard'))
        elif 'login' in request.form:
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and user.password == password:
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Credenciais inválidas.', 'error')
            return redirect(url_for('auth'))
    return render_template('auth.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')
@app.route('/dashboard')
@login_required
def dashboard():
    project_in_analysis = Project.query.filter_by(owner=current_user, status='analyzing').first()
    user_projects = Project.query.filter_by(owner=current_user).order_by(Project.id.desc()).all()
    return render_template('dashboard.html', 
                           username=current_user.username,
                           projects=user_projects,
                           project_in_analysis=bool(project_in_analysis))

@app.route('/project/new', methods=['POST'])
@login_required
def new_project():
    project_name = request.form.get('project_name')
    if not project_name:
        return "Nome do projeto é obrigatório", 400
    new_proj = Project(name=project_name, owner=current_user)
    db.session.add(new_proj)
    db.session.commit()
    return redirect(url_for('project_chat', project_id=new_proj.id))

@app.route('/project/<int:project_id>')
@login_required
def project_chat(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user:
        return "Acesso não autorizado", 403
    return render_template('project_chat.html', project=project)


# --- ROTA DO CHAT EXTERNO CORRIGIDA ---
@app.route('/api/external_chat', methods=['POST'])
def external_chat():
    data = request.get_json()
    user_message = data.get('message', '')
    conversation_history = data.get('history', [])
    
    conversation_history.append({"role": "user", "content": user_message})

    try:
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            system_prompt = f.read().split('---')[0].strip()
    except FileNotFoundError:
        return jsonify({"error": "Arquivo de prompt não encontrado."}), 500
        
    messages_for_api = [{"role": "system", "content": system_prompt}] + conversation_history

    try:
        # --- MUDANÇA AQUI ---
        # Conecta ao container do Ollama pelo nome do serviço
        ollama_url = "http://ollama:11434/api/chat"
        payload = {"model": "llama3:8b", "messages": messages_for_api, "stream": False}

        response = requests.post(ollama_url, json=payload, timeout=20)
        response.raise_for_status()
        
        response_data = response.json()
        ai_message = response_data['message']['content']
        
        conversation_history.append({"role": "assistant", "content": ai_message})

        if "##LEAD_CAPTURED##" in ai_message:
            ai_message = ai_message.replace("##LEAD_CAPTURED##", "").strip()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"lead_{timestamp}.txt"
            filepath = os.path.join(app.config['LEADS_FOLDER'], filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("--- Lead Capturado ---\n\n")
                for msg in conversation_history:
                    f.write(f"[{msg['role'].capitalize()}]: {msg['content']}\n\n")

        return jsonify({'text': ai_message, 'history': conversation_history})

    except requests.exceptions.Timeout:
        error_message = "A resposta do assistente demorou muito para chegar. Tente novamente."
        return jsonify({'text': error_message, 'history': conversation_history}), 504
    except requests.exceptions.RequestException as e:
        error_message = f"Não consegui me conectar ao assistente. (Erro: {e})"
        return jsonify({'text': error_message, 'history': conversation_history}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
# ... (O resto do seu código, como o chat interno e a finalização de projeto, permanece igual) ...
@app.route('/api/project_chat/<int:project_id>', methods=['POST'])
@login_required
def project_chat_api(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user:
        return jsonify({"error": "Não autorizado"}), 403
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "Mensagem vazia"}), 400
    db.session.add(ChatMessage(role='user', content=user_message, project=project))
    chat_history = [{"role": msg.role, "content": msg.content} for msg in project.chat_messages]
    try:
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            system_prompt = f.read()
    except FileNotFoundError:
        return jsonify({"error": "Arquivo de prompt não encontrado."}), 500
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                *chat_history
            ]
        )
        ai_message = response.choices[0].message.content
        db.session.add(ChatMessage(role='assistant', content=ai_message, project=project))
        db.session.commit()
        return jsonify({'text': ai_message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/project/finalize/<int:project_id>', methods=['POST'])
@login_required
def finalize_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user:
        return "Não autorizado", 403
    with open('prompt.txt', 'r', encoding='utf-8') as f:
        system_prompt = f.read()
    chat_history = [{"role": msg.role, "content": msg.content} for msg in project.chat_messages]
    final_instruction = {
        "role": "user",
        "content": "Com base em toda a nossa conversa, por favor, gere o briefing completo do projeto seguindo estritamente a estrutura 5W2H definida nas suas instruções iniciais."
    }
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                *chat_history,
                final_instruction
            ]
        )
        summary = response.choices[0].message.content
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        filename = f"projeto_{project.id}_{current_user.username}.txt"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary)
        project.status = 'analyzing'
        project.summary_file_path = filepath
        db.session.commit()
        return redirect(url_for('dashboard'))
    except Exception as e:
        return f"Ocorreu um erro ao finalizar o projeto: {str(e)}", 500

with app.app_context():
    db.create_all()