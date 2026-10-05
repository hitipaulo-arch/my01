"""Integração com provedores de IA usada pelo painel administrativo."""

import logging
import os

from flask import current_app

from appmodules.utils.validators import _parse_int_field

try:
    from openai import OpenAI as _OpenAI
except ImportError:  # pragma: no cover
    _OpenAI = None

logger = logging.getLogger(__name__)


def get_nvidia_ai_client(openai_cls=None):
    """Cria o cliente da IA com suporte a NVIDIA, OpenAI e Ollama."""
    client_class = _OpenAI if openai_cls is None else openai_cls
    if client_class is None:
        raise RuntimeError("A biblioteca 'openai' não está instalada.")

    provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()
    nvidia_key = os.getenv("NVIDIA_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()

    if provider == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1").strip()
        api_key = os.getenv("OLLAMA_API_KEY", "ollama").strip() or "ollama"
        if not base_url:
            raise RuntimeError(
                "A variável de ambiente OLLAMA_BASE_URL não foi configurada. "
                "Use http://localhost:11434/v1 em desenvolvimento."
            )
        return client_class(base_url=base_url, api_key=api_key)

    if provider == "openai":
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
        api_key = openai_key or nvidia_key
        if not api_key:
            raise RuntimeError(
                "A variável de ambiente OPENAI_API_KEY não foi configurada. "
                "Defina a chave antes de usar a IA do painel administrativo."
            )
        return client_class(base_url=base_url, api_key=api_key)

    api_key = nvidia_key or openai_key
    if not api_key:
        raise RuntimeError(
            "Nenhuma chave de IA configurada. Defina NVIDIA_API_KEY, OPENAI_API_KEY "
            "ou use AI_PROVIDER=ollama com OLLAMA_BASE_URL."
        )

    return client_class(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
    )


def get_ai_model_candidates():
    """Retorna uma lista priorizada de modelos que ainda estão disponíveis."""
    provider = os.getenv("AI_PROVIDER", "ollama").strip().lower()
    if provider == "ollama":
        return [os.getenv("OLLAMA_MODEL", "qwen2.5:3b").strip() or "qwen2.5:3b"]
    if provider == "openai":
        return [os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"]
    primary = os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct").strip()
    candidates = [primary] if primary else []
    candidates.extend(["meta/llama-3.1-8b-instruct", "microsoft/phi-3.5-mini-instruct"])
    dedup = []
    for model in candidates:
        if model and model not in dedup:
            dedup.append(model)
    return dedup


def get_ai_model_name():
    """Retorna o nome do modelo conforme o provedor configurado."""
    candidates = get_ai_model_candidates()
    return candidates[0] if candidates else "qwen2.5:3b"


def build_admin_ai_context():
    """Gera um contexto resumido do sistema para o chat do admin."""
    context_lines = [
        (
            "Você é um assistente do painel administrativo da empresa. "
            "Responda com base no contexto do sistema e em fatos reais do projeto."
        ),
        "Contexto do sistema:",
    ]

    sheets_service = current_app.config.get("sheets_service")
    try:
        if sheets_service:
            itens = sheets_service.get_all_producao(use_cache=True) or []
            total_itens = len(itens)
            status_counts = {}
            responsavel_counts = {}
            total_produzido = 0
            total_meta = 0

            for item in itens:
                status = str(item.get("Status", "")).strip() or "Sem status"
                status_counts[status] = status_counts.get(status, 0) + 1
                responsavel = str(item.get("Responsável", "")).strip() or "Não atribuído"
                responsavel_counts[responsavel] = responsavel_counts.get(responsavel, 0) + 1
                total_produzido += _parse_int_field(item.get("Quantidade produzida", 0), 0)
                total_meta += _parse_int_field(item.get("Meta de produção", 0), 0)

            context_lines.append(f"- Total de itens de produção: {total_itens}")
            context_lines.append(f"- Produção acumulada: {total_produzido} / meta total {total_meta}")
            if status_counts:
                context_lines.append("- Status dos itens: " + ", ".join(
                    f"{key}={value}" for key, value in sorted(status_counts.items())
                ))
            if responsavel_counts:
                context_lines.append("- Responsáveis: " + ", ".join(
                    f"{key}={value}" for key, value in sorted(responsavel_counts.items())
                ))

            itens_abertos = [
                item for item in itens
                if str(item.get("Status", "")).strip().lower()
                not in {"concluído", "concluido", "bloqueado", "bloqueada", "cancelado", "cancelada"}
            ]
            if itens_abertos:
                context_lines.append("- Itens em aberto: " + ", ".join(
                    str(item.get("Nome do item", "Sem nome")) for item in itens_abertos[:5]
                ))
        else:
            context_lines.append("- Dados da produção indisponíveis no momento.")
    except (RuntimeError, ValueError, TypeError, OSError, AttributeError, KeyError) as exc:
        logger.warning("Não foi possível montar o contexto do sistema para o chat admin: %s", exc)
        context_lines.append("- Não foi possível recuperar contexto adicional do sistema.")

    return "\n".join(context_lines)
