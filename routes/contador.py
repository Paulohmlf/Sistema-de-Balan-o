# routes/contador.py (VERSÃO FINAL E CORRIGIDA)

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify
)
from routes.auth import login_required
import data_manager
from data_manager import find_item, update_item, add_new_item, NOTIFICATIONS
import pandas as pd
from datetime import datetime
from urllib.parse import unquote, quote
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

contador_bp = Blueprint('contador', __name__, url_prefix='/contador')


def tem_dados_balcao(fabricante):
    """Verifica se a contagem de balcão já foi realizada (mesmo que seja 0)."""
    for item in data_manager.INVENTORY_DATA:
        if (str(item.get('FABRICANTE', '')) == fabricante and
            item.get('STATUS') == 'Em Andamento' and
            item.get('CONTADOR') == session.get('user_full_name') and
            item.get('ESTOQUE_BALCAO') is not None):
            return True
    return False

def tem_dados_deposito(fabricante):
    """Verifica se a contagem de depósito já foi realizada (mesmo que seja 0)."""
    for item in data_manager.INVENTORY_DATA:
        if (str(item.get('FABRICANTE', '')) == fabricante and
            item.get('STATUS') == 'Em Andamento' and
            item.get('CONTADOR') == session.get('user_full_name') and
            item.get('ESTOQUE_DEPOSITO') is not None):
            return True
    return False

def is_ajax_request():
    """Detecta se a requisição é AJAX de forma robusta."""
    return (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '') or
        request.headers.get('Content-Type', '').startswith('application/json')
    )

@contador_bp.route('/adicionar_item', methods=['GET', 'POST'])
@login_required(role="contador")
def adicionar_item():
    """Rota principal para adicionar itens - usada pela página completa do dashboard."""
    if request.method == 'POST':
        # Esta rota não deve processar AJAX do modal - apenas formulários normais
        try:
            codigo_produto = request.form.get('produto_codigo')
            novo_lote = request.form.get('novo_lote', '').strip()
            quantidade_balcao = int(request.form.get('quantidade_balcao', 0))
            quantidade_deposito = int(request.form.get('quantidade_deposito', 0))
            data_fabricacao = request.form.get('data_fabricacao')
            data_validade = request.form.get('data_validade')
            fabricante = request.form.get('fabricante')

            logger.info(f"Página - Dados recebidos - Código: {codigo_produto}, Lote: {novo_lote}, Fabricante: {fabricante}")

            # Validações básicas
            if not codigo_produto or not codigo_produto.strip():
                flash("Código do produto é obrigatório.", 'danger')
                return redirect(url_for('contador.adicionar_item'))

            if not novo_lote or not novo_lote.strip():
                flash("Número do lote é obrigatório.", 'danger')
                return redirect(url_for('contador.adicionar_item'))

            if quantidade_balcao < 0 or quantidade_deposito < 0:
                flash("As quantidades não podem ser negativas.", 'danger')
                return redirect(url_for('contador.adicionar_item'))

            # Buscar item modelo
            item_modelo = find_item(codigo_produto)

            if not item_modelo:
                flash(f'Produto com código {codigo_produto} não encontrado no sistema.', 'danger')
                return redirect(url_for('contador.adicionar_item'))

            # Verificar se já existe um lote com o mesmo código e número
            for existing_item in data_manager.INVENTORY_DATA:
                if (existing_item.get('CÓDIGO') == codigo_produto and 
                    existing_item.get('LOTE') == novo_lote):
                    flash(f'Já existe um lote {novo_lote} para o produto {codigo_produto}.', 'danger')
                    return redirect(url_for('contador.adicionar_item'))

            # Criar novo item
            novo_item = {
                'CÓDIGO': item_modelo.get('CÓDIGO'),
                'PRODUTO': item_modelo.get('PRODUTO'),
                'FABRICANTE': item_modelo.get('FABRICANTE'),
                'CONTROLE_LOTE': 'S',
                'LOTE': novo_lote,
                'ESTOQUE_SISTEMA': 0,
                'STATUS': 'Concluído',
                'ESTOQUE_BALCAO': quantidade_balcao,
                'ESTOQUE_DEPOSITO': quantidade_deposito,
                'INVENTARIO': quantidade_balcao + quantidade_deposito,
                'CONTADOR': session.get('user_full_name'),
                'DATA_FABRICACAO': data_fabricacao,
                'DATA_VALIDADE': data_validade,
                'CONTADOR_ORIGINAL': '',
                'HORARIO_RECONTAGEM_SOLICITADA': '',
                'GESTOR_RECONTAGEM': '',
                'CONFERENCIA': f'Lote adicionado por {session.get("user_full_name")} em {datetime.now().strftime("%d/%m/%Y %H:%M")}'
            }

            # Tentar salvar o item
            if add_new_item(novo_item):
                flash(f'Novo lote {novo_lote} para o produto {novo_item["PRODUTO"]} adicionado com sucesso!', 'success')
                logger.info(f"Página - Novo lote adicionado com sucesso: {codigo_produto} - {novo_lote}")
                return redirect(url_for('contador.adicionar_item'))
            else:
                flash('Erro ao salvar o novo lote no banco de dados.', 'danger')
                logger.error(f"Página - Falha ao salvar novo lote: {codigo_produto} - {novo_lote}")
                return redirect(url_for('contador.adicionar_item'))

        except ValueError as ve:
            logger.error(f"Página - Erro de validação: {ve}")
            flash(f"Erro de validação: {str(ve)}", 'danger')
            return redirect(url_for('contador.adicionar_item'))
                
        except Exception as e:
            logger.error(f"Página - Erro inesperado: {e}")
            flash('Erro interno do servidor ao processar a solicitação.', 'danger')
            return redirect(url_for('contador.adicionar_item'))

    # Parte GET - renderizar página de adicionar item
    fabricantes = sorted(list(set(str(item['FABRICANTE']) for item in data_manager.INVENTORY_DATA if 'FABRICANTE' in item)))
    return render_template('contador/adicionar_item.html', fabricantes=fabricantes)

