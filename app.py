import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
import logging
from threading import Lock
import secrets 

# --- 1. CONFIGURAÇÃO INICIAL (Google Sheets & Flask) ---

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# --- LÓGICA DE CREDENCIAIS SIMPLIFICADA (Lê o ficheiro 'credentials.json') ---
creds = None
client = None
sheet = None
sheet_error = None

try:
    CREDS_FILE = Path(__file__).parent / 'credentials.json'
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    logger.info("Credenciais carregadas com sucesso a partir do ficheiro (local ou Secret File).")
    
except FileNotFoundError:
    logger.error("ERRO: Ficheiro 'credentials.json' não encontrado na pasta do projeto.")
    logger.error("Por favor, baixe o JSON do Google Cloud e coloque-o na mesma pasta do 'app.py'")
    logger.error("Se estiver no Render, certifique-se que o 'Secret File' está configurado.")
    sheet_error = "Ficheiro de credenciais não encontrado."
except Exception as e:
    logger.error(f"ERRO CRÍTICO AO CARREGAR CREDENCIAIS: {e}")
    sheet_error = f"Erro ao carregar credenciais: {e}"

# Variáveis de ambiente para configuração (permite substituir via env vars)
SHEET_ID = os.getenv('GOOGLE_SHEET_ID', '1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg')
SHEET_TAB_NAME = os.getenv('GOOGLE_SHEET_TAB', 'Respostas ao formulário 3')
SHEET_HORARIO_TAB = os.getenv('GOOGLE_SHEET_HORARIO_TAB', 'Controle de Horário')

# Variável para planilha de controle de horário
sheet_horario = None

# Só tenta conectar se as credenciais foram carregadas
if creds:
    try:
        client = gspread.authorize(creds)
        spreadsheet = client.open_by_key(SHEET_ID)
        sheet = spreadsheet.worksheet(SHEET_TAB_NAME)
        logger.info(f"Conectado com sucesso à planilha '{SHEET_TAB_NAME}'!")
        
        # Tenta conectar à aba de controle de horário (cria se não existir)
        try:
            sheet_horario = spreadsheet.worksheet(SHEET_HORARIO_TAB)
            logger.info(f"Conectado à aba '{SHEET_HORARIO_TAB}'")
        except:
            # Cria aba se não existir
            sheet_horario = spreadsheet.add_worksheet(title=SHEET_HORARIO_TAB, rows=1000, cols=10)
            # Adiciona cabeçalho
            sheet_horario.append_row(['Data', 'Funcionário', 'Pedido/OS', 'Tipo', 'Horário', 'Observação'])
            logger.info(f"Aba '{SHEET_HORARIO_TAB}' criada com sucesso")
            
    except Exception as e:
        logger.error(f"Erro ao conectar na planilha (verifique permissões de partilha): {e}")
        sheet_error = f"Erro ao conectar à planilha: {e}"
# --- FIM DA LÓGICA DE CREDENCIAIS ---

