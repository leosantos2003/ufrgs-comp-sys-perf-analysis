#!/usr/bin/env python3
"""Materializa e valida o DOE a partir de config/experiment.yaml.

O formato da configuração é propositalmente lido com a biblioteca padrão:
o gerador usa apenas o subconjunto YAML (mapeamentos por indentação, listas
em linha e listas simples) presente em experiment.yaml. Isso evita introduzir
uma dependência de execução só para gerar o CSV do projeto experimental.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "experiment.yaml"
DEFAULT_OUTPUT = ROOT / "config" / "design.csv"
FIELDNAMES = [
    "run_id",
    "block",
    "order",
    "measurement_mode",
    "perf_group",
    "N",
    "L",
    "G",
    "batch",
    "replication",
    "seed",
    "core_id",
    "design_random_seed",
]


class DesignError(ValueError):
    """Indica uma configuração ou um CSV de DOE inválido."""


@dataclass(frozen=True)
class Experiment:
    study_id: str
    design_type: str
    combinations: int
    population_levels: tuple[int, ...]
    chromosome_levels: tuple[int, ...]
    generations: int
    baseline_replications: int
    profile_replications: int
    perf_replications: int
    execution_order: str
    design_random_seed: int
    block: str
    batch: int
    treatment_batches: dict[tuple[int, int], int] | None
    perf_groups: dict[str, tuple[str, ...]]
    perf_privilege_scope: str
    measurement_modes: tuple[str, ...]
    target_core: int


PERF_HARDWARE_EVENTS = frozenset(
    {"cycles", "instructions", "cache-references", "cache-misses"}
)
PERF_SYSTEM_EVENTS = frozenset({"context-switches", "cpu-migrations"})
PERF_EVENTS_REQUESTED = PERF_HARDWARE_EVENTS | PERF_SYSTEM_EVENTS


def uncomment(line: str) -> str:
    """Remove comentários do subconjunto de YAML aceito por este arquivo."""
    return line.split("#", maxsplit=1)[0].rstrip()


def node(lines: list[str], path: str) -> tuple[int, int, str]:
    """Localiza uma chave em um caminho de mapeamentos YAML por indentação."""
    start, end, parent_indent = 0, len(lines), -1
    for key in path.split("."):
        found: tuple[int, int, str] | None = None
        pattern = re.compile(r"^( *)([A-Za-z0-9_-]+):(?:[ \t]*(.*))?$")
        for index in range(start, end):
            match = pattern.match(uncomment(lines[index]))
            if match is None or match.group(2) != key:
                continue
            indentation = len(match.group(1))
            if indentation <= parent_indent:
                continue
            value = (match.group(3) or "").strip()
            child_end = end
            for child_index in range(index + 1, end):
                child = uncomment(lines[child_index])
                if not child.strip():
                    continue
                child_indent = len(child) - len(child.lstrip(" "))
                if child_indent <= indentation:
                    child_end = child_index
                    break
            found = (index, child_end, value)
            break
        if found is None:
            raise DesignError(f"chave ausente em experiment.yaml: {path}")
        start, end, value = found
        parent_indent = len(uncomment(lines[start])) - len(uncomment(lines[start]).lstrip(" "))
    return start, end, value


def scalar(lines: list[str], path: str) -> str:
    _, _, value = node(lines, path)
    if not value:
        raise DesignError(f"a chave {path} precisa ter um valor escalar")
    return value.strip("\"'")


def integer(lines: list[str], path: str) -> int:
    value = scalar(lines, path)
    try:
        parsed = int(value)
    except ValueError as error:
        raise DesignError(f"{path} deve ser inteiro, recebido: {value!r}") from error
    if parsed < 1:
        raise DesignError(f"{path} deve ser positivo, recebido: {parsed}")
    return parsed


def non_negative_integer(lines: list[str], path: str) -> int:
    value = scalar(lines, path)
    try:
        parsed = int(value)
    except ValueError as error:
        raise DesignError(f"{path} deve ser inteiro, recebido: {value!r}") from error
    if parsed < 0:
        raise DesignError(f"{path} não pode ser negativo, recebido: {parsed}")
    return parsed


def inline_integer_list(lines: list[str], path: str) -> tuple[int, ...]:
    value = scalar(lines, path)
    match = re.fullmatch(r"\[\s*([0-9]+(?:\s*,\s*[0-9]+)*)\s*\]", value)
    if match is None:
        raise DesignError(f"{path} deve ser uma lista não vazia de inteiros: {value!r}")
    parsed = tuple(int(item.strip()) for item in match.group(1).split(","))
    if len(set(parsed)) != len(parsed):
        raise DesignError(f"{path} não pode conter níveis duplicados")
    if any(item < 1 for item in parsed):
        raise DesignError(f"{path} deve conter somente níveis positivos")
    return parsed


def string_list(lines: list[str], path: str) -> tuple[str, ...]:
    index, end, value = node(lines, path)
    if value:
        raise DesignError(f"{path} deve ser uma lista em linhas separadas")
    indentation = len(uncomment(lines[index])) - len(uncomment(lines[index]).lstrip(" "))
    values: list[str] = []
    for child in lines[index + 1 : end]:
        text = uncomment(child)
        if not text.strip():
            continue
        child_indent = len(text) - len(text.lstrip(" "))
        match = re.fullmatch(r"\s*-\s*([A-Za-z0-9_-]+)\s*", text)
        if child_indent <= indentation or match is None:
            raise DesignError(f"item inválido em {path}: {child.rstrip()!r}")
        values.append(match.group(1))
    if not values or len(set(values)) != len(values):
        raise DesignError(f"{path} deve conter itens únicos")
    return tuple(values)


def named_string_lists(lines: list[str], path: str) -> dict[str, tuple[str, ...]]:
    """Lê um mapeamento YAML cujos valores são listas simples de strings."""
    index, end, value = node(lines, path)
    if value:
        raise DesignError(f"{path} deve ser um mapeamento de listas")
    indentation = len(uncomment(lines[index])) - len(uncomment(lines[index]).lstrip(" "))
    names: list[str] = []
    for child in lines[index + 1 : end]:
        text = uncomment(child)
        if not text.strip():
            continue
        child_indent = len(text) - len(text.lstrip(" "))
        if child_indent <= indentation:
            continue
        if child_indent != indentation + 2:
            continue
        match = re.fullmatch(r"\s*([A-Za-z0-9_-]+):\s*", text)
        if match is None:
            raise DesignError(f"item inválido em {path}: {child.rstrip()!r}")
        names.append(match.group(1))
    if not names or len(set(names)) != len(names):
        raise DesignError(f"{path} deve conter grupos únicos")
    return {name: string_list(lines, f"{path}.{name}") for name in names}


def treatment_batch_map(
    lines: list[str], path: str, population_levels: tuple[int, ...], chromosome_levels: tuple[int, ...]
) -> dict[tuple[int, int], int] | None:
    """Lê B congelado por tratamento, quando a calibração já ocorreu.

    As chaves seguem ``n<N>_l<L>`` para caber no subconjunto YAML já aceito
    pelo gerador. Sem esse mapa, o lote provisório
    ``design.initial_design.batch`` continua sendo usado.
    """
    try:
        index, end, value = node(lines, path)
    except DesignError as error:
        if "chave ausente" in str(error):
            return None
        raise
    if value:
        raise DesignError(f"{path} deve ser um mapeamento por tratamento")

    indentation = len(uncomment(lines[index])) - len(uncomment(lines[index]).lstrip(" "))
    values: dict[tuple[int, int], int] = {}
    pattern = re.compile(r"\s*n([0-9]+)_l([0-9]+):\s*([0-9]+)\s*")
    for child in lines[index + 1 : end]:
        text = uncomment(child)
        if not text.strip():
            continue
        child_indent = len(text) - len(text.lstrip(" "))
        match = pattern.fullmatch(text)
        if child_indent <= indentation or match is None:
            raise DesignError(f"item inválido em {path}: {child.rstrip()!r}")
        treatment = (int(match.group(1)), int(match.group(2)))
        batch = int(match.group(3))
        if treatment in values or batch < 1:
            raise DesignError(f"item duplicado ou lote não positivo em {path}: {child.rstrip()!r}")
        values[treatment] = batch

    expected = {
        (population_size, chromosome_length)
        for population_size in population_levels
        for chromosome_length in chromosome_levels
    }
    if set(values) != expected:
        missing = sorted(expected - set(values))
        unexpected = sorted(set(values) - expected)
        details: list[str] = []
        if missing:
            details.append("ausentes=" + ", ".join(f"n{n}_l{l}" for n, l in missing))
        if unexpected:
            details.append("inesperados=" + ", ".join(f"n{n}_l{l}" for n, l in unexpected))
        raise DesignError(f"{path} deve conter exatamente todos os tratamentos: {'; '.join(details)}")
    return values


def read_experiment(path: Path) -> Experiment:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise DesignError(f"não foi possível ler {path}: {error}") from error

    population_levels = inline_integer_list(
        lines, "factors.primary.population_size_N.candidate_levels"
    )
    chromosome_levels = inline_integer_list(
        lines, "factors.primary.chromosome_length_L.candidate_levels"
    )
    experiment = Experiment(
        study_id=scalar(lines, "study.id"),
        design_type=scalar(lines, "design.type"),
        combinations=integer(lines, "design.combinations"),
        population_levels=population_levels,
        chromosome_levels=chromosome_levels,
        generations=integer(lines, "algorithm.termination.generations"),
        baseline_replications=integer(lines, "design.baseline_replications"),
        profile_replications=integer(lines, "design.profile_replications"),
        perf_replications=integer(lines, "design.perf_replications"),
        execution_order=scalar(lines, "design.execution_order"),
        design_random_seed=integer(lines, "design.design_random_seed"),
        block=scalar(lines, "design.initial_design.block"),
        batch=integer(lines, "design.initial_design.batch"),
        treatment_batches=treatment_batch_map(
            lines,
            "design.measurement_batch.frozen_batches",
            population_levels,
            chromosome_levels,
        ),
        perf_groups=named_string_lists(lines, "design.initial_design.perf_groups"),
        perf_privilege_scope=scalar(lines, "measurement.perf_privilege_scope"),
        measurement_modes=string_list(lines, "design.planned_measurement_modes"),
        target_core=non_negative_integer(lines, "environment_controls.target_core"),
    )
    if experiment.design_type != "full_factorial":
        raise DesignError("design.type deve ser exatamente 'full_factorial'")
    declared_combinations = len(experiment.population_levels) * len(experiment.chromosome_levels)
    if experiment.combinations != declared_combinations:
        raise DesignError(
            "design.combinations diverge do produto dos níveis de N e L: "
            f"declarado {experiment.combinations}, calculado {declared_combinations}"
        )
    if experiment.execution_order != "randomized":
        raise DesignError("design.execution_order deve ser exatamente 'randomized'")
    expected_modes = {"baseline", "phases", "perf"}
    if set(experiment.measurement_modes) != expected_modes:
        raise DesignError(
            "design.planned_measurement_modes deve conter baseline, phases e perf exatamente uma vez"
        )
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", experiment.study_id):
        raise DesignError("study.id deve conter apenas letras, números, '_' e '-'")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", experiment.block):
        raise DesignError("design.initial_design.block deve conter apenas letras, números, '_' e '-'")
    expected_perf_groups = {"ipc_user", "cache_user"}
    if set(experiment.perf_groups) != expected_perf_groups:
        raise DesignError(
            "design.initial_design.perf_groups deve conter exatamente ipc_user e cache_user"
        )
    expected_group_events = {
        "ipc_user": ("cycles", "instructions", "context-switches", "cpu-migrations"),
        "cache_user": (
            "cache-references",
            "cache-misses",
            "context-switches",
            "cpu-migrations",
        ),
    }
    if experiment.perf_groups != expected_group_events:
        raise DesignError(
            "os grupos perf devem preservar os pares cycles/instructions e "
            "cache-references/cache-misses, com os eventos de qualidade"
        )
    if experiment.perf_privilege_scope != "user":
        raise DesignError("measurement.perf_privilege_scope deve ser exatamente 'user'")
    return experiment


def splitmix64(state: int) -> tuple[int, int]:
    """Gera inteiros de 64 bits sem depender do PRNG da versão do Python."""
    state = (state + 0x9E3779B97F4A7C15) & 0xFFFFFFFFFFFFFFFF
    value = state
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
    return state, (value ^ (value >> 31)) & 0xFFFFFFFFFFFFFFFF


def seed_list(random_seed: int, count: int) -> tuple[int, ...]:
    state = random_seed
    values: list[int] = []
    while len(values) < count:
        state, value = splitmix64(state)
        if value not in values:
            values.append(value)
    return tuple(values)


def shuffle(items: list[dict[str, str]], random_seed: int) -> None:
    state = random_seed ^ 0xD1B54A32D192ED03
    for index in range(len(items) - 1, 0, -1):
        state, value = splitmix64(state)
        other = value % (index + 1)
        items[index], items[other] = items[other], items[index]


def replication_count(mode: str, experiment: Experiment) -> int:
    return {
        "baseline": experiment.baseline_replications,
        "phases": experiment.profile_replications,
        "perf": experiment.perf_replications,
    }[mode]


def batch_for_treatment(population_size: int, chromosome_length: int, experiment: Experiment) -> int:
    if experiment.treatment_batches is None:
        return experiment.batch
    return experiment.treatment_batches[(population_size, chromosome_length)]


def perf_events(experiment: Experiment, group: str) -> tuple[str, ...]:
    """Resolve eventos do grupo para a sintaxe literal da PMU selecionada."""
    try:
        requested = experiment.perf_groups[group]
    except KeyError as error:
        raise DesignError(f"grupo perf desconhecido: {group}") from error
    suffix = "/u" if experiment.perf_privilege_scope == "user" else "/"
    return tuple(
        f"cpu_core/{event}{suffix}" if event in PERF_HARDWARE_EVENTS else event
        for event in requested
    )


def perf_event_selector(experiment: Experiment, group: str) -> str:
    """Cria o seletor perf mantendo os eventos de hardware no mesmo grupo."""
    events = perf_events(experiment, group)
    hardware = [event for event in events if event.startswith("cpu_core/")]
    software = [event for event in events if not event.startswith("cpu_core/")]
    hardware_selector = "{" + ",".join(hardware) + "}"
    return ",".join([hardware_selector, *software])


def make_rows(experiment: Experiment) -> list[dict[str, str]]:
    max_replications = max(
        experiment.baseline_replications,
        experiment.profile_replications,
        experiment.perf_replications,
    )
    seeds = seed_list(experiment.design_random_seed, max_replications)
    rows: list[dict[str, str]] = []
    for mode in experiment.measurement_modes:
        for population_size in experiment.population_levels:
            for chromosome_length in experiment.chromosome_levels:
                groups = experiment.perf_groups if mode == "perf" else {"not_applicable": ()}
                for group in groups:
                    for replication in range(1, replication_count(mode, experiment) + 1):
                        rows.append(
                            {
                                "run_id": "",
                                "block": experiment.block,
                                "order": "",
                                "measurement_mode": mode,
                                "perf_group": group,
                                "N": str(population_size),
                                "L": str(chromosome_length),
                                "G": str(experiment.generations),
                                "batch": str(
                                    batch_for_treatment(population_size, chromosome_length, experiment)
                                ),
                                "replication": str(replication),
                                "seed": str(seeds[replication - 1]),
                                "core_id": str(experiment.target_core),
                                "design_random_seed": str(experiment.design_random_seed),
                            }
                        )
    shuffle(rows, experiment.design_random_seed)
    width = max(4, len(str(len(rows))))
    for order, row in enumerate(rows, start=1):
        row["order"] = str(order)
        row["run_id"] = f"{experiment.study_id}-{experiment.block}-{order:0{width}d}"
    return rows


def expected_row_count(experiment: Experiment) -> int:
    treatment_count = len(experiment.population_levels) * len(experiment.chromosome_levels)
    return treatment_count * sum(
        replication_count(mode, experiment)
        * (len(experiment.perf_groups) if mode == "perf" else 1)
        for mode in experiment.measurement_modes
    )


def validate_rows(rows: Iterable[dict[str, str]], experiment: Experiment) -> None:
    actual = list(rows)
    expected = make_rows(experiment)
    if len(actual) != expected_row_count(experiment):
        raise DesignError(
            f"quantidade de linhas inválida: esperadas {expected_row_count(experiment)}, obtidas {len(actual)}"
        )
    if actual != expected:
        raise DesignError(
            "o CSV não corresponde ao DOE determinístico da configuração; gere-o novamente com make design"
        )


def read_csv(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != FIELDNAMES:
                raise DesignError(
                    f"cabeçalho inválido em {path}; esperado: {','.join(FIELDNAMES)}"
                )
            return list(reader)
    except OSError as error:
        raise DesignError(f"não foi possível ler {path}: {error}") from error


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, text=True
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDNAMES, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gera ou valida o DOE do AG a partir de experiment.yaml."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="configuração YAML")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="CSV do DOE")
    parser.add_argument(
        "--check", action="store_true", help="valida o CSV existente sem gravar um novo"
    )
    parser.add_argument(
        "--print-perf-groups",
        action="store_true",
        help="imprime grupo e seletor perf derivados da configuração",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        experiment = read_experiment(arguments.config)
        if arguments.print_perf_groups:
            for group in experiment.perf_groups:
                print(f"{group}\t{perf_event_selector(experiment, group)}")
            return 0
        if arguments.check:
            rows = read_csv(arguments.output)
            validate_rows(rows, experiment)
            print(f"DOE válido: {arguments.output} ({len(rows)} execuções planejadas).")
        else:
            rows = make_rows(experiment)
            validate_rows(rows, experiment)
            write_csv(arguments.output, rows)
            print(f"DOE gerado: {arguments.output} ({len(rows)} execuções planejadas).")
    except DesignError as error:
        print(f"erro: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
