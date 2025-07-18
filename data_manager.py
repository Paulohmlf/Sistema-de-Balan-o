import pandas as pd
import logging
from datetime import datetime
from typing import List, Dict, Optional, Union, Any
from pathlib import Path
import sqlite3
from contextlib import contextmanager

from config import DATABASE_FILE, TABLE_NAME

class CacheManager:
    def __init__(self, ttl_seconds=300):
        self._cache = {}
        self._ttl = ttl_seconds
    def get(self, key):
        
        return self._cache.get(key)
    def set(self, key, value):
        self._cache[key] = value
    def invalidate(self):
        self._cache.clear()


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class InventoryDataManager:
    def __init__(self):
        self.inventory_data: List[Dict] = []
        self.notifications: List[Dict] = []
        self._db_file = DATABASE_FILE
        self._table_name = TABLE_NAME
        
        self._cache = CacheManager(ttl_seconds=300)
        
        self._codigo_index: Dict[str, List[Dict]] = {}
        self._codigo_lote_index: Dict[str, Dict] = {}

    def _rebuild_indexes(self):
        """Reconstrói índices para busca O(1)"""
        self._codigo_index.clear()
        self._codigo_lote_index.clear()
        
        for item in self.inventory_data:
            codigo = str(item.get('CÓDIGO', '')).strip().replace('.0', '')
            lote = str(item.get('LOTE', '')).strip()
            
            if codigo not in self._codigo_index:
                self._codigo_index[codigo] = []
            self._codigo_index[codigo].append(item)
            
            key = f"{codigo}|{lote}"
            self._codigo_lote_index[key] = item

    @contextmanager
    def _get_db_connection(self):
        """Context manager para conexões com o banco de dados."""
        conn = None
        try:
            conn = sqlite3.connect(self._db_file)
            conn.row_factory = sqlite3.Row
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Erro na conexão com SQLite: {e}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                conn.close()

    def _validate_codigo(self, codigo: Union[str, int]) -> str:
        """Valida e normaliza código de produto."""
        if not codigo:
            raise ValueError("Código não pode estar vazio")
        return str(codigo).strip().replace('.0', '')

    def _validate_item_data(self, item_data: Dict) -> Dict:
        """Valida dados do item antes da inserção."""
        required_fields = ['CÓDIGO']
        for field in required_fields:
            if field not in item_data or not item_data[field]:
                raise ValueError(f"Campo obrigatório '{field}' está ausente ou vazio")
        
        validated_data = item_data.copy()
        validated_data['CÓDIGO'] = self._validate_codigo(validated_data['CÓDIGO'])
        validated_data['LOTE'] = str(validated_data.get('LOTE', '')).strip()
        # Garante que 'VALIDADO' exista e tenha um valor padrão se não for fornecido
        validated_data['VALIDADO'] = str(validated_data.get('VALIDADO', 'Não')).strip()
        
        return validated_data

    def _create_table_if_not_exists(self) -> bool:
        """Cria as tabelas de inventário e usuários se não existirem."""
        create_inventory_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self._table_name} (
            ID INTEGER PRIMARY KEY AUTOINCREMENT, "CÓDIGO" TEXT NOT NULL, PRODUTO TEXT,
            FABRICANTE TEXT, LOTE TEXT, ESTOQUE_SISTEMA INTEGER DEFAULT 0,
            CONTROLE_LOTE TEXT, STATUS TEXT DEFAULT 'Pendente',
            ESTOQUE_BALCAO INTEGER DEFAULT NULL, ESTOQUE_DEPOSITO INTEGER DEFAULT NULL,
            INVENTARIO INTEGER DEFAULT 0, CONTADOR TEXT, DATA_FABRICACAO TEXT,
            DATA_VALIDADE TEXT, CONTADOR_ORIGINAL TEXT, HORARIO_RECONTAGEM_SOLICITADA TEXT,
            GESTOR_RECONTAGEM TEXT, CONFERENCIA TEXT,RECONTAGEM_COUNT INTEGER DEFAULT 0,
            VALIDADO TEXT DEFAULT 'Não', -- <--- NOVA COLUNA AQUI
            UNIQUE ("CÓDIGO", LOTE)
        );
        """
        create_users_table_sql = """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('gestor', 'contador'))
        );
        """
        create_indexes_sql = [
            f'CREATE INDEX IF NOT EXISTS idx_codigo ON {self._table_name}("CÓDIGO")',
            f'CREATE INDEX IF NOT EXISTS idx_fabricante ON {self._table_name}(FABRICANTE)',
            f'CREATE INDEX IF NOT EXISTS idx_status ON {self._table_name}(STATUS)',
            f'CREATE INDEX IF NOT EXISTS idx_contador ON {self._table_name}(CONTADOR)',
            f'CREATE INDEX IF NOT EXISTS idx_codigo_lote ON {self._table_name}("CÓDIGO", LOTE)'
        ]
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(create_inventory_table_sql)
                cursor.execute(create_users_table_sql)
                
                for index_sql in create_indexes_sql:
                    cursor.execute(index_sql)
                    
                conn.commit()
                logger.info(f"Tabelas '{self._table_name}' e 'users' e índices verificados/criados com sucesso")
                return True
        except sqlite3.Error as e:
            logger.error(f"Erro ao criar tabelas/índices: {e}")
            return False

    def _load_from_database(self) -> bool:
        """Carrega dados do banco para a memória."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT * FROM {self._table_name}")
                self.inventory_data = [dict(row) for row in cursor.fetchall()]
                self._rebuild_indexes()
                logger.info(f"Carregados {len(self.inventory_data)} itens do banco")
                return True
        except sqlite3.Error as e:
            logger.error(f"Erro ao carregar dados: {e}")
            return False

    def _process_excel_data(self, excel_file_path: Union[str, Path]) -> Optional[pd.DataFrame]:
        """Processa dados do Excel e retorna DataFrame limpo."""
        try:
            df_excel = pd.read_excel(
                excel_file_path, sheet_name='INVENTÁRIO', header=14, dtype={'CÓDIGO': str}
            )
            
            df_excel.columns = df_excel.columns.str.strip()
            column_mapping = {
                'DESCRIÇÃO DO PRODUTO/SERVIÇO': 'PRODUTO', 'FORNECEDOR': 'FABRICANTE',
                'QUANTIDADE': 'ESTOQUE_SISTEMA', 'CONTROLE DE LOTE S/N': 'CONTROLE_LOTE'
            }
            df_excel.rename(columns=column_mapping, inplace=True)
            
            required_columns = ['CÓDIGO', 'PRODUTO', 'FABRICANTE', 'LOTE', 'ESTOQUE_SISTEMA', 'CONTROLE_LOTE']
            df_clean = df_excel[required_columns].copy()
            df_clean.dropna(subset=['CÓDIGO'], inplace=True)
            df_clean['LOTE'] = df_clean['LOTE'].fillna('')
            
            
            df_clean = df_clean.drop_duplicates(subset=['CÓDIGO', 'LOTE', 'FABRICANTE'], keep='last')
            
            return df_clean
            
        except Exception as e:
            logger.error(f"Erro ao processar Excel: {e}")
            return None

    def _bulk_insert_data(self, df: pd.DataFrame) -> bool:
        """Insere dados em lote no banco."""
        if df.empty:
            return False
            
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                columns = df.columns.tolist()
                columns_quoted = ', '.join(f'"{col}"' for col in columns)
                placeholders = ', '.join(['?'] * len(columns))
                insert_sql = f"INSERT OR IGNORE INTO {self._table_name} ({columns_quoted}) VALUES ({placeholders})"
                data_tuples = [tuple(row) for row in df.to_numpy()]
                cursor.executemany(insert_sql, data_tuples)
                conn.commit()
                logger.info(f"Inseridos/Ignorados {cursor.rowcount} registros do Excel")
                return True
        except sqlite3.Error as e:
            logger.error(f"Erro na inserção em lote: {e}")
            return False

    
    def load_or_create_inventory(self, excel_file_path: Union[str, Path] = 'teste.xlsx') -> bool:
        """Carrega inventário existente ou cria novo a partir do Excel."""
        if not self._create_table_if_not_exists():
            return False
            
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(ID) FROM {self._table_name}")
                item_count = cursor.fetchone()[0]

                if item_count > 0:
                    return self._load_from_database()
                else:
                    df_clean = self._process_excel_data(excel_file_path)
                    if df_clean is not None and self._bulk_insert_data(df_clean):
                        return self._load_from_database()
                    return False
                    
        except sqlite3.Error as e:
            logger.error(f"Erro ao verificar inventário: {e}")
            return False

    def find_item(self, codigo: Union[str, int], lote: Union[str, None] = None) -> Optional[Dict]:
        """Busca item usando índices hash O(1)"""
        try:
            codigo_normalizado = self._validate_codigo(codigo)
        except ValueError as e:
            logger.warning(f"Código inválido: {e}")
            return None
            
        if lote is None:
            items = self._codigo_index.get(codigo_normalizado, [])
            return items[0] if items else None
        else:
            lote_normalizado = str(lote).strip() if lote else ''
            key = f"{codigo_normalizado}|{lote_normalizado}"
            return self._codigo_lote_index.get(key)

    def update_item(self, codigo: Union[str, int], lote: Union[str, None], updates: Dict) -> bool:
        """Atualiza item no inventário e banco de dados."""
        item = self.find_item(codigo, lote)
        if not item:
            logger.warning(f"Item não encontrado para atualização: {codigo} - {lote}")
            return False
            
        if not updates:
            logger.warning("Nenhuma atualização fornecida")
            return False
            
        item.update(updates)
        self._rebuild_indexes()
        
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                set_clause = ', '.join([f'"{key}" = ?' for key in updates.keys()])
                update_sql = f'UPDATE {self._table_name} SET {set_clause} WHERE "CÓDIGO" = ? AND LOTE = ?'
                lote_str = str(lote) if lote is not None else ''
                values = list(updates.values()) + [self._validate_codigo(codigo), lote_str]
                cursor.execute(update_sql, tuple(values))
                conn.commit()
                if cursor.rowcount > 0:
                    self._cache.invalidate()
                    return True
                return False
        except sqlite3.Error as e:
            logger.error(f"Erro ao atualizar item no DB: {e}")
            return False

    def add_new_item(self, new_item_data: Dict) -> bool:
        """Adiciona novo item ao inventário."""
        try:
            validated_data = self._validate_item_data(new_item_data)
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                columns = list(validated_data.keys())
                columns_quoted = ', '.join(f'"{col}"' for col in columns)
                placeholders = ', '.join(['?'] * len(columns))
                insert_sql = f"INSERT INTO {self._table_name} ({columns_quoted}) VALUES ({placeholders})"
                cursor.execute(insert_sql, tuple(validated_data.values()))
                conn.commit()
                self.inventory_data.append(validated_data)
                self._rebuild_indexes()
                self._cache.invalidate()
                logger.info(f"Item adicionado: {validated_data.get('CÓDIGO')} - {validated_data.get('LOTE')}")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Item duplicado. Tentando atualizar: {new_item_data.get('CÓDIGO')}/{new_item_data.get('LOTE')}")
            codigo = new_item_data.pop('CÓDIGO')
            lote = new_item_data.pop('LOTE', '')
            return self.update_item(codigo, lote, new_item_data)
        except (ValueError, sqlite3.Error) as e:
            logger.error(f"Erro ao adicionar novo item: {e}")
            return False

    def find_user_by_username(self, username: str) -> Optional[Dict]:
        """Busca um usuário pelo nome no banco de dados."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                user = cursor.fetchone()
                return dict(user) if user else None
        except sqlite3.Error as e:
            logger.error(f"Erro ao buscar usuário '{username}': {e}")
            return None

    def add_user(self, username: str, password_hash: str, role: str) -> bool:
        """Adiciona um novo usuário ao banco de dados."""
        sql = "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)"
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (username, password_hash, role))
                conn.commit()
                logger.info(f"Usuário '{username}' com perfil '{role}' criado com sucesso.")
                return True
        except sqlite3.IntegrityError:
            logger.warning(f"Tentativa de criar usuário duplicado: '{username}'")
            return False
        except sqlite3.Error as e:
            logger.error(f"Erro ao adicionar usuário '{username}': {e}")
            return False
            
    def get_inventory_summary(self) -> Dict[str, int]:
        """Resumo do inventário com cache"""
        cache_key = "inventory_summary"
        cached_result = self._cache.get(cache_key)
        if cached_result is not None: return cached_result
        if not self.inventory_data:
            result = {'total': 0, 'pendente': 0, 'concluido': 0, 'outros': 0}
        else:
            try:
                df = pd.DataFrame(self.inventory_data)
                if 'STATUS' not in df.columns:
                    result = {'total': len(self.inventory_data), 'pendente': 0, 'concluido': 0, 'outros': len(self.inventory_data)}
                else:
                    status_counts = df['STATUS'].value_counts()
                    result = {
                        'total': len(self.inventory_data),
                        'pendente': status_counts.get('Pendente', 0),
                        'concluido': status_counts.get('Concluído', 0),
                        'outros': len(self.inventory_data) - status_counts.get('Pendente', 0) - status_counts.get('Concluído', 0)
                    }
            except Exception as e:
                logger.error(f"Erro ao gerar resumo: {e}")
                result = {'total': 0, 'pendente': 0, 'concluido': 0, 'outros': 0}
        self._cache.set(cache_key, result)
        return result

    def get_all_users(self) -> List[Dict]:
        """Busca todos os usuários do banco de dados."""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, role FROM users ORDER BY username ASC")
                users = [dict(row) for row in cursor.fetchall()]
                return users
        except sqlite3.Error as e:
            logger.error(f"Erro ao buscar todos os usuários: {e}")
            return []

    def update_user_password(self, user_id: int, new_password_hash: str) -> bool:
        """Atualiza o hash da senha de um usuário específico."""
        sql = "UPDATE users SET password_hash = ? WHERE id = ?"
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (new_password_hash, user_id))
                conn.commit()
                # Verifica se a atualização foi bem-sucedida
                return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Erro ao atualizar a senha para o usuário ID {user_id}: {e}")
            return False
    
    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Cria backup do banco de dados."""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"backup_inventory_{timestamp}.db"
        try:
            import shutil
            shutil.copy2(self._db_file, backup_path)
            logger.info(f"Backup criado: {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Erro ao criar backup: {e}")
            return False

# --- Instância e Funções de Conveniência ---

_manager = InventoryDataManager()

def find_item(codigo, lote=None): return _manager.find_item(codigo, lote)
def update_item(codigo, lote, updates): return _manager.update_item(codigo, lote, updates)
def add_new_item(item_data): return _manager.add_new_item(item_data)
def load_or_create_inventory(excel_file_path='teste.xlsx'):
    result = _manager.load_or_create_inventory(excel_file_path)
    global INVENTORY_DATA, NOTIFICATIONS
    INVENTORY_DATA = _manager.inventory_data
    NOTIFICATIONS = _manager.notifications
    return result
def backup_database(backup_path=None): return _manager.backup_database(backup_path)
def get_inventory_summary(): return _manager.get_inventory_summary()
def find_user_by_username(username: str): return _manager.find_user_by_username(username)
def add_user(username: str, password_hash: str, role: str): return _manager.add_user(username, password_hash, role)
def get_all_users(): return _manager.get_all_users()
def update_user_password(user_id, new_password_hash): return _manager.update_user_password(user_id, new_password_hash)
INVENTORY_DATA = _manager.inventory_data
NOTIFICATIONS = _manager.notifications