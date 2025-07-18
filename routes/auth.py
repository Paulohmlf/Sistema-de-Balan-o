# routes/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from functools import wraps
# --- Imports para hashing de senha e acesso ao DB ---
from werkzeug.security import generate_password_hash, check_password_hash
import data_manager # Importa o módulo data_manager

auth_bp = Blueprint('auth', __name__)

def login_required(role="any"):
    """
    Decorador que exige que um usuário esteja logado com um perfil específico.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in_as' not in session:
                flash("Por favor, faça login para acessar esta página.", "info")
                return redirect(url_for('auth.login'))
            
            # Se o papel requerido não for "any" e o papel do usuário na sessão for diferente
            if role != "any" and session['logged_in_as'] != role:
                flash(f"Acesso negado. Esta área é restrita para o perfil de '{role}'.", "warning")
                # Redireciona para o painel apropriado do usuário logado
                if session['logged_in_as'] == 'gestor':
                    return redirect(url_for('gestor.index'))
                elif session['logged_in_as'] == 'contador':
                    return redirect(url_for('contador.dashboard'))
                else:
                    # Caso inesperado, desloga por segurança
                    return redirect(url_for('auth.logout'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- ROTA DE CADASTRO ---
@auth_bp.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        username = request.form.get('username', '').lower().strip()
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        gestor_token = request.form.get('gestor_token')

        # --- Validações ---
        if not username or not password or not confirm_password:
            flash('Todos os campos de usuário e senha são obrigatórios!', 'warning')
            return redirect(url_for('auth.cadastro'))

        if password != confirm_password:
            flash('As senhas não coincidem!', 'danger')
            return redirect(url_for('auth.cadastro'))

        if data_manager.find_user_by_username(username):
            flash('Este nome de usuário já existe. Por favor, escolha outro.', 'danger')
            return redirect(url_for('auth.cadastro'))

        # --- Define o perfil (role) ---
        GESTOR_SECRET_TOKEN = "Token@123" 
        role = 'gestor' if gestor_token == GESTOR_SECRET_TOKEN else 'contador'

        # --- Cria o hash da senha ---
        # Usando um método de hashing forte padrão da indústria
        password_hash = generate_password_hash(password, method='pbkdf2:sha256')
        
        # --- Adiciona o usuário ao banco de dados ---
        if data_manager.add_user(username, password_hash, role):
            flash(f'Conta para "{username}" criada com sucesso como {role}! Você já pode fazer login.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Ocorreu um erro ao criar a conta. Tente novamente.', 'danger')
            return redirect(url_for('auth.cadastro'))

    # Se for GET, apenas renderiza a página de cadastro
    return render_template('cadastro.html')


# --- ROTA DE LOGIN ATUALIZADA ---
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password')

        if not username or not password:
            flash('Usuário e senha são obrigatórios!', 'warning')
            return redirect(url_for('auth.login'))

        username_lower = username.lower()
        
        # Busca o usuário no banco de dados
        user = data_manager.find_user_by_username(username_lower)

        # Verifica se o usuário existe e se a senha com hash corresponde
        if user and check_password_hash(user['password_hash'], password):
            session['logged_in_as'] = user['role']
            session['user_full_name'] = username.strip().title()
            session['user_id'] = user['id'] # Opcional, mas útil para o futuro
            session['seen_notifications'] = 0
            
            flash(f'Login realizado com sucesso! Bem-vindo, {session["user_full_name"]}!', 'success')
            
            if user['role'] == 'gestor':
                return redirect(url_for('gestor.index'))
            else: # contador
                return redirect(url_for('contador.dashboard'))
        else:
            flash('Credenciais inválidas. Verifique seu usuário e senha.', 'danger')
            return redirect(url_for('auth.login'))

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Você saiu do sistema.', 'info')
    return redirect(url_for('auth.login'))
