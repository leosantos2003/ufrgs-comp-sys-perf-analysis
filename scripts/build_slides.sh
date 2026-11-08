#!/usr/bin/env bash
# Compila a apresentação da Etapa 2 e converte em PDF as figuras SVG geradas
# pelo caderno. As figuras não são editadas aqui: o pacote svg delega a
# conversão ao Inkscape durante a compilação do Beamer.
set -euo pipefail

for command in pdflatex inkscape kpsewhich; do
    if ! command -v "$command" >/dev/null 2>&1; then
        printf 'Erro: %s não está disponível. Instale uma distribuição TeX, o pacote svg e o Inkscape.\n' "$command" >&2
        exit 1
    fi
done

for tex_file in svg.sty brazil.ldf; do
    if ! kpsewhich "$tex_file" >/dev/null 2>&1; then
        printf 'Erro: %s não foi encontrado. Instale texlive-latex-extra e texlive-lang-portuguese.\n' "$tex_file" >&2
        exit 1
    fi
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root/slides"

pdflatex -shell-escape -interaction=nonstopmode -halt-on-error slides-etapa-2.tex
pdflatex -shell-escape -interaction=nonstopmode -halt-on-error slides-etapa-2.tex
