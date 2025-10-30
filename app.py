import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# --- 1. CONFIGURAÇÃO INICIAL (Google Sheets & Flask) ---

# Define os escopos (permissões) que a API necessita
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# Encontra o ficheiro 'credentials.json' na MESMA pasta que este script
try:
    CREDS_FILE = Path(__file__).parent / 'credentials.json'
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
except FileNotFoundError:
    print("ERRO: Ficheiro 'credentials.json' não encontrado na pasta do projeto.")
    print("Por favor, baixe o JSON do Google Cloud e coloque-o na mesma pasta do 'app.py'")
    exit()

# Autoriza o cliente gspread
client = gspread.authorize(creds)

# ID da Planilha (da URL)
SHEET_ID = '1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg'
# Nome exato da Aba (Guia)
SHEET_TAB_NAME = 'Respostas ao formulário 3' 

# Tenta conectar-se à planilha
try:
    spreadsheet = client.open_by_key(SHEET_ID)
    sheet = spreadsheet.worksheet(SHEET_TAB_NAME)
    print(f"Conectado com sucesso à planilha '{SHEET_TAB_NAME}'!")
except Exception as e:
    print(f"Erro ao conectar na planilha: {e}")
    exit()

# Inicializa a aplicação Flask
app = Flask(__name__)

# --- 2. ROTA PRINCIPAL (Formulário de Abertura) ---

@app.route('/')
def homepage():
    """Exibe a página inicial com o formulário (index.html)."""
    return render_template('index.html')

# --- 3. ROTA DE ENVIO (Recebe dados do Formulário) ---

