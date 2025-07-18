# utils/cache_manager.py (VERSÃO CORRIGIDA)
from functools import lru_cache
from typing import Dict, Any
import time
import pandas as pd  # ADICIONADO: Import do pandas

class CacheManager:
    def __init__(self, ttl_seconds: int = 300):  # Cache por 5 minutos
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl_seconds
    
    def get(self, key: str) -> Any:
        if key in self._cache:
            data = self._cache[key]
            if time.time() - data['timestamp'] < self._ttl:
                return data['value']
            else:
                del self._cache[key]  # Expirou
        return None
    
    def set(self, key: str, value: Any):
        self._cache[key] = {
            'value': value,
            'timestamp': time.time()
        }
    
    def invalidate(self, pattern: str = None):
        """Invalida cache por padrão ou limpa tudo"""
        if pattern:
            keys_to_remove = [k for k in self._cache.keys() if pattern in k]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            self._cache.clear()

# Exemplo de uso no data_manager.py
class InventoryDataManager:
    def __init__(self):
        # ... código existente
        self._cache = CacheManager(ttl_seconds=300)
    
    def get_inventory_summary(self) -> Dict[str, int]:
        """Cache do resumo por 5 minutos"""
        cache_key = "inventory_summary"
        cached_result = self._cache.get(cache_key)
        
        if cached_result is not None:
            return cached_result
        
        # Calcula normalmente se não há cache
        if not self.inventory_data:
            result = {'total': 0, 'pendente': 0, 'concluido': 0, 'outros': 0}
        else:
            # CORRIGIDO: Agora pd está importado
            df = pd.DataFrame(self.inventory_data)
            status_counts = df['STATUS'].value_counts() if 'STATUS' in df.columns else {}
            result = {
                'total': len(self.inventory_data),
                'pendente': status_counts.get('Pendente', 0),
                'concluido': status_counts.get('Concluído', 0),
                'outros': len(self.inventory_data) - status_counts.get('Pendente', 0) - status_counts.get('Concluído', 0)
            }
        
        self._cache.set(cache_key, result)
        return result
    
    def update_item(self, codigo, lote, updates):
        """Invalida cache ao atualizar dados"""
        result = super().update_item(codigo, lote, updates)
        if result:
            self._cache.invalidate()  # Limpa cache após mudança
        return result