app = Flask(__name__)
# Gera chave secreta segura se não definida
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = os.getenv('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# --- CONFIGURAÇÃO DE CACHE ---
CACHE_TTL = int(os.getenv('CACHE_TTL_SECONDS', 300))  # 5 minutos padrão
cache_lock = Lock()
cache_data = {
    'dashboard': {'data': None, 'timestamp': None},
    'gerenciar': {'data': None, 'timestamp': None},
    'relatorios': {'data': None, 'timestamp': None}
}

# --- FUNÇÕES AUXILIARES ---

def validar_formulario(form_data):
    """Valida os campos do formulário de abertura de OS."""
    erros = []
    
    if not form_data.get('nome_solicitante', '').strip():
        erros.append('Nome do solicitante é obrigatório.')
    elif len(form_data.get('nome_solicitante', '')) > 100:
        erros.append('Nome do solicitante muito longo (máx 100 caracteres).')
    
    if not form_data.get('setor', '').strip():
        erros.append('Setor é obrigatório.')
    
    if not form_data.get('descricao', '').strip():
        erros.append('Descrição é obrigatória.')
    elif len(form_data.get('descricao', '')) > 1000:
        erros.append('Descrição muito longa (máx 1000 caracteres).')
    
    if not form_data.get('equipamento', '').strip():
        erros.append('Equipamento/Local é obrigatório.')
    
    if not form_data.get('prioridade'):
        erros.append('Prioridade é obrigatória.')
    
    return erros

def obter_proximo_id():
    """Busca o último ID da planilha e retorna o próximo número disponível."""
    try:
        # Obtém todos os valores da coluna A (IDs)
        ids_column = sheet.col_values(1)
        
        # Remove o cabeçalho
        if ids_column:
            ids_column = ids_column[1:]
        
        # Converte para inteiros, ignorando valores vazios ou inválidos
        ids_numericos = []
        for id_val in ids_column:
            try:
                if id_val and str(id_val).strip():
                    ids_numericos.append(int(id_val))
            except ValueError:
                continue
        
        # Retorna o máximo + 1, ou 1 se não houver IDs
        if ids_numericos:
            return max(ids_numericos) + 1
        else:
            return 1
    except Exception as e:
        logger.error(f"Erro ao obter próximo ID: {e}")
        # Fallback: usar timestamp como ID
        return int(datetime.datetime.now().timestamp())

def verificar_sheet_disponivel():
    """Verifica se a conexão com a planilha está disponível."""
    if sheet is None:
        logger.warning("Tentativa de acesso à planilha sem conexão estabelecida.")
        return False, sheet_error or "Conexão com Google Sheets não disponível."
    return True, None

def obter_cache(chave):
    """Obtém dados do cache se ainda válidos."""
    with cache_lock:
        cache_entry = cache_data.get(chave)
        if cache_entry and cache_entry['timestamp']:
            idade = (datetime.datetime.now() - cache_entry['timestamp']).total_seconds()
            if idade < CACHE_TTL:
                logger.info(f"Cache HIT para '{chave}' (idade: {idade:.1f}s)")
                return cache_entry['data']
            else:
                logger.info(f"Cache EXPIRED para '{chave}' (idade: {idade:.1f}s)")
        else:
            logger.info(f"Cache MISS para '{chave}'")
    return None

def salvar_cache(chave, dados):
    """Armazena dados no cache com timestamp."""
    with cache_lock:
        cache_data[chave] = {
            'data': dados,
            'timestamp': datetime.datetime.now()
        }
        logger.info(f"Cache SAVED para '{chave}'")

def limpar_cache(chave=None):
    """Limpa o cache (específico ou todo)."""
    with cache_lock:
        if chave:
            if chave in cache_data:
                cache_data[chave] = {'data': None, 'timestamp': None}
                logger.info(f"Cache limpo para '{chave}'")
        else:
            for key in cache_data:
                cache_data[key] = {'data': None, 'timestamp': None}
            logger.info("Todo o cache foi limpo")

# --- 2. ROTA PRINCIPAL (Formulário de Abertura) ---

@app.route('/')
def homepage():
    """Exibe a página inicial com o formulário (index.html)."""
    return render_template('index.html')

# --- 3. ROTA DE ENVIO (Recebe dados do Formulário) ---

@app.route('/enviar', methods=['POST'])
def receber_requerimento():
    """Recebe os dados do formulário e adiciona como uma nova linha na planilha."""
    # Verifica disponibilidade da planilha
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        logger.error(f"Tentativa de envio sem sheet disponível: {erro_msg}")
        return render_template('erro.html', mensagem=erro_msg), 503
    
    # Valida os dados do formulário
    erros = validar_formulario(request.form)
    if erros:
        logger.warning(f"Validação falhou: {erros}")
        return render_template('index.html', erros=erros), 400
    
    try:
        solicitante = request.form.get('nome_solicitante').strip()
        setor = request.form.get('setor').strip()
        descricao = request.form.get('descricao').strip()
        equipamento = request.form.get('equipamento').strip()
        prioridade = request.form.get('prioridade')
        info_adicional = request.form.get('info_adicional', '').strip() 

        agora = datetime.datetime.now()
        data_solicitacao = agora.strftime("%d/%m/%Y")
        timestamp = agora.strftime("%d/%m/%Y %H:%M:%S")
        status_os = "Aberto"
        
        coluna_id_temporaria = "" 
        servico_realizado = ""
        horario_inicio = ""
        horario_termino = ""
        horas_trabalhadas = ""

        nova_linha = [
            coluna_id_temporaria, # A: / (Será preenchido abaixo)
            timestamp,          # B: Carimbo de data/hora
            solicitante,        # C: Nome do solicitante
            setor,              # D: Setor em que será realizado o serviço
            data_solicitacao,   # E: Data da Solicitação (Formato dd/mm/YYYY)
            descricao,          # F: Descrição do Problema...
            equipamento,        # G: Equipamento ou Local afetado
            prioridade,         # H: Nível de prioridade
            status_os,          # I: Status da OS
            info_adicional,     # J: Informações adicionais (Opcional)
            servico_realizado,  # K: Serviço realizado
            horario_inicio,     # L: Horario de Inicio
            horario_termino,    # M: Horario de Término
            horas_trabalhadas   # N: Horas trabalhadas
        ]

        # Obtém o próximo ID de forma robusta
        numero_pedido = obter_proximo_id()
        
        # Atualiza a primeira coluna com o ID correto
        nova_linha[0] = numero_pedido
        
        try:
            # Garante que a linha será adicionada ao final da planilha
            result = sheet.append_row(nova_linha, value_input_option='USER_ENTERED', insert_data_option='INSERT_ROWS')
            
            # Invalida cache após inserção
            limpar_cache()
            
            logger.info(f"Nova OS (Pedido #{numero_pedido}) adicionada por: {solicitante}")
            
            return render_template('sucesso.html', nome=solicitante, os_numero=numero_pedido)
            
        except Exception as e:
            logger.error(f"ERRO ao adicionar linha na planilha: {e}")
            return render_template('erro.html', 
                mensagem="Erro ao salvar OS. Por favor, tente novamente."), 500

    except Exception as e:
        logger.error(f"Erro ao salvar dados: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao salvar seu requerimento: {e}"), 500

# --- 4. ROTA DO DASHBOARD (Gráficos) ---

@app.route('/dashboard')
def dashboard():
    """Exibe o dashboard com gráficos de análise dos chamados."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        return render_template('dashboard.html', labels_meses=[], datasets_status=[], 
            mensagem_erro=erro_msg)
    
    # Tenta obter do cache primeiro
    cache_result = obter_cache('dashboard')
    if cache_result:
        return render_template('dashboard.html', 
            labels_meses=cache_result['labels_meses'],
            datasets_status=cache_result['datasets_status'])
    
    try:
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return render_template('dashboard.html', labels_meses=[], datasets_status=[])

        headers = data.pop(0) 
        df = pd.DataFrame(data, columns=headers)

        if 'Carimbo de data/hora' not in df.columns or 'Status da OS' not in df.columns:
            raise Exception("Planilha não contém 'Carimbo de data/hora' ou 'Status da OS'.")

        df['Carimbo de data/hora'] = pd.to_datetime(df['Carimbo de data/hora'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df = df.dropna(subset=['Carimbo de data/hora'])
        
        df['MesAno'] = df['Carimbo de data/hora'].dt.to_period('M').astype(str)

        status_por_mes = df.groupby(['MesAno', 'Status da OS']).size().unstack(fill_value=0)

        labels_meses = status_por_mes.index.tolist()
        
        datasets_status = []
        cores = {
            'Finalizada': 'rgba(75, 192, 192, 0.7)',  # Verde
            'Em Andamento': 'rgba(54, 162, 235, 0.7)', # Azul
            'Aguardando Compra': 'rgba(255, 159, 64, 0.7)', # Laranja
            'Cancelada': 'rgba(217, 83, 79, 0.7)', # Vermelho
            'Aberto': 'rgba(108, 117, 125, 0.7)' # Cinza
         }

        for status in status_por_mes.columns:
            dataset = {
                'label': status,
                'data': status_por_mes[status].values.tolist(),
                'backgroundColor': cores.get(status, 'rgba(201, 203, 207, 0.7)')
            }
            datasets_status.append(dataset)
        
        # Salva no cache antes de retornar
        resultado = {
            'labels_meses': labels_meses,
            'datasets_status': datasets_status
        }
        salvar_cache('dashboard', resultado)
        
        return render_template(
            'dashboard.html',
            labels_meses=labels_meses,
            datasets_status=datasets_status
        )
    except Exception as e:
        logger.error(f"Erro ao carregar dashboard: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao carregar o dashboard: {e}"), 500

# --- 5. ROTA DE GERENCIAMENTO (Listar e Editar Chamados) ---

@app.route('/gerenciar')
def gerenciar():
    """Exibe a página de gerenciamento com a lista de todos os chamados."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        return render_template('gerenciar.html', chamados=[], 
            current_sort='Carimbo de data/hora', current_order='desc',
            mensagem_erro=erro_msg)
    
    sort_by = request.args.get('sort_by', 'Carimbo de data/hora')
    order = request.args.get('order', 'desc')
    
    # Tenta obter do cache primeiro
    cache_result = obter_cache('gerenciar')
    if cache_result:
        chamados_filtrados = cache_result
    else:
        try:
            data = sheet.get_all_values()
            if not data or len(data) < 2:
                return render_template('gerenciar.html', chamados=[], current_sort=sort_by, current_order=order)

            headers = data.pop(0)
            
            if 'Status da OS' not in headers:
                raise ValueError("A coluna 'Status da OS' não foi encontrada na planilha. Verifique o cabeçalho.")
            
            status_index = headers.index('Status da OS')
            
            chamados_filtrados = []
            
            for i, row in enumerate(data):
                if not any(row):
                    continue

                if len(row) > status_index and row[status_index] == 'Cancelada':
                    continue
                    
                chamado = {'row_id': i + 2}
                
                full_row = row + [''] * (len(headers) - len(row))
                
                chamado.update(zip(headers, full_row))
                chamados_filtrados.append(chamado)
            
            # Salva os dados filtrados no cache
            salvar_cache('gerenciar', chamados_filtrados)
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados da planilha: {e}")
            return render_template('erro.html', 
                mensagem=f"Erro ao carregar dados: {e}"), 500
    
    # Aplica ordenação (sempre executada, mesmo com cache)
    try:
        def sort_key(item):
            try:
                if sort_by == 'Carimbo de data/hora':
                    return datetime.datetime.strptime(item.get(sort_by, ''), '%d/%m/%Y %H:%M:%S')
                return item.get(sort_by, '').lower()
            except ValueError:
                return datetime.datetime.min

        chamados_ordenados = sorted(chamados_filtrados, key=sort_key, reverse=(order == 'desc'))
        
        return render_template(
            'gerenciar.html',
            chamados=chamados_ordenados,
            current_sort=sort_by,
            current_order=order
        )
    except Exception as e:
        logger.error(f"Erro ao ordenar chamados: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao processar dados: {e}"), 500

