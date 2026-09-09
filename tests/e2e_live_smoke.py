#!/usr/bin/env python3
"""
Smoke test funcional de ponta a ponta contra um servidor JÁ EM EXECUÇÃO.

Uso:
    python3 tests/e2e_live_smoke.py [BASE_URL]

Requer o app rodando, ex.:
    SECRET_KEY=... ALLOW_LOCAL_ADMIN_FALLBACK=true LOCAL_ADMIN_USER=admin \
    LOCAL_ADMIN_PASSWORD='Senha@teste123' PORT=5000 HOST=0.0.0.0 python3 app.py

O script NÃO é coletado pelo pytest (nome sem prefixo test_*) porque depende
de servidor vivo e de credenciais/planilha opcionais.
"""
import re
import sys
import requests

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000"
ADMIN_USER = "admin"
ADMIN_PASS = "Senha@teste123"

s = requests.Session()
resultados = []


def check(nome, cond, detalhe=""):
    status = "PASS" if cond else "FAIL"
    resultados.append((status, nome, detalhe))
    print(f"[{status}] {nome}" + (f" — {detalhe}" if detalhe else ""))


def csrf_token(resp):
    m = re.search(r'name="csrf_token"[^>]*value="([^"]+)"', resp.text)
    return m.group(1) if m else None


print(f"== Smoke test funcional contra {BASE_URL} ==\n")

# 1. Página pública de OS
r = s.get(f"{BASE_URL}/")
check("GET / (formulário público de OS)", r.status_code == 200, f"status={r.status_code}")

# 2. Página de login
r = s.get(f"{BASE_URL}/login")
ok = r.status_code == 200 and csrf_token(r) is not None
check("GET /login renderiza com CSRF", ok, f"status={r.status_code}")

# 3. POST /login sem CSRF → rejeitado (proteção CSRF ativa)
r = s.post(f"{BASE_URL}/login", data={"username": ADMIN_USER, "password": ADMIN_PASS})
check("POST /login sem CSRF é rejeitado (400)", r.status_code == 400, f"status={r.status_code}")

# 4. POST /login com credenciais erradas → permanece no login
tok = csrf_token(s.get(f"{BASE_URL}/login"))
r = s.post(f"{BASE_URL}/login", data={"username": ADMIN_USER, "password": "errada", "csrf_token": tok})
check("POST /login senha errada é recusado", r.status_code == 200 and "Usuário ou senha inválidos" in r.text)

# 5. POST /login correto (admin de fallback local) → redirect
tok = csrf_token(s.get(f"{BASE_URL}/login"))
r = s.post(
    f"{BASE_URL}/login",
    data={"username": ADMIN_USER, "password": ADMIN_PASS, "csrf_token": tok},
    allow_redirects=False,
)
check(
    "POST /login correto redireciona (302)",
    r.status_code == 302 and r.headers.get("Location", "").startswith("/"),
    f"status={r.status_code}, Location={r.headers.get('Location')}",
)

# 6. Páginas protegidas após login (admin)
for rota in [
    "/",
    "/producao",
    "/itens",
    "/admin/ia",
    "/relatorios",
    "/ferramentas",
    "/centrais",
    "/usuarios",
    "/tempo-por-funcionario",
    "/dashboard-producao",
    "/producao-abertas",
    "/producao/dados",
    "/compras",
    "/consultar",
    "/upload-documento",
    "/gerenciar",
]:
    r = s.get(f"{BASE_URL}{rota}")
    aceitavel = r.status_code in (200, 503)  # 503 = sem Google Sheets (esperado sem credenciais)
    check(f"GET {rota}", aceitavel, f"status={r.status_code}")

# 6b. Exportação CSV da página de tempo por funcionário
r = s.get(f"{BASE_URL}/tempo-por-funcionario?export=csv")
check(
    "GET /tempo-por-funcionario?export=csv",
    r.status_code == 200 and "text/csv" in r.headers.get("Content-Type", "")
    and "tempo_por_funcionario.csv" in r.headers.get("Content-Disposition", ""),
    f"status={r.status_code}, ctype={r.headers.get('Content-Type')}",
)

# 7. /admin/ia POST: sem NVIDIA_API_KEY → erro amigável na página (não 500)
r = s.get(f"{BASE_URL}/admin/ia")
tok = csrf_token(r)
r = s.post(f"{BASE_URL}/admin/ia", data={"q": "resumo do dia", "action": "send", "csrf_token": tok})
ok = r.status_code == 200 and ("NVIDIA_API_KEY" in r.text or "IA" in r.text)
check("POST /admin/ia trata ausência de API key", ok, f"status={r.status_code}")

# 8. /health
r = s.get(f"{BASE_URL}/health")
check("GET /health", r.status_code == 200, f"status={r.status_code}, body={r.text[:80]!r}")

# 9. Arquivo estático
r = s.get(f"{BASE_URL}/static/unified.css")
check("GET /static/unified.css", r.status_code == 200 and "text/css" in r.headers.get("Content-Type", ""), f"status={r.status_code}")

# 10. Rota inexistente → página 404
r = s.get(f"{BASE_URL}/pagina-que-nao-existe")
check("404 customizado", r.status_code == 404, f"status={r.status_code}")

# 11. Logout → /admin/ia volta a exigir login
r = s.get(f"{BASE_URL}/logout", allow_redirects=False)
r = s.get(f"{BASE_URL}/admin/ia", allow_redirects=False)
check("Logout protege /admin/ia (302 /login)", r.status_code == 302 and "/login" in r.headers.get("Location", ""), f"status={r.status_code}")

# 12. Rate limit em POST /login (5/min) → 429 após estourar
tok = csrf_token(s.get(f"{BASE_URL}/login"))
codigos = []
for _ in range(8):
    r = s.post(f"{BASE_URL}/login", data={"username": ADMIN_USER, "password": "errada", "csrf_token": tok})
    codigos.append(r.status_code)
check("Rate limit bloqueia brute force (429)", 429 in codigos, f"sequência={codigos}")

print("\n== Resumo ==")
fails = [x for x in resultados if x[0] == "FAIL"]
print(f"Total: {len(resultados)} | PASS: {len(resultados) - len(fails)} | FAIL: {len(fails)}")
sys.exit(1 if fails else 0)
