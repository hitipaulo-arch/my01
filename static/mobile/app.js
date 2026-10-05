/* ==========================================================================
   App mobile (PWA) — comportamento compartilhado
   --------------------------------------------------------------------------
   Responsabilidades:
     • registrar o service worker (cache do shell + tela offline);
     • indicar estado offline e oferecer recarga;
     • exibir o banner/atalho de instalação na tela inicial;
     • utilitários reaproveitados das telas web: máscaras de código/MTC,
       filtro cliente-side e confirmação de exclusão.
   Nenhuma regra de negócio: os formulários continuam postando nas rotas
   Flask existentes (/enviar, /atualizar_chamado, /producao/atualizar/...).
   ========================================================================== */
(function () {
    "use strict";

    var meta = document.querySelector('meta[name="mobile-app-prefix"]');
    var PREFIX = (meta && meta.content) || "/m";
    var SW_URL = PREFIX + "/service-worker.js";

    /* ---------------------------------------------------------------- offline */
    function updateConnectivity() {
        var online = navigator.onLine;
        document.body.classList.toggle("m-offline", !online);
        var bar = document.getElementById("m-offline-text");
        if (bar) {
            bar.textContent = online
                ? "Conexão restabelecida"
                : "Sem conexão — os dados podem estar desatualizados";
        }
    }

    window.addEventListener("online", updateConnectivity);
    window.addEventListener("offline", updateConnectivity);

    /* --------------------------------------------------------- service worker */
    if ("serviceWorker" in navigator) {
        window.addEventListener("load", function () {
            navigator.serviceWorker.register(SW_URL, { scope: PREFIX + "/" }).catch(function (err) {
                // Em desenvolvimento (http://localhost) o registro é permitido;
                // em previews sem HTTPS pode falhar — o app segue funcionando.
                console.warn("[PWA] Service worker não registrado:", err && err.message);
            });
        });
    }

    /* -------------------------------------------------------- instalar app */
    var deferredPrompt = null;
    var installButtons = document.querySelectorAll("[data-m-install]");
    var DISMISS_KEY = "gestaoos_install_dismissed";

    function jaInstalado() {
        return (
            window.matchMedia("(display-mode: standalone)").matches ||
            window.navigator.standalone === true
        );
    }

    window.addEventListener("beforeinstallprompt", function (event) {
        event.preventDefault();
        deferredPrompt = event;
        if (!localStorage.getItem(DISMISS_KEY)) {
            document.body.classList.add("m-can-install");
        }
    });

    window.addEventListener("appinstalled", function () {
        deferredPrompt = null;
        document.body.classList.remove("m-can-install");
        showToast("App instalado na tela inicial 🎉");
    });

    // iOS/Safari não dispara beforeinstallprompt: mostramos o convite com o
    // passo a passo (Compartilhar → Adicionar à Tela de Início) uma vez.
    (function conviteIOS() {
        var ehIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
        if (ehIOS && !jaInstalado() && !localStorage.getItem(DISMISS_KEY)) {
            document.body.classList.add("m-can-install");
        }
    })();

    function triggerInstall() {
        if (!deferredPrompt) {
            window.location.href = PREFIX + "/instalar";
            return;
        }
        deferredPrompt.prompt();
        deferredPrompt.userChoice.then(function (choice) {
            if (choice && choice.outcome === "accepted") {
                document.body.classList.remove("m-can-install");
            }
            deferredPrompt = null;
        });
    }

    installButtons.forEach(function (btn) {
        btn.addEventListener("click", function (event) {
            event.preventDefault();
            triggerInstall();
        });
    });

    document.querySelectorAll("[data-m-install-dismiss]").forEach(function (btn) {
        btn.addEventListener("click", function (event) {
            event.preventDefault();
            document.body.classList.remove("m-can-install");
            try {
                localStorage.setItem(DISMISS_KEY, "1");
            } catch (e) {
                /* modo privado: ignora */
            }
        });
    });

    /* --------------------------------------------------------------- toast */
    function showToast(message, variant) {
        var existing = document.querySelector(".m-toast");
        if (existing) existing.remove();

        var toast = document.createElement("div");
        toast.className = "m-alert m-alert-" + (variant || "info") + " m-toast";
        toast.style.position = "fixed";
        toast.style.left = "12px";
        toast.style.right = "12px";
        toast.style.bottom = "calc(var(--m-tabbar-height) + env(safe-area-inset-bottom, 0px) + 16px)";
        toast.style.zIndex = "1080";
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(function () {
            toast.remove();
        }, 3200);
    }
    window.mShowToast = showToast;

    /* ------------------------------------------------------- confirm nativo */
    document.querySelectorAll("form[data-m-confirm]").forEach(function (form) {
        form.addEventListener("submit", function (event) {
            var msg = form.getAttribute("data-m-confirm") || "Confirmar ação?";
            if (!window.confirm(msg)) {
                event.preventDefault();
            }
        });
    });

    /* ------------------------------------------------ máscaras (igual ao web) */
    function formatarCodigoCode(valor) {
        var digits = String(valor || "").replace(/\D/g, "").slice(0, 9);
        if (digits.length <= 2) return digits;
        if (digits.length <= 4) return digits.slice(0, 2) + "-" + digits.slice(2);
        return digits.slice(0, 2) + "-" + digits.slice(2, 4) + "-" + digits.slice(4);
    }

    function formatarMtcCode(valor) {
        return String(valor || "").replace(/\D/g, "").slice(0, 4);
    }

    function aplicarMascara(seletor, formatador, inputMode) {
        document.querySelectorAll(seletor).forEach(function (input) {
            if (inputMode) input.setAttribute("inputmode", inputMode);
            input.addEventListener("input", function () {
                var cursorNoFim = this.selectionStart === this.value.length;
                this.value = formatador(this.value);
                if (cursorNoFim) {
                    this.setSelectionRange(this.value.length, this.value.length);
                }
            });
            input.addEventListener("blur", function () {
                this.value = formatador(this.value);
            });
        });
    }

    aplicarMascara(".js-codigo-code", formatarCodigoCode, "numeric");
    aplicarMascara(".js-mtc-code", formatarMtcCode, "numeric");

    /* -------------------------------------------------- filtro cliente-side */
    document.querySelectorAll("[data-m-filter]").forEach(function (input) {
        var alvoSeletor = input.getAttribute("data-m-filter");
        input.addEventListener("input", function () {
            var termo = this.value.toLowerCase().trim();
            document.querySelectorAll(alvoSeletor).forEach(function (item) {
                var texto = (item.textContent || "").toLowerCase();
                item.style.display = termo === "" || texto.indexOf(termo) > -1 ? "" : "none";
            });
        });
    });

    /* --------------------------------------------------- chips de filtro */
    document.querySelectorAll("[data-m-chip-filter]").forEach(function (chip) {
        chip.addEventListener("click", function (event) {
            event.preventDefault();

            var alvoSeletor = chip.getAttribute("data-m-chip-filter");
            var valor = (chip.getAttribute("data-m-chip-value") || "").toLowerCase().trim();
            var grupo = chip.getAttribute("data-m-chip-group") || "default";
            var contadorSeletor = chip.getAttribute("data-m-chip-count");

            document
                .querySelectorAll('[data-m-chip-group="' + grupo + '"]')
                .forEach(function (outro) {
                    outro.classList.remove("m-chip-active");
                });
            chip.classList.add("m-chip-active");

            var visiveis = 0;
            document.querySelectorAll(alvoSeletor).forEach(function (item) {
                var texto = (item.textContent || "").toLowerCase();
                var mostrar = valor === "" || texto.indexOf(valor) > -1;
                item.style.display = mostrar ? "" : "none";
                if (mostrar) visiveis += 1;
            });

            if (contadorSeletor) {
                var contador = document.querySelector(contadorSeletor);
                if (contador) contador.textContent = String(visiveis);
            }
        });
    });

    /* ------------------------------------------------ links wa.me automático */
    function normalizarWhatsApp(numero) {
        if (!numero) return "";
        var digitos = String(numero).replace(/\D/g, "");
        if (!digitos) return "";
        if (digitos.indexOf("55") !== 0) {
            digitos = "55" + digitos;
        }
        return digitos;
    }

    document.querySelectorAll("[data-whatsapp]").forEach(function (el) {
        var numero = normalizarWhatsApp(el.getAttribute("data-whatsapp"));
        if (numero && el.tagName === "A") {
            el.href = "https://wa.me/" + numero;
        }
    });

    window.mNormalizarWhatsApp = normalizarWhatsApp;

    /* --------------------------------------------- recarrega ao voltar online */
    document.querySelectorAll("[data-m-reload]").forEach(function (btn) {
        btn.addEventListener("click", function () {
            window.location.reload();
        });
    });

    /* ------------------------------------------------- sessão expirada (AJAX)
       Várias telas postam via fetch (produção, centrais, ferramentas). Quando a
       sessão expira, o Flask responde com o HTML da tela de login e o usuário
       via apenas "erro ao atualizar". Aqui detectamos o desvio para o login e
       levamos de volta à tela de acesso, avisando o motivo. */
    (function interceptarSessaoExpirada() {
        if (typeof window.fetch !== "function") return;

        var fetchOriginal = window.fetch;
        var avisando = false;

        window.fetch = function () {
            return fetchOriginal.apply(this, arguments).then(function (resp) {
                var destino = resp.url || "";
                var expirou =
                    resp.status === 401 || (resp.redirected && destino.indexOf("/login") > -1);

                if (expirou && !avisando) {
                    avisando = true;
                    showToast("Sessão expirada. Faça login novamente.", "warning");
                    setTimeout(function () {
                        var atual = encodeURIComponent(window.location.pathname);
                        window.location.href = PREFIX + "/login?next=" + atual;
                    }, 1200);
                }
                return resp;
            });
        };
    })();

    updateConnectivity();
})();
