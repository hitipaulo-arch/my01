"""Sistema de Ordens de Serviço — pacote de aplicação.

O pacote é mantido **leve** de propósito: o app de produção por setor
(``appmodules/producao_web``) é importado por um programa separado e não deve
carregar a configuração do sistema de OS (que exige ``SECRET_KEY``).

A factory fica em :mod:`appmodules.app_factory` e é exposta sob demanda:

    from appmodules import create_app   # importa a factory só quando usada
"""

__version__ = "2.0.0"
__author__ = "Gestão OS Team"

__all__ = ["create_app", "__version__", "__author__"]


def __getattr__(name):
    """Importa a factory (e só ela) quando alguém pedir ``create_app``."""

    if name == "create_app":
        from appmodules.app_factory import create_app

        return create_app
    raise AttributeError(f"module 'appmodules' has no attribute {name!r}")
