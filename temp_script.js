
        let editModal;
        let programacaoModal;
        let programacaoEstados = [];
        let programacaoTotalPortas = 0;
        
        document.addEventListener('DOMContentLoaded', function() {
            editModal = new bootstrap.Modal(document.getElementById('editModal'));
            programacaoModal = new bootstrap.Modal(document.getElementById('programacaoModal'));
            renderAllProgramSummaries();
        });

        function formatProgramacaoSummaryFromEstados(estados) {
            // estados: array where each index is an array of selected column indices
            const parts = [];
            for (let i = 0; i < estados.length; i++) {
                const cols = Array.isArray(estados[i]) ? estados[i] : [];
                if (!cols || cols.length === 0) continue;
                const colsText = cols.map(c => (c + 1)).join(',');
                parts.push(`${i + 1}â†’${colsText}`);
            }
            return parts.join('; ');
        }

        function parseProgramacaoToEstados(raw, totalPortas) {
            return normalizarProgramacao(raw, totalPortas);
        }

        function renderSummaryElement(el) {
            try {
                const resumoPreferido = el.getAttribute('data-programacao-resumo');
                if (resumoPreferido && String(resumoPreferido).trim()) {
                    el.textContent = resumoPreferido;
                    return;
                }

                const raw = el.getAttribute('data-programacao') || '';
                const portas = parseInt(el.getAttribute('data-portas') || '0', 10) || 0;
                const estados = parseProgramacaoToEstados(raw, portas);
                const summary = formatProgramacaoSummaryFromEstados(estados);
                el.textContent = summary || 'â€”';
            } catch (e) {
                el.textContent = 'â€”';
            }
        }

        function renderAllProgramSummaries() {
            document.querySelectorAll('[id^="program-summary-"]').forEach(function(el) {
                renderSummaryElement(el);
            });
        }

        function normalizarProgramacao(valor, totalPortas) {
            const selecoes = Array.from({ length: totalPortas }, () => []);

            if (!valor) {
                return selecoes;
            }

            try {
                const parsed = JSON.parse(valor);

                if (Array.isArray(parsed)) {
                    if (parsed.length && Array.isArray(parsed[0])) {
                        parsed.forEach((linha, rowIndex) => {
                            if (rowIndex >= totalPortas || !Array.isArray(linha)) {
                                return;
                            }

                            const colunasSelecionadas = linha
                                .map((celula, colunaIndex) => String(celula || '').trim().toUpperCase() === 'X' ? colunaIndex : null)
                                .filter((colunaIndex) => colunaIndex !== null);

                            selecoes[rowIndex] = colunasSelecionadas;
                        });
                    } else {
                        parsed.forEach((item, rowIndex) => {
                            if (rowIndex >= totalPortas || item === null || item === '') {
                                return;
                            }

                            if (Array.isArray(item)) {
                                selecoes[rowIndex] = item
                                    .map((numero) => parseInt(numero, 10) - 1)
                                    .filter((numero) => Number.isInteger(numero) && numero >= 0 && numero < totalPortas);
                                return;
                            }

                            const numero = parseInt(item, 10);
                            if (!Number.isNaN(numero) && numero >= 1 && numero <= totalPortas) {
                                selecoes[rowIndex] = [numero - 1];
                            }
                        });
                    }
                }

                if (parsed && typeof parsed === 'object' && Array.isArray(parsed.selecoes)) {
                    parsed.selecoes.forEach((item, rowIndex) => {
                        if (rowIndex >= totalPortas || item === null || item === '') {
                            return;
                        }

                        if (Array.isArray(item)) {
                            selecoes[rowIndex] = item
                                .map((numero) => parseInt(numero, 10) - 1)
                                .filter((numero) => Number.isInteger(numero) && numero >= 0 && numero < totalPortas);
                            return;
                        }

                        const numero = parseInt(item, 10);
                        if (!Number.isNaN(numero) && numero >= 1 && numero <= totalPortas) {
                            selecoes[rowIndex] = [numero - 1];
                        }
                    });
                }
            } catch (error) {
                return selecoes;
            }

            return selecoes;
        }

        function renderProgramacaoGrid() {
            const container = document.getElementById('programacao_grid');
            const totalPortas = programacaoTotalPortas;

            if (!container) {
                return;
            }

            if (!totalPortas || totalPortas <= 0) {
                container.innerHTML = '<div class="alert alert-warning mb-0">NÃºmero de portas invÃ¡lido para montar a programaÃ§Ã£o.</div>';
                return;
            }

            const tabela = document.createElement('table');
            tabela.className = 'table table-bordered align-middle text-center programacao-table mb-0';

            const thead = document.createElement('thead');
            thead.className = 'table-light';
            const headerRow = document.createElement('tr');
            const cornerCell = document.createElement('th');
            cornerCell.className = 'programacao-label';
            cornerCell.textContent = 'Aberta / Fechada';
            headerRow.appendChild(cornerCell);

            for (let coluna = 0; coluna < totalPortas; coluna += 1) {
                const th = document.createElement('th');
                th.className = 'programacao-label';
                th.textContent = `Fechada ${coluna + 1}`;
                headerRow.appendChild(th);
            }
            thead.appendChild(headerRow);
            tabela.appendChild(thead);

            const tbody = document.createElement('tbody');

            for (let linha = 0; linha < totalPortas; linha += 1) {
                const tr = document.createElement('tr');
                const rowLabel = document.createElement('th');
                rowLabel.scope = 'row';
                rowLabel.className = 'programacao-label';
                rowLabel.textContent = `Aberta ${linha + 1}`;
                tr.appendChild(rowLabel);

                for (let coluna = 0; coluna < totalPortas; coluna += 1) {
                    const td = document.createElement('td');
                    const button = document.createElement('button');
                    button.type = 'button';
                    button.className = 'programacao-cell';
                    const linhaAtual = Array.isArray(programacaoEstados[linha]) ? programacaoEstados[linha] : [];
                    const estaAtivo = linhaAtual.includes(coluna);
                    button.textContent = estaAtivo ? 'X' : '';
                    if (estaAtivo) {
                        button.classList.add('active');
                    } else {
                        button.classList.add('empty');
                    }
                    button.addEventListener('click', function() {
                        const selecionados = Array.isArray(programacaoEstados[linha]) ? [...programacaoEstados[linha]] : [];
                        const indice = selecionados.indexOf(coluna);

                        if (indice >= 0) {
                            selecionados.splice(indice, 1);
                        } else {
                            selecionados.push(coluna);
                        }

                        programacaoEstados[linha] = selecionados.sort((a, b) => a - b);
                        renderProgramacaoGrid();
                    });
                    td.appendChild(button);
                    tr.appendChild(td);
                }

                tbody.appendChild(tr);
            }

            tabela.appendChild(tbody);
            container.innerHTML = '';
            container.appendChild(tabela);
        }

        function abrirProgramacao(rowId, totalPortas, programacaoAtual) {
            programacaoTotalPortas = parseInt(totalPortas, 10) || 0;
            programacaoEstados = normalizarProgramacao(programacaoAtual, programacaoTotalPortas);

            document.getElementById('programacao_row_id').value = rowId;
            document.getElementById('programacao_total_portas').value = programacaoTotalPortas;
            document.getElementById('programacao_matrix_data').value = programacaoAtual || '';

            renderProgramacaoGrid();
            programacaoModal.show();
        }

        function salvarProgramacao() {
            const rowId = document.getElementById('programacao_row_id').value;
            const formData = new FormData();
            formData.append('csrf_token', '{{ csrf_token() }}');
            formData.append('programacao', JSON.stringify({ selecoes: programacaoEstados.map((item) => Array.isArray(item) ? item.map((coluna) => coluna + 1) : []) }));

            fetch(`/centrais/programacao/${rowId}`, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('programacao_alert_container');
                    if (data.success) {
                        container.innerHTML = '<div class="alert alert-success">' + data.message + '</div>';

                        // Atualiza o botÃ£o na tabela para indicar sucesso sem recarregar
                        try {
                            const btn = document.getElementById('program-btn-' + rowId);
                            if (btn) {
                                btn.classList.remove('btn-outline-primary');
                                btn.classList.add('btn-success');
                                btn.textContent = 'âš™ï¸ ProgramaÃ§Ã£o âœ“';
                            }
                        } catch (e) {
                            console.warn('NÃ£o foi possÃ­vel atualizar botÃ£o da tabela', e);
                        }

                        // Atualiza o resumo na tabela usando o estado atual em memÃ³ria
                        try {
                            const summaryEl = document.getElementById('program-summary-' + rowId);
                            if (summaryEl) {
                                // atualiza atributo data-programacao para refletir novo valor
                                const novoRaw = JSON.stringify({ selecoes: programacaoEstados.map((item) => Array.isArray(item) ? item.map((c) => c + 1) : []) });
                                summaryEl.setAttribute('data-programacao', novoRaw);
                                // se o servidor retornou o resumo, use-o; caso contrÃ¡rio, recalcule localmente
                                if (data.resumo) {
                                    summaryEl.setAttribute('data-programacao-resumo', data.resumo);
                                } else {
                                    summaryEl.removeAttribute('data-programacao-resumo');
                                }
                                renderSummaryElement(summaryEl);
                            }
                        } catch (e) {
                            console.warn('NÃ£o foi possÃ­vel atualizar resumo da tabela', e);
                        }

                        // Fecha o modal apÃ³s um curto delay
                        setTimeout(() => {
                            container.innerHTML = '';
                            programacaoModal.hide();
                        }, 900);
                    } else {
                        container.innerHTML = '<div class="alert alert-danger">Erro: ' + data.message + '</div>';
                    }
            })
            .catch(error => {
                const container = document.getElementById('programacao_alert_container');
                container.innerHTML = '<div class="alert alert-danger">Erro ao salvar programaÃ§Ã£o: ' + error + '</div>';
            });
        }
        
        function editarCentral(rowId, status, obra) {
            document.getElementById('edit_row_id').value = rowId;
            document.getElementById('edit_status').value = status;
            document.getElementById('edit_obra').value = obra;
            editModal.show();
        }
        
        function salvarEdicao() {
            const rowId = document.getElementById('edit_row_id').value;
            const formData = new FormData(document.getElementById('editForm'));
            
            fetch(`/centrais/atualizar/${rowId}`, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert('Erro: ' + data.message);
                }
            })
            .catch(error => {
                alert('Erro ao atualizar: ' + error);
            });
        }
        
        function deletarCentral(rowId) {
            if (!confirm('Tem certeza que deseja deletar esta central?')) {
                return;
            }
            
            const formData = new FormData();
            formData.append('csrf_token', '{{ csrf_token() }}');
            
            fetch(`/centrais/deletar/${rowId}`, {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert(data.message);
                    location.reload();
                } else {
                    alert('Erro: ' + data.message);
                }
            })
            .catch(error => {
                alert('Erro ao deletar: ' + error);
            });
        }
    
