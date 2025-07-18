# database_pool.py - Novo arquivo
import sqlite3
import threading
from queue import Queue, Empty
from contextlib import contextmanager
import logging

class ConnectionPool:
    def __init__(self, database_file: str, pool_size: int = 5):
        self.database_file = database_file
        self.pool_size = pool_size
        self._pool = Queue(maxsize=pool_size)
        self._lock = threading.Lock()
        
        # Pré-aloca conexões
        for _ in range(pool_size):
            conn = self._create_connection()
            self._pool.put(conn)
    
    def _create_connection(self):
        conn = sqlite3.connect(
            self.database_file,
            check_same_thread=False,
            timeout=30
        )
        conn.row_factory = sqlite3.Row
        # Otimizações SQLite
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA temp_store=memory")
        return conn
    
    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = self._pool.get(timeout=10)
            yield conn
        except Empty:
            # Pool esgotado, cria conexão temporária
            conn = self._create_connection()
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                try:
                    self._pool.put(conn, timeout=1)
                except:
                    # Pool cheio, fecha conexão extra
                    conn.close()

# Usar no data_manager.py
class InventoryDataManager:
    def __init__(self):
        # ... código existente
        self._connection_pool = ConnectionPool(self._db_file, pool_size=5)
    
    @contextmanager
    def _get_db_connection(self):
        """Usa pool de conexões"""
        with self._connection_pool.get_connection() as conn:
            yield conn
