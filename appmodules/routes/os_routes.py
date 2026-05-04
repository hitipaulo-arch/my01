"""Rotas de Ordens de Serviço."""

import datetime
import io
import logging
from pathlib import Path
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, send_file
import qrcode
from werkzeug.utils import secure_filename
from appmodules.models import OrdemServico, ValidadorOS
from appmodules.services import NotificationService
from appmodules.utils import admin_required

logger = logging.getLogger(__name__)

ALLOWED_UPLOAD_EXTENSIONS = {
    'pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'webp', 'xlsx', 'xls'
}
MAX_UPLOAD_SIZE_BYTES = 10 * 1024 * 1024

os_bp = Blueprint('os', __name__)


def _primeiro_valor_disponivel(data: dict, *chaves: str, default: str = '') -> str:
    """Obtém o primeiro valor não vazio a partir de várias chaves possíveis."""
    for chave in chaves:
        if chave in data and str(data.get(chave, '')).strip():
            return str(data.get(chave, '')).strip()
    return default


def _valor_form_ou_original(form_value: str, original_data: dict, *chaves: str, default: str = '') -> str:
    """Usa o valor do formulário quando presente; caso contrário, preserva o valor original."""
    if str(form_value or '').strip():
        return str(form_value).strip()
    return _primeiro_valor_disponivel(original_data, *chaves, default=default)


def _extensao_permitida(filename: str) -> bool:
    """Valida se a extensão do arquivo está na lista permitida."""
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in ALLOWED_UPLOAD_EXTENSIONS


@os_bp.route('/')
def homepage():
    """Exibe a página inicial com o formulário."""
    return render_template('index.html')


def _gerar_qr_buffer(formato: str = 'PNG'):
    """Gera o QR code do formulário em memória no formato solicitado."""
    formulario_url = url_for('os.homepage', _external=True)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(formulario_url)
    qr.make(fit=True)

    img = qr.make_image(fill_color='black', back_color='white')
    buffer = io.BytesIO()
    img.save(buffer, format=formato)
    buffer.seek(0)
    return buffer



@os_bp.route('/qr-formulario.png')
def qr_formulario_png():
    """Gera um QR code apontando para a página do formulário em PNG."""
    buffer = _gerar_qr_buffer('PNG')
    return send_file(buffer, mimetype='image/png', as_attachment=False, download_name='qr-formulario.png')


