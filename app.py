# app.py (Versão com Chatbot - Corrigido o erro de importação circular)

import os
from flask import Flask
from config import SECRET_KEY
from data_manager import load_or_create_inventory
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# REMOVA A SEGUINTE LINHA:
# from app import create_app # Importa a função create_app do seu app.py

# Importa os blueprints dos arquivos de rotas
from routes.auth import auth_bp
from routes.gestor import gestor_bp
from routes.contador import contador_bp
# --- NOVO ---
from routes.chatbot import chatbot_bp

def create_app():
    """Cria e configura a instância da aplicação Flask."""
    # Linha alterada: Adicione template_folder para configurar explicitamente a pasta de templates
    app = Flask(__name__, template_folder='templates')
    app.config['SECRET_KEY'] = SECRET_KEY
    
    print("Iniciando conexão com o banco de dados e carregando dados...")
    
    if not load_or_create_inventory():
        print("\n!!! ERRO CRÍTICO: Não foi possível carregar ou criar os dados do inventário no banco de dados.")
    else:
        print("Dados de inventário carregados com sucesso do banco de dados.")
    
    # Registra os Blueprints na aplicação
    app.register_blueprint(auth_bp)
    app.register_blueprint(gestor_bp)
    app.register_blueprint(contador_bp)
    # --- NOVO ---
    app.register_blueprint(chatbot_bp) # Registra o blueprint do chatbot
    
    return app

if __name__ == '__main__':
    app = create_app()
    # Use debug=True apenas durante o desenvolvimento.
    # O reloader automático do Flask garante que as alterações nos ficheiros reiniciem o servidor.
    app.run(host='127.0.0.1', port=5000, debug=True)
