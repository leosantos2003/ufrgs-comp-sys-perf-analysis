#!/usr/bin/env python3
"""Executa uma campanha ``baseline`` planejada no DOE congelado.

Cada linha medida é executada uma única vez, na ordem global registrada em
``config/design.csv``.  O script mantém a saída literal do executável, o
comando, a saída de erro, o uso de recursos e uma tabela de rastreabilidade no
mesmo diretório bruto.  Uma falha não é reexecutada: ela é registrada e a
campanha termina, para que uma eventual repetição tenha uma justificativa
explícita no caderno de laboratório.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from generate_design import (
    DEFAULT_CONFIG,
    DEFAULT_OUTPUT,
    FIELDNAMES as DESIGN_FIELDS,
    DesignError,
    Experiment,
    integer,
    make_rows,
    read_experiment,
    scalar,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BINARY = ROOT / "build" / "ag_bench"
RAW_ROOT = ROOT / "data" / "raw"
METADATA_ROOT = ROOT / "data" / "metadata"
ENVIRONMENT_SCRIPT = ROOT / "scripts" / "capture_environment.sh"
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
    "run_id",
    "status",
    "timestamp",
    "block",
    "order",
    "measurement_mode",
    "perf_group",
    "git_commit",
    "binary_sha256",
    "compiler",
    "compiler_flags",
    "target_core",
    "core_id",
    "N",
    "L",
    "G",
    "batch",
    "replication",
    "seed",
    "p_c",
    "p_m",
    "wall_time_ns",
    "phase_eval_ns",
    "phase_selection_ns",
    "phase_crossover_ns",
    "phase_mutation_ns",
    "phase_replacement_ns",
    "max_rss_kib",
    "best_fitness",
    "checksum",
    "command_path",
    "status_path",
    "stdout_path",
    "stderr_path",
    "resource_path",
    "exclusion_reason",
]
SUMMARY_FIELDS = ["N", "L", "planned", "success", "failed", "invalid"]


class CampaignError(RuntimeError):
    """Indica uma pré-condição ou observação inválida da campanha."""


@dataclass(frozen=True)
class CampaignConfig:
    experiment: Experiment
    crossover_probability: float
    mutation_probability: float
    warmup_runs: int


@dataclass(frozen=True)
class CampaignIdentity:
    git_commit: str
    binary_sha256: str
    compiler: str
    compiler_flags: str


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def timestamp_slug() -> str:
    return now().replace(":", "_").replace("+", "_")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise CampaignError(f"não foi possível ler {path}: {error}") from error


def probability(lines: list[str], path: str) -> float:
    value = scalar(lines, path)
    try:
        result = float(value)
    except ValueError as error:
        raise CampaignError(f"{path} deve ser numérico, recebido: {value!r}") from error
    if not 0.0 <= result <= 1.0:
        raise CampaignError(f"{path} deve estar no intervalo [0, 1]")
    return result


def read_campaign_config(path: Path) -> CampaignConfig:
    try:
        experiment = read_experiment(path)
    except DesignError as error:
        raise CampaignError(str(error)) from error
    lines = read_lines(path)
    warmup_runs = integer(lines, "measurement.warmup_runs_per_mode")
    if warmup_runs != 1:
        raise CampaignError(
            "a campanha baseline requer exatamente um aquecimento por modo; "
            f"configurado: {warmup_runs}"
        )
    if scalar(lines, "environment_controls.cpu_affinity") != "required":
        raise CampaignError("environment_controls.cpu_affinity deve permanecer required")
    if scalar(lines, "environment_controls.power_source") != "AC_when_available":
        raise CampaignError("environment_controls.power_source deve permanecer AC_when_available")
    return CampaignConfig(
        experiment=experiment,
        crossover_probability=probability(lines, "algorithm.crossover.probability"),
        mutation_probability=probability(lines, "algorithm.mutation.probability_per_gene"),
        warmup_runs=warmup_runs,
    )


def read_frozen_design(path: Path, experiment: Experiment) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != DESIGN_FIELDS:
                raise CampaignError(
                    "cabeçalho inesperado em design.csv; execute make design e make check-design"
                )
            rows = list(reader)
    except OSError as error:
        raise CampaignError(f"não foi possível ler {path}: {error}") from error
    expected = make_rows(experiment)
    if rows != expected:
        raise CampaignError(
            "design.csv diverge do DOE determinístico derivado de experiment.yaml; "
            "execute make design e revise a mudança antes da campanha"
        )
    baseline = [row for row in rows if row["measurement_mode"] == "baseline"]
    baseline.sort(key=lambda row: int(row["order"]))
    expected_count = experiment.combinations * experiment.baseline_replications
    if len(baseline) != expected_count:
        raise CampaignError(
            f"DOE baseline incompleto: esperadas {expected_count} linhas, encontradas {len(baseline)}"
        )
    return baseline


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


def read_identity(binary: Path) -> CampaignIdentity:
    try:
        git_commit = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as error:
        raise CampaignError(f"não foi possível identificar o commit Git: {error}") from error
    build_info = ROOT / "build" / "build-info.txt"
    values: dict[str, str] = {}
    for line in read_lines(build_info):
        if "=" in line:
            key, value = line.split("=", maxsplit=1)
            values[key] = value
    if not values.get("compiler") or not values.get("flags"):
        raise CampaignError(f"metadados de compilação inválidos: {build_info}; execute make build")
    return CampaignIdentity(
        git_commit=git_commit,
        binary_sha256=sha256(binary),
        compiler=values["compiler"],
        compiler_flags=values["flags"],
    )


def benchmark_command(binary: Path, row: dict[str, str], config: CampaignConfig) -> list[str]:
    return [
        "taskset",
        "-c",
        str(config.experiment.target_core),
        str(binary),
        "--header",
        "--population",
        row["N"],
        "--length",
        row["L"],
        "--generations",
        row["G"],
        "--batch",
        row["batch"],
        "--seed",
        row["seed"],
        "--crossover",
        str(config.crossover_probability),
        "--mutation",
        str(config.mutation_probability),
        "--mode",
        "baseline",
    ]


def parse_resource_output(path: Path) -> str:
    try:
        values = dict(
            line.split("=", maxsplit=1)
            for line in path.read_text(encoding="utf-8").splitlines()
            if "=" in line
        )
        value = values["max_rss_kib"]
        if int(value) < 0:
            raise ValueError(value)
        return value
    except (OSError, KeyError, ValueError) as error:
        raise CampaignError(f"uso de memória inválido em {path}: {error}") from error


def integer_field(result: dict[str, str], field: str, minimum: int = 0) -> int:
    try:
        value = int(result[field])
    except (KeyError, ValueError) as error:
        raise CampaignError(f"campo inválido emitido por ag_bench: {field}") from error
    if value < minimum:
        raise CampaignError(f"campo emitido por ag_bench fora do limite: {field}={value}")
    return value


def parse_benchmark_output(
    stdout: str, row: dict[str, str], config: CampaignConfig
) -> dict[str, str]:
    reader = csv.DictReader(io.StringIO(stdout))
    if reader.fieldnames != BENCHMARK_FIELDS:
        raise CampaignError(
            "cabeçalho inesperado do ag_bench; reconstrua o binário. "
            f"Esperado: {','.join(BENCHMARK_FIELDS)}"
        )
    results = list(reader)
    if len(results) != 1:
        raise CampaignError(f"ag_bench deveria emitir uma observação, emitiu {len(results)}")
    result = results[0]
    expected = {
        "population_size": row["N"],
        "chromosome_length": row["L"],
        "generations": row["G"],
        "batch": row["batch"],
        "seed": row["seed"],
        "core_id": row["core_id"],
    }
    for field, value in expected.items():
        if str(integer_field(result, field)) != value:
            raise CampaignError(f"{field} esperado {value}, recebido {result.get(field)!r}")
    if result["measurement_mode"] != "baseline":
        raise CampaignError("a campanha atual aceita somente measurement_mode=baseline")
    try:
        crossover = float(result["crossover_probability"])
        mutation = float(result["mutation_probability"])
    except (KeyError, ValueError) as error:
        raise CampaignError("probabilidade inválida emitida por ag_bench") from error
    if crossover != config.crossover_probability or mutation != config.mutation_probability:
        raise CampaignError("as probabilidades emitidas pelo ag_bench divergem dos controles congelados")
    integer_field(result, "elapsed_ns", minimum=1)
    for field in (
        "evaluation_ns",
        "selection_ns",
        "crossover_ns",
        "mutation_ns",
        "replacement_ns",
    ):
        if integer_field(result, field) != 0:
            raise CampaignError(f"{field} deve ser zero no modo baseline")
    best_fitness = integer_field(result, "best_fitness")
    if best_fitness > int(row["L"]):
        raise CampaignError(f"best_fitness fora do intervalo para L={row['L']}: {best_fitness}")
    integer_field(result, "checksum")
    return result


def write_observations(path: Path, observations: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OBSERVATION_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(observations)


def observation_template(
    row: dict[str, str], identity: CampaignIdentity, config: CampaignConfig
) -> dict[str, str]:
    return {
        "run_id": row["run_id"],
        "status": "",
        "timestamp": now(),
        "block": row["block"],
        "order": row["order"],
        "measurement_mode": row["measurement_mode"],
        "perf_group": row["perf_group"],
        "git_commit": identity.git_commit,
        "binary_sha256": identity.binary_sha256,
        "compiler": identity.compiler,
        "compiler_flags": identity.compiler_flags,
        "target_core": str(config.experiment.target_core),
        "core_id": "",
        "N": row["N"],
        "L": row["L"],
        "G": row["G"],
        "batch": row["batch"],
        "replication": row["replication"],
        "seed": row["seed"],
        "p_c": str(config.crossover_probability),
        "p_m": str(config.mutation_probability),
        "wall_time_ns": "",
        "phase_eval_ns": "",
        "phase_selection_ns": "",
        "phase_crossover_ns": "",
        "phase_mutation_ns": "",
        "phase_replacement_ns": "",
        "max_rss_kib": "",
        "best_fitness": "",
        "checksum": "",
        "command_path": "",
        "status_path": "",
        "stdout_path": "",
        "stderr_path": "",
        "resource_path": "",
        "exclusion_reason": "",
    }


def run_benchmark(
    output_dir: Path,
    index: int,
    kind: str,
    row: dict[str, str],
    binary: Path,
    config: CampaignConfig,
    identity: CampaignIdentity,
) -> dict[str, str] | None:
    label = f"{index:03d}-{kind}-{row['run_id']}"
    command_path = output_dir / f"{label}.command"
    status_path = output_dir / f"{label}.status"
    stdout_path = output_dir / f"{label}.stdout.csv"
    stderr_path = output_dir / f"{label}.stderr.txt"
    resource_path = output_dir / f"{label}.resources.txt"
    command = benchmark_command(binary, row, config)
    time_command = [
        "/usr/bin/time",
        "--quiet",
        "--output",
        str(resource_path),
        "--format=max_rss_kib=%M\\nelapsed_real_seconds=%e",
        *command,
    ]
    command_path.write_text(shlex.join(time_command) + "\n", encoding="utf-8")

    observation = observation_template(row, identity, config) if kind == "baseline" else None
    if observation is not None:
        observation.update(
            {
                "command_path": command_path.name,
                "status_path": status_path.name,
                "stdout_path": stdout_path.name,
                "stderr_path": stderr_path.name,
                "resource_path": resource_path.name,
            }
        )

    ac_online, power_details = ac_status()
    if not ac_online:
        reason = "energia AC não confirmada antes da execução: " + "; ".join(power_details)
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(reason + "\n", encoding="utf-8")
        status_path.write_text("exit_status=not_started\nreason=" + reason + "\n", encoding="utf-8")
        if observation is not None:
            observation["status"] = "invalid"
            observation["exclusion_reason"] = reason
            return observation
        raise CampaignError(reason)

    try:
        completed = subprocess.run(time_command, check=False, capture_output=True, text=True)
    except OSError as error:
        reason = f"erro ao iniciar o comando: {error}"
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text(reason + "\n", encoding="utf-8")
        status_path.write_text("launch_error=" + str(error) + "\n", encoding="utf-8")
        if observation is not None:
            observation["status"] = "failed"
            observation["exclusion_reason"] = reason
            return observation
        raise CampaignError(reason) from error
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    status_path.write_text(f"exit_status={completed.returncode}\n", encoding="utf-8")
    if completed.returncode != 0:
        reason = f"comando retornou status {completed.returncode}"
        with status_path.open("a", encoding="utf-8") as stream:
            stream.write(f"validation_error={reason}\n")
        if observation is not None:
            observation["status"] = "failed"
            observation["exclusion_reason"] = reason
            return observation
        raise CampaignError(reason)

    try:
        result = parse_benchmark_output(completed.stdout, row, config)
        max_rss_kib = parse_resource_output(resource_path)
    except CampaignError as error:
        with status_path.open("a", encoding="utf-8") as stream:
            stream.write(f"validation_error={error}\n")
        if observation is not None:
            observation["status"] = "invalid"
            observation["exclusion_reason"] = str(error)
            return observation
        raise

    if observation is None:
        return None
    observation.update(
        {
            "status": "success",
            "core_id": result["core_id"],
            "wall_time_ns": result["elapsed_ns"],
            "phase_eval_ns": result["evaluation_ns"],
            "phase_selection_ns": result["selection_ns"],
            "phase_crossover_ns": result["crossover_ns"],
            "phase_mutation_ns": result["mutation_ns"],
            "phase_replacement_ns": result["replacement_ns"],
            "max_rss_kib": max_rss_kib,
            "best_fitness": result["best_fitness"],
            "checksum": result["checksum"],
        }
    )
    return observation


def write_summary(path: Path, rows: list[dict[str, str]], observations: list[dict[str, str]]) -> None:
    statuses = {(row["N"], row["L"]): {"success": 0, "failed": 0, "invalid": 0} for row in rows}
    planned = {(row["N"], row["L"]): 0 for row in rows}
    for row in rows:
        planned[(row["N"], row["L"])] += 1
    for observation in observations:
        statuses[(observation["N"], observation["L"])][observation["status"]] += 1
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=SUMMARY_FIELDS, lineterminator="\n")
        writer.writeheader()
        for treatment in sorted(planned, key=lambda item: (int(item[0]), int(item[1]))):
            counts = statuses[treatment]
            writer.writerow(
                {
                    "N": treatment[0],
                    "L": treatment[1],
                    "planned": planned[treatment],
                    "success": counts["success"],
                    "failed": counts["failed"],
                    "invalid": counts["invalid"],
                }
            )


def capture_environment(output_dir: Path, metadata_dir: Path, binary: Path) -> None:
    command = [str(ENVIRONMENT_SCRIPT), "--output-dir", str(metadata_dir), "--binary", str(binary)]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    (output_dir / "environment.command").write_text(shlex.join(command) + "\n", encoding="utf-8")
    (output_dir / "environment.stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (output_dir / "environment.stderr.txt").write_text(completed.stderr, encoding="utf-8")
    (output_dir / "environment.status").write_text(
        f"exit_status={completed.returncode}\nmetadata_dir={metadata_dir}\n", encoding="utf-8"
    )
    if completed.returncode != 0:
        raise CampaignError(
            "o inventário imediatamente anterior à campanha falhou; "
            f"consulte {output_dir / 'environment.stderr.txt'}"
        )
    taskset_status = metadata_dir / "taskset-test.status"
    if "taskset_result=passed" not in read_lines(taskset_status):
        raise CampaignError(f"o inventário não confirmou a afinidade; consulte {taskset_status}")


def append_manifest(path: Path, **values: str) -> None:
    with path.open("a", encoding="utf-8") as stream:
        for key, value in values.items():
            stream.write(f"{key}={value}\n")


def dry_run(config: CampaignConfig, design: list[dict[str, str]], binary: Path) -> None:
    print("Campanha baseline validada; nenhum dado foi escrito (--dry-run).")
    print(
        f"linhas={len(design)}; tratamentos={config.experiment.combinations}; "
        f"réplicas/tratamento={config.experiment.baseline_replications}; "
        f"CPU={config.experiment.target_core}; aquecimentos={config.warmup_runs}."
    )
    print("aquecimento: " + shlex.join(benchmark_command(binary, design[0], config)))
    print("primeira observação: " + design[0]["run_id"])
    print("última observação: " + design[-1]["run_id"])


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa a campanha baseline do DOE congelado e preserva suas saídas brutas."
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="configuração YAML")
    parser.add_argument("--design", type=Path, default=DEFAULT_OUTPUT, help="DOE CSV congelado")
    parser.add_argument("--binary", type=Path, default=DEFAULT_BINARY, help="ag_bench compilado")
    parser.add_argument("--output-dir", type=Path, help="novo diretório para as saídas brutas")
    parser.add_argument("--dry-run", action="store_true", help="valida e mostra o plano sem executar")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    output_dir: Path | None = None
    manifest_path: Path | None = None
    try:
        config = read_campaign_config(arguments.config)
        design = read_frozen_design(arguments.design, config.experiment)
        if arguments.dry_run:
            dry_run(config, design, arguments.binary)
            return 0
        if not arguments.binary.is_file() or not os.access(arguments.binary, os.X_OK):
            raise CampaignError(f"binário ausente ou não executável: {arguments.binary}; execute make build")
        if not ENVIRONMENT_SCRIPT.is_file() or not os.access(ENVIRONMENT_SCRIPT, os.X_OK):
            raise CampaignError(f"script de inventário ausente ou não executável: {ENVIRONMENT_SCRIPT}")
        ac_online, power_details = ac_status()
        if not ac_online:
            raise CampaignError(
                "energia AC não confirmada; a campanha não foi iniciada. Estado observado: "
                + "; ".join(power_details)
            )
        identity = read_identity(arguments.binary)
        output_dir = arguments.output_dir or RAW_ROOT / f"baseline-{timestamp_slug()}"
        if output_dir.exists():
            raise CampaignError(f"diretório de saída já existe: {output_dir}")
        output_dir.mkdir(parents=True)
        metadata_dir = METADATA_ROOT / f"environment-baseline-{timestamp_slug()}"
        manifest_path = output_dir / "manifest.txt"
        manifest_path.write_text(
            "\n".join(
                [
                    f"started_at={now()}",
                    f"config={arguments.config}",
                    f"config_sha256={sha256(arguments.config)}",
                    f"design={arguments.design}",
                    f"design_sha256={sha256(arguments.design)}",
                    f"binary={arguments.binary}",
                    f"binary_sha256={identity.binary_sha256}",
                    f"git_commit={identity.git_commit}",
                    f"compiler={identity.compiler}",
                    f"compiler_flags={identity.compiler_flags}",
                    f"target_core={config.experiment.target_core}",
                    f"power_state={'; '.join(power_details)}",
                    f"warmup_runs_per_mode={config.warmup_runs}",
                    f"planned_baseline_observations={len(design)}",
                    f"environment_metadata={metadata_dir}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        capture_environment(output_dir, metadata_dir, arguments.binary)

        observations: list[dict[str, str]] = []
        observations_path = output_dir / "observations.csv"
        write_observations(observations_path, observations)
        warmup = run_benchmark(
            output_dir, 0, "warmup", design[0], arguments.binary, config, identity
        )
        if warmup is not None:
            raise CampaignError("erro interno: aquecimento foi gravado como observação planejada")
        for index, row in enumerate(design, start=1):
            observation = run_benchmark(
                output_dir, index, "baseline", row, arguments.binary, config, identity
            )
            if observation is None:
                raise CampaignError("erro interno: execução baseline não gerou observação")
            observations.append(observation)
            write_observations(observations_path, observations)
            if observation["status"] != "success":
                write_summary(output_dir / "summary.csv", design, observations)
                raise CampaignError(
                    f"{row['run_id']} terminou com status {observation['status']}; "
                    "a saída foi preservada e nenhuma linha foi repetida"
                )

        write_summary(output_dir / "summary.csv", design, observations)
        if len(observations) != len(design) or any(
            observation["status"] != "success" for observation in observations
        ):
            raise CampaignError("a campanha não produziu todas as observações baseline válidas")
        append_manifest(manifest_path, completed_at=now(), status="completed")
        print(f"Campanha baseline concluída: {len(observations)} observações em {output_dir}")
        return 0
    except (CampaignError, DesignError, OSError) as error:
        if manifest_path is not None:
            append_manifest(manifest_path, finished_at=now(), status="failed", reason=str(error))
        print(f"erro: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
