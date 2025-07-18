# routes/chatbot.py (Versão Analista de Dados)

import os
import google.generativeai as genai
from flask import Blueprint, request, jsonify
from dotenv import load_dotenv
import sqlite3
import unicodedata
import re
import json

# --- Configuração de Caminho e Constantes ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(project_root, 'inventario.db')
SEARCH_INTENT = "busca_de_item"
CALCULATE_INTENT = "calculo_agregado"

# --- Configuração do Blueprint e do Modelo Gemini ---
chatbot_bp = Blueprint('chatbot_bp', __name__)
load_dotenv()

try:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("AVISO: A variável de ambiente GEMINI_API_KEY não foi definida.")
        model = None
    else:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        print("Modelo Gemini para Chatbot (Analista) configurado com sucesso.")
except Exception as e:
    print(f"Erro ao configurar a API do Gemini para o Chatbot: {e}")
    model = None

# --- Funções Auxiliares de Texto e Busca ( existentes ) ---

def remover_acentos(texto):
    nfkd_form = unicodedata.normalize('NFKD', texto)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

def buscar_dados_inventario(termo_busca):
    # Esta função continua a ser usada para a intenção de 'busca_de_item'
    if not termo_busca: return []
    termo_busca_limpo = remover_acentos(termo_busca.lower())
    palavras_todas = re.findall(r'\b\w{2,}\b', termo_busca_limpo)
    stopwords = {'de', 'da', 'do', 'das', 'dos', 'em', 'na', 'no', 'para', 'por', 'com', 'que', 'ou', 'e', 'o', 'a', 'os', 'as', 'sao', 'qual', 'quais', 'um', 'uma', 'produto', 'produtos', 'item', 'itens', 'fabricante', 'lista', 'liste', 'mostre', 'me'}
    palavras_chave = [palavra for palavra in palavras_todas if palavra not in stopwords]
    if not palavras_chave: return []
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query_conditions_list = []
    params = []
    for palavra in palavras_chave:
        query_conditions_list.append("LOWER(PRODUTO || ' ' || FABRICANTE) LIKE ?")
        params.append(f'%{palavra}%')
    query_conditions = " AND ".join(query_conditions_list)
    query = f"SELECT CÓDIGO as codigo, PRODUTO as produto, FABRICANTE as fabricante, ESTOQUE_SISTEMA as estoque_sistema, INVENTARIO as inventario_final FROM inventario WHERE {query_conditions} LIMIT 15"
    
    try:
        cursor.execute(query, params)
        produtos = [dict(row) for row in cursor.fetchall()]
        print(f"[Busca] Encontrados {len(produtos)} resultados para '{termo_busca}'")
        return produtos
    except sqlite3.Error as e:
        print(f"[Busca] Erro SQLite: {e}")
        return []
    finally:
        if conn: conn.close()


# --- NOVAS FUNÇÕES DE ANÁLISE ---

def detectar_intencao(pergunta_usuario: str) -> dict:
    """
    Usa Gemini para classificar a intenção do usuário e extrair entidades.
    """
    if not model: return {"intent": SEARCH_INTENT}

    # Prompt para que a IA estruture a pergunta do usuário
    prompt = f"""
    Analise a pergunta do usuário e a estruture em um objeto JSON.

    As intenções possíveis são:
    - '{SEARCH_INTENT}': Para buscar itens, produtos ou fabricantes.
    - '{CALCULATE_INTENT}': Para contar, somar ou fazer qualquer cálculo.

    As agregações possíveis são: 'COUNT', 'SUM', 'AVG'.
    As colunas possíveis são: 'FABRICANTE', 'PRODUTO', 'ESTOQUE_SISTEMA', 'INVENTARIO', 'STATUS'.
    Os status possíveis são: 'Concluído', 'Pendente', 'Em Andamento'.

    Exemplos:
    1. Pergunta: "quais são os produtos da bayer?"
       JSON: {{"intent": "{SEARCH_INTENT}", "details": "bayer"}}
    2. Pergunta: "quantos fabricantes estão concluidos?"
       JSON: {{"intent": "{CALCULATE_INTENT}", "aggregation": "COUNT", "column": "FABRICANTE", "filters": {{"STATUS": "Concluído"}}}}
    3. Pergunta: "qual o total em estoque do produto X"
       JSON: {{"intent": "{CALCULATE_INTENT}", "aggregation": "SUM", "column": "ESTOQUE_SISTEMA", "filters": {{"PRODUTO": "produto X"}}}}

    Pergunta do Usuário: "{pergunta_usuario}"

    Objeto JSON:
    """
    try:
        # Força a resposta a ser um JSON
        generation_config = genai.types.GenerationConfig(
            candidate_count=1,
            response_mime_type="application/json"
        )
        response = model.generate_content(prompt, generation_config=generation_config)
        
        # Limpeza e parse do JSON
        json_text = response.text.strip().replace('```json', '').replace('```', '')
        intent_data = json.loads(json_text)
        print(f"[Análise de Intenção] Resultado: {intent_data}")
        return intent_data
    except Exception as e:
        print(f"[Análise de Intenção] Erro ao detectar intenção: {e}. Usando busca padrão.")
        # Se a IA falhar, assume que é uma busca simples
        return {"intent": SEARCH_INTENT, "details": pergunta_usuario}


