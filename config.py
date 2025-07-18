import os
import secrets
from pathlib import Path
import logging

# Configuração do logger
logger = logging.getLogger(__name__)

class Config:
    """Classe de configuração centralizada."""
    
    # --- CONFIGURAÇÕES DE SEGURANÇA ---
    
    @staticmethod
    def _generate_secret_key() -> str:
        """Gera uma chave secreta segura ou usa variável de ambiente."""
        env_key = os.environ.get('FLASK_SECRET_KEY')
        if env_key:
            return env_key
        
        key_file = Path('.secret_key')
        if key_file.exists():
            return key_file.read_text().strip()
        
        new_key = secrets.token_urlsafe(32)
        key_file.write_text(new_key)
        logger.info("Nova chave secreta gerada e salva em .secret_key")
        return new_key
    
    SECRET_KEY = _generate_secret_key()
    
    # --- CONFIGURAÇÕES DO SISTEMA ---
    
    BASE_DIR = Path(__file__).parent.absolute()
    
    DATABASE_CONFIG = {
        'filename': os.environ.get('DB_FILENAME', 'inventario.db'),
        'backup_dir': os.environ.get('DB_BACKUP_DIR', 'backups'),
        'timeout': int(os.environ.get('DB_TIMEOUT', '30')),
        'check_same_thread': False,
        'journal_mode': 'WAL',
        'synchronous': 'NORMAL'
    }
    
    DATABASE_FILE = BASE_DIR / DATABASE_CONFIG['filename']
    TABLE_NAME = os.environ.get('TABLE_NAME', 'inventario')
    
    APP_CONFIG = {
        'name': 'Sistema de Inventário',
        'version': '2.1.0', # Versão atualizada
        'debug': os.environ.get('FLASK_DEBUG', 'False').lower() == 'true',
        'host': os.environ.get('FLASK_HOST', '0.0.0.0'),
        'port': int(os.environ.get('FLASK_PORT', '5000')),
        'max_content_length': 16 * 1024 * 1024,
    }
    
    # --- MÉTODOS DE CONFIGURAÇÃO ---
    
    @classmethod
    def init_directories(cls):
        """Cria diretórios necessários se não existirem."""
        directories = [
            cls.BASE_DIR / cls.DATABASE_CONFIG['backup_dir'],
            cls.BASE_DIR / 'uploads',
            cls.BASE_DIR / 'logs'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Diretório verificado/criado: {directory}")

    @classmethod
    def get_database_url(cls) -> str:
        """Retorna URL de conexão do banco SQLite."""
        return f"sqlite:///{cls.DATABASE_FILE.absolute()}"

    @classmethod
    def is_development(cls) -> bool:
        """Verifica se está em modo de desenvolvimento."""
        return cls.APP_CONFIG['debug']

    @classmethod
    def get_app_info(cls) -> dict:
        """Retorna informações da aplicação."""
        return {
            'name': cls.APP_CONFIG['name'],
            'version': cls.APP_CONFIG['version'],
            'environment': 'development' if cls.is_development() else 'production',
            'database': str(cls.DATABASE_FILE.name)
        }

# --- CONFIGURAÇÕES GLOBAIS ---

config = Config()

# Variáveis globais para compatibilidade com o restante do código
SECRET_KEY = config.SECRET_KEY
DATABASE_FILE = str(config.DATABASE_FILE)
TABLE_NAME = config.TABLE_NAME

# --- FUNÇÕES DE CONVENIÊNCIA ---

def initialize_config():
    """Inicializa configurações e diretórios necessários."""
    try:
        config.init_directories()
        logger.info(f"Configuração inicializada - {config.get_app_info()}")
        return True
    except Exception as e:
        logger.error(f"Erro ao inicializar configuração: {e}")
        return False

# --- INICIALIZAÇÃO AUTOMÁTICA ---

# Garante que a inicialização ocorra quando o módulo for importado
if __name__ != '__main__':
    initialize_config()

# --- BLOCO DE TESTE ---

if __name__ == '__main__':
    print("=== TESTE DE CONFIGURAÇÃO SIMPLIFICADA ===")
    print(f"Informações do sistema: {config.get_app_info()}")
    print(f"Arquivo do Banco de Dados: {DATABASE_FILE}")
    print(f"Modo debug: {config.is_development()}")
    print("O gerenciamento de usuários foi movido para o banco de dados.")
