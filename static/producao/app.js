/* ==========================================================================
   App de produção — comportamento compartilhado
   --------------------------------------------------------------------------
   Responsabilidades:
     • registrar o service worker (cache do shell + tela offline);
     • indicar estado offline e oferecer recarga;
     • exibir o convite de instalação (Android/desktop e instruções no iOS);
     • filtro instantâneo das listas, máscaras de código/MTC/prazo e confirmação;
     • marcar o status do setor sem recarregar a página.
   Nenhuma regra de negócio: os formulários postam nas rotas Flask do app.
   ========================================================================== */
(function () {
    "use strict";

    var SW_URL = "/service-worker.js";
    var DISMISS_KEY = "producao_install_dismissed";

    /* ---------------------------------------------------------------- offline */
    function updateConnectivity() {
        var online = navigator.onLine;
        document.body.classList.toggle("p-offline", !online);
        var barra = document.getElementById("p-offline-text");
        if (barra) {
            barra.textContent = online
                ? "Conexão restabelecida"
                : "Sem conexão — os status podem não gravar";
        }
    }

    window.addEventListener("online", updateConnectivity);
    window.addEventListener("offline", updateConnectivity);

    /* --------------------------------------------------------- service worker */
    if ("serviceWorker" in navigator) {
        window.addEventListener("load", function () {
            navigator.serviceWorker.register(SW_URL, { scope: "/" }).catch(function (erro) {
                console.warn("[produção] Service worker não registrado:", erro && erro.message);
            });
        });
    }

    /* ------------------------------------------------------------ instalação */
    var deferredPrompt = null;

    function jaInstalado() {
        return (
            window.matchMedia("(display-mode: standalone)").matches ||
            window.navigator.standalone === true
        );
    }

    window.addEventListener("beforeinstallprompt", function (evento) {
        evento.preventDefault();
        deferredPrompt = evento;
        if (!localStorage.getItem(DISMISS_KEY)) {
            document.body.classList.add("p-can-install");
        }
    });

    window.addEventListener("appinstalled", function () {
        deferredPrompt = null;
        document.body.classList.remove("p-can-install");
        showToast("App instalado na tela inicial 🎉", "success");
    });

    (function conviteIOS() {
        var ehIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
        if (ehIOS && !jaInstalado() && !localStorage.getItem(DISMISS_KEY)) {
            document.body.classList.add("p-can-install");
        }
    })();

    document.querySelectorAll("[data-p-install]").forEach(function (botao) {
        botao.addEventListener("click", function (evento) {
            evento.preventDefault();
            if (!deferredPrompt) {
                window.location.href = "/instalar";
                return;
            }
            deferredPrompt.prompt();
            deferredPrompt.userChoice.then(function (escolha) {
                if (escolha && escolha.outcome === "accepted") {
                    document.body.classList.remove("p-can-install");
                }
                deferredPrompt = null;
            });
        });
    });

    document.querySelectorAll("[data-p-install-dismiss]").forEach(function (botao) {
        botao.addEventListener("click", function (evento) {
            evento.preventDefault();
            document.body.classList.remove("p-can-install");
            try {
                localStorage.setItem(DISMISS_KEY, "1");
            } catch (erro) {
                /* janela privada: ignora */
            }
        });
    });

    /* ----------------------------------------------------------------- toast */
    function showToast(mensagem, variante) {
        var antigo = document.querySelector(".p-toast");
        if (antigo) antigo.remove();

        var toast = document.createElement("div");
        toast.className = "p-alert p-alert-" + (variante || "info") + " p-toast";
        toast.setAttribute("role", "status");
        toast.textContent = mensagem;
        document.body.appendChild(toast);
        setTimeout(function () {
            toast.remove();
        }, 3200);
    }
    window.pShowToast = showToast;

    /* ------------------------------------------------------------- recarregar */
    document.querySelectorAll("[data-p-reload]").forEach(function (botao) {
        botao.addEventListener("click", function () {
            window.location.reload();
        });
    });

    /* ---------------------------------------------------------- confirmações */
    document.querySelectorAll("form[data-p-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (evento) {
            var mensagem = form.getAttribute("data-p-confirm") || "Confirmar ação?";
            if (!window.confirm(mensagem)) {
                evento.preventDefault();
            }
        });
    });

    /* -------------------------------------------------- filtro das listas */
    document.querySelectorAll("[data-p-filter]").forEach(function (campo) {
        var alvo = campo.getAttribute("data-p-filter");
        campo.addEventListener("input", function () {
            var termo = this.value.toLowerCase().trim();
            var visiveis = 0;
            document.querySelectorAll(alvo).forEach(function (item) {
                var texto = (item.textContent || "").toLowerCase();
                var mostrar = termo === "" || texto.indexOf(termo) > -1;
                item.style.display = mostrar ? "" : "none";
                if (mostrar) visiveis += 1;
            });
            var contador = document.getElementById("contadorOps");
            if (contador) contador.textContent = String(visiveis);
        });
    });

    /* ------------------------------------------- máscaras (iguais ao sistema) */
    function formatarCodigo(valor) {
        var digitos = String(valor || "").replace(/\D/g, "").slice(0, 9);
        if (digitos.length <= 2) return digitos;
        if (digitos.length <= 4) return digitos.slice(0, 2) + "-" + digitos.slice(2);
        return digitos.slice(0, 2) + "-" + digitos.slice(2, 4) + "-" + digitos.slice(4);
    }

    function formatarMtc(valor) {
        return String(valor || "").replace(/\D/g, "").slice(0, 4);
    }

    function formatarData(valor) {
        var digitos = String(valor || "").replace(/\D/g, "").slice(0, 8);
        if (digitos.length <= 2) return digitos;
        if (digitos.length <= 4) return digitos.slice(0, 2) + "/" + digitos.slice(2);
        return digitos.slice(0, 2) + "/" + digitos.slice(2, 4) + "/" + digitos.slice(4);
    }

    function aplicarMascara(seletor, formatador, modo) {
        document.querySelectorAll(seletor).forEach(function (campo) {
            if (modo) campo.setAttribute("inputmode", modo);
            campo.addEventListener("input", function () {
                var noFim = this.selectionStart === this.value.length;
                this.value = formatador(this.value);
                if (noFim) this.setSelectionRange(this.value.length, this.value.length);
            });
            campo.addEventListener("blur", function () {
                this.value = formatador(this.value);
            });
        });
    }

    aplicarMascara(".js-codigo-code", formatarCodigo, "numeric");
    aplicarMascara(".js-mtc-code", formatarMtc, "numeric");
    aplicarMascara('input[name="prazo"]', formatarData, "numeric");

    /* ------------------------------------- status do setor sem recarregar */
    function tokenCsrf() {
        var campo = document.querySelector('input[name="csrf_token"]');
        return campo ? campo.value : "";
    }

    document.querySelectorAll("form[data-p-quick]").forEach(function (form) {
        var campoStatus = form.querySelector('input[name="status"]');
        var botoes = form.querySelectorAll("button[type=submit]");

        botoes.forEach(function (botao) {
            botao.addEventListener("click", function (evento) {
                if (!window.fetch || !campoStatus) return; // sem JS: o POST normal funciona
                evento.preventDefault();

                var novoStatus = botao.getAttribute("data-p-valor") || botao.value || "";
                campoStatus.value = novoStatus;
                botoes.forEach(function (outro) {
                    outro.disabled = true;
                });

                fetch(form.action, {
                    method: "POST",
                    body: new FormData(form),
                    headers: { "X-Requested-With": "XMLHttpRequest" },
                })
                    .then(function (resposta) {
                        return resposta.json().catch(function () {
                            return { success: false, message: "Resposta inesperada do servidor." };
                        });
                    })
                    .then(function (dados) {
                        if (!dados.success) {
                            throw new Error(dados.message || "Não foi possível salvar.");
                        }
                        atualizarCartao(form, dados.status);
                        showToast(dados.message || "Status atualizado.", "success");
                    })
                    .catch(function (erro) {
                        showToast("Erro: " + erro.message, "danger");
                    })
                    .finally(function () {
                        botoes.forEach(function (outro) {
                            outro.disabled = false;
                        });
                    });
            });
        });
    });

    function atualizarCartao(form, status) {
        var caixa = form.closest(".p-flow-item");
        if (caixa) {
            caixa.classList.remove("st-pendente", "st-andamento", "st-concluido");
            caixa.classList.add(
                status === "Concluído" ? "st-concluido" : status === "Em andamento" ? "st-andamento" : "st-pendente"
            );
            var selo = caixa.querySelector(".p-selo");
            if (selo) {
                selo.textContent =
                    (status === "Concluído" ? "● " : status === "Em andamento" ? "◐ " : "○ ") + status;
                selo.className = "p-selo " + (status === "Concluído" ? "st-concluido" : status === "Em andamento" ? "st-andamento" : "st-pendente");
            }
        }

        // Na lista (fila): o cartão sai da fila quando o setor conclui.
        var card = form.closest(".p-card");
        if (card && status === "Concluído") {
            var acoes = card.querySelector(".p-acoes-rapidas");
            if (acoes) {
                acoes.innerHTML = '<span class="p-ok-setor">✔️ Seu setor concluiu</span>';
            }
        }
    }

    /* ---------------------------------------------- sessão expirada (AJAX) */
    (function interceptarSessaoExpirada() {
        if (typeof window.fetch !== "function") return;
        var fetchOriginal = window.fetch;
        var avisando = false;

        window.fetch = function () {
            return fetchOriginal.apply(this, arguments).then(function (resposta) {
                var destino = resposta.url || "";
                if ((resposta.status === 401 || (resposta.redirected && destino.indexOf("/login") > -1)) && !avisando) {
                    avisando = true;
                    showToast("Sessão expirada. Entre novamente.", "warning");
                    setTimeout(function () {
                        window.location.href = "/login";
                    }, 1200);
                }
                return resposta;
            });
        };
    })();

    updateConnectivity();
})();
