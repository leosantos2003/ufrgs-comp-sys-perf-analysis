#!/usr/bin/env python3
"""Executa calibrações de B sem alterar controles do AG.

O piloto começa com B=1, mede três réplicas em cargas pequena, média e grande
sob a afinidade configurada e recomenda um B para cada uma delas. Em seguida,
verifica uma vez o lote recomendado. O mesmo protocolo pode calibrar somente
as combinações da grade que não são âncoras do piloto. O arquivo de
configuração e o DOE nunca são regravados: a decisão de congelar B para a
campanha continua sendo humana e documentada.
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import os
import shlex
import statistics
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from generate_design import (
    DEFAULT_CONFIG,
    DesignError,
    Experiment,
    integer,
    read_experiment,
    scalar,
    seed_list,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BINARY = ROOT / "build" / "ag_bench"
RAW_ROOT = ROOT / "data" / "raw"
BENCHMARK_FIELDS = [
    "population_size",
    "chromosome_length",
    "generations",
    "batch",
    "seed",
    "crossover_probability",
    "mutation_probability",
    "measurement_mode",
    "core_id",
    "elapsed_ns",
    "evaluation_ns",
    "selection_ns",
    "crossover_ns",
    "mutation_ns",
    "replacement_ns",
    "best_fitness",
    "checksum",
]
OBSERVATION_FIELDS = [
    "timestamp",
    "point",
    "kind",
    "replication",
    "N",
    "L",
    "G",
    "batch",
    "seed",
    "target_core",
    "observed_core",
    "elapsed_ns",
    "best_fitness",
    "checksum",
    "command_path",
    "status_path",
    "stdout_path",
    "stderr_path",
]
SUMMARY_FIELDS = [
    "point",
    "N",
    "L",
    "G",
    "baseline_replications",
    "median_elapsed_ns_batch_1",
    "recommended_batch",
    "projected_elapsed_ns",
    "verification_elapsed_ns",
    "target_status",
]


class PilotError(RuntimeError):
    """Indica pré-condição, configuração ou saída inválida do piloto."""


@dataclass(frozen=True)
class PilotPoint:
    name: str
    population_size: int
    chromosome_length: int


@dataclass(frozen=True)
class PilotConfig:
    experiment: Experiment
    crossover_probability: float
    mutation_probability: float
    pilot_seed: int
    replications: int
    maximum_batch: int
    target_min_ns: int
    target_max_ns: int
    points: tuple[PilotPoint, ...]


@dataclass(frozen=True)
class Observation:
    point: PilotPoint
    kind: str
    replication: int
    batch: int
    seed: int
    timestamp: str
    result: dict[str, str]
    command_path: Path
    status_path: Path
    stdout_path: Path
    stderr_path: Path


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise PilotError(f"não foi possível ler {path}: {error}") from error


def probability(lines: list[str], path: str) -> float:
    value = scalar(lines, path)
    try:
        parsed = float(value)
    except ValueError as error:
        raise PilotError(f"{path} deve ser numérico, recebido: {value!r}") from error
    if not 0.0 <= parsed <= 1.0:
        raise PilotError(f"{path} deve estar no intervalo [0, 1]")
    return parsed


def duration_range_ns(lines: list[str]) -> tuple[int, int]:
    value = scalar(lines, "design.measurement_batch.target_duration_seconds")
    if not value.startswith("[") or not value.endswith("]"):
        raise PilotError("design.measurement_batch.target_duration_seconds deve ser uma lista de dois valores")
    values = [item.strip() for item in value[1:-1].split(",")]
    if len(values) != 2:
        raise PilotError("design.measurement_batch.target_duration_seconds deve ter dois valores")
    try:
        minimum, maximum = (float(item) for item in values)
    except ValueError as error:
        raise PilotError("a faixa de duração do lote deve ser numérica") from error
    if minimum <= 0.0 or maximum < minimum:
        raise PilotError("a faixa de duração do lote é inválida")
    return math.ceil(minimum * 1_000_000_000), math.floor(maximum * 1_000_000_000)


def pilot_point(lines: list[str], name: str) -> PilotPoint:
    return PilotPoint(
        name=name,
        population_size=integer(lines, f"design.measurement_batch.pilot.points.{name}.N"),
        chromosome_length=integer(lines, f"design.measurement_batch.pilot.points.{name}.L"),
    )


def grid_points_not_in_pilot(
    experiment: Experiment, anchors: tuple[PilotPoint, ...]
) -> tuple[PilotPoint, ...]:
    anchor_treatments = {
        (point.population_size, point.chromosome_length) for point in anchors
    }
    return tuple(
        PilotPoint(f"n{population_size}_l{chromosome_length}", population_size, chromosome_length)
        for population_size in experiment.population_levels
        for chromosome_length in experiment.chromosome_levels
        if (population_size, chromosome_length) not in anchor_treatments
    )


def read_pilot_config(path: Path, remaining_grid: bool = False) -> PilotConfig:
    try:
        experiment = read_experiment(path)
    except DesignError as error:
        raise PilotError(str(error)) from error
    lines = read_lines(path)
    minimum, maximum = duration_range_ns(lines)
    points = tuple(pilot_point(lines, name) for name in ("small", "medium", "large"))
    workloads = [point.population_size * point.chromosome_length for point in points]
    if len(set((point.population_size, point.chromosome_length) for point in points)) != len(points):
        raise PilotError("os três pontos do piloto precisam ser distintos")
    if workloads != sorted(workloads) or len(set(workloads)) != len(workloads):
        raise PilotError("os pontos small, medium e large devem ter N x L estritamente crescente")
    for point in points:
        if point.population_size not in experiment.population_levels:
            raise PilotError(f"N do ponto {point.name} não pertence aos níveis candidatos")
        if point.chromosome_length not in experiment.chromosome_levels:
            raise PilotError(f"L do ponto {point.name} não pertence aos níveis candidatos")
    if scalar(lines, "design.measurement_batch.selection") != "calibration_before_main_campaign":
        raise PilotError("a seleção do lote deve permanecer calibration_before_main_campaign")
    if scalar(lines, "design.measurement_batch.fixed_generations_per_ag_run") != "true":
        raise PilotError("fixed_generations_per_ag_run deve ser true")
    if remaining_grid:
        points = grid_points_not_in_pilot(experiment, points)
        if not points:
            raise PilotError("não há combinações da grade fora dos pontos âncora do piloto")
    return PilotConfig(
        experiment=experiment,
        crossover_probability=probability(lines, "algorithm.crossover.probability"),
        mutation_probability=probability(lines, "algorithm.mutation.probability_per_gene"),
        pilot_seed=integer(lines, "design.measurement_batch.pilot.seed"),
        replications=integer(lines, "design.measurement_batch.pilot.replications"),
        maximum_batch=integer(lines, "design.measurement_batch.pilot.maximum_batch"),
        target_min_ns=minimum,
        target_max_ns=maximum,
        points=points,
    )


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def default_output_dir() -> Path:
    timestamp = now().replace(":", "_").replace("+", "_")
    return RAW_ROOT / f"pilot-{timestamp}"


def remaining_grid_output_dir() -> Path:
    timestamp = now().replace(":", "_").replace("+", "_")
    return RAW_ROOT / f"batch-calibration-remaining-{timestamp}"


def ac_status() -> tuple[bool, list[str]]:
    supplies = Path("/sys/class/power_supply")
    details: list[str] = []
    if not supplies.is_dir():
        return False, ["/sys/class/power_supply indisponível"]
    for supply in sorted(supplies.iterdir()):
        try:
            supply_type = (supply / "type").read_text(encoding="utf-8").strip()
            online = (supply / "online").read_text(encoding="utf-8").strip()
        except OSError:
            continue
        details.append(f"{supply.name} type={supply_type} online={online}")
        if supply_type in {"Mains", "USB", "USB_C"} and online == "1":
            return True, details
    return False, details or ["nenhuma fonte de alimentação legível"]


def benchmark_command(
    binary: Path, config: PilotConfig, point: PilotPoint, seed: int, batch: int
) -> list[str]:
    return [
        "taskset",
        "-c",
        str(config.experiment.target_core),
        str(binary),
        "--header",
        "--population",
        str(point.population_size),
        "--length",
        str(point.chromosome_length),
        "--generations",
        str(config.experiment.generations),
        "--batch",
        str(batch),
        "--seed",
        str(seed),
        "--crossover",
        str(config.crossover_probability),
        "--mutation",
        str(config.mutation_probability),
        "--mode",
        "baseline",
    ]


def parse_benchmark_output(stdout: str, config: PilotConfig, point: PilotPoint, seed: int, batch: int) -> dict[str, str]:
    reader = csv.DictReader(io.StringIO(stdout))
    if reader.fieldnames != BENCHMARK_FIELDS:
        raise PilotError(
            "cabeçalho inesperado do ag_bench; reconstrua o binário. "
            f"Esperado: {','.join(BENCHMARK_FIELDS)}"
        )
    rows = list(reader)
    if len(rows) != 1:
        raise PilotError(f"ag_bench deveria emitir uma observação, emitiu {len(rows)}")
    row = rows[0]
    expected = {
        "population_size": point.population_size,
        "chromosome_length": point.chromosome_length,
        "generations": config.experiment.generations,
        "batch": batch,
        "seed": seed,
        "core_id": config.experiment.target_core,
    }
    for field, value in expected.items():
        try:
            observed = int(row[field])
        except (KeyError, ValueError) as error:
            raise PilotError(f"campo inválido emitido por ag_bench: {field}") from error
        if observed != value:
            raise PilotError(f"{field} esperado {value}, recebido {observed}")
    if row["measurement_mode"] != "baseline":
        raise PilotError("o piloto deve usar measurement_mode=baseline")
    try:
        if int(row["elapsed_ns"]) <= 0:
            raise PilotError("ag_bench retornou elapsed_ns não positivo")
    except ValueError as error:
        raise PilotError("elapsed_ns não é inteiro") from error
    return row


def run_observation(
    output_dir: Path,
    index: int,
    binary: Path,
    config: PilotConfig,
    point: PilotPoint,
    kind: str,
    replication: int,
    seed: int,
    batch: int,
) -> Observation:
    command = benchmark_command(binary, config, point, seed, batch)
    label = f"{index:03d}-{point.name}-{kind}-r{replication}-b{batch}"
    command_path = output_dir / f"{label}.command"
    status_path = output_dir / f"{label}.status"
    stdout_path = output_dir / f"{label}.stdout.csv"
    stderr_path = output_dir / f"{label}.stderr.txt"
    command_path.write_text(shlex.join(command) + "\n", encoding="utf-8")
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
    except OSError as error:
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(f"erro ao iniciar o comando: {error}\n", encoding="utf-8")
        status_path.write_text(f"launch_error={error}\n", encoding="utf-8")
        raise PilotError(f"não foi possível iniciar {label}; saídas preservadas em {output_dir}") from error
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    status_path.write_text(f"exit_status={completed.returncode}\n", encoding="utf-8")
    if completed.returncode != 0:
        raise PilotError(
            f"{label} retornou status {completed.returncode}; saídas preservadas em {output_dir}"
        )
    try:
        result = parse_benchmark_output(completed.stdout, config, point, seed, batch)
    except PilotError as error:
        with status_path.open("a", encoding="utf-8") as stream:
            stream.write(f"validation_error={error}\n")
        raise
    return Observation(
        point=point,
        kind=kind,
        replication=replication,
        batch=batch,
        seed=seed,
        timestamp=now(),
        result=result,
        command_path=command_path,
        status_path=status_path,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
    )


def write_observations(path: Path, observations: list[Observation], target_core: int) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OBSERVATION_FIELDS, lineterminator="\n")
        writer.writeheader()
        for observation in observations:
            writer.writerow(
                {
                    "timestamp": observation.timestamp,
                    "point": observation.point.name,
                    "kind": observation.kind,
                    "replication": observation.replication,
                    "N": observation.point.population_size,
                    "L": observation.point.chromosome_length,
                    "G": observation.result["generations"],
                    "batch": observation.result["batch"],
                    "seed": observation.result["seed"],
                    "target_core": target_core,
                    "observed_core": observation.result["core_id"],
                    "elapsed_ns": observation.result["elapsed_ns"],
                    "best_fitness": observation.result["best_fitness"],
                    "checksum": observation.result["checksum"],
                    "command_path": observation.command_path.name,
                    "status_path": observation.status_path.name,
                    "stdout_path": observation.stdout_path.name,
                    "stderr_path": observation.stderr_path.name,
                }
            )


def target_status(elapsed_ns: int, config: PilotConfig) -> str:
    if elapsed_ns < config.target_min_ns:
        return "below_target"
    if elapsed_ns > config.target_max_ns:
        return "above_target"
    return "within_target"


def write_summary(
    output_dir: Path,
    config: PilotConfig,
    baseline: dict[str, list[Observation]],
    verification: dict[str, Observation],
    batches: dict[str, int],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for point in config.points:
        median_ns = statistics.median(int(item.result["elapsed_ns"]) for item in baseline[point.name])
        verified = int(verification[point.name].result["elapsed_ns"])
        rows.append(
            {
                "point": point.name,
                "N": str(point.population_size),
                "L": str(point.chromosome_length),
                "G": str(config.experiment.generations),
                "baseline_replications": str(config.replications),
                "median_elapsed_ns_batch_1": str(median_ns),
                "recommended_batch": str(batches[point.name]),
                "projected_elapsed_ns": str(math.ceil(median_ns * batches[point.name])),
                "verification_elapsed_ns": str(verified),
                "target_status": target_status(verified, config),
            }
        )
    with (output_dir / "summary.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return rows


def write_recommendation(output_dir: Path, config: PilotConfig, rows: list[dict[str, str]]) -> None:
    has_outside_target = any(row["target_status"] != "within_target" for row in rows)
    lines = [
        "# Recomendação gerada pelo piloto de lote",
        "",
        "Este arquivo é derivado automaticamente das saídas brutas do diretório atual. "
        "Ele não altera `config/experiment.yaml` nem `config/design.csv`.",
        "",
        f"- `G` confirmado durante o piloto: `{config.experiment.generations}` gerações por execução completa.",
        f"- Faixa-alvo agregada: `{config.target_min_ns / 1e9:g}` a `{config.target_max_ns / 1e9:g}` s.",
        "- Cada B recomendado repete a mesma configuração e semente; B não muda N, L, G, "
        "taxas do AG ou o número de threads.",
        "",
        "| ponto | N | L | mediana com B=1 (ns) | B recomendado | verificação (ns) | situação |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['point']} | {row['N']} | {row['L']} | "
            f"{row['median_elapsed_ns_batch_1']} | {row['recommended_batch']} | "
            f"{row['verification_elapsed_ns']} | {row['target_status']} |"
        )
    lines.extend(
        [
            "",
            "## Decisão ainda necessária",
            "",
            "Revisar `summary.csv`, `observations.csv` e cada par `*.command`/`*.stdout.csv` "
            "antes de congelar a grade final e os valores de B por configuração. "
            "Se algum ponto grande exceder a faixa já com B=1, não reduza G apenas naquele "
            "tratamento: revise a grade antes da campanha. Depois da decisão, atualize os "
            "controles por código, gere um novo DOE e inicie um novo bloco de medições.",
        ]
    )
    if has_outside_target:
        lines.extend(
            [
                "",
                "**Atenção:** ao menos uma verificação ficou fora da faixa. A campanha não deve "
                "ser iniciada sem decisão documentada sobre a grade ou a calibração.",
            ]
        )
    (output_dir / "recommendation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def dry_run(config: PilotConfig, binary: Path) -> None:
    seeds = seed_list(config.pilot_seed, config.replications)
    print("Calibração validada; nenhum dado foi escrito (--dry-run).")
    print(
        f"G={config.experiment.generations}; alvo={config.target_min_ns / 1e9:g}-"
        f"{config.target_max_ns / 1e9:g}s; CPU={config.experiment.target_core}."
    )
    for point in config.points:
        command = benchmark_command(binary, config, point, seeds[0], 1)
        print(f"{point.name}: N={point.population_size}, L={point.chromosome_length}; {shlex.join(command)}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa calibração de B e recomenda um lote por configuração."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="configuração YAML")
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY, help="ag_bench compilado")
    parser.add_argument("--output-dir", type=Path, help="novo diretório para as saídas brutas")
    parser.add_argument("--dry-run", action="store_true", help="valida e mostra os comandos sem executar")
    parser.add_argument(
        "--remaining-grid",
        action="store_true",
        help="calibra somente as combinações N × L que não são âncoras do piloto",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    output_dir: Path | None = None
    try:
        config = read_pilot_config(arguments.config, remaining_grid=arguments.remaining_grid)
        if arguments.dry_run:
            dry_run(config, arguments.binary)
            return 0
        if not arguments.binary.is_file() or not os.access(arguments.binary, os.X_OK):
            raise PilotError(f"binário ausente ou não executável: {arguments.binary}; execute make build")
        ac_online, power_details = ac_status()
        if not ac_online:
            raise PilotError(
                "energia AC não confirmada; o piloto não foi iniciado. Estado observado: "
                + "; ".join(power_details)
            )
        output_dir = arguments.output_dir or (
            remaining_grid_output_dir() if arguments.remaining_grid else default_output_dir()
        )
        if output_dir.exists():
            raise PilotError(f"diretório de saída já existe: {output_dir}")
        output_dir.mkdir(parents=True)
        (output_dir / "manifest.txt").write_text(
            "\n".join(
                [
                    f"started_at={now()}",
                    f"config={arguments.config}",
                    f"binary={arguments.binary}",
                    f"target_core={config.experiment.target_core}",
                    f"power_state={'; '.join(power_details)}",
                    f"G={config.experiment.generations}",
                    f"pilot_replications={config.replications}",
                    f"target_duration_ns={config.target_min_ns},{config.target_max_ns}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        seeds = seed_list(config.pilot_seed, config.replications)
        observations: list[Observation] = []
        observations_path = output_dir / "observations.csv"
        write_observations(observations_path, observations, config.experiment.target_core)
        index = 1
        warmup = run_observation(
            output_dir, index, arguments.binary, config, config.points[0], "warmup", 0, seeds[0], 1
        )
        observations.append(warmup)
        write_observations(observations_path, observations, config.experiment.target_core)
        index += 1

        baseline: dict[str, list[Observation]] = {point.name: [] for point in config.points}
        for point in config.points:
            for replication, seed in enumerate(seeds, start=1):
                observation = run_observation(
                    output_dir,
                    index,
                    arguments.binary,
                    config,
                    point,
                    "baseline_batch_1",
                    replication,
                    seed,
                    1,
                )
                observations.append(observation)
                write_observations(observations_path, observations, config.experiment.target_core)
                baseline[point.name].append(observation)
                index += 1

        batches: dict[str, int] = {}
        for point in config.points:
            median_ns = statistics.median(int(item.result["elapsed_ns"]) for item in baseline[point.name])
            recommended = max(1, math.ceil(config.target_min_ns / median_ns))
            if recommended > config.maximum_batch:
                raise PilotError(
                    f"B recomendado para {point.name} é {recommended}, acima do máximo "
                    f"configurado ({config.maximum_batch}); saídas parciais preservadas em {output_dir}"
                )
            batches[point.name] = recommended

        verification: dict[str, Observation] = {}
        for point in config.points:
            observation = run_observation(
                output_dir,
                index,
                arguments.binary,
                config,
                point,
                "batch_verification",
                1,
                seeds[0],
                batches[point.name],
            )
            observations.append(observation)
            write_observations(observations_path, observations, config.experiment.target_core)
            verification[point.name] = observation
            index += 1

        rows = write_summary(output_dir, config, baseline, verification, batches)
        write_recommendation(output_dir, config, rows)
        with (output_dir / "manifest.txt").open("a", encoding="utf-8") as stream:
            stream.write(f"completed_at={now()}\nstatus=completed\n")
        calibration_name = "Calibração das combinações restantes" if arguments.remaining_grid else "Piloto"
        print(f"{calibration_name} concluído; saídas brutas e recomendação em {output_dir}")
        if any(row["target_status"] != "within_target" for row in rows):
            print("aviso: há verificação fora da faixa; revise a grade antes da campanha", file=sys.stderr)
            return 1
        return 0
    except (PilotError, DesignError, OSError) as error:
        if output_dir is not None and output_dir.is_dir():
            with (output_dir / "manifest.txt").open("a", encoding="utf-8") as stream:
                stream.write(f"finished_at={now()}\nstatus=failed\nreason={error}\n")
        print(f"erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
