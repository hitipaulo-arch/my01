"""Gera os ícones do app de produção (PWA).

Uso:
    python scripts/gerar_icones_producao.py

Desenha a mesma identidade do sistema (gradiente #5d6bd6 → #7a5bc2) com uma
silhueta de fábrica em branco e grava os PNGs em ``static/producao/icons``:

* ``icon-192.png`` / ``icon-512.png``  — ícone normal (Android/desktop);
* ``icon-maskable-512.png``           — com área de segurança (Android adaptativo);
* ``apple-touch-icon.png``            — 180x180 para iOS;
* ``favicon-64.png``                  — aba do navegador.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

BASE = Path(__file__).resolve().parents[1]
DESTINO = BASE / "static" / "producao" / "icons"

INICIO = (93, 107, 214)   # #5d6bd6
FIM = (122, 91, 194)      # #7a5bc2


def gradiente(largura: int, altura: int) -> Image.Image:
    """Fundo em degradê na diagonal, igual ao resto do sistema."""

    pequeno = Image.new("RGB", (64, 64))
    pixels = pequeno.load()
    for y in range(64):
        for x in range(64):
            fator = (x + y) / 126
            pixels[x, y] = tuple(
                round(INICIO[i] + (FIM[i] - INICIO[i]) * fator) for i in range(3)
            )
    return pequeno.resize((largura, altura), Image.BICUBIC)


def desenhar_fabrica(imagem: Image.Image, escala: float = 1.0) -> None:
    """Silhueta de fábrica (galpão + dentes de serra + chaminé) em branco."""

    largura, altura = imagem.size
    desenho = ImageDraw.Draw(imagem, "RGBA")

    def px(x: float, y: float) -> tuple[float, float]:
        """Converte coordenadas de um desenho 100x100 no tamanho real."""

        return (
            largura / 2 + (x - 50) * escala * largura / 100,
            altura / 2 + (y - 50) * escala * altura / 100,
        )

    branco = (255, 255, 255, 255)

    # Chaminé
    desenho.rectangle([px(20, 26), px(30, 56)], fill=branco)
    # Corpo do galpão
    desenho.rectangle([px(12, 54), px(88, 80)], fill=branco)
    # Telhado em dentes de serra
    for indice in range(4):
        x0 = 12 + indice * 19
        desenho.polygon(
            [px(x0, 54), px(x0 + 19, 40), px(x0 + 19, 54)],
            fill=branco,
        )
    # Janelas vazadas (mostram o degradê do fundo)
    vazado = (0, 0, 0, 0)
    for x0 in (20, 44, 68):
        desenho.rectangle([px(x0, 62), px(x0 + 12, 72)], fill=vazado)
    # Porta
    desenho.rectangle([px(58, 66), px(74, 80)], fill=vazado)


def gerar(tamanho: int, nome: str, margem: float = 1.0, fundo_opaco: bool = False) -> None:
    imagem = gradiente(tamanho, tamanho)
    desenhar_fabrica(imagem, escala=margem)
    if fundo_opaco:
        fundo = Image.new("RGB", (tamanho, tamanho), INICIO)
        fundo.paste(imagem, (0, 0))
        imagem = fundo
    destino = DESTINO / nome
    imagem.save(destino, format="PNG", optimize=True)
    print(f"  {destino.relative_to(BASE)}  ({tamanho}x{tamanho})")


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    print("Gerando ícones do app de produção:")
    gerar(192, "icon-192.png")
    gerar(512, "icon-512.png")
    gerar(512, "icon-maskable-512.png", margem=0.72)
    gerar(180, "apple-touch-icon.png", margem=0.82, fundo_opaco=True)
    gerar(64, "favicon-64.png", margem=0.9, fundo_opaco=True)
    print("Pronto.")


if __name__ == "__main__":
    main()
