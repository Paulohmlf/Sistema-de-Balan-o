import sqlite3

DB_PATH = 'inventario_BRCPG.db'
TABELA = 'inventario'

# ➕ Colunas que precisamos adicionar (caso não existam)
colunas_novas = {
    'VALIDADO': 'INTEGER DEFAULT 0',         # Você pode mudar o tipo se quiser
    'RECONTAGEM_COUNT': 'INTEGER DEFAULT 0'  # Por exemplo: TEXT, REAL, BOOLEAN etc.
}

def adicionar_colunas_ausentes():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Obtemos as colunas atuais
        cursor.execute(f"PRAGMA table_info({TABELA})")
        colunas_atual = [col[1] for col in cursor.fetchall()]

        alteradas = []
        for coluna, tipo in colunas_novas.items():
            if coluna not in colunas_atual:
                try:
                    print(f"➕ Adicionando coluna '{coluna}'...")
                    cursor.execute(f"ALTER TABLE {TABELA} ADD COLUMN {coluna} {tipo}")
                    alteradas.append(coluna)
                except Exception as e:
                    print(f"❌ Erro ao adicionar coluna '{coluna}': {e}")

        if alteradas:
            conn.commit()
            print(f"\n✅ Colunas adicionadas com sucesso: {alteradas}")
        else:
            print("\nℹ️ Nenhuma coluna foi adicionada (já existiam).")

if __name__ == '__main__':
    adicionar_colunas_ausentes()