@os_bp.route('/qr-formulario.pdf')
def qr_formulario_pdf():
    """Gera um QR code apontando para a página do formulário em PDF."""
    buffer = _gerar_qr_buffer('PDF')
    return send_file(buffer, mimetype='application/pdf', as_attachment=False, download_name='qr-formulario.pdf')


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
        return render_template(
            'index.html',
            erros=validacao.erros,
            form_data=request.form
        ), 400
    
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
            NotificationService.enqueue_notificar_nova_os(
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


@os_bp.route('/os-abertas')
def os_abertas():
    """Exibe a lista pública de OS abertas e em andamento."""

    def _parse_datetime_maybe_time(valor, base_dt):
        texto = str(valor or '').strip()
        if not texto:
            return None

        # Aceita somente hora (HH:MM ou HH:MM:SS) combinando com a data base.
        if ':' in texto and '/' not in texto:
            if not isinstance(base_dt, datetime.datetime):
                return None
            for fmt in ('%H:%M:%S', '%H:%M'):
                try:
                    t = datetime.datetime.strptime(texto, fmt).time()
                    return datetime.datetime.combine(base_dt.date(), t)
                except ValueError:
                    continue

        for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M'):
            try:
                return datetime.datetime.strptime(texto, fmt)
            except ValueError:
                continue

        return None

    empty_metrics = {
        'percentual_concluidas': '0,0%',
        'tempo_medio_conclusao': 'N/A',
    }

    sheets_service = current_app.config.get('sheets_service')
    if not sheets_service:
        return render_template(
            'os_abertas.html',
            chamados=[],
            total_chamados=0,
            mensagem_erro='Serviço de planilhas indisponível',
            **empty_metrics,
        ), 503

    disponivel, erro_msg = sheets_service.is_available()
    if not disponivel:
        return render_template(
            'os_abertas.html',
            chamados=[],
            total_chamados=0,
            mensagem_erro=erro_msg,
            **empty_metrics,
        ), 503

    try:
        os_list = sheets_service.get_all_os(use_cache=True)
        
        # Otimização: filtrar OS abertas em memória ao invés de chamar get_open_os()
        # que internamente chama get_all_os() novamente (evita N+1 query pattern)
        abertos_status = {'aberto', 'em andamento'}
        chamados_publicos = [
            item for item in os_list
            if str(item.get('Status da OS', '')).strip().lower() in abertos_status
        ]

        total_os = len(os_list)
        finalizadas_status = {'finalizada', 'concluido', 'concluído'}
        finalizadas = [
            item for item in os_list
            if str(item.get('Status da OS', '')).strip().lower() in finalizadas_status
        ]

        percentual_concluidas = '0,0%'
        if total_os > 0:
            percentual = (len(finalizadas) / total_os) * 100
            percentual_concluidas = f"{percentual:.1f}%".replace('.', ',')

        duracoes_horas = []
        for item in finalizadas:
            ts_base = _parse_datetime_maybe_time(item.get('Carimbo de data/hora', ''), None)
            inicio_txt = item.get('Horario de Andamento', '') or item.get('Horario de Inicio', '')
            termino_txt = item.get('Horario de Término', '')
            dt_inicio = _parse_datetime_maybe_time(inicio_txt, ts_base)
            dt_fim = _parse_datetime_maybe_time(termino_txt, ts_base)
            if not dt_inicio or not dt_fim:
                continue

            delta_h = (dt_fim - dt_inicio).total_seconds() / 3600
            if delta_h > 0:
                duracoes_horas.append(delta_h)

        tempo_medio_conclusao = 'N/A'
        if duracoes_horas:
            media_h = sum(duracoes_horas) / len(duracoes_horas)
            if media_h < 1:
                tempo_medio_conclusao = f"{int(media_h * 60)} min"
            else:
                tempo_medio_conclusao = f"{media_h:.1f} h".replace('.', ',')

        def sort_key(item):
            try:
                return datetime.datetime.strptime(
                    str(item.get('Carimbo de data/hora', '')).strip(),
                    '%d/%m/%Y %H:%M:%S'
                )
            except ValueError:
                return datetime.datetime.min

        chamados_publicos = sorted(chamados_publicos, key=sort_key, reverse=True)

        return render_template(
            'os_abertas.html',
            chamados=chamados_publicos,
            total_chamados=len(chamados_publicos),
            percentual_concluidas=percentual_concluidas,
            tempo_medio_conclusao=tempo_medio_conclusao,
        )
    except Exception as e:
        logger.error(f"Erro ao carregar OS abertas: {e}")
        return render_template(
            'os_abertas.html',
            chamados=[],
            total_chamados=0,
            mensagem_erro=f"Erro ao processar dados: {e}",
            **empty_metrics,
        ), 500


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

        try:
            row_id = int(request.form.get('row_id', '').strip())
        except (TypeError, ValueError):
            return render_template('erro.html', mensagem="ID da linha inválido"), 400

        # Busca dados originais da linha
        os_original = sheets_service.get_os_by_row_id(row_id)

        if not os_original:
            return render_template('erro.html', 
                mensagem="OS não encontrada"), 404

        solicitante = _valor_form_ou_original(
            request.form.get('nome_solicitante', ''),
            os_original,
            'Nome do solicitante',
            default=''
        )
        setor = _valor_form_ou_original(
            request.form.get('setor', ''),
            os_original,
            'Setor em que será realizado o serviço',
            'Setor',
            default=''
        )
        data_solicitacao = _valor_form_ou_original(
            request.form.get('data_solicitacao', ''),
            os_original,
            'Data da Solicitação',
            default=''
        )
        descricao = _valor_form_ou_original(
            request.form.get('descricao', ''),
            os_original,
            'Descrição do Problema ou Serviço Solicitado',
            'Descrição',
            default=''
        )
        equipamento = _valor_form_ou_original(
            request.form.get('equipamento', ''),
            os_original,
            'Equipamento ou Local afetado',
            'Equipamento/Local',
            default=''
        )
        prioridade = _valor_form_ou_original(
            request.form.get('prioridade', ''),
            os_original,
            'Nível de prioridade',
            'Prioridade',
            default=''
        )
        info_adicional = _valor_form_ou_original(
            request.form.get('info_adicional', ''),
            os_original,
            'Informações adicionais (Opcional)',
            'Informações adicionais',
            default=''
        )
        whatsapp_form = request.form.get('whatsapp_solicitante', '').strip()
        
        status_os = _valor_form_ou_original(
            request.form.get('status_os', ''),
            os_original,
            'Status da OS',
            default=''
        )
        servico_realizado = _valor_form_ou_original(
            request.form.get('servico_realizado', ''),
            os_original,
            'Serviço realizado',
            default=''
        )
        horario_inicio = _valor_form_ou_original(
            request.form.get('horario_inicio', ''),
            os_original,
            'Horario de Inicio',
            default=''
        )
        horario_andamento = _valor_form_ou_original(
            request.form.get('horario_andamento', ''),
            os_original,
            'Horario de Andamento',
            default=''
        )
        horario_termino = _valor_form_ou_original(
            request.form.get('horario_termino', ''),
            os_original,
            'Horario de Término',
            default=''
        )
        horas_trabalhadas = _valor_form_ou_original(
            request.form.get('horas_trabalhadas', ''),
            os_original,
            'Horas trabalhadas',
            default=''
        )

        status_original = str(os_original.get('Status da OS', '')).strip()
        numero_pedido = _primeiro_valor_disponivel(os_original, 'ID', '/', default=str(row_id))
        whatsapp_solicitante = whatsapp_form or _primeiro_valor_disponivel(
            os_original,
            'WhatsApp do solicitante',
            'WhatsApp',
            'Whatsapp do solicitante',
            'Whatsapp'
        )

        agora = datetime.datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        # Ao entrar em andamento, registra horário automaticamente (se vazio).
        if status_os == 'Em Andamento' and not horario_andamento:
            horario_andamento = agora

        # Ao finalizar, registra término automaticamente (se vazio).
        if status_os == 'Finalizada' and not horario_termino:
            horario_termino = agora

        # Se foi finalizada sem andamento preenchido, registra andamento também.
        if status_os == 'Finalizada' and not horario_andamento:
            horario_andamento = agora
        
        linha_atualizada = [
            numero_pedido,
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
            horario_andamento,
            horario_termino,
            horas_trabalhadas,
            whatsapp_solicitante
        ]
        
        if not sheets_service.update_os(row_id, linha_atualizada):
            return render_template('erro.html', 
                mensagem="Erro ao atualizar OS"), 500
        
        logger.info(f"OS (linha {row_id}) atualizada com status: {status_os}")

        status_original_norm = status_original.strip().lower()
        status_novo_norm = status_os.strip().lower()
        if status_novo_norm == 'finalizada' and status_original_norm != 'finalizada':
            try:
                enfileirado = NotificationService.enqueue_notificar_finalizacao_os(
                    numero_pedido=numero_pedido,
                    solicitante=solicitante,
                    whatsapp_solicitante=whatsapp_solicitante,
                    servico_realizado=servico_realizado,
                    status_os=status_os
                )
                if enfileirado:
                    logger.info("Notificação de finalização enfileirada com sucesso para OS #%s", numero_pedido)
                else:
                    logger.warning("Notificação de finalização não foi enfileirada para OS #%s", numero_pedido)
            except Exception as e:
                logger.error("Erro ao enviar WhatsApp de finalização da OS #%s: %s", os_original.get('ID', row_id), e)

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


@os_bp.route('/upload-documento', methods=['GET', 'POST'])
def upload_documento():
    """Página pública para recebimento de arquivos."""
    mensagem = None
    tipo_mensagem = 'success'

    if request.method == 'POST':
        if request.content_length and request.content_length > MAX_UPLOAD_SIZE_BYTES:
            mensagem = 'Arquivo muito grande. Limite máximo de 10 MB.'
            tipo_mensagem = 'danger'
            return render_template('upload_arquivo.html', mensagem=mensagem, tipo_mensagem=tipo_mensagem), 400

        file = request.files.get('arquivo')
        if not file or not file.filename:
            mensagem = 'Selecione um arquivo para enviar.'
            tipo_mensagem = 'danger'
            return render_template('upload_arquivo.html', mensagem=mensagem, tipo_mensagem=tipo_mensagem), 400

        if not _extensao_permitida(file.filename):
            mensagem = 'Formato não permitido. Use: PDF, DOC, DOCX, TXT, PNG, JPG, JPEG, WEBP, XLSX ou XLS.'
            tipo_mensagem = 'danger'
            return render_template('upload_arquivo.html', mensagem=mensagem, tipo_mensagem=tipo_mensagem), 400

        try:
            upload_dir = Path(current_app.root_path) / 'uploads' / 'documentos'
            upload_dir.mkdir(parents=True, exist_ok=True)

            filename_original = secure_filename(file.filename)
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename_original}"
            file_path = upload_dir / filename

            file.save(file_path)
            logger.info("Arquivo recebido com sucesso: %s", file_path.name)

            mensagem = 'Arquivo enviado com sucesso!'
            tipo_mensagem = 'success'
            return render_template('upload_arquivo.html', mensagem=mensagem, tipo_mensagem=tipo_mensagem)
        except Exception as e:
            logger.error("Erro ao salvar arquivo enviado: %s", e, exc_info=True)
            mensagem = 'Não foi possível enviar o arquivo agora. Tente novamente.'
            tipo_mensagem = 'danger'
            return render_template('upload_arquivo.html', mensagem=mensagem, tipo_mensagem=tipo_mensagem), 500

    return render_template('upload_arquivo.html', mensagem=mensagem, tipo_mensagem=tipo_mensagem)


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
