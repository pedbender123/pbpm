import os
import openai
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

# --- CONFIGURAÇÃO INICIAL ---
app = Flask(__name__)
# Lê a chave secreta do ambiente
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = 'project_briefings'

# Lê as credenciais do banco de dados das variáveis de ambiente
db_user = os.getenv('POSTGRES_USER')
db_password = os.getenv('POSTGRES_PASSWORD')
db_name = os.getenv('POSTGRES_DB')
db_host = 'db' # Nome do serviço no docker-compose.yml

database_uri = f'postgresql://{db_user}:{db_password}@{db_host}:5432/{db_name}'
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialização das extensões
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth'

# Configuração da API da OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# --- MODELOS DO BANCO DE DADOS ---
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
    # --- DEBUG ---
    print(f"--- DEBUG: Tentando carregar o utilizador com ID: {user_id}")
    user = User.query.get(int(user_id))
    if user:
        print(f"--- DEBUG: Utilizador {user.username} encontrado na base de dados.")
    else:
        print("--- DEBUG: Utilizador NÃO foi encontrado na base de dados.")
    return user

# --- ROTAS PRINCIPAIS E DE AUTENTICAÇÃO ---
@app.route('/')
def index():
    return render_template('index.html')

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
            # --- DEBUG ---
            print(f"--- DEBUG: Novo utilizador '{new_user.username}' criado com ID: {new_user.id}")
            
            login_user(new_user)
            # --- DEBUG ---
            print(f"--- DEBUG: Função login_user chamada para '{new_user.username}'. Redirecionando para o dashboard.")
            
            return redirect(url_for('dashboard'))

        elif 'login' in request.form:
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            if user and user.password == password:
                login_user(user)
                # --- DEBUG ---
                print(f"--- DEBUG: Utilizador '{user.username}' logado com sucesso. Redirecionando para o dashboard.")
                return redirect(url_for('dashboard'))
            
            # --- DEBUG ---
            print(f"--- DEBUG: Tentativa de login falhou para o utilizador '{username}'.")
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

# --- ROTAS DO DASHBOARD E PROJETOS ---
@app.route('/dashboard')
@login_required
def dashboard():
    # --- DEBUG ---
    print(f"--- DEBUG: A aceder ao dashboard. Estado de autenticação: {current_user.is_authenticated}")
    project_in_analysis = Project.query.filter_by(owner=current_user, status='analyzing').first()
    user_projects = Project.query.filter_by(owner=current_user).order_by(Project.id.desc()).all()
    return render_template('dashboard.html', 
                           username=current_user.username,
                           projects=user_projects,
                           project_in_analysis=bool(project_in_analysis))

# ... (o resto das suas rotas continua igual) ...
# --- ROTAS DO DASHBOARD E PROJETOS ---
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

# --- ROTAS DA API DE CHAT ---

# 1) Chat Externo (Não Logado)
@app.route('/api/external_chat', methods=['POST'])
def external_chat():
    data = request.get_json()
    user_message = data.get('message', '').lower()
    message_count = data.get('count', 0)

    if message_count == 0:
        response_text = "Olá! Que ótima ideia você tem em mente. Me conte um pouco sobre ela."
    elif message_count == 1:
        # Lógica de análise de palavras-chave
        tech_keywords = {
            "bubble": ["app sem código", "bubble.io", "aplicativo rápido"],
            "n8n": ["automação", "integrar sistemas", "n8n", "workflow"],
            "appsheet": ["aplicativo para empresa", "appsheet", "planilhas"],
            "web": ["site", "sistema web", "loja online", "python", "javascript"]
        }
        
        found_tech = "web" # Padrão
        for tech, keywords in tech_keywords.items():
            if any(keyword in user_message for keyword in keywords):
                found_tech = tech
                break
        
        response_text = f"Interessante! Parece que seu projeto envolve {found_tech}. Acreditamos que temos as ferramentas certas para te ajudar! Para darmos o próximo passo e detalhar sua ideia com um especialista, por favor, crie uma conta. A partir da sua área de cliente, você poderá iniciar formalmente o seu projeto."
    else:
        response_text = "" # Não responde mais

    return jsonify({'text': response_text, 'disable_chat': message_count >= 1})

# 2) Chat Interno (Dashboard)
@app.route('/api/project_chat/<int:project_id>', methods=['POST'])
@login_required
def project_chat_api(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user:
        return jsonify({"error": "Não autorizado"}), 403

    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"error": "Mensagem vazia"}), 400

    # Salva a mensagem do usuário no DB
    db.session.add(ChatMessage(role='user', content=user_message, project=project))
    
    # Monta o histórico para a IA
    chat_history = [{"role": msg.role, "content": msg.content} for msg in project.chat_messages]
    
    # 4) Carrega o prompt do arquivo
    try:
        with open('prompt.txt', 'r', encoding='utf-8') as f:
            system_prompt = f.read()
    except FileNotFoundError:
        return jsonify({"error": "Arquivo de prompt não encontrado."}), 500

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                *chat_history
            ]
        )
        ai_message = response.choices[0].message.content
        
        # Salva a resposta da IA no DB
        db.session.add(ChatMessage(role='assistant', content=ai_message, project=project))
        db.session.commit()
        
        return jsonify({'text': ai_message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 5) Finalização do Projeto e Geração do 5W2H
@app.route('/project/finalize/<int:project_id>', methods=['POST'])
@login_required
def finalize_project(project_id):
    project = Project.query.get_or_404(project_id)
    if project.owner != current_user:
        return "Não autorizado", 403

    # Carrega o prompt e o histórico
    with open('prompt.txt', 'r', encoding='utf-8') as f:
        system_prompt = f.read()
    chat_history = [{"role": msg.role, "content": msg.content} for msg in project.chat_messages]
    
    # Adiciona a instrução final para gerar o 5W2H
    final_instruction = {
        "role": "user",
        "content": "Com base em toda a nossa conversa, por favor, gere o briefing completo do projeto seguindo estritamente a estrutura 5W2H definida nas suas instruções iniciais."
    }
    
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                *chat_history,
                final_instruction
            ]
        )
        summary = response.choices[0].message.content
        
        # Salva o arquivo .txt
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
            
        filename = f"projeto_{project.id}_{current_user.username}.txt"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(summary)
            
        # Atualiza o projeto no banco de dados
        project.status = 'analyzing'
        project.summary_file_path = filepath
        db.session.commit()
        
        return redirect(url_for('dashboard'))
    except Exception as e:
        # Adicione um tratamento de erro aqui
        return f"Ocorreu um erro ao finalizar o projeto: {str(e)}", 500

# Cria as tabelas no contexto da aplicação
with app.app_context():
    db.create_all()