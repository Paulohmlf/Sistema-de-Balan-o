# utils/async_operations.py (VERSÃO COMPLETA COM AIOFILES)
import asyncio
import aiofiles
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class AsyncInventoryOperations:
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def backup_database_async(self, backup_path: str):
        """Backup assíncrono que não bloqueia a aplicação"""
        loop = asyncio.get_event_loop()
        
        def backup_sync():
            return self.data_manager.backup_database(backup_path)
        
        try:
            result = await loop.run_in_executor(self.executor, backup_sync)
            return result
        except Exception as e:
            logger.error(f"Erro no backup assíncrono: {e}")
            return False
    
    async def process_excel_async(self, excel_path: str):
        """Processamento assíncrono de Excel"""
        loop = asyncio.get_event_loop()
        
        def process_sync():
            return self.data_manager._process_excel_data(excel_path)
        
        try:
            return await loop.run_in_executor(self.executor, process_sync)
        except Exception as e:
            logger.error(f"Erro no processamento assíncrono do Excel: {e}")
            return None
    
    async def read_file_async(self, file_path: str) -> str:
        """Lê arquivo de forma assíncrona usando aiofiles"""
        try:
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                return content
        except Exception as e:
            logger.error(f"Erro ao ler arquivo {file_path}: {e}")
            return ""
    
    async def write_file_async(self, file_path: str, content: str) -> bool:
        """Escreve arquivo de forma assíncrona usando aiofiles"""
        try:
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
                return True
        except Exception as e:
            logger.error(f"Erro ao escrever arquivo {file_path}: {e}")
            return False
    
    def __del__(self):
        """Limpa recursos ao destruir a instância"""
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
