#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build_dir="${project_root}/build"
compiler="${CXX:-g++}"

compiler_flags=(
    -std=c++20
    -O3
    -DNDEBUG
    -Wall
    -Wextra
    -Wpedantic
)

mkdir -p "${build_dir}"

"${compiler}" "${compiler_flags[@]}" \
    "${project_root}/src/ga.cpp" \
    "${project_root}/src/main.cpp" \
    -o "${build_dir}/ag_bench"

"${compiler}" "${compiler_flags[@]}" \
    "${project_root}/src/ga.cpp" \
    "${project_root}/src/tests.cpp" \
    -o "${build_dir}/ag_tests"

sha256sum "${build_dir}/ag_bench" > "${build_dir}/ag_bench.sha256"
{
    printf 'compiler='
    "${compiler}" --version | head -n 1
    printf 'flags='
    printf '%q ' "${compiler_flags[@]}"
    printf '\n'
} > "${build_dir}/build-info.txt"

printf 'Binários criados em %s\n' "${build_dir}"