# --- 6. ROTA DE ATUALIZAÇÃO (Recebe dados do Modal de Edição) ---

@app.route('/atualizar_chamado', methods=['POST'])
def atualizar_chamado():
    """Atualiza uma linha inteira na planilha com os dados do modal de edição."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        logger.error(f"Tentativa de atualização sem sheet disponível: {erro_msg}")
        return render_template('erro.html', mensagem=erro_msg), 503
    
    try:
        solicitante = request.form.get('nome_solicitante', '')
        setor = request.form.get('setor', '')
        data_solicitacao = request.form.get('data_solicitacao', '')
        descricao = request.form.get('descricao', '')
        equipamento = request.form.get('equipamento', '')
        prioridade = request.form.get('prioridade', '')
        info_adicional = request.form.get('info_adicional', '')
        
        status_os = request.form.get('status_os', '')
        servico_realizado = request.form.get('servico_realizado', '')
        horario_inicio = request.form.get('horario_inicio', '')
        horario_termino = request.form.get('horario_termino', '')
        horas_trabalhadas = request.form.get('horas_trabalhadas', '')
        
        row_id = int(request.form.get('row_id'))
        
        timestamp = sheet.cell(row_id, 2).value # Coluna B = 2
        os_id = sheet.cell(row_id, 1).value # Coluna A = 1

        linha_atualizada = [
            os_id,              # A: / (Preservado)
            timestamp,          # B: Carimbo de data/hora (Preservado)
            solicitante,        # C: Nome do solicitante
            setor,              # D: Setor
            data_solicitacao,   # E: Data da Solicitação
            descricao,          # F: Descrição
            equipamento,        # G: Equipamento
            prioridade,         # H: Prioridade
            status_os,          # I: Status da OS (Atualizado)
            info_adicional,     # J: Informações Adicionais
            servico_realizado,  # K: Serviço Realizado (Atualizado)
            horario_inicio,     # L: Horário Início (Atualizado)
            horario_termino,    # M: Horário Término (Atualizado)
            horas_trabalhadas   # N: Horas Trabalhadas (Atualizado)
        ]

        sheet.update(f'A{row_id}:N{row_id}', [linha_atualizada])
        
        # Invalida cache após atualização
        limpar_cache()

        logger.info(f"Chamado (Linha {row_id}) atualizado com status: {status_os}")

        return redirect(url_for('gerenciar'))
        
    except Exception as e:
        logger.error(f"Erro ao atualizar chamado: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao atualizar o chamado: {e}"), 500

# --- 7. ROTA DE SUCESSO (Página de confirmação) ---

@app.route('/sucesso')
def sucesso():
    """Página de sucesso (para caso o /enviar fosse GET)."""
    return render_template('sucesso.html', nome="Usuário")

# --- 7.1. ROTA ADMINISTRATIVA - LIMPAR CACHE ---

@app.route('/admin/limpar-cache', methods=['POST', 'GET'])
def admin_limpar_cache():
    """Limpa o cache manualmente (útil para admins/devs)."""
    try:
        limpar_cache()
        logger.info("Cache limpo manualmente via rota /admin/limpar-cache")
        flash('Cache limpo com sucesso!', 'success')
        return redirect(request.referrer or url_for('homepage'))
    except Exception as e:
        logger.error(f"Erro ao limpar cache: {e}")
        return render_template('erro.html', mensagem=f"Erro ao limpar cache: {e}"), 500


# --- 8. ROTA DE CONTROLE DE HORÁRIO ---

@app.route('/controle-horario', methods=['GET', 'POST'])
def controle_horario():
    """Página de controle de ponto com registros de entrada, saída e pausas."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    
    # Inicializa variáveis
    status_atual = 'inativo'
    horario_entrada = None
    horario_saida = None
    tempo_trabalhado = '0h 0m'
    tempo_pausa = '0h 0m'
    registros = []
    mensagem = None
    tipo_mensagem = 'success'
    
    if not disponivel or sheet_horario is None:
        return render_template('controle_horario.html',
            status_atual=status_atual,
            registros=[],
            mensagem="Sistema de controle de horário indisponível. Verifique a conexão com Google Sheets.",
            tipo_mensagem='error',
            horario_entrada=horario_entrada,
            horario_saida=horario_saida,
            tempo_trabalhado=tempo_trabalhado,
            tempo_pausa=tempo_pausa)
    
    try:
        hoje = datetime.datetime.now().strftime('%d/%m/%Y')
        agora = datetime.datetime.now()
        
        # Processa ação se for POST
        if request.method == 'POST':
            acao = request.form.get('acao')
            nome_usuario = request.form.get('nome_usuario', 'Usuário').strip() or 'Usuário'
            pedido_os = request.form.get('pedido_os', '').strip()
            horario_registro = agora.strftime('%H:%M:%S')
            
            tipo_map = {
                'entrada': 'Entrada',
                'saida': 'Saída',
                'pausa': 'Pausa',
                'retorno': 'Retorno'
            }
            
            # Registra na planilha
            nova_linha = [
                hoje,
                nome_usuario,
                pedido_os,
                tipo_map.get(acao, acao),
                horario_registro,
                ''  # Observação
            ]
            
            sheet_horario.append_row(nova_linha, value_input_option='USER_ENTERED')
            logger.info(f"Registro de {acao} às {horario_registro}")
            
            mensagem = f"{tipo_map.get(acao, acao)} registrada com sucesso às {horario_registro}"
            limpar_cache()  # Invalida cache se houver
        
        # Busca registros de hoje
        all_data = sheet_horario.get_all_values()
        if len(all_data) > 1:
            headers = all_data[0]
            registros_raw = all_data[1:]
            
            # Filtra registros de hoje
            registros_hoje = []
            for row in registros_raw:
                if len(row) > 0 and row[0] == hoje:
                    registros_hoje.append({
                        'data': row[0],
                        'funcionario': row[1] if len(row) > 1 else '',
                        'pedido_os': row[2] if len(row) > 2 else '',
                        'tipo': row[3].lower() if len(row) > 3 else '',
                        'tipo_nome': row[3] if len(row) > 3 else '',
                        'horario': row[4] if len(row) > 4 else '',
                        'observacao': row[5] if len(row) > 5 else ''
                    })
            
            registros = sorted(registros_hoje, key=lambda x: x['horario'], reverse=True)
            
            # Calcula status atual e tempos
            if registros_hoje:
                ultimo_registro = registros_hoje[-1]['tipo']
                
                if ultimo_registro == 'entrada' or ultimo_registro == 'retorno':
                    status_atual = 'ativo'
                elif ultimo_registro == 'pausa':
                    status_atual = 'pausa'
                elif ultimo_registro == 'saída':
                    status_atual = 'inativo'
                
                # Calcula horários
                entradas = [r for r in registros_hoje if r['tipo'] in ['entrada', 'retorno']]
                saidas = [r for r in registros_hoje if r['tipo'] in ['saída', 'pausa']]
                
                if entradas:
                    horario_entrada = entradas[0]['horario']
                if saidas and saidas[-1]['tipo'] == 'saída':
                    horario_saida = saidas[-1]['horario']
                
                # Calcula tempo trabalhado e pausas
                total_trabalho = datetime.timedelta()
                total_pausa = datetime.timedelta()
                
                tempo_inicio = None
                em_pausa = False
                pausa_inicio = None
                
                for reg in sorted(registros_hoje, key=lambda x: x['horario']):
                    horario = datetime.datetime.strptime(reg['horario'], '%H:%M:%S')
                    
                    if reg['tipo'] == 'entrada':
                        tempo_inicio = horario
                        em_pausa = False
                    elif reg['tipo'] == 'pausa' and tempo_inicio:
                        if not em_pausa:
                            total_trabalho += horario - tempo_inicio
                            pausa_inicio = horario
                            em_pausa = True
                    elif reg['tipo'] == 'retorno' and pausa_inicio:
                        total_pausa += horario - pausa_inicio
                        tempo_inicio = horario
                        em_pausa = False
                    elif reg['tipo'] == 'saída' and tempo_inicio:
                        if em_pausa and pausa_inicio:
                            total_pausa += horario - pausa_inicio
                        else:
                            total_trabalho += horario - tempo_inicio
                        tempo_inicio = None
                
                # Se ainda está trabalhando
                if tempo_inicio and not em_pausa:
                    total_trabalho += agora - tempo_inicio.replace(year=agora.year, month=agora.month, day=agora.day)
                
                # Se está em pausa
                if em_pausa and pausa_inicio:
                    total_pausa += agora - pausa_inicio.replace(year=agora.year, month=agora.month, day=agora.day)
                
                # Formata tempos
                horas_trabalho = int(total_trabalho.total_seconds() // 3600)
                minutos_trabalho = int((total_trabalho.total_seconds() % 3600) // 60)
                tempo_trabalhado = f"{horas_trabalho}h {minutos_trabalho}m"
                
                horas_pausa = int(total_pausa.total_seconds() // 3600)
                minutos_pausa = int((total_pausa.total_seconds() % 3600) // 60)
                tempo_pausa = f"{horas_pausa}h {minutos_pausa}m"
        
        return render_template('controle_horario.html',
            status_atual=status_atual,
            registros=registros,
            mensagem=mensagem,
            tipo_mensagem=tipo_mensagem,
            horario_entrada=horario_entrada,
            horario_saida=horario_saida,
            tempo_trabalhado=tempo_trabalhado,
            tempo_pausa=tempo_pausa)
            
    except Exception as e:
        logger.error(f"Erro no controle de horário: {e}")
        return render_template('erro.html',
            mensagem=f"Erro ao processar controle de horário: {e}"), 500

# --- 9. ENDPOINT DE HEALTHCHECK ---

@app.route('/health')
def health_check():
    """Endpoint para monitoramento de saúde da aplicação."""
    status = {
        'status': 'healthy',
        'timestamp': datetime.datetime.now().isoformat(),
        'sheets_connected': sheet is not None,
        'cache_enabled': True
    }
    return jsonify(status), 200

# --- 10. ROTA DE RELATÓRIOS DETALHADOS ---

@app.route('/relatorios')
def relatorios():
    """Exibe página de relatórios com gráficos detalhados."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        return render_template('relatorios.html', 
            mensagem_erro=erro_msg,
            labels_prioridade=[], dados_prioridade=[],
            labels_setor=[], dados_setor=[],
            labels_tempo_resolucao=[], dados_tempo_resolucao=[],
            labels_dia_semana=[], dados_dia_semana=[],
            total_os=0, tempo_medio='0 dias', taxa_conclusao='0%')
    
    # Tenta obter do cache primeiro
    cache_result = obter_cache('relatorios')
    if cache_result:
        return render_template('relatorios.html', **cache_result)
    
    try:
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return render_template('relatorios.html',
                labels_prioridade=[], dados_prioridade=[],
                labels_setor=[], dados_setor=[],
                labels_tempo_resolucao=[], dados_tempo_resolucao=[],
                labels_dia_semana=[], dados_dia_semana=[],
                total_os=0, tempo_medio='0 dias', taxa_conclusao='0%')

        headers = data.pop(0)
        df = pd.DataFrame(data, columns=headers)

        # Converte timestamps
        df['Carimbo de data/hora'] = pd.to_datetime(df['Carimbo de data/hora'], 
            format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df = df.dropna(subset=['Carimbo de data/hora'])
        
        # 1. Gráfico de Pizza - Distribuição por Prioridade
        prioridade_count = df['Nível de prioridade'].value_counts()
        labels_prioridade = prioridade_count.index.tolist()
        dados_prioridade = prioridade_count.values.tolist()
        
        # 2. Gráfico de Barras Horizontal - OS por Setor
        setor_count = df['Setor em que será realizado o serviço'].value_counts().head(10)
        labels_setor = setor_count.index.tolist()
        dados_setor = setor_count.values.tolist()
        
        # 3. Gráfico de Linha - Tempo médio de resolução por mês
        df_finalizada = df[df['Status da OS'] == 'Finalizada'].copy()
        if not df_finalizada.empty and 'Horário de Início' in df.columns:
            df_finalizada['Horário de Início'] = pd.to_datetime(
                df_finalizada['Horário de Início'], format='%H:%M', errors='coerce')
            df_finalizada['Horário de Término'] = pd.to_datetime(
                df_finalizada['Horário de Término'], format='%H:%M', errors='coerce')
            
            df_finalizada['Tempo'] = (df_finalizada['Horário de Término'] - 
                df_finalizada['Horário de Início']).dt.total_seconds() / 3600
            
            df_finalizada['MesAno'] = df_finalizada['Carimbo de data/hora'].dt.to_period('M').astype(str)
            tempo_por_mes = df_finalizada.groupby('MesAno')['Tempo'].mean()
            
            labels_tempo_resolucao = tempo_por_mes.index.tolist()
            dados_tempo_resolucao = tempo_por_mes.values.tolist()
        else:
            labels_tempo_resolucao = []
            dados_tempo_resolucao = []
        
        # 4. Gráfico de Barras - OS abertas por dia da semana
        df['DiaSemana'] = df['Carimbo de data/hora'].dt.day_name()
        dias_ordem = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        dias_pt = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
        
        dia_count = df['DiaSemana'].value_counts()
        labels_dia_semana = []
        dados_dia_semana = []
        for dia_en, dia_pt in zip(dias_ordem, dias_pt):
            labels_dia_semana.append(dia_pt)
            dados_dia_semana.append(int(dia_count.get(dia_en, 0)))
        
        # Métricas gerais
        total_os = len(df)
        finalizadas = len(df[df['Status da OS'] == 'Finalizada'])
        taxa_conclusao = f"{(finalizadas/total_os*100):.1f}%" if total_os > 0 else "0%"
        
        # Tempo médio de resolução
        if not df_finalizada.empty and 'Tempo' in df_finalizada.columns:
            tempo_medio = f"{df_finalizada['Tempo'].mean():.1f} horas"
        else:
            tempo_medio = "N/A"
        
        resultado = {
            'labels_prioridade': labels_prioridade,
            'dados_prioridade': dados_prioridade,
            'labels_setor': labels_setor,
            'dados_setor': dados_setor,
            'labels_tempo_resolucao': labels_tempo_resolucao,
            'dados_tempo_resolucao': dados_tempo_resolucao,
            'labels_dia_semana': labels_dia_semana,
            'dados_dia_semana': dados_dia_semana,
            'total_os': total_os,
            'tempo_medio': tempo_medio,
            'taxa_conclusao': taxa_conclusao,
            'total_finalizadas': finalizadas,
            'total_abertas': len(df[df['Status da OS'] == 'Aberto']),
            'total_andamento': len(df[df['Status da OS'] == 'Em Andamento'])
        }
        
        salvar_cache('relatorios', resultado)
        return render_template('relatorios.html', **resultado)
        
    except Exception as e:
        logger.error(f"Erro ao carregar relatórios: {e}")
        return render_template('erro.html', 
            mensagem=f"Erro ao carregar relatórios: {e}"), 500

# --- 11. ROTA DE CONSULTA DE STATUS ---

@app.route('/consultar', methods=['GET', 'POST'])
def consultar_pedido():
    """Página pública para um solicitante consultar o status de um pedido."""
    disponivel, erro_msg = verificar_sheet_disponivel()
    if not disponivel:
        return render_template('consultar.html', 
            resultado={'erro': erro_msg}, pedido_buscado=None)
    
    resultado = None
    pedido_buscado = None

    if request.method == 'POST':
        # Usuário enviou o formulário de consulta
        pedido_buscado = request.form.get('numero_pedido')
    elif request.method == 'GET' and 'numero_pedido' in request.args:
        # Usuário clicou no link da página de sucesso (pré-preenchido)
        pedido_buscado = request.args.get('numero_pedido')
    
    if pedido_buscado:
        try:
            # Tenta encontrar o pedido na Coluna A (in_column=1)
            # sheet.find() procura pela string formatada, o que é perfeito para nós
            cell = sheet.find(str(pedido_buscado), in_column=1) 
            
            if cell:
                # Se encontrou, pega os dados daquela linha
                all_data = sheet.row_values(cell.row)
                
                # Monta o dicionário de resultado
                resultado = {
                    'id': all_data[0],       # Col A (ID)
                    'data': all_data[4],     # Col E (Data Solicitação)
                    'descricao': all_data[5], # Col F (Descrição)
                    'status': all_data[8]    # Col I (Status)
                }
            else:
                # Se não encontrou, define uma mensagem de erro
                resultado = {'erro': f"Pedido número '{pedido_buscado}' não encontrado."}
        
        except Exception as e:
            # Captura erros de conexão ou outros problemas
            logger.error(f"Erro ao buscar pedido: {e}")
            resultado = {'erro': 'Ocorreu um erro ao consultar o pedido.'}
    
    # Renderiza a página de consulta, passando o resultado e o número buscado
    return render_template('consultar.html', resultado=resultado, pedido_buscado=pedido_buscado)


# --- 12. ROTA PARA FAVICON ---

@app.route('/favicon.ico')
def favicon():
    """Retorna um favicon vazio para evitar erro 404."""
    return '', 204

# --- Ponto de Entrada Principal ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Iniciando aplicação na porta {port} (debug={debug_mode})")
    
    # debug=False é crucial para produção
    # host='0.0.0.0' permite que o Render se conecte
    app.run(host='0.0.0.0', port=port, debug=debug_mode)

