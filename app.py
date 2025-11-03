import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import re 
import os 
# import base64 # Removido
import json   # Mantido para a rota do dashboard

# --- 1. CONFIGURAÇÃO INICIAL (Google Sheets & Flask) ---

SCOPES = [
    'https.www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]

# --- LÓGICA DE CREDENCIAIS (Leitura Direta do Ficheiro) ---
try:
    # Lê diretamente o ficheiro 'credentials.json'
    # (Funciona localmente ou com o "Secret File" do Render)
    CREDS_FILE = Path(__file__).parent / 'credentials.json'
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    print("Credenciais carregadas com sucesso a partir do ficheiro (credentials.json).")

except FileNotFoundError:
    print("ERRO: Ficheiro 'credentials.json' não encontrado.")
    print("Verifique se o ficheiro está na pasta ou se o 'Secret File' do Render está configurado.")
    exit()
except Exception as e:
    print(f"ERRO CRÍTICO AO CARREGAR CREDENCIAIS: {e}")
    exit()
# --- FIM DA LÓGICA DE CREDENCIAIS ---

client = gspread.authorize(creds)

SHEET_ID = '1qs3cxlklTnzCp4RpQGhxIrEF4CbeUvid1S0Cp2tC3Xg'
SHEET_TAB_NAME = 'Respostas ao formulário 3' 

try:
    spreadsheet = client.open_by_key(SHEET_ID)
    sheet = spreadsheet.worksheet(SHEET_TAB_NAME)
    print(f"Conectado com sucesso à planilha '{SHEET_TAB_NAME}'!")
except Exception as e:
    print(f"Erro ao conectar na planilha (verifique permissões de partilha): {e}")
    exit()

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
        solicitante = request.form.get('nome_solicitante')
        setor = request.form.get('setor')
        descricao = request.form.get('descricao')
        equipamento = request.form.get('equipamento')
        prioridade = request.form.get('prioridade')
        info_adicional = request.form.get('info_adicional', '') 

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

        # 5a. Adiciona a nova linha na planilha e captura o resultado
        result = sheet.append_row(nova_linha)

        # 5b. Pega o número da linha que acabou de ser criada
        # Esta é a forma mais robusta: lê todos os dados e conta as linhas
        all_data = sheet.get_all_values()
        row_number = len(all_data) # O número da linha recém-adicionada
        
        # 5c. Cria o ID do Pedido (Número da Linha - 2)
        numero_pedido = row_number - 2 
        
        # 5d. Atualiza a Coluna A com o número do pedido
        sheet.update_cell(row_number, 1, numero_pedido) # (linha, coluna, valor)

        print(f"Nova OS (Pedido #{numero_pedido}) adicionada por: {solicitante}")

        return render_template('sucesso.html', nome=solicitante, os_numero=numero_pedido)

    except Exception as e:
        print(f"Erro ao salvar dados: {e}")
        return f"<h1>Erro ao salvar seu requerimento.</h1><p>Por favor, tente novamente. Erro: {e}</p>"

# --- 4. ROTA DO DASHBOARD (Gráficos) ---

@app.route('/dashboard')
def dashboard():
    """Exibe o dashboard com gráficos de análise dos chamados."""
    try:
        data = sheet.get_all_values()
        if not data or len(data) < 2:
            return render_template('dashboard.html', labels_meses="[]", datasets_status="[]") # Envia JSON vazio

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
        
        # Converte para JSON aqui para evitar erros no template
        labels_meses_json = json.dumps(labels_meses)
        datasets_status_json = json.dumps(datasets_status)

        return render_template(
            'dashboard.html',
            labels_meses=labels_meses_json,
            datasets_status=datasets_status_json
        )
    except Exception as e:
        print(f"Erro ao carregar dashboard: {e}")
        return f"<h1>Erro ao carregar o dashboard.</h1><p>Verifique os nomes das colunas na planilha. Erro: {e}</p>"

# --- 5. ROTA DE GERENCIAMENTO (Listar e Editar Chamados) ---

@app.route('/gerenciar')
def gerenciar():
    """Exibe a página de gerenciamento com a lista de todos os chamados."""
    try:
        sort_by = request.args.get('sort_by', 'Carimbo de data/hora')
        order = request.args.get('order', 'desc')
        
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
        print(f"Erro ao carregar gerenciador: {e}")
        return f"<h1>Erro ao carregar o gerenciador.</h1><p>Erro: {e}</p>"

# --- 6. ROTA DE ATUALIZAÇÃO (Recebe dados do Modal de Edição) ---

@app.route('/atualizar_chamado', methods=['POST'])
def atualizar_chamado():
    """Atualiza uma linha inteira na planilha com os dados do modal de edição."""
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

        print(f"Chamado (Linha {row_id}) atualizado com status: {status_os}")

        return redirect(url_for('gerenciar'))
        
    except Exception as e:
        print(f"Erro ao atualizar chamado: {e}")
        return f"<h1>Erro ao atualizar o chamado.</h1><p>Erro: {e}</p>"

# --- 7. ROTA DE SUCESSO (Página de confirmação) ---

@app.route('/sucesso')
def sucesso():
    """Página de sucesso (para caso o /enviar fosse GET)."""
    return render_template('sucesso.html', nome="Usuário")


# --- 8. ROTA DE CONSULTA DE STATUS (NOVA) ---

@app.route('/consultar', methods=['GET', 'POST'])
def consultar_pedido():
    """Página pública para um solicitante consultar o status de um pedido."""
    resultado = None
    pedido_buscado = None

    if request.method == 'POST':
        pedido_buscado = request.form.get('numero_pedido')
    elif request.method == 'GET' and 'numero_pedido' in request.args:
        pedido_buscado = request.args.get('numero_pedido')
    
    if pedido_buscado:
        try:
            # sheet.find() procura pela string formatada, o que é perfeito para nós
            cell = sheet.find(str(pedido_buscado), in_column=1) 
            
            if cell:
                all_data = sheet.row_values(cell.row)
                
                resultado = {
                    'id': all_data[0],       # Col A (ID)
                    'data': all_data[4],     # Col E (Data Solicitação)
                    'descricao': all_data[5], # Col F (Descrição)
                    'status': all_data[8]    # Col I (Status)
                }
            else:
                resultado = {'erro': f"Pedido número '{pedido_buscado}' não encontrado."}
        
        except Exception as e:
            print(f"Erro ao buscar pedido: {e}")
            resultado = {'erro': 'Ocorreu um erro ao consultar o pedido.'}
    
    return render_template('consultar.html', resultado=resultado, pedido_buscado=pedido_buscado)


# --- Ponto de Entrada Principal ---
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # debug=False é crucial para produção
    # host='0.0.0.0' permite que o Render se conecte
    app.run(host='0.0.0.0', port=port, debug=False)



