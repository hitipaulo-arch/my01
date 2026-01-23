"""Rotas de Ordens de Serviço."""

import datetime
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from appmodules.models import OrdemServico, ValidadorOS
from appmodules.services import NotificationService
from appmodules.utils import admin_required

logger = logging.getLogger(__name__)

os_bp = Blueprint('os', __name__)


@os_bp.route('/')
def homepage():
    """Exibe a página inicial com o formulário."""
    return render_template('index.html')


@os_bp.route('/enviar', methods=['POST'])
def criar_os():
    """Recebe dados do formulário e cria nova OS."""
    sheets_service = current_app.config.get('sheets_service')
    if not sheets_service:
        logger.error("Sheets service não inicializado")
        return render_template('erro.html', mensagem="Serviço de planilhas indisponível"), 503
    
    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        logger.error(f"Tentativa de envio sem sheet disponível: {erro_msg}")
        return render_template('erro.html', mensagem=erro_msg), 503
    
    # Valida dados
    validacao = ValidadorOS.validar_formulario(request.form)
    if not validacao.valido:
        logger.warning(f"Validação falhou: {validacao.erros}")
        return render_template('index.html', erros=validacao.erros), 400
    
    try:
        # Obtém próximo ID
        numero_pedido = sheets_service.get_next_id()
        
        # Cria OS
        os_data = OrdemServico.from_form(request.form, numero_pedido)
        row_data = os_data.to_sheet_row()
        
        # Salva no Sheets
        if not sheets_service.add_os(row_data):
            return render_template('erro.html', 
                mensagem="Erro ao salvar OS. Por favor, tente novamente."), 500
        
        logger.info(f"Nova OS (Pedido #{numero_pedido}) adicionada por: {os_data.solicitante}")
        
        # Envia notificações (não bloqueia)
        try:
            NotificationService.notificar_nova_os(
                numero_pedido=str(numero_pedido),
                solicitante=os_data.solicitante,
                setor=os_data.setor,
                prioridade=os_data.prioridade,
                descricao=os_data.descricao,
                equipamento=os_data.equipamento,
                timestamp=os_data.timestamp,
                info_adicional=os_data.info_adicional
            )
        except Exception as e:
            logger.error(f"Erro ao notificar (OS #{numero_pedido}): {e}")
        
        return render_template('sucesso.html', 
            nome=os_data.solicitante, os_numero=numero_pedido)
    
    except Exception as e:
        logger.error(f"Erro ao criar OS: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao salvar seu requerimento: {e}"), 500


@os_bp.route('/gerenciar')
@admin_required
def gerenciar():
    """Exibe página de gerenciamento de OS."""
    sheets_service = current_app.config.get('sheets_service')
    if not sheets_service:
        return render_template('gerenciar.html', chamados=[], 
            current_sort='Carimbo de data/hora', current_order='desc',
            mensagem_erro="Serviço de planilhas indisponível"), 503
    
    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        return render_template('gerenciar.html', chamados=[], 
            current_sort='Carimbo de data/hora', current_order='desc',
            mensagem_erro=erro_msg)
    
    sort_by = request.args.get('sort_by', 'Carimbo de data/hora')
    order = request.args.get('order', 'desc')
    
    try:
        chamados = sheets_service.get_all_os()
        
        # Aplica ordenação
        def sort_key(item):
            try:
                if sort_by == 'Carimbo de data/hora':
                    return datetime.datetime.strptime(item.get(sort_by, ''), '%d/%m/%Y %H:%M:%S')
                return item.get(sort_by, '').lower()
            except ValueError:
                return datetime.datetime.min
        
        chamados_ordenados = sorted(chamados, key=sort_key, reverse=(order == 'desc'))
        
        return render_template(
            'gerenciar.html',
            chamados=chamados_ordenados,
            current_sort=sort_by,
            current_order=order
        )
    except Exception as e:
        logger.error(f"Erro ao carregar OS: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao processar dados: {e}"), 500


@os_bp.route('/atualizar_chamado', methods=['POST'])
@admin_required
def atualizar_chamado():
    """Atualiza uma OS."""
    sheets_service = current_app.config.get('sheets_service')
    if not sheets_service:
        return render_template('erro.html', mensagem="Serviço de planilhas indisponível"), 503
    
    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        return render_template('erro.html', mensagem=erro_msg), 503
    
    try:
        # Debug: log dos dados recebidos
        logger.info(f"POST /atualizar_chamado - form data: {dict(request.form)}")
        
        validacao = ValidadorOS.validar_atualizacao(request.form)
        if not validacao.valido:
            logger.warning(f"Validação falhou: {validacao.erros}")
            return render_template('erro.html', mensagem=' '.join(validacao.erros)), 400

        solicitante = request.form.get('nome_solicitante', '')
        setor = request.form.get('setor', '')
        data_solicitacao = request.form.get('data_solicitacao', '')
        descricao = request.form.get('descricao', '')
        equipamento = request.form.get('equipamento', '')
        prioridade = request.form.get('prioridade', '')
        info_adicional = request.form.get('info_adicional', '')
        
        status_os = request.form.get('status_os', '').strip()
        servico_realizado = request.form.get('servico_realizado', '')
        horario_inicio = request.form.get('horario_inicio', '')
        horario_termino = request.form.get('horario_termino', '')
        horas_trabalhadas = request.form.get('horas_trabalhadas', '')
        
        try:
            row_id = int(request.form.get('row_id', '').strip())
        except (TypeError, ValueError):
            return render_template('erro.html', mensagem="ID da linha inválido"), 400
        
        # Busca timestamp e ID originais
        os_list = sheets_service.get_all_os()
        os_original = None
        for os_item in os_list:
            if os_item.get('row_id') == row_id:
                os_original = os_item
                break
        
        if not os_original:
            return render_template('erro.html', 
                mensagem="OS não encontrada"), 404
        
        linha_atualizada = [
            os_original.get('ID', ''),
            os_original.get('Carimbo de data/hora', ''),
            solicitante,
            setor,
            data_solicitacao,
            descricao,
            equipamento,
            prioridade,
            status_os,
            info_adicional,
            servico_realizado,
            horario_inicio,
            horario_termino,
            horas_trabalhadas
        ]
        
        if not sheets_service.update_os(row_id, linha_atualizada):
            return render_template('erro.html', 
                mensagem="Erro ao atualizar OS"), 500
        
        logger.info(f"OS (linha {row_id}) atualizada com status: {status_os}")
        flash('OS atualizada com sucesso!', 'success')
        
        return redirect(url_for('os.gerenciar'))
    
    except Exception as e:
        logger.error(f"Erro ao atualizar OS: {e}", exc_info=True)
        return render_template('erro.html', 
            mensagem=f"Erro ao atualizar: {e}"), 500


@os_bp.route('/consultar', methods=['GET', 'POST'])
def consultar_pedido():
    """Página pública para consultar status de OS."""
    sheets_service = current_app.config.get('sheets_service')
    if not sheets_service:
        return render_template('consultar.html', 
            resultado={'erro': "Serviço de planilhas indisponível"}, pedido_buscado=None)
    
    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        return render_template('consultar.html', 
            resultado={'erro': erro_msg}, pedido_buscado=None)
    
    resultado = None
    pedido_buscado = None
    
    if request.method == 'POST':
        pedido_buscado = request.form.get('numero_pedido')
    elif request.method == 'GET' and 'numero_pedido' in request.args:
        pedido_buscado = request.args.get('numero_pedido')
    
    if pedido_buscado:
        try:
            os_data = sheets_service.get_os_by_id(pedido_buscado)
            
            if os_data:
                resultado = {
                    'id': os_data['id'],
                    'data': os_data['timestamp'],
                    'descricao': os_data['descricao'],
                    'status': os_data['status']
                }
            else:
                resultado = {'erro': f"Pedido número '{pedido_buscado}' não encontrado."}
        
        except Exception as e:
            logger.error(f"Erro ao buscar pedido: {e}")
            resultado = {'erro': 'Ocorreu um erro ao consultar o pedido.'}
    
    return render_template('consultar.html', resultado=resultado, pedido_buscado=pedido_buscado)


@os_bp.route('/health')
def health():
    """Endpoint de healthcheck."""
    sheets_service = current_app.config.get('sheets_service')
    if not sheets_service:
        return {
            'status': 'degraded',
            'sheets_connected': False,
            'timestamp': datetime.datetime.now().isoformat(),
            'reason': 'sheets_service not initialized'
        }, 503
    
    disponivel, _ = sheets_service.is_available()
    
    return {
        'status': 'healthy' if disponivel else 'degraded',
        'sheets_connected': disponivel,
        'timestamp': datetime.datetime.now().isoformat()
    }, 200