@contador_bp.route('/adicionar_lote_modal', methods=['POST'])
@login_required(role="contador")
def adicionar_lote_modal():
    """Rota específica para adicionar lote via modal AJAX na tela de confirmação."""
    # Esta rota é APENAS para requisições AJAX
    if not is_ajax_request():
        return jsonify({'success': False, 'message': 'Esta rota é apenas para requisições AJAX'}), 400
    
    try:
        codigo_produto = request.form.get('produto_codigo')
        novo_lote = request.form.get('novo_lote', '').strip()
        quantidade_balcao = int(request.form.get('quantidade_balcao', 0))
        quantidade_deposito = int(request.form.get('quantidade_deposito', 0))
        data_fabricacao = request.form.get('data_fabricacao')
        data_validade = request.form.get('data_validade')
        fabricante = request.form.get('fabricante')

        logger.info(f"Modal - Dados recebidos - Código: {codigo_produto}, Lote: {novo_lote}, Fabricante: {fabricante}")

        # Validações básicas
        if not codigo_produto or not codigo_produto.strip():
            return jsonify({'success': False, 'message': 'Código do produto é obrigatório.'}), 400

        if not novo_lote or not novo_lote.strip():
            return jsonify({'success': False, 'message': 'Número do lote é obrigatório.'}), 400

        if quantidade_balcao < 0 or quantidade_deposito < 0:
            return jsonify({'success': False, 'message': 'As quantidades não podem ser negativas.'}), 400

        # Buscar item modelo
        item_modelo = find_item(codigo_produto)

        if not item_modelo:
            return jsonify({'success': False, 'message': f'Produto com código {codigo_produto} não encontrado no sistema.'}), 404

        # Verificar se o fabricante do produto coincide com o informado
        if fabricante and item_modelo.get('FABRICANTE') != fabricante:
            return jsonify({'success': False, 'message': f'O produto {codigo_produto} não pertence ao fabricante {fabricante}.'}), 400

        # Verificar se já existe um lote com o mesmo código e número
        for existing_item in data_manager.INVENTORY_DATA:
            if (existing_item.get('CÓDIGO') == codigo_produto and 
                existing_item.get('LOTE') == novo_lote):
                return jsonify({'success': False, 'message': f'Já existe um lote {novo_lote} para o produto {codigo_produto}.'}), 400

        # Criar novo item
        novo_item = {
            'CÓDIGO': item_modelo.get('CÓDIGO'),
            'PRODUTO': item_modelo.get('PRODUTO'),
            'FABRICANTE': item_modelo.get('FABRICANTE'),
            'CONTROLE_LOTE': 'S',
            'LOTE': novo_lote,
            'ESTOQUE_SISTEMA': 0,
            'STATUS': 'Concluído',
            'ESTOQUE_BALCAO': quantidade_balcao,
            'ESTOQUE_DEPOSITO': quantidade_deposito,
            'INVENTARIO': quantidade_balcao + quantidade_deposito,
            'CONTADOR': session.get('user_full_name'),
            'DATA_FABRICACAO': data_fabricacao,
            'DATA_VALIDADE': data_validade,
            'CONTADOR_ORIGINAL': '',
            'HORARIO_RECONTAGEM_SOLICITADA': '',
            'GESTOR_RECONTAGEM': '',
            'CONFERENCIA': f'Lote adicionado via modal por {session.get("user_full_name")} em {datetime.now().strftime("%d/%m/%Y %H:%M")}'
        }

        # Tentar salvar o item
        if add_new_item(novo_item):
            success_msg = f'Novo lote {novo_lote} para o produto {novo_item["PRODUTO"]} adicionado com sucesso!'
            logger.info(f"Modal - Novo lote adicionado com sucesso: {codigo_produto} - {novo_lote}")
            
            response = jsonify({
                'success': True, 
                'message': success_msg,
                'data': {
                    'codigo': codigo_produto,
                    'lote': novo_lote,
                    'produto': novo_item["PRODUTO"],
                    'fabricante': novo_item["FABRICANTE"]
                }
            })
            response.headers['Content-Type'] = 'application/json'
            return response
        else:
            logger.error(f"Modal - Falha ao salvar novo lote: {codigo_produto} - {novo_lote}")
            return jsonify({'success': False, 'message': 'Erro ao salvar o novo lote no banco de dados.'}), 500

    except ValueError as ve:
        logger.error(f"Modal - Erro de validação: {ve}")
        return jsonify({'success': False, 'message': f'Erro de validação: {str(ve)}'}), 400
        
    except Exception as e:
        logger.error(f"Modal - Erro inesperado: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor ao processar a solicitação.'}), 500

@contador_bp.route('/api/produtos/<path:fabricante>')
@login_required(role="contador")
def get_produtos_por_fabricante(fabricante):
    """API para buscar produtos únicos de um fabricante específico."""
    try:
        # Decodificar o fabricante se necessário
        fabricante = unquote(fabricante)
        
        logger.info(f"Buscando produtos para fabricante: {fabricante}")
        
        # Buscar produtos únicos do fabricante
        produtos = []
        codigos_vistos = set()
        
        for item in data_manager.INVENTORY_DATA:
            if (str(item.get('FABRICANTE', '')) == fabricante and 
                item.get('CÓDIGO') not in codigos_vistos):
                produtos.append({
                    'codigo': item['CÓDIGO'],
                    'nome': item['PRODUTO']
                })
                codigos_vistos.add(item.get('CÓDIGO'))
        
        logger.info(f"Encontrados {len(produtos)} produtos únicos para {fabricante}")
        return jsonify(produtos)
        
    except Exception as e:
        logger.error(f"Erro ao buscar produtos do fabricante {fabricante}: {e}")
        return jsonify({'error': 'Erro interno do servidor'}), 500

@contador_bp.route('/atualizar_item_individual', methods=['POST'])
@login_required(role="contador")
def atualizar_item_individual():
    try:
        dados = request.get_json()
        codigo = dados.get('codigo')
        lote = dados.get('lote', '')
        estoque_balcao = int(dados.get('estoque_balcao', 0))
        estoque_deposito = int(dados.get('estoque_deposito', 0))
        item_encontrado = find_item(codigo, lote)
        if not item_encontrado:
            return jsonify({'success': False, 'message': 'Item não encontrado'})
        current_user = session.get('user_full_name')
        if (item_encontrado.get('STATUS') != 'Em Andamento' or item_encontrado.get('CONTADOR') != current_user):
            return jsonify({'success': False, 'message': 'Sem permissão para editar este item'})
        updates = {'ESTOQUE_BALCAO': estoque_balcao, 'ESTOQUE_DEPOSITO': estoque_deposito, 'INVENTARIO': estoque_balcao + estoque_deposito}
        update_item(codigo, lote, updates)
        return jsonify({'success': True, 'message': 'Item atualizado com sucesso', 'nova_soma': estoque_balcao + estoque_deposito})
    except Exception as e:
        logger.error(f"Erro ao atualizar item individual: {e}")
        return jsonify({'success': False, 'message': 'Erro interno do servidor'})

@contador_bp.route('/dashboard')
@login_required(role="contador")
def dashboard():
    fab_status = {}
    recontagens_pendentes = []
    if data_manager.INVENTORY_DATA:
        for item in data_manager.INVENTORY_DATA:
            if item.get('STATUS') == 'Recontagem':
                contador_original = item.get('CONTADOR_ORIGINAL', '')
                is_invalid_recount = not (contador_original and str(contador_original).strip() and str(contador_original).lower() not in ['nan', 'none', 'não informado'])
                if is_invalid_recount:
                    updates = {'STATUS': 'Pendente', 'CONTADOR_ORIGINAL': '', 'HORARIO_RECONTAGEM_SOLICITADA': '', 'GESTOR_RECONTAGEM': '', 'CONFERENCIA': ''}
                    update_item(item.get('CÓDIGO'), item.get('LOTE'), updates)
        recontagens_pendentes = [item for item in data_manager.INVENTORY_DATA if item.get('STATUS') == 'Recontagem']
        fabricantes_df = pd.DataFrame(data_manager.INVENTORY_DATA)
        if 'FABRICANTE' in fabricantes_df.columns:
            fabricantes_validos = [str(f) for f in fabricantes_df['FABRICANTE'].astype(str).dropna().unique() if str(f).strip()]
            fabricantes = sorted(list(set(fabricantes_validos)))
            for fab in fabricantes:
                items_fab = [i for i in data_manager.INVENTORY_DATA if str(i.get('FABRICANTE','')) == fab and i.get('STATUS') != 'Recontagem']
                if not items_fab: continue
                if any(str(i.get('STATUS')) == 'Em Andamento' for i in items_fab):
                    user = next((str(i.get('CONTADOR','')) for i in items_fab if str(i.get('STATUS')) == 'Em Andamento'), '')
                    fab_status[fab] = {'status': 'Em Andamento', 'user': user}
                elif all(str(i.get('STATUS')) == 'Concluído' for i in items_fab):
                    user = next((str(i.get('CONTADOR','')) for i in items_fab if str(i.get('STATUS')) == 'Concluído'), '')
                    fab_status[fab] = {'status': 'Concluído', 'user': user}
                else:
                    fab_status[fab] = {'status': 'Pendente', 'user': ''}
    return render_template('contador_dashboard.html', fabricantes_status=fab_status, recontagens=recontagens_pendentes)

@contador_bp.route('/escolher_ordem/<path:fabricante_encoded>')
@login_required("contador")
def escolher_ordem(fabricante_encoded):
    fabricante = unquote(fabricante_encoded)
    current_user = session.get('user_full_name')

    # --- Validation 1: Supplier Availability Check ---
    # Check if the manufacturer is already "Em Andamento" by another user
    # or if it's already "Concluído"
    items_for_manufacturer = [item for item in data_manager.INVENTORY_DATA if str(item.get('FABRICANTE','')) == fabricante]
    
    if not items_for_manufacturer:
        flash(f"Nenhum item encontrado para o fabricante '{fabricante}'.", 'danger')
        return redirect(url_for('contador.dashboard'))

    is_in_progress_by_other = False
    is_completed = True
    for item in items_for_manufacturer:
        if item.get('STATUS') == 'Em Andamento' and item.get('CONTADOR') != current_user:
            flash(f"O fabricante '{fabricante}' já está sendo contado por outro usuário ({item.get('CONTADOR')}).", 'warning')
            return redirect(url_for('contador.dashboard'))
        if item.get('STATUS') != 'Concluído':
            is_completed = False
    
    if is_completed:
        # If all items for this manufacturer are 'Concluído', prevent re-starting from here
        # Unless a specific re-count task is initiated for this manufacturer, this path is for new counts
        # This prevents accidental re-counts of completed manufacturers from the dashboard
        flash(f"A contagem para o fabricante '{fabricante}' já foi concluída. Inicie uma nova contagem a partir de um item de recontagem, se necessário.", 'info')
        return redirect(url_for('contador.dashboard'))

    return render_template('contador/escolher_ordem.html', fabricante=fabricante)

@contador_bp.route('/iniciar_contagem', methods=['POST'])
@login_required("contador")
def iniciar_contagem():
    fabricante = request.form.get('fabricante')
    ordem = request.form.get('ordem')
    fabricante_encoded = quote(fabricante, safe='')
    current_user = session.get('user_full_name')

    # Re-validate supplier status to prevent race conditions or direct POST attacks
    items_for_manufacturer = [item for item in data_manager.INVENTORY_DATA if str(item.get('FABRICANTE','')) == fabricante]
    
    if not items_for_manufacturer:
        flash(f"Erro: Fabricante '{fabricante}' não encontrado para iniciar contagem.", 'danger')
        return redirect(url_for('contador.dashboard'))

    for item in items_for_manufacturer:
        if item.get('STATUS') == 'Em Andamento' and item.get('CONTADOR') != current_user:
            flash(f"O fabricante '{fabricante}' está sendo contado por outro usuário ({item.get('CONTADOR')}). Não é possível iniciar.", 'warning')
            return redirect(url_for('contador.dashboard'))
        if item.get('STATUS') == 'Concluído':
            # If even one item is concluded, we might want to prevent starting a full new count
            # This depends on business logic. If it's a re-count, it should come from a specific re-count flow.
            # For this context, we assume if it's already concluded, it shouldn't be started as a new count.
            flash(f"A contagem para o fabricante '{fabricante}' já foi concluída.", 'info')
            return redirect(url_for('contador.dashboard'))

    # --- Validation 2: Order Selection and State Check ---
    if ordem == 'balcao':
        # If 'deposito' data already exists but 'balcao' doesn't, force 'balcao' first
        if tem_dados_deposito(fabricante) and not tem_dados_balcao(fabricante):
            flash("Você já informou dados do depósito. Por favor, comece ou continue a contagem pelo balcão.", "warning")
            return redirect(url_for('contador.contar_balcao', fabricante_encoded=fabricante_encoded))
        return redirect(url_for('contador.contar_balcao', fabricante_encoded=fabricante_encoded))
    elif ordem == 'deposito':
        # If 'balcao' data already exists but 'deposito' doesn't, force 'deposito' first
        if tem_dados_balcao(fabricante) and not tem_dados_deposito(fabricante):
            flash("Você já informou dados do balcão. Por favor, comece ou continue a contagem pelo depósito.", "warning")
            return redirect(url_for('contador.contar_deposito', fabricante_encoded=fabricante_encoded))
        return redirect(url_for('contador.contar_deposito', fabricante_encoded=fabricante_encoded))
    else:
        flash('Selecione uma ordem válida para iniciar a contagem!', 'danger')
        return redirect(url_for('contador.escolher_ordem', fabricante_encoded=fabricante_encoded))


@contador_bp.route('/contar_balcao/<path:fabricante_encoded>')
@login_required(role="contador")
def contar_balcao(fabricante_encoded):
    # Decodificar o nome do fabricante
    fabricante = unquote(fabricante_encoded)
    
    current_user = session.get('user_full_name')
    
    # Resto da função continua igual...
    items_do_fabricante = [item for item in data_manager.INVENTORY_DATA if str(item.get('FABRICANTE','')) == fabricante]
    for item in items_do_fabricante:
        if item.get('STATUS') in ['Pendente', 'Recontagem']:
            updates = {'STATUS': 'Em Andamento', 'CONTADOR': current_user}
            update_item(item.get('CÓDIGO'), item.get('LOTE'), updates)
    
    produtos_fabricante = [item for item in data_manager.INVENTORY_DATA if str(item.get('FABRICANTE','')) == fabricante and item.get('STATUS') != 'Recontagem']
    return render_template('contar_balcao.html', produtos=produtos_fabricante, fabricante=fabricante)

@contador_bp.route('/salvar_balcao', methods=['POST'])
@login_required("contador")
def salvar_balcao():
    fabricante = request.form.get('fabricante')
    for key, value in request.form.items():
        if key.startswith('balcao_'):
            codigo, lote = key.replace('balcao_', '').split('|')
            updates = {'ESTOQUE_BALCAO': int(value) if value and value.strip() else 0}
            update_item(codigo, lote, updates)
    fabricante_encoded = quote(fabricante, safe='')
    if tem_dados_deposito(fabricante):
        return redirect(url_for('contador.confirmar', fabricante_encoded=fabricante_encoded))
    else:
        return redirect(url_for('contador.contar_deposito', fabricante_encoded=fabricante_encoded))

@contador_bp.route('/contar_deposito/<path:fabricante_encoded>')
@login_required(role="contador")
def contar_deposito(fabricante_encoded):
    # Decodificar o nome do fabricante
    fabricante = unquote(fabricante_encoded)
    
    current_user = session.get('user_full_name')
    
    # O resto da função é idêntico à contar_balcao...
    items_do_fabricante = [item for item in data_manager.INVENTORY_DATA if str(item.get('FABRICANTE','')) == fabricante]
    for item in items_do_fabricante:
        if item.get('STATUS') in ['Pendente', 'Recontagem']:
            updates = {'STATUS': 'Em Andamento', 'CONTADOR': current_user}
            update_item(item.get('CÓDIGO'), item.get('LOTE'), updates)

    produtos_fabricante = [item for item in data_manager.INVENTORY_DATA if str(item.get('FABRICANTE','')) == fabricante and item.get('STATUS') != 'Recontagem']
    return render_template('contar_deposito.html', produtos=produtos_fabricante, fabricante=fabricante)

@contador_bp.route('/salvar_deposito', methods=['POST'])
@login_required("contador")
def salvar_deposito():
    fabricante = request.form.get('fabricante')
    for key, value in request.form.items():
        if key.startswith('deposito_'):
            codigo, lote = key.replace('deposito_', '').split('|')
            updates = {'ESTOQUE_DEPOSITO': int(value) if value and value.strip() else 0}
            update_item(codigo, lote, updates)
    fabricante_encoded = quote(fabricante, safe='')
    if tem_dados_balcao(fabricante):
        return redirect(url_for('contador.confirmar', fabricante_encoded=fabricante_encoded))
    else:
        return redirect(url_for('contador.contar_balcao', fabricante_encoded=fabricante_encoded))

@contador_bp.route('/confirmar/<path:fabricante_encoded>')
@login_required(role="contador")
def confirmar(fabricante_encoded):
    fabricante = unquote(fabricante_encoded)
    produtos_fabricante = [item for item in data_manager.INVENTORY_DATA if str(item.get('FABRICANTE','')) == fabricante and item.get('STATUS') == 'Em Andamento' and item.get('CONTADOR') == session.get('user_full_name')]
    for item in produtos_fabricante:
        balcao = item.get('ESTOQUE_BALCAO')
        deposito = item.get('ESTOQUE_DEPOSITO')
        # Garante que valores nulos (None) sejam tratados como 0 para a soma
        item['SOMA'] = (balcao if balcao is not None else 0) + (deposito if deposito is not None else 0)
    return render_template('confirmar.html', produtos=produtos_fabricante, fabricante=fabricante)

@contador_bp.route('/cancelar/<path:fabricante_encoded>')
@login_required(role="contador")
def cancelar_contagem(fabricante_encoded):
    fabricante = unquote(fabricante_encoded)
    current_user = session.get('user_full_name')
    flash(f"Contagem de '{fabricante}' pausada. Você pode retomá-la a qualquer momento.", "info")
    return redirect(url_for('contador.dashboard'))

@contador_bp.route('/recontar_item/<codigo>', endpoint='recontar_item_sem_lote')
@contador_bp.route('/recontar_item/<codigo>/', endpoint='recontar_item_sem_lote_barra')
@contador_bp.route('/recontar_item/<codigo>/<path:lote_encoded>', endpoint='recontar_item_com_lote')
@login_required(role="contador")
def recontar_item(codigo, lote_encoded=''):
    lote = unquote(lote_encoded) if lote_encoded else ''
    lote_comparacao = str(lote).strip() if lote and str(lote).lower() != 'nan' else ''
    item_para_recontar = find_item(codigo, lote_comparacao)
    if not item_para_recontar:
        flash(f"Item para recontagem não encontrado (Cód: {codigo}, Lote: {lote_comparacao}).", "danger")
        return redirect(url_for('contador.dashboard'))
    if (item_para_recontar.get('STATUS') == 'Recontagem' or (item_para_recontar.get('STATUS') == 'Em Andamento' and item_para_recontar.get('CONTADOR') == session.get('user_full_name'))):
        updates = {'STATUS': 'Em Andamento', 'CONTADOR': session.get('user_full_name')}
        update_item(codigo, lote_comparacao, updates)
        item_para_recontar.update(updates)
        return render_template('recontar_item.html', item=item_para_recontar)
    else:
        flash(f"Este item ('{item_para_recontar.get('PRODUTO')}') não está disponível para recontagem por você.", "warning")
        return redirect(url_for('contador.dashboard'))

@contador_bp.route('/salvar_recontagem', methods=['POST'])
@login_required(role="contador")
def salvar_recontagem():
    try:
        codigo = request.form.get('codigo', '').strip()
        lote = request.form.get('lote', '').strip()
        if not codigo:
            flash("Código do produto é obrigatório.", "danger")
            return redirect(url_for('contador.dashboard'))
        estoque_balcao = int(request.form.get('estoque_balcao', 0))
        estoque_deposito = int(request.form.get('estoque_deposito', 0))
        if estoque_balcao < 0 or estoque_deposito < 0:
            flash("Valores de estoque não podem ser negativos.", "danger")
            return redirect(url_for('contador.dashboard'))
        item_recontado = find_item(codigo, lote)
        if not item_recontado:
            flash("Ocorreu um erro ao salvar a recontagem. Item não encontrado.", "danger")
            return redirect(url_for('contador.dashboard'))
        if item_recontado.get('STATUS') == 'Em Andamento' and item_recontado.get('CONTADOR') == session.get('user_full_name'):
            updates = {'ESTOQUE_BALCAO': estoque_balcao, 'ESTOQUE_DEPOSITO': estoque_deposito, 'INVENTARIO': estoque_balcao + estoque_deposito, 'STATUS': 'Concluído'}
            if update_item(codigo, lote, updates):
                flash(f"Recontagem do produto {item_recontado['PRODUTO']} salva com sucesso!", "success")
            else:
                flash("Erro ao salvar a recontagem no banco de dados.", "danger")
        else:
            flash("Não foi possível salvar. O item não estava em recontagem por você.", "warning")
        return redirect(url_for('contador.dashboard'))
    except ValueError:
        flash("Valores de estoque devem ser números válidos.", "danger")
        return redirect(url_for('contador.dashboard'))
    except Exception as e:
        logger.error(f"Erro ao salvar recontagem: {e}")
        flash("Erro interno ao salvar recontagem.", "danger")
        return redirect(url_for('contador.dashboard'))

@contador_bp.route('/cancelar_recontagem_item/<codigo>', endpoint='cancelar_recontagem_item_sem_lote')
@contador_bp.route('/cancelar_recontagem_item/<codigo>/', endpoint='cancelar_recontagem_item_sem_lote_barra')
@contador_bp.route('/cancelar_recontagem_item/<codigo>/<path:lote_encoded>', endpoint='cancelar_recontagem_item_com_lote')
@login_required(role="contador")
def cancelar_recontagem_item(codigo, lote_encoded=''):
    """
    COMPORTAMENTO CORRIGIDO: Apenas redireciona para o dashboard, sem alterar o status do item.
    O item continuará 'Em Andamento' com o usuário atual.
    """
    lote = unquote(lote_encoded) if lote_encoded else ''
    item = find_item(codigo, lote)
    produto_nome = item.get('PRODUTO', 'Item') if item else 'Item'

    # Nenhuma alteração é feita no banco de dados. Apenas redirecionamos.
    flash(f"Recontagem de '{produto_nome}' pausada. A tarefa continua em andamento com você.", "info")
    return redirect(url_for('contador.dashboard'))

@contador_bp.route('/salvar_item_parcial', methods=['POST'])
@login_required(role="contador")
def salvar_item_parcial():
    """Recebe e salva a contagem de um único item via AJAX."""
    try:
        dados = request.get_json()
        codigo = dados.get('codigo')
        lote = dados.get('lote', '')
        # tipo_estoque será 'ESTOQUE_BALCAO' ou 'ESTOQUE_DEPOSITO'
        tipo_estoque = dados.get('tipo_estoque')
        valor = int(dados.get('valor', 0))

        if not all([codigo, tipo_estoque]):
            return jsonify({'success': False, 'message': 'Dados incompletos'}), 400

        # O dicionário 'updates' contém a coluna a ser atualizada e o novo valor
        updates = {
            tipo_estoque: valor
        }
        
        if update_item(codigo, lote, updates):
            return jsonify({'success': True, 'message': 'Salvo!'})
        else:
            return jsonify({'success': False, 'message': 'Erro ao salvar'}), 500

    except Exception as e:
        logger.error(f"Erro ao salvar contagem parcial: {e}")
        return jsonify({'success': False, 'message': 'Erro interno'}), 500
@contador_bp.route('/buscar_produto', methods=['GET', 'POST'])
@login_required(role="contador")
def buscar_produto():
    query = request.args.get('q', '').strip().lower()
    resultados = []
    if query:
        resultados = [item for item in data_manager.INVENTORY_DATA
                      if query in str(item.get('PRODUTO', '')).lower() or
                         query in str(item.get('CÓDIGO', '')).lower()]
    return render_template('contador/buscar_produto.html', resultados=resultados, query=query)



@contador_bp.route('/salvar_final/<path:fabricante_encoded>', methods=['POST'])
@login_required(role="contador")
def salvar_final(fabricante_encoded):
    fabricante = unquote(fabricante_encoded)
    contador_nome = session.get('user_full_name', 'Não identificado')
    alteracoes_feitas = False
    for key, value in request.form.items():
        if key.startswith('confirm_'):
            codigo, lote = key.replace('confirm_', '').split('|')
            item = find_item(codigo, lote)
            if item and item.get('STATUS') == 'Em Andamento' and item.get('CONTADOR') == contador_nome:
                updates = {
                    'INVENTARIO': int(value), 'STATUS': 'Concluído', 'CONTADOR_ORIGINAL': '',
                    'HORARIO_RECONTAGEM_SOLICITADA': '', 'GESTOR_RECONTAGEM': '', 'CONFERENCIA': ''
                }
                if update_item(codigo, lote, updates):
                    alteracoes_feitas = True
    if alteracoes_feitas:
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        NOTIFICATIONS.append({'user': contador_nome, 'manufacturer': fabricante, 'timestamp': timestamp})
    return redirect(url_for('contador.dashboard'))
