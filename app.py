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

db_user = os.getenv('POSTGRES_USER')
db_password = os.getenv('POSTGRES_PASSWORD')
db_name = os.getenv('POSTGRES_DB')
db_host = 'db'

database_uri = f'postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}'
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth'

# --- MODELOS (sem alteração) ---
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

# --- ROTAS (sem alteração no geral) ---
@app.route('/')
def index(): return render_template('index.html')

@app.route('/auth', methods=['GET', 'POST'])
def auth():
    if current_user.is_authenticated: return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if 'register' in request.form:
            username, password = request.form['username'], request.form['password']
            if User.query.filter_by(username=username).first():
                flash('Usuário já existe.', 'error')
                return redirect(url_for('auth'))
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for('dashboard'))
        elif 'login' in request.form:
            username, password = request.form['username'], request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and user.password == password:
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Credenciais inválidas.', 'error')
    return render_template('auth.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/terms')
def terms(): return render_template('terms.html')

@app.route('/privacy')
def privacy(): return render_template('privacy.html')

@app.route('/dashboard')
@login_required
def dashboard():
    project_in_analysis = Project.query.filter_by(owner=current_user, status='analyzing').first()
    user_projects = Project.query.filter_by(owner=current_user).order_by(Project.id.desc()).all()
    return render_template('dashboard.html', username=current_user.username, projects=user_projects, project_in_analysis=bool(project_in_analysis))

@app.route('/project/new', methods=['POST'])
@login_required
def new_project():
    project_name = request.form.get('project_name')
    if not project_name: return "Nome do projeto é obrigatório", 400
    new_proj = Project(name=project_name, owner=current_user)
    db.session.add(new_proj)
    db.session.commit()
    return redirect(url_for('project_chat', project_id=new_proj.id))

