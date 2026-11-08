#!/usr/bin/env python3
"""Arquiva os controles históricos exigidos para validar campanhas preservadas.

As campanhas registram hashes de `experiment.yaml` e `design.csv`. Quando a
entrega é extraída sem `.git`, o validador ainda precisa dos bytes exatos
daqueles arquivos. Este script materializa cópias verificadas em metadata;
ele não modifica dados brutos, medições ou o DOE corrente.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "experiment.yaml"
DESIGN = ROOT / "config" / "design.csv"
ARCHIVE_ROOT = ROOT / "data" / "metadata" / "frozen-inputs"
CAMPAIGNS = (
    ROOT / "data" / "raw" / "baseline-2026-11-07T17_08_32-03_00",
    ROOT / "data" / "raw" / "phases-2026-11-08T00_39_18-03_00",
    ROOT / "data" / "raw" / "perf-2026-11-08T01_45_16-03_00",
)


class ArchiveError(RuntimeError):
    """Indica ausência ou divergência de um snapshot histórico."""


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def manifest_values(path: Path) -> dict[str, str]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ArchiveError(f"não foi possível ler {path.relative_to(ROOT)}: {error}") from error
    values: dict[str, str] = {}
    for line in lines:
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def required_pairs() -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for campaign in CAMPAIGNS:
        values = manifest_values(campaign / "manifest.txt")
        config_hash = values.get("config_sha256")
        design_hash = values.get("design_sha256")
        if not config_hash or not design_hash:
            raise ArchiveError(f"manifesto incompleto: {(campaign / 'manifest.txt').relative_to(ROOT)}")
        pairs.add((config_hash, design_hash))
    return pairs


def git_content(commit: str, relative_path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{commit}:{relative_path}"],
        check=False,
        capture_output=True,
    )
    return result.stdout if result.returncode == 0 else None


def candidates() -> list[tuple[str, bytes, bytes]]:
    result: list[tuple[str, bytes, bytes]] = [("worktree", CONFIG.read_bytes(), DESIGN.read_bytes())]
    history = subprocess.run(
        ["git", "-C", str(ROOT), "rev-list", "--all"],
        check=False,
        capture_output=True,
        text=True,
    )
    if history.returncode != 0:
        return result
    for commit in history.stdout.splitlines():
        config = git_content(commit, "config/experiment.yaml")
        design = git_content(commit, "config/design.csv")
        if config is not None and design is not None:
            result.append((f"Git {commit}", config, design))
    return result


def snapshot_directory(config_hash: str, design_hash: str) -> Path:
    return ARCHIVE_ROOT / f"config-{config_hash}_design-{design_hash}"


def checked_snapshot(config_hash: str, design_hash: str) -> tuple[bytes, bytes]:
    directory = snapshot_directory(config_hash, design_hash)
    try:
        config = (directory / "experiment.yaml").read_bytes()
        design = (directory / "design.csv").read_bytes()
    except OSError as error:
        raise ArchiveError(f"snapshot ausente: {directory.relative_to(ROOT)} ({error})") from error
    if sha256(config) != config_hash or sha256(design) != design_hash:
        raise ArchiveError(f"hash divergente no snapshot: {directory.relative_to(ROOT)}")
    return config, design


def write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(delete=False, dir=path.parent, prefix=path.name + ".") as stream:
        temporary = Path(stream.name)
        stream.write(content)
    temporary.replace(path)


def materialize(pairs: set[tuple[str, str]]) -> None:
    available = candidates()
    for config_hash, design_hash in sorted(pairs):
        match = next(
            ((label, config, design) for label, config, design in available if sha256(config) == config_hash and sha256(design) == design_hash),
            None,
        )
        if match is None:
            raise ArchiveError(f"não há worktree ou histórico Git para config={config_hash} design={design_hash}")
        label, config, design = match
        directory = snapshot_directory(config_hash, design_hash)
        write_bytes(directory / "experiment.yaml", config)
        write_bytes(directory / "design.csv", design)
        write_bytes(
            directory / "manifest.txt",
            (
                f"config_sha256={config_hash}\n"
                f"design_sha256={design_hash}\n"
                f"source={label}\n"
            ).encode("utf-8"),
        )
        print(f"Snapshot arquivado: {directory.relative_to(ROOT)}")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="arquiva snapshots históricos de configuração e DOE")
    parser.add_argument("--check", action="store_true", help="confere snapshots sem regravá-los")
    return parser.parse_args()


def main() -> int:
    args = arguments()
    try:
        pairs = required_pairs()
        if args.check:
            for config_hash, design_hash in sorted(pairs):
                checked_snapshot(config_hash, design_hash)
            print(f"Snapshots históricos válidos: {len(pairs)} pares.")
        else:
            materialize(pairs)
    except ArchiveError as error:
        print(f"Arquivamento de inputs falhou: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
