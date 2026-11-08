#!/usr/bin/env python3
"""Valida e consolida as campanhas brutas da Etapa 2.

O arquivo de saída é deliberadamente uma cópia rastreável das observações
brutas, com uma coluna que identifica a campanha e o CSV de origem.  Nenhum
valor medido é corrigido aqui: uma violação do contrato interrompe a geração
dos dados tratados e deixa os artefatos em ``data/raw`` intactos.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import math
import os
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from generate_design import (
    DEFAULT_CONFIG,
    DEFAULT_OUTPUT as DEFAULT_DESIGN,
    FIELDNAMES as DESIGN_FIELDS,
    DesignError,
    make_rows,
    read_experiment,
    scalar,
)


ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = ROOT / "data" / "raw"
PROCESSED_ROOT = ROOT / "data" / "processed"
FROZEN_INPUTS_ROOT = ROOT / "data" / "metadata" / "frozen-inputs"
METADATA_ROOT = ROOT / "data" / "metadata"
DEFAULT_BASELINE = RAW_ROOT / "baseline-2026-11-07T17_08_32-03_00"
DEFAULT_PHASES = RAW_ROOT / "phases-2026-11-08T00_39_18-03_00"
DEFAULT_PERF = RAW_ROOT / "perf-2026-11-08T01_45_16-03_00"

COMMON_FIELDS = {
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
}
PERF_FIELDS = {
    "perf_events",
    "perf_event_runtime_ns",
    "perf_running_percent",
    "perf_multiplexed",
    "cycles",
    "instructions",
    "cache_references",
    "cache_misses",
    "context_switches",
    "cpu_migrations",
    "perf_path",
}
PROCESSED_FIELDS = [
    "source_campaign",
    "source_observations_csv",
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
    "perf_events",
    "perf_event_runtime_ns",
    "perf_running_percent",
    "perf_multiplexed",
    "cycles",
    "instructions",
    "cache_references",
    "cache_misses",
    "context_switches",
    "cpu_migrations",
    "max_rss_kib",
    "best_fitness",
    "checksum",
    "command_path",
    "status_path",
    "stdout_path",
    "stderr_path",
    "perf_path",
    "resource_path",
    "exclusion_reason",
]
ENVIRONMENT_FIELDS = [
    "source_campaign",
    "measurement_mode",
    "captured_at",
    "target_core",
    "git_commit",
    "binary",
    "cpu_model",
    "architecture",
    "l1d_cache",
    "l2_cache",
    "l3_cache",
    "kernel",
    "gcc",
    "perf",
    "power_state",
    "metadata_dir",
]
PHASE_FIELDS = (
    "phase_eval_ns",
    "phase_selection_ns",
    "phase_crossover_ns",
    "phase_mutation_ns",
    "phase_replacement_ns",
)


class ValidationError(RuntimeError):
    """Indica que uma observação não é analisável sob o protocolo congelado."""


@dataclass(frozen=True)
class FrozenSnapshot:
    """DOE e controles literalmente usados por uma campanha preservada."""

    label: str
    design_rows: list[dict[str, str]]
    target_core: int
    crossover_probability: float
    mutation_probability: float


PERF_EVENTS = {
    "ipc_user": (
        "cpu_core/cycles/u",
        "cpu_core/instructions/u",
        "context-switches",
        "cpu-migrations",
    ),
    "cache_user": (
        "cpu_core/cache-references/u",
        "cpu_core/cache-misses/u",
        "context-switches",
        "cpu-migrations",
    ),
}


def repository_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError as error:
        raise ValidationError(f"caminho fora do repositório: {path}") from error


def integer(row: dict[str, str], field: str, *, minimum: int = 0) -> int:
    value = row.get(field, "")
    try:
        parsed = int(value)
    except ValueError as error:
        raise ValidationError(f"{field} não é inteiro: {value!r}") from error
    if parsed < minimum:
        raise ValidationError(f"{field}={parsed} é menor que {minimum}")
    return parsed


def number(row: dict[str, str], field: str, *, minimum: float | None = None) -> float:
    value = row.get(field, "")
    try:
        parsed = float(value)
    except ValueError as error:
        raise ValidationError(f"{field} não é numérico: {value!r}") from error
    if not math.isfinite(parsed):
        raise ValidationError(f"{field} não é finito: {value!r}")
    if minimum is not None and parsed < minimum:
        raise ValidationError(f"{field}={parsed} é menor que {minimum}")
    return parsed


def parse_key_values(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ValidationError(f"não foi possível ler {repository_relative(path)}: {error}") from error
    return dict(line.split("=", 1) for line in lines if "=" in line)


def artifact(directory: Path, row: dict[str, str], field: str, *, required: bool = True) -> Path | None:
    name = row.get(field, "")
    if not name:
        if required:
            raise ValidationError(f"{field} está vazio")
        return None
    candidate = Path(name)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValidationError(f"{field} deve ser um caminho relativo seguro: {name!r}")
    path = directory / candidate
    if not path.is_file():
        raise ValidationError(f"artefato ausente para {field}: {repository_relative(path)}")
    return path


def read_design(path: Path, experiment: object) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != DESIGN_FIELDS:
                raise ValidationError("cabeçalho inesperado em config/design.csv")
            rows = list(reader)
    except OSError as error:
        raise ValidationError(f"não foi possível ler {repository_relative(path)}: {error}") from error
    expected = make_rows(experiment)
    if rows != expected:
        raise ValidationError(
            "config/design.csv diverge do DOE determinístico; execute make design e make check-design"
        )
    return rows


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def design_from_text(content: str, label: str) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(content))
    if reader.fieldnames != DESIGN_FIELDS:
        raise ValidationError(f"cabeçalho inesperado no DOE congelado {label}")
    rows = list(reader)
    if not rows:
        raise ValidationError(f"DOE congelado vazio: {label}")
    return rows


def controls_from_text(content: str, label: str) -> tuple[int, float, float]:
    lines = content.splitlines()
    try:
        target_core = int(scalar(lines, "environment_controls.target_core"))
        crossover = float(scalar(lines, "algorithm.crossover.probability"))
        mutation = float(scalar(lines, "algorithm.mutation.probability_per_gene"))
    except (DesignError, ValueError) as error:
        raise ValidationError(f"controles inválidos em {label}: {error}") from error
    if target_core < 0 or not 0.0 <= crossover <= 1.0 or not 0.0 <= mutation <= 1.0:
        raise ValidationError(f"controles fora do intervalo em {label}")
    return target_core, crossover, mutation


def git_file(commit: str, path: str) -> bytes | None:
    completed = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
        check=False,
        capture_output=True,
    )
    return completed.stdout if completed.returncode == 0 else None


def archived_snapshot(config_hash: str, design_hash: str) -> tuple[str, bytes, bytes] | None:
    """Lê um par histórico enviado junto da entrega, sem exigir `.git`.

    Os manifestos das campanhas registram somente hashes. A cópia literal dos
    dois arquivos fica em metadata e é criada pelo script de arquivamento; os
    hashes ainda são conferidos abaixo antes de qualquer uso.
    """
    directory = FROZEN_INPUTS_ROOT / f"config-{config_hash}_design-{design_hash}"
    config_path = directory / "experiment.yaml"
    design_path = directory / "design.csv"
    try:
        return (f"snapshot arquivado {repository_relative(directory)}", config_path.read_bytes(), design_path.read_bytes())
    except OSError:
        return None


def frozen_snapshot(directory: Path) -> FrozenSnapshot:
    """Resolve o par configuração/DOE pelo hash do manifesto da campanha.

    A campanha baseline e a de fases foram realizadas antes de a separação dos
    grupos de perf reordenar o DOE. Portanto, compará-las ao design atual
    apagaria a proveniência histórica. O manifesto contém hashes dos dois
    arquivos; esta função localiza a versão no histórico Git (ou no worktree)
    com os mesmos bytes, sem alterar o dado bruto.
    """
    manifest = parse_key_values(directory / "manifest.txt")
    config_hash = manifest.get("config_sha256")
    design_hash = manifest.get("design_sha256")
    if not config_hash or not design_hash:
        raise ValidationError(f"manifesto sem hashes de config/DOE: {repository_relative(directory / 'manifest.txt')}")

    candidates: list[tuple[str, bytes, bytes]] = []
    try:
        candidates.append(("worktree atual", DEFAULT_CONFIG.read_bytes(), DEFAULT_DESIGN.read_bytes()))
    except OSError as error:
        raise ValidationError(f"não foi possível ler configuração atual: {error}") from error
    archived = archived_snapshot(config_hash, design_hash)
    if archived is not None:
        candidates.append(archived)
    history = subprocess.run(
        ["git", "-C", str(ROOT), "rev-list", "--all"], check=False, capture_output=True, text=True
    )
    if history.returncode == 0:
        for commit in history.stdout.splitlines():
            config = git_file(commit, "config/experiment.yaml")
            design = git_file(commit, "config/design.csv")
            if config is not None and design is not None:
                candidates.append((f"Git {commit}", config, design))
    for label, config, design in candidates:
        if sha256_bytes(config) != config_hash or sha256_bytes(design) != design_hash:
            continue
        try:
            config_text = config.decode("utf-8")
            design_text = design.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValidationError(f"snapshot não UTF-8: {label}") from error
        target_core, crossover, mutation = controls_from_text(config_text, label)
        return FrozenSnapshot(
            label=label,
            design_rows=design_from_text(design_text, label),
            target_core=target_core,
            crossover_probability=crossover,
            mutation_probability=mutation,
        )
    raise ValidationError(
        "não foi encontrado no worktree, snapshot arquivado ou histórico Git o par de configuração e DOE "
        f"referenciado por {repository_relative(directory / 'manifest.txt')}"
    )


def check_identity(row: dict[str, str]) -> None:
    for field in ("git_commit", "binary_sha256", "compiler", "compiler_flags"):
        if not row.get(field, "").strip():
            raise ValidationError(f"metadado de identidade vazio: {field}")


def expected_perf_values(group: str) -> tuple[str, ...]:
    try:
        return PERF_EVENTS[group]
    except KeyError as error:
        raise ValidationError(f"grupo perf desconhecido: {group}") from error


def check_perf(row: dict[str, str]) -> None:
    group = row["perf_group"]
    events = expected_perf_values(group)
    if row.get("perf_events", "") != ",".join(events):
        raise ValidationError(f"perf_events não corresponde ao grupo {group}")
    if row.get("perf_multiplexed", "") != "no":
        raise ValidationError("perf_multiplexed deve ser 'no' para dados analisáveis")
    for field in ("perf_event_runtime_ns", "perf_running_percent"):
        parts = row.get(field, "").split(";")
        if len(parts) != len(events):
            raise ValidationError(f"{field} deve conter uma entrada por evento")
        for event, part in zip(events, parts, strict=True):
            if not part.startswith(event + ":"):
                raise ValidationError(f"{field} não mantém a ordem literal de eventos")
            value = part.split(":", 1)[1]
            if field == "perf_event_runtime_ns":
                try:
                    if int(value) <= 0:
                        raise ValueError(value)
                except ValueError as error:
                    raise ValidationError(f"tempo de perf inválido: {part!r}") from error
            else:
                try:
                    if abs(float(value) - 100.0) > 0.001:
                        raise ValueError(value)
                except ValueError as error:
                    raise ValidationError(f"contador perf multiplexado: {part!r}") from error

    expected_populated = {
        "ipc_user": {"cycles", "instructions", "context_switches", "cpu_migrations"},
        "cache_user": {"cache_references", "cache_misses", "context_switches", "cpu_migrations"},
    }[group]
    for field in ("cycles", "instructions", "cache_references", "cache_misses", "context_switches", "cpu_migrations"):
        value = row.get(field, "")
        if field in expected_populated:
            minimum = 1 if field in {"cycles", "instructions", "cache_references"} else 0
            integer({field: value}, field, minimum=minimum)
        elif value:
            raise ValidationError(f"{field} não deveria estar preenchido no grupo {group}")


def check_row(
    row: dict[str, str], expected: dict[str, str], directory: Path, snapshot: FrozenSnapshot,
) -> None:
    if row.get("status") != "success":
        raise ValidationError(
            f"status={row.get('status')!r}; dados incompletos permanecem brutos e não entram na análise"
        )
    for field in (
        "run_id", "block", "order", "measurement_mode", "perf_group", "N", "L", "G", "batch",
        "replication", "seed",
    ):
        if row.get(field) != expected[field]:
            raise ValidationError(
                f"{field} diverge do DOE para {expected['run_id']}: "
                f"esperado {expected[field]!r}, recebido {row.get(field)!r}"
            )
    if integer(row, "target_core") != snapshot.target_core:
        raise ValidationError("target_core diverge do CPU congelado")
    if integer(row, "core_id") != int(expected["core_id"]):
        raise ValidationError("core_id efetivo diverge do CPU congelado")
    if abs(number(row, "p_c") - snapshot.crossover_probability) > 1e-15:
        raise ValidationError("p_c diverge da configuração congelada")
    if abs(number(row, "p_m") - snapshot.mutation_probability) > 1e-15:
        raise ValidationError("p_m diverge da configuração congelada")

    wall_time = integer(row, "wall_time_ns", minimum=1)
    phase_sum = sum(integer(row, field) for field in PHASE_FIELDS)
    mode = row["measurement_mode"]
    if mode in {"baseline", "perf"} and phase_sum != 0:
        raise ValidationError(f"fases devem ser zero em {mode}")
    if mode == "phases" and phase_sum > wall_time:
        raise ValidationError("soma das fases excede wall_time_ns")
    if integer(row, "max_rss_kib") < 0:
        raise ValidationError("max_rss_kib negativo")
    if integer(row, "best_fitness") > integer(row, "L", minimum=1):
        raise ValidationError("best_fitness excede L")
    integer(row, "checksum")
    check_identity(row)

    for field in ("command_path", "status_path", "stdout_path", "stderr_path", "resource_path"):
        artifact(directory, row, field)
    status_path = artifact(directory, row, "status_path")
    assert status_path is not None
    if parse_key_values(status_path).get("exit_status") != "0":
        raise ValidationError(f"artefato de status sem exit_status=0: {repository_relative(status_path)}")

    if mode == "perf":
        perf_path = artifact(directory, row, "perf_path")
        assert perf_path is not None
        check_perf(row)
        if perf_path.stat().st_size == 0:
            raise ValidationError(f"saída perf vazia: {repository_relative(perf_path)}")
    else:
        for field in PERF_FIELDS:
            if row.get(field, ""):
                raise ValidationError(f"{field} deve estar vazio no modo {mode}")


def read_campaign(
    directory: Path, mode: str, expected_rows: list[dict[str, str]], snapshot: FrozenSnapshot,
) -> list[dict[str, str]]:
    observation_path = directory / "observations.csv"
    try:
        with observation_path.open(encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is None:
                raise ValidationError(f"CSV sem cabeçalho: {repository_relative(observation_path)}")
            missing = COMMON_FIELDS - set(reader.fieldnames)
            if missing:
                raise ValidationError(f"colunas ausentes em {repository_relative(observation_path)}: {sorted(missing)}")
            if mode == "perf" and (missing := PERF_FIELDS - set(reader.fieldnames)):
                raise ValidationError(f"colunas perf ausentes: {sorted(missing)}")
            rows = list(reader)
    except OSError as error:
        raise ValidationError(f"não foi possível ler {repository_relative(observation_path)}: {error}") from error

    expected_by_key = {
        (row["run_id"], row["measurement_mode"], row["perf_group"]): row for row in expected_rows
    }
    observed_keys: set[tuple[str, str, str]] = set()
    normalized: list[dict[str, str]] = []
    for index, row in enumerate(rows, start=2):
        key = (row.get("run_id", ""), row.get("measurement_mode", ""), row.get("perf_group", ""))
        if key in observed_keys:
            raise ValidationError(f"chave duplicada em {repository_relative(observation_path)}:{index}: {key}")
        observed_keys.add(key)
        if key not in expected_by_key:
            raise ValidationError(f"linha fora do DOE em {repository_relative(observation_path)}:{index}: {key}")
        try:
            check_row(row, expected_by_key[key], directory, snapshot)
        except ValidationError as error:
            raise ValidationError(f"{repository_relative(observation_path)}:{index}: {error}") from error
        normalized.append(
            {
                "source_campaign": directory.name,
                "source_observations_csv": repository_relative(observation_path),
                **{field: row.get(field, "") for field in PROCESSED_FIELDS if field not in {"source_campaign", "source_observations_csv"}},
            }
        )
    expected_keys = set(expected_by_key)
    if observed_keys != expected_keys:
        missing = sorted(expected_keys - observed_keys)
        extra = sorted(observed_keys - expected_keys)
        details = []
        if missing:
            details.append(f"ausentes={missing}")
        if extra:
            details.append(f"extras={extra}")
        raise ValidationError(f"observações não correspondem ao DOE em {repository_relative(observation_path)}: {'; '.join(details)}")
    return normalized


def first_value(path: Path, prefix: str) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith(prefix):
                return line.split(":", 1)[1].strip()
    except OSError as error:
        raise ValidationError(f"não foi possível ler {repository_relative(path)}: {error}") from error
    return ""


def compact_text(path: Path) -> str:
    try:
        return " ".join(line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError as error:
        raise ValidationError(f"não foi possível ler {repository_relative(path)}: {error}") from error


def resolve_metadata_directory(recorded: str) -> Path:
    """Localiza um inventário preservado depois que a entrega muda de pasta.

    As campanhas antigas guardam em `environment.status` o caminho absoluto
    observado no momento da coleta. Esse texto continua sendo uma evidência,
    mas não deve impedir a auditoria de uma cópia relocada do repositório. O
    diretório de metadados é resolvido pelo seu nome sob `data/metadata/` e
    continua sujeito às verificações de existência e de escopo.
    """
    original = Path(recorded)
    if original.is_absolute() and original.is_relative_to(ROOT):
        candidate = original
    elif original.is_absolute():
        if not original.name.startswith("environment-"):
            raise ValidationError(f"metadata_dir absoluto inválido: {original}")
        candidate = METADATA_ROOT / original.name
    else:
        candidate = ROOT / original
    try:
        candidate.resolve().relative_to(ROOT)
    except ValueError as error:
        raise ValidationError(f"metadata_dir fora do repositório: {candidate}") from error
    if not candidate.is_dir():
        raise ValidationError(f"metadata_dir ausente: {repository_relative(candidate)}")
    return candidate


def read_environment(directory: Path, mode: str) -> dict[str, str]:
    status = parse_key_values(directory / "environment.status")
    if status.get("exit_status") != "0" or not status.get("metadata_dir"):
        raise ValidationError(f"inventário inválido para campanha {directory.name}")
    metadata = resolve_metadata_directory(status["metadata_dir"])
    manifest = parse_key_values(metadata / "manifest.txt")
    required = ("captured_at", "target_core", "git_commit", "binary")
    if any(not manifest.get(field) for field in required):
        raise ValidationError(f"manifesto de ambiente incompleto: {repository_relative(metadata / 'manifest.txt')}")
    return {
        "source_campaign": directory.name,
        "measurement_mode": mode,
        "captured_at": manifest["captured_at"],
        "target_core": manifest["target_core"],
        "git_commit": manifest["git_commit"],
        "binary": manifest["binary"],
        "cpu_model": first_value(metadata / "lscpu.txt", "Model name:"),
        "architecture": first_value(metadata / "lscpu.txt", "Architecture:"),
        "l1d_cache": first_value(metadata / "lscpu.txt", "L1d cache:"),
        "l2_cache": first_value(metadata / "lscpu.txt", "L2 cache:"),
        "l3_cache": first_value(metadata / "lscpu.txt", "L3 cache:"),
        "kernel": compact_text(metadata / "uname.txt"),
        "gcc": compact_text(metadata / "gcc-version.txt").split("\n")[0],
        "perf": compact_text(metadata / "perf-version.txt").split("\n")[0],
        "power_state": compact_text(metadata / "power-state.txt"),
        "metadata_dir": repository_relative(metadata),
    }


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="", delete=False, dir=path.parent, prefix=path.name + "."
    ) as stream:
        temporary = Path(stream.name)
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False, dir=path.parent, prefix=path.name + "."
    ) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    os.replace(temporary, path)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="valida e consolida as campanhas brutas")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--phases", type=Path, default=DEFAULT_PHASES)
    parser.add_argument("--perf", type=Path, default=DEFAULT_PERF)
    parser.add_argument("--output", type=Path, default=PROCESSED_ROOT / "measurements.csv")
    parser.add_argument("--environment-output", type=Path, default=PROCESSED_ROOT / "environment.csv")
    parser.add_argument("--report", type=Path, default=PROCESSED_ROOT / "validation-report.md")
    parser.add_argument("--check", action="store_true", help="valida sem criar arquivos derivados")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    try:
        experiment = read_experiment(args.config)
        read_design(args.design, experiment)
        campaigns = ((args.baseline, "baseline"), (args.phases, "phases"), (args.perf, "perf"))
        all_rows: list[dict[str, str]] = []
        environments: list[dict[str, str]] = []
        expected_counts: Counter[str] = Counter()
        for directory, mode in campaigns:
            snapshot = frozen_snapshot(directory)
            expected = [row for row in snapshot.design_rows if row["measurement_mode"] == mode]
            if not expected:
                raise ValidationError(f"DOE congelado {snapshot.label} não contém o modo {mode}")
            expected_counts[mode] = len(expected)
            all_rows.extend(read_campaign(directory, mode, expected, snapshot))
            environments.append(read_environment(directory, mode))
        all_rows.sort(key=lambda row: (row["measurement_mode"], row["perf_group"], int(row["order"])))
        counts = Counter(row["measurement_mode"] for row in all_rows)
        if counts != expected_counts:
            raise ValidationError(f"contagens inesperadas após validação: {dict(counts)}")
        if not args.check:
            write_csv(args.output, PROCESSED_FIELDS, all_rows)
            write_csv(args.environment_output, ENVIRONMENT_FIELDS, environments)
            write_text(
                args.report,
                "# Validação dos dados\n\n"
                "A validação leu somente as três campanhas brutas declaradas, conferiu o DOE congelado, "
                "as chaves, os controles, os artefatos de cada observação, a afinidade e os contratos de fase/perf.\n\n"
                f"- baseline: {counts['baseline']} observações válidas\n"
                f"- phases: {counts['phases']} observações válidas\n"
                f"- perf: {counts['perf']} observações válidas\n\n"
                "Nenhuma observação foi removida ou editada; `measurements.csv` é uma consolidação rastreável.\n",
            )
    except (ValidationError, DesignError) as error:
        print(f"Validação de dados falhou: {error}", file=sys.stderr)
        return 1
    action = "validado sem gerar derivados" if args.check else f"gerado {repository_relative(args.output)}"
    print(
        "Dados válidos: "
        f"baseline={counts['baseline']}, phases={counts['phases']}, perf={counts['perf']}; {action}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