def executar_calculo_agregado(intent_data: dict) -> any:
    """
    Executa uma query SQL com base na intenção de cálculo detectada.
    """
    agg = intent_data.get("aggregation")
    col = intent_data.get("column")
    filters = intent_data.get("filters", {})

    if not agg or not col:
        return None

    # Mapeamento seguro para evitar SQL Injection
    allowed_aggs = {"COUNT": "COUNT", "SUM": "SUM", "AVG": "AVG"}
    allowed_cols = {"FABRICANTE": "FABRICANTE", "PRODUTO": "PRODUTO", "ESTOQUE_SISTEMA": "ESTOQUE_SISTEMA", "STATUS": "STATUS"}
    
    if agg not in allowed_aggs or col not in allowed_cols:
        return None
    
    # Monta a query
    # Usando DISTINCT para contagens de fabricantes ou produtos
    col_to_agg = f"DISTINCT {allowed_cols[col]}" if agg == "COUNT" and col in ["FABRICANTE", "PRODUTO"] else allowed_cols[col]
    query = f"SELECT {allowed_aggs[agg]}({col_to_agg}) FROM inventario"
    
    # Adiciona filtros (WHERE)
    params = []
    where_clauses = []
    if filters:
        for key, value in filters.items():
            if key in allowed_cols:
                where_clauses.append(f"{allowed_cols[key]} = ?")
                params.append(value)
        
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
            
    print(f"[Cálculo] Executando Query: {query} com Parâmetros: {params}")

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()[0]
        conn.close()
        print(f"[Cálculo] Resultado da Query: {result}")
        return result
    except Exception as e:
        print(f"[Cálculo] Erro ao executar a query: {e}")
        return None


# --- Endpoint Principal do Chatbot (Refatorado) ---
@chatbot_bp.route('/api/chatbot', methods=['POST'])
def ask_chatbot():
    if not model:
        return jsonify({"error": "Desculpe, o assistente de IA não está disponível no momento."}), 503

    data = request.get_json()
    pergunta_usuario = data.get('question')

    if not pergunta_usuario:
        return jsonify({"error": "Nenhuma pergunta foi enviada."}), 400

    # Passo 1: Detectar a intenção do usuário
    intent_data = detectar_intencao(pergunta_usuario)
    intent = intent_data.get("intent")

    resultado_final = None
    prompt_final = ""

    # Passo 2: Executar a ação correta com base na intenção
    if intent == CALCULATE_INTENT:
        resultado_calculo = executar_calculo_agregado(intent_data)
        resultado_final = f"O resultado do cálculo é: {resultado_calculo if resultado_calculo is not None else 'não foi possível calcular'}."
        # Cria um prompt para a IA apenas formatar a resposta
        prompt_final = (
            f"O usuário perguntou: '{pergunta_usuario}'.\n"
            f"Nós executamos um cálculo e o resultado foi '{resultado_calculo}'.\n"
            "Formule uma resposta final amigável e direta em português para o usuário com este resultado."
        )

    else: # O padrão é 'busca_de_item'
        texto_busca = intent_data.get("details", pergunta_usuario)
        resultado_busca = buscar_dados_inventario(texto_busca)
        if not resultado_busca:
            resultado_final = "Não encontrei dados específicos sobre isso no inventário."
        else:
            resultado_final = "\n".join([str(item) for item in resultado_busca])
        # Cria um prompt para a IA analisar os dados ou informar que não encontrou
        prompt_final = (
            "Você é um assistente de gestão de inventário e deve responder em português do Brasil.\n"
            f"O usuário perguntou: '{pergunta_usuario}'.\n"
            f"O resultado da nossa busca no banco de dados foi:\n{resultado_final}\n\n"
            "Com base nesse resultado, formule uma resposta clara e útil para o usuário. Se for uma lista, resuma-a. Se não houver resultados, informe educadamente."
        )

    # Passo 3: Gerar a resposta final para o usuário
    try:
        print(f"--- PROMPT FINAL ENVIADO PARA O GEMINI ---\n{prompt_final[:500]}...\n------------------------------------")
        response = model.generate_content(prompt_final)
        return jsonify({"answer": response.text})
    except Exception as e:
        print(f"Erro na chamada final da API do Gemini: {e}")
        return jsonify({"error": "Ocorreu um erro ao formular a resposta final."}), 500