@app.route('/enviar', methods=['POST'])
def receber_requerimento():
    """Recebe os dados do formulário e adiciona como uma nova linha na planilha."""
    try:
        # --- 3a. Coleta de dados do formulário ---
        solicitante = request.form.get('nome_solicitante')
        setor = request.form.get('setor')
        descricao = request.form.get('descricao')
        equipamento = request.form.get('equipamento')
        prioridade = request.form.get('prioridade')
        info_adicional = request.form.get('info_adicional', '') # Opcional

        # --- 3b. Geração de dados automáticos ---
        agora = datetime.datetime.now()
        # Formato PT-BR (dd/mm/AAAA) para a coluna 'Data da Solicitação'
        data_solicitacao = agora.strftime("%d/%m/%Y")
        # Formato completo para o 'Carimbo de data/hora'
        timestamp = agora.strftime("%d/%m/%Y %H:%M:%S")
        status_os = "Aberto" # Define o status padrão para novos chamados
        
        # --- 3c. Campos em branco (para manutenção) ---
        coluna_barra = ""
        servico_realizado = ""
        horario_inicio = ""
        horario_termino = ""
        horas_trabalhadas = ""

        # --- 3d. Montagem da linha (na ordem exata da planilha) ---
        nova_linha = [
            coluna_barra,       # A: /
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

        # 5. Adiciona a nova linha na planilha
        sheet.append_row(nova_linha)

        print(f"Nova OS adicionada por: {solicitante}")

        # 6. Redireciona para a página de sucesso
        return render_template('sucesso.html', nome=solicitante)

    except Exception as e:
        print(f"Erro ao salvar dados: {e}")
        return f"<h1>Erro ao salvar seu requerimento.</h1><p>{e}</p>"

# --- 4. ROTA DO DASHBOARD (Gráficos) ---

@app.route('/dashboard')
def dashboard():
    """Exibe o dashboard com gráficos de análise dos chamados."""
    try:
        # 1. Puxa TODOS os dados da planilha
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return render_template('dashboard.html', labels_meses=[], datasets_status=[])

        # 2. Converte os dados para um DataFrame do Pandas
        headers = data.pop(0) 
        df = pd.DataFrame(data, columns=headers)

        # 3. Verifica se as colunas essenciais existem
        if 'Carimbo de data/hora' not in df.columns or 'Status da OS' not in df.columns:
            raise Exception("Planilha não contém 'Carimbo de data/hora' ou 'Status da OS'.")

        # 4. Limpa e processa os dados de data
        # Converte a coluna de data (formato dd/mm/YYYY H:M:S)
        df['Carimbo de data/hora'] = pd.to_datetime(df['Carimbo de data/hora'], format='%d/%m/%Y %H:%M:%S', errors='coerce')
        df = df.dropna(subset=['Carimbo de data/hora']) # Remove linhas com datas inválidas
        
        # Cria uma nova coluna 'MesAno' (ex: '2025-10') para agrupar
        df['MesAno'] = df['Carimbo de data/hora'].dt.to_period('M').astype(str)

        # 5. Agrupa os dados para o gráfico
        status_por_mes = df.groupby(['MesAno', 'Status da OS']).size().unstack(fill_value=0)

        # 6. Formata os dados para o Chart.js
        labels_meses = status_por_mes.index.tolist()
        
        datasets_status = []
        # Dicionário de cores para os status
        cores = {
            'Finalizada': 'rgba(75, 192, 192, 0.7)',  # Verde
            'Em andamento': 'rgba(54, 162, 235, 0.7)', # Azul
            'Aguardando compra': 'rgba(255, 159, 64, 0.7)', # Laranja
            'Cancelada': 'rgba(217, 83, 79, 0.7)', # Vermelho
            'Aguardando liberação': 'rgba(52, 21, 57, 0.7)' # Roxo   
         }

        for status in status_por_mes.columns:
            dataset = {
                'label': status,
                'data': status_por_mes[status].values.tolist(),
                'backgroundColor': cores.get(status, 'rgba(201, 203, 207, 0.7)') # Cor cinza padrão
            }
            datasets_status.append(dataset)
        
        # 7. Envia os dados para a página do dashboard
        return render_template(
            'dashboard.html',
            labels_meses=labels_meses,
            datasets_status=datasets_status
        )
    except Exception as e:
        print(f"Erro ao carregar dashboard: {e}")
        return f"<h1>Erro ao carregar o dashboard.</h1><p>Verifique os nomes das colunas na planilha. Erro: {e}</p>"

# --- 5. ROTA DE GERENCIAMENTO (Listar e Editar Chamados) ---

@app.route('/gerenciar')
def gerenciar():
    """Exibe a página de gerenciamento com a lista de todos os chamados."""
    try:
        # 1. Obtém parâmetros de ordenação da URL
        sort_by = request.args.get('sort_by', 'Carimbo de data/hora') # Padrão
        order = request.args.get('order', 'desc') # Padrão (mais novos primeiro)
        
        # 2. Busca todos os dados da planilha
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return render_template('gerenciar.html', chamados=[], current_sort=sort_by, current_order=order)

        headers = data.pop(0)
        
        # --- INÍCIO DA CORREÇÃO ---
        # 3. Verifica se a coluna de status vital existe
        if 'Status da OS' not in headers:
            raise ValueError("A coluna 'Status da OS' não foi encontrada na planilha. Verifique o cabeçalho.")
        
        status_index = headers.index('Status da OS')
        # --- FIM DA CORREÇÃO ---
        
        # 3b. Filtra chamados e converte para dicionários
        chamados_filtrados = []
        
        for i, row in enumerate(data):
            # Ignora linhas que estão completamente vazias
            if not any(row):
                continue

            # --- INÍCIO DA CORREÇÃO 2 ---
            # Regra: Não mostrar chamados 'Cancelada'
            # Verifica se a linha tem dados suficientes ANTES de ler o status
            if len(row) > status_index and row[status_index] == 'Cancelada':
                continue
            # --- FIM DA CORREÇÃO 2 ---
                
            chamado = {'row_id': i + 2} # +2 (índice 1-based + cabeçalho)
            chamado.update(zip(headers, row))
            chamados_filtrados.append(chamado)

        # 4. Lógica de Ordenação
        # Converte a data de string (dd/mm/YYYY H:M:S) para um objeto datetime real
        def sort_key(item):
            try:
                # Ordena pela data/hora real, não pelo texto
                if sort_by == 'Carimbo de data/hora':
                    return datetime.datetime.strptime(item.get(sort_by, ''), '%d/%m/%Y %H:%M:%S')
                # Ordenação padrão para outras colunas (texto)
                return item.get(sort_by, '').lower()
            except ValueError:
                # Retorna um valor padrão se a data estiver mal formatada
                return datetime.datetime.min

        chamados_ordenados = sorted(chamados_filtrados, key=sort_key, reverse=(order == 'desc'))
        
        # 5. Renderiza a página
        return render_template(
            'gerenciar.html',
            chamados=chamados_ordenados,
            current_sort=sort_by,
            current_order=order
        )
    except Exception as e:
        print(f"Erro ao carregar gerenciador: {e}")
        return f"<h1>Erro ao carregar o gerenciador.</h1><p>Erro: {e}</p>"

# --- 6. ROTA DE ATUALIZAÇÃO (Recebe dados do Modal de Edição) ---

@app.route('/atualizar_chamado', methods=['POST'])
def atualizar_chamado():
    """Atualiza uma linha inteira na planilha com os dados do modal de edição."""
    try:
        # 1. Coleta TODOS os campos (usando .get() para segurança)
        # Campos "readonly" (originais da solicitação)
        solicitante = request.form.get('nome_solicitante', '')
        setor = request.form.get('setor', '')
        data_solicitacao = request.form.get('data_solicitacao', '')
        descricao = request.form.get('descricao', '')
        equipamento = request.form.get('equipamento', '')
        prioridade = request.form.get('prioridade', '')
        info_adicional = request.form.get('info_adicional', '')
        
        # Campos "editáveis" (da manutenção)
        status_os = request.form.get('status_os', '')
        servico_realizado = request.form.get('servico_realizado', '')
        horario_inicio = request.form.get('horario_inicio', '')
        horario_termino = request.form.get('horario_termino', '')
        horas_trabalhadas = request.form.get('horas_trabalhadas', '')
        
        # Identificador da Linha (essencial)
        row_id = int(request.form.get('row_id'))
        
        # O 'Carimbo de data/hora' não está no formulário,
        # precisamos de o ir buscar à planilha para não o apagar.
        timestamp = sheet.cell(row_id, 2).value # Coluna B = 2

        # 2. Monta a linha completa na ordem correta
        linha_atualizada = [
            "",                 # A: /
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

        # 3. Atualiza a linha inteira na planilha
        # [linha_atualizada] -> Coloca a lista dentro de outra lista
        sheet.update(f'A{row_id}:N{row_id}', [linha_atualizada])

        print(f"Chamado (Linha {row_id}) atualizado com status: {status_os}")

        # 4. Redireciona de volta para a página de gerenciamento
        return redirect(url_for('gerenciar'))
        
    except Exception as e:
        print(f"Erro ao atualizar chamado: {e}")
        return f"<h1>Erro ao atualizar o chamado.</h1><p>Erro: {e}</p>"

# --- 7. ROTA DE SUCESSO (Página de confirmação) ---

@app.route('/sucesso')
def sucesso():
    """Página de sucesso (para caso o /enviar fosse GET)."""
    # Esta rota não é usada diretamente pelo POST, mas é bom tê-la
    # O render_template() é chamado diretamente no /enviar
    return render_template('sucesso.html', nome="Usuário")

# --- Ponto de Entrada Principal ---
if __name__ == '__main__':
    app.run(debug=True)

