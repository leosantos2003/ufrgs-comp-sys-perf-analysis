#!/usr/bin/env python3
"""Executa as células Python de ``analysis/etapa2.qmd`` e o renderiza.

Quarto é usado somente como renderizador neste projeto.  As células usam a
biblioteca padrão do Python e são extraídas em ordem por este pequeno executor,
evitando depender de Jupyter ou de bibliotecas científicas não versionadas no
ambiente da coleta.  Assim, a lógica, a prosa e as referências dos resultados
continuam concentradas no próprio arquivo ``.qmd``.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QMD = ROOT / "analysis" / "etapa2.qmd"


class RenderError(RuntimeError):
    """Indica que o caderno não pode ser executado ou renderizado."""


def python_cells(source: str) -> list[str]:
    """Extrai as células ``{python}`` preservando a ordem do caderno."""
    cells: list[str] = []
    pattern = re.compile(r"^```\{python\}[^\n]*\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)
    for match in pattern.finditer(source):
        lines = [line for line in match.group(1).splitlines() if not line.startswith("#|")]
        cells.append("\n".join(lines) + "\n")
    if not cells:
        raise RenderError("nenhuma célula {python} foi encontrada no caderno")
    return cells


def execute_cells(path: Path) -> None:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as error:
        raise RenderError(f"não foi possível ler {path}: {error}") from error
    namespace = {"__name__": "__etapa2_qmd__", "__file__": str(path)}
    for index, cell in enumerate(python_cells(source), start=1):
        try:
            compiled = compile(cell, f"{path} (célula {index})", "exec")
            exec(compiled, namespace, namespace)
        except Exception as error:  # A mensagem com a célula preserva o diagnóstico útil.
            raise RenderError(f"falha na célula Python {index}: {error}") from error


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="executa e renderiza o caderno da Etapa 2")
    parser.add_argument("--input", type=Path, default=DEFAULT_QMD)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results")
    parser.add_argument("--quarto", default="quarto", help="executável Quarto disponível no PATH")
    return parser.parse_args()


def resolve_quarto(requested: str) -> str | None:
    """Localiza Quarto no PATH ou na instalação Linux empacotada pelo RStudio."""
    candidates: list[Path] = []
    if "/" in requested:
        candidates.append(Path(requested))
    else:
        discovered = shutil.which(requested)
        if discovered:
            candidates.append(Path(discovered))
    # Algumas instalações Linux do RStudio incluem Quarto sem registrá-lo no
    # PATH. É uma descoberta de ferramenta do sistema, não um caminho do
    # projeto; o argumento --quarto continua tendo precedência.
    if requested == "quarto":
        candidates.append(Path("/usr/lib/rstudio/resources/app/bin/quarto/bin/quarto"))
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def main() -> int:
    args = arguments()
    input_path = args.input.resolve()
    output_dir = args.output_dir.resolve()
    try:
        execute_cells(input_path)
        quarto = resolve_quarto(args.quarto)
        if not quarto:
            raise RenderError(
                "Quarto não está disponível; instale-o ou defina QUARTO=/caminho/para/quarto"
            )
        # Quarto só aceita um output-dir que pertença ao projeto do .qmd.
        # Renderizamos em um estágio descartável dentro de analysis/ e depois
        # publicamos HTML e recursos em results/, mantendo os links relativos
        # para ../figures válidos no relatório final.
        staging = input_path.parent / ".rendered"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        completed = subprocess.run(
            [quarto, "render", str(input_path), "--output-dir", str(staging), "--no-execute"],
            cwd=ROOT,
            check=False,
            text=True,
        )
        if completed.returncode != 0:
            raise RenderError(f"quarto render terminou com status {completed.returncode}")
        staged_html = staging / (input_path.stem + ".html")
        if not staged_html.is_file() or staged_html.stat().st_size == 0:
            raise RenderError(f"renderização não gerou {staged_html}")
        output_dir.mkdir(parents=True, exist_ok=True)
        expected = output_dir / staged_html.name
        staged_resources = staging / f"{input_path.stem}_files"
        published_resources = output_dir / staged_resources.name
        if expected.exists():
            expected.unlink()
        if published_resources.exists():
            shutil.rmtree(published_resources)
        shutil.move(str(staged_html), str(expected))
        if staged_resources.exists():
            shutil.move(str(staged_resources), str(published_resources))
        shutil.rmtree(staging)
    except RenderError as error:
        print(f"Renderização da análise falhou: {error}", file=sys.stderr)
        return 1
    print(f"Caderno renderizado: {expected.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