@app.route('/project/<int:project_id>')
@login_required
def project_chat(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user: return "Acesso não autorizado", 403
    return render_template('project_chat.html', project=project)

# --- NOVA LÓGICA DO CHAT EXTERNO ---

LEAD_QUESTIONS = [
    "Olá! Sou o assistente de projetos da PBPM. Para começarmos, qual o seu nome?",
    "Prazer, {name}! Agora, pode me informar seu melhor contato (email ou WhatsApp)?",
    "Obrigado! Vamos ao projeto. **(What?)** O que exatamente você quer construir? Descreva a ideia principal.",
    "Entendido. **(Why?)** Por que esse projeto é importante? Qual o principal problema que ele resolve?",
    "Interessante. **(Who?)** Quem serão os usuários do sistema? Para quem ele se destina?",
    "Ok. **(Where?)** Onde esse sistema será usado? Em um site (web), aplicativo de celular (mobile) ou ambos?",
    "Estamos quase no fim! **(When?)** Você tem algum prazo em mente ou data importante para o lançamento?",
]

def call_ollama(system_prompt, user_content):
    """Função auxiliar para chamar a API do Ollama de forma segura."""
    try:
        ollama_url = "http://ollama:11434/api/chat"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        payload = {"model": "llama3:8b", "messages": messages, "stream": False}
        response = requests.post(ollama_url, json=payload, timeout=45)
        response.raise_for_status()
        return response.json()['message']['content'], None
    except requests.exceptions.RequestException as e:
        error_message = f"Não consegui me conectar ao assistente. O serviço pode estar sobrecarregado. (Erro: {e})"
        return None, error_message
    except Exception as e:
        return None, f"Ocorreu um erro inesperado: {str(e)}"

def save_lead_to_file(answers, complement=""):
    """Salva o lead completo em um arquivo de texto."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"lead_{answers.get('Nome', 'desconhecido')}_{timestamp}.txt"
    filepath = os.path.join(app.config['LEADS_FOLDER'], filename)
    
    content = f"""--- Lead Capturado ---
Nome: {answers.get('Nome', 'N/A')}
Contato: {answers.get('Contato', 'N/A')}

--- Briefing do Projeto ---
1. O quê (What?):
{answers.get('What?', 'N/A')}

2. Por quê (Why?):
{answers.get('Why?', 'N/A')}

3. Quem (Who?):
{answers.get('Who?', 'N/A')}

4. Onde (Where?):
{answers.get('Where?', 'N/A')}

5. Quando (When?):
{answers.get('When?', 'N/A')}
"""
    if complement:
        content += f"\n--- Complemento do Cliente ---\n{complement}\n"
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

@app.route('/api/external_chat', methods=['POST'])
def external_chat_enxuto():
    data = request.get_json()
    current_step = data.get('step', 0)
    user_message = data.get('message', '')
    answers = data.get('answers', {})

    # Etapa 0: Início
    if current_step == 0:
        return jsonify({'text': LEAD_QUESTIONS[0], 'step': 1, 'answers': {}})

    # Etapas de Perguntas Fixas (1 a 7)
    if 1 <= current_step <= len(LEAD_QUESTIONS):
        # Armazena a resposta anterior
        question_key = LEAD_QUESTIONS[current_step - 1].split('**')[0].strip()
        if 'nome' in question_key.lower():
            answers['Nome'] = user_message
        elif 'contato' in question_key.lower():
            answers['Contato'] = user_message
        else:
            # Extrai a chave do 5W (ex: "What?")
            key_5w = LEAD_QUESTIONS[current_step - 1].split('(')[1].split(')')[0]
            answers[key_5w] = user_message

        # Se ainda houver perguntas a fazer
        if current_step < len(LEAD_QUESTIONS):
            next_question = LEAD_QUESTIONS[current_step]
            if '{name}' in next_question:
                next_question = next_question.format(name=answers.get('Nome', ''))
            return jsonify({'text': next_question, 'step': current_step + 1, 'answers': answers})
        
        # Se for a última pergunta, chama a IA para o primeiro resumo
        else:
            prompt_content = f"Respostas do cliente:\n{answers}"
            system_prompt = "Você é um assistente de projetos. Com base nas respostas do cliente, crie um resumo conciso e bem estruturado do projeto. Finalize perguntando de forma clara se o cliente gostaria de adicionar ou alterar alguma informação."
            summary, error = call_ollama(system_prompt, prompt_content)
            if error: return jsonify({'text': error, 'step': 'error'})
            
            return jsonify({'text': summary, 'step': 'summary_review', 'answers': answers})

    # Etapa de Revisão do Resumo
    elif current_step == 'summary_review':
        # Se o usuário não quiser complementar
        if any(keyword in user_message.lower() for keyword in ['não', 'nao', 'tudo certo', 'perfeito', 'correto']):
            save_lead_to_file(answers)
            final_message = "Entendido! Agradecemos muito pelo seu tempo. Suas informações foram salvas e nossa equipe entrará em contato em breve. Tenha um ótimo dia!"
            return jsonify({'text': final_message, 'step': 'finished', 'answers': answers})
        # Se o usuário quiser complementar
        else:
            return jsonify({'text': "Ótimo! Por favor, escreva o que você gostaria de adicionar ou modificar.", 'step': 'adding_complement', 'answers': answers})

    # Etapa de Adicionar Complemento
    elif current_step == 'adding_complement':
        complement = user_message
        save_lead_to_file(answers, complement)
        final_message = "Perfeito, seu complemento foi adicionado! Nossa equipe analisará tudo e entrará em contato em breve. Muito obrigado novamente!"
        return jsonify({'text': final_message, 'step': 'finished', 'answers': answers})

    return jsonify({'text': "Ocorreu um erro no fluxo do chat. Reiniciando...", 'step': 0, 'answers': {}})


# --- CHAT INTERNO (sem alteração) ---
@app.route('/api/project_chat/<int:project_id>', methods=['POST'])
@login_required
def project_chat_api(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user: return jsonify({"error": "Não autorizado"}), 403
    user_message = request.json.get('message')
    if not user_message: return jsonify({"error": "Mensagem vazia"}), 400
    db.session.add(ChatMessage(role='user', content=user_message, project=project))
    chat_history = [{"role": msg.role, "content": msg.content} for msg in project.chat_messages]
    try:
        with open('prompt.txt', 'r', encoding='utf-8') as f: system_prompt = f.read()
    except FileNotFoundError: return jsonify({"error": "Arquivo de prompt não encontrado."}), 500
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, *chat_history])
        ai_message = response.choices[0].message.content
        db.session.add(ChatMessage(role='assistant', content=ai_message, project=project))
        db.session.commit()
        return jsonify({'text': ai_message})
    except Exception as e: return jsonify({'error': str(e)}), 500

@app.route('/project/finalize/<int:project_id>', methods=['POST'])
@login_required
def finalize_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user: return "Não autorizado", 403
    with open('prompt.txt', 'r', encoding='utf-8') as f: system_prompt = f.read()
    chat_history = [{"role": msg.role, "content": msg.content} for msg in project.chat_messages]
    final_instruction = {"role": "user", "content": "Com base em toda a nossa conversa, por favor, gere o briefing completo do projeto seguindo estritamente a estrutura 5W2H definida nas suas instruções iniciais."}
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, *chat_history, final_instruction])
        summary = response.choices[0].message.content
        if not os.path.exists(app.config['UPLOAD_FOLDER']): os.makedirs(app.config['UPLOAD_FOLDER'])
        filename = f"projeto_{project.id}_{current_user.username}.txt"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        with open(filepath, 'w', encoding='utf-8') as f: f.write(summary)
        project.status = 'analyzing'
        project.summary_file_path = filepath
        db.session.commit()
        return redirect(url_for('dashboard'))
    except Exception as e: return f"Ocorreu um erro ao finalizar o projeto: {str(e)}", 500

with app.app_context():
    db.create_all()