#!/usr/bin/env bash
# Captura um instantâneo auditável da plataforma e testa os pré-requisitos da
# campanha. Não altera governor, Turbo, afinidade global nem perf_event_paranoid.
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config_file="${project_root}/config/experiment.yaml"
binary="${project_root}/build/ag_bench"
metadata_root="${project_root}/data/metadata"
summary_file="${project_root}/docs/environment.md"
target_core=""
output_dir=""

usage() {
    cat <<'EOF'
Uso: scripts/capture_environment.sh [opções]

Captura o inventário em data/metadata/environment-<timestamp>/, testa o
binário no CPU lógico configurado e atualiza docs/environment.md.

Opções:
  --core CPU          sobrescreve temporariamente environment_controls.target_core
  --output-dir DIR    diretório de saída explícito (deve ainda não existir)
  --binary CAMINHO    binário a testar (padrão: build/ag_bench)
  --help              mostra esta ajuda

O teste de perf é apenas uma pré-condição: sua falha é registrada no
instantâneo, mas não modifica a configuração de segurança do sistema.
EOF
}

die() {
    printf 'erro: %s\n' "$*" >&2
    exit 2
}

read_configured_core() {
    local core
    core="$(awk -F: '
        /^[[:space:]]*target_core[[:space:]]*:/ {
            value = $2
            sub(/#.*/, "", value)
            gsub(/[[:space:]]/, "", value)
            if (value ~ /^[0-9]+$/) {
                print value
                exit
            }
        }
    ' "${config_file}")"
    [[ -n "${core}" ]] || die "target_core numérico ausente em ${config_file}"
    printf '%s\n' "${core}"
}

while (($# > 0)); do
    case "$1" in
        --core)
            (($# >= 2)) || die "faltou valor para --core"
            target_core="$2"
            shift 2
            ;;
        --output-dir)
            (($# >= 2)) || die "faltou valor para --output-dir"
            output_dir="$2"
            shift 2
            ;;
        --binary)
            (($# >= 2)) || die "faltou valor para --binary"
            binary="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            die "opção desconhecida: $1"
            ;;
    esac
done

[[ -f "${config_file}" ]] || die "configuração ausente: ${config_file}"
[[ -n "${target_core}" ]] || target_core="$(read_configured_core)"
[[ "${target_core}" =~ ^[0-9]+$ ]] || die "CPU alvo deve ser um inteiro não negativo"
[[ -d "/sys/devices/system/cpu/cpu${target_core}" ]] || \
    die "CPU lógico ${target_core} não existe ou não está exposto pelo sistema"
[[ -x "${binary}" ]] || die "binário ausente ou não executável: ${binary}; execute make build"

if [[ -z "${output_dir}" ]]; then
    timestamp="$(date --iso-8601=seconds | tr ':+' '__' | sed 's/[+-][0-9][0-9]*$//')"
    output_dir="${metadata_root}/environment-${timestamp}"
fi
[[ ! -e "${output_dir}" ]] || die "diretório de saída já existe: ${output_dir}"
mkdir -p "${output_dir}"

run_capture() {
    local label="$1"
    shift
    local destination="${output_dir}/${label}"
    local status=0
    {
        printf '# comando:'
        printf ' %q' "$@"
        printf '\n\n'
        set +e
        "$@"
        status=$?
        set -e
        printf '\n# status=%s\n' "${status}"
    } >"${destination}" 2>&1
    printf '%s=%s\n' "${label}" "${status}" >> "${output_dir}/command-status.txt"
    return 0
}

read_sysfs() {
    local path="$1"
    local value
    if [[ -r "${path}" ]]; then
        value="$(<"${path}")"
        printf '%s' "${value}"
    else
        printf 'UNAVAILABLE'
    fi
}

append_cpu_snapshot() {
    local cpu_path cpu_id
    printf 'cpu,core_id,package_id,thread_siblings_list,cpu_capacity,governor,scaling_cur_freq_khz,energy_performance_preference\n'
    for cpu_path in /sys/devices/system/cpu/cpu[0-9]*; do
        cpu_id="${cpu_path##*cpu}"
        printf '%s,%s,%s,%s,%s,%s,%s,%s\n' \
            "${cpu_id}" \
            "$(read_sysfs "${cpu_path}/topology/core_id")" \
            "$(read_sysfs "${cpu_path}/topology/physical_package_id")" \
            "$(read_sysfs "${cpu_path}/topology/thread_siblings_list")" \
            "$(read_sysfs "${cpu_path}/cpu_capacity")" \
            "$(read_sysfs "${cpu_path}/cpufreq/scaling_governor")" \
            "$(read_sysfs "${cpu_path}/cpufreq/scaling_cur_freq")" \
            "$(read_sysfs "${cpu_path}/cpufreq/energy_performance_preference")"
    done
}

capture_control_snapshot() {
    {
        printf 'intel_pstate_no_turbo='
        read_sysfs /sys/devices/system/cpu/intel_pstate/no_turbo
        printf '\ncpufreq_boost='
        read_sysfs /sys/devices/system/cpu/cpufreq/boost
        printf '\nperf_event_paranoid='
        read_sysfs /proc/sys/kernel/perf_event_paranoid
        printf '\nnmi_watchdog='
        read_sysfs /proc/sys/kernel/nmi_watchdog
        printf '\n'
    } > "${output_dir}/kernel-controls.txt"

    {
        for supply in /sys/class/power_supply/*; do
            [[ -e "${supply}" ]] || continue
            printf '%s type=%s online=%s status=%s\n' \
                "${supply##*/}" \
                "$(read_sysfs "${supply}/type")" \
                "$(read_sysfs "${supply}/online")" \
                "$(read_sysfs "${supply}/status")"
        done
    } > "${output_dir}/power-state.txt"
}

printf 'captured_at=%s\n' "$(date --iso-8601=seconds)" > "${output_dir}/manifest.txt"
printf 'target_core=%s\n' "${target_core}" >> "${output_dir}/manifest.txt"
printf 'binary=%s\n' "${binary}" >> "${output_dir}/manifest.txt"
printf 'git_commit=%s\n' "$(git -C "${project_root}" rev-parse HEAD)" >> "${output_dir}/manifest.txt"
: > "${output_dir}/command-status.txt"

run_capture uname.txt uname -a
run_capture os-release.txt cat /etc/os-release
run_capture lscpu.txt lscpu
run_capture lscpu.json lscpu -J
run_capture lscpu-extended.txt lscpu --all --extended=CPU,CORE,SOCKET,NODE,ONLINE
run_capture meminfo.txt cat /proc/meminfo
run_capture free.txt free -h
run_capture load.txt sh -c 'uptime; cat /proc/loadavg'
run_capture gcc-version.txt g++ --version
run_capture perf-version.txt perf --version
run_capture perf-list.txt perf list --no-desc
run_capture time-version.txt /usr/bin/time --version
run_capture git-status.txt git -C "${project_root}" status --short
run_capture git-diff.txt git -C "${project_root}" diff --check
run_capture binary-sha256.txt sha256sum "${binary}"
run_capture build-info.txt cat "${project_root}/build/build-info.txt"
run_capture binary-help.txt "${binary}" --help

append_cpu_snapshot > "${output_dir}/cpu-topology-and-frequency.csv"
capture_control_snapshot

taskset_stdout="${output_dir}/taskset-test.csv"
taskset_stderr="${output_dir}/taskset-test.stderr"
set +e
taskset -c "${target_core}" "${binary}" --header --population 8 --length 8 --generations 2 \
    --seed 0 --crossover 0.90 --mutation 0.01 --mode baseline \
    > "${taskset_stdout}" 2> "${taskset_stderr}"
taskset_status=$?
set -e
printf 'taskset_command=taskset -c %q %q --header --population 8 --length 8 --generations 2 --seed 0 --crossover 0.90 --mutation 0.01 --mode baseline\n' \
    "${target_core}" "${binary}" > "${output_dir}/taskset-test.command"
printf 'taskset_exit_status=%s\n' "${taskset_status}" > "${output_dir}/taskset-test.status"

observed_core=""
if [[ "${taskset_status}" -eq 0 ]]; then
    observed_core="$(awk -F, '
        NR == 1 {
            for (i = 1; i <= NF; ++i) if ($i == "core_id") column = i
            next
        }
        NR == 2 && column { print $column; exit }
    ' "${taskset_stdout}")"
fi
if [[ "${observed_core}" == "${target_core}" ]]; then
    taskset_result="passed"
else
    taskset_result="failed"
fi
printf 'taskset_result=%s\nobserved_core=%s\n' "${taskset_result}" "${observed_core:-UNAVAILABLE}" \
    >> "${output_dir}/taskset-test.status"

# O CPU alvo foi selecionado como P-core. Em processadores Intel híbridos,
# os aliases genéricos fazem o perf abrir simultaneamente cpu_core e cpu_atom;
# a instância atom aparece como <not counted> quando o processo está preso ao
# P-core. Estes nomes literais mantêm apenas a PMU pertinente à campanha.
perf_events='cpu_core/cycles/,cpu_core/instructions/,cpu_core/cache-references/,cpu_core/cache-misses/,context-switches,cpu-migrations'
printf '%s\n' "${perf_events}" > "${output_dir}/perf-test.events"
printf 'perf stat --no-big-num -x, -e %q -- taskset -c %q %q --population 8 --length 8 --generations 2 --seed 0 --crossover 0.90 --mutation 0.01 --mode baseline\n' \
    "${perf_events}" "${target_core}" "${binary}" > "${output_dir}/perf-test.command"
set +e
perf stat --no-big-num -x, -e "${perf_events}" -- \
    taskset -c "${target_core}" "${binary}" --population 8 --length 8 --generations 2 \
    --seed 0 --crossover 0.90 --mutation 0.01 --mode baseline \
    > "${output_dir}/perf-test.stdout" 2> "${output_dir}/perf-test.stderr"
perf_status=$?
set -e
printf 'perf_exit_status=%s\n' "${perf_status}" > "${output_dir}/perf-test.status"
if [[ "${perf_status}" -eq 0 ]]; then
    if grep -qE '<not counted>|<not supported>' "${output_dir}/perf-test.stderr"; then
        perf_result="incomplete_event_set"
        perf_multiplexing="unknown"
    elif awk -F, '
        NF >= 5 { observed = 1; if ($5 !~ /^100(\.0+)?$/) invalid = 1 }
        END { exit (observed && !invalid) ? 0 : 1 }
    ' "${output_dir}/perf-test.stderr"; then
        perf_result="passed_without_multiplexing"
        perf_multiplexing="no"
    else
        perf_result="passed_with_multiplexing"
        perf_multiplexing="yes_or_unknown"
    fi
elif grep -q 'perf_event_paranoid setting is' "${output_dir}/perf-test.stderr"; then
    perf_result="blocked_by_permissions"
    perf_multiplexing="unknown"
else
    perf_result="unavailable_or_failed"
    perf_multiplexing="unknown"
fi
printf 'perf_result=%s\nperf_multiplexing=%s\n' "${perf_result}" "${perf_multiplexing}" \
    >> "${output_dir}/perf-test.status"

cpu_model="$(awk -F: '/^Model name:/ { sub(/^[[:space:]]*/, "", $2); print $2; exit }' "${output_dir}/lscpu.txt")"
kernel="$(awk 'NR == 3 { print $3; exit }' "${output_dir}/uname.txt")"
governor="$(awk -F, -v cpu="${target_core}" '$1 == cpu { print $6; exit }' "${output_dir}/cpu-topology-and-frequency.csv")"
epp="$(awk -F, -v cpu="${target_core}" '$1 == cpu { print $8; exit }' "${output_dir}/cpu-topology-and-frequency.csv")"
perf_paranoid="$(awk -F= '/^perf_event_paranoid=/ { print $2; exit }' "${output_dir}/kernel-controls.txt")"
smt_cpus="$(awk -F, 'NR > 1 && $4 ~ /-/ { printf "%s%s", separator, $1; separator = "," }' "${output_dir}/cpu-topology-and-frequency.csv")"
power_state="$(tr '\n' ';' < "${output_dir}/power-state.txt" | sed 's/;$//')"
if [[ "${perf_result}" == "passed_without_multiplexing" ]]; then
    perf_detail="os eventos literais do P-core foram aceitos e todos reportaram 100.00%, sem multiplexação"
    perf_limitation="Os contadores estão disponíveis para a futura campanha no P-core, mas este teste curto não é uma observação de desempenho e não deve ser analisado como tal."
elif [[ "${perf_result}" == "incomplete_event_set" ]]; then
    perf_detail="o comando terminou, mas ao menos uma instância de evento ficou indisponível; consultar perf-test.stderr"
    perf_limitation="A cadeia de eventos precisa ser corrigida antes de produzir contadores de campanha."
elif [[ "${perf_result}" == "passed_with_multiplexing" ]]; then
    perf_detail="os eventos foram aceitos, mas a razão de execução indica multiplexação ou formato inesperado; consultar perf-test.stderr"
    perf_limitation="A cadeia de eventos precisa ser reduzida ou agrupada antes de produzir contadores de campanha."
elif [[ "${perf_result}" == "blocked_by_permissions" ]]; then
    perf_detail="a coleta foi bloqueada por permissão; o kernel reportou perf_event_paranoid=${perf_paranoid}"
    perf_limitation="Contadores de hardware ficam fora da campanha enquanto o perf não puder ser executado com eventos válidos; não se deve inferi-los a partir de execuções diferentes."
else
    perf_detail="a coleta falhou; consultar perf-test.stderr para a mensagem literal"
    perf_limitation="Contadores de hardware ficam fora da campanha enquanto o perf não puder ser executado com eventos válidos; não se deve inferi-los a partir de execuções diferentes."
fi
relative_snapshot="${output_dir#"${project_root}/"}"

cat > "${summary_file}" <<EOF
# Ambiente experimental

Este resumo foi gerado por \`scripts/capture_environment.sh\` a partir do instantâneo bruto em [\`${relative_snapshot}\`](../${relative_snapshot}). Ele descreve a plataforma observada em **$(awk -F= '/^captured_at=/ { print $2; exit }' "${output_dir}/manifest.txt")**, e não substitui uma nova captura antes de uma campanha.

## Plataforma e CPU selecionado

- Processador informado pelo sistema: \`${cpu_model}\`.
- Kernel observado: \`${kernel}\`; inventários de CPU, caches, memória e sistema estão no instantâneo bruto.
- CPU lógico alvo: **${target_core}**. Nesta máquina, ele pertence ao núcleo físico \`$(awk -F, -v cpu="${target_core}" '$1 == cpu { print $2; exit }' "${output_dir}/cpu-topology-and-frequency.csv")\` e tem irmãos lógicos \`$(awk -F, -v cpu="${target_core}" '$1 == cpu { print $4; exit }' "${output_dir}/cpu-topology-and-frequency.csv")\`.
- A escolha de P-core é uma inferência da topologia: neste instantâneo, os CPUs ${smt_cpus} têm SMT, enquanto os demais têm uma única thread; o sistema não expôs um atributo explícito de tipo de núcleo. Se a plataforma, BIOS ou kernel mudar, a seleção precisa ser confirmada novamente.

## Pré-condições da campanha

- Teste de afinidade: **${taskset_result}**. \`taskset -c ${target_core}\` executou o binário de teste e ele reportou \`core_id=${observed_core:-UNAVAILABLE}\`; os arquivos \`taskset-test.*\` preservam comando, saída e status.
- Ferramentas inventariadas: \`taskset\`, \`perf\`, \`g++\` e \`/usr/bin/time\`; suas versões, ajuda/lista de eventos e status estão no instantâneo.
- Teste de \`perf stat\` com \`${perf_events}\`: **${perf_result}** (status ${perf_status}); ${perf_detail}. A saída literal está em \`perf-test.stderr\` e não é dado de desempenho.
- Controle observado no CPU ${target_core}: governor \`${governor}\`, preferência energética \`${epp}\`; \`intel_pstate/no_turbo\`, \`nmi_watchdog\` e o estado da alimentação estão em \`kernel-controls.txt\` e \`power-state.txt\`.
- Alimentação no momento do instantâneo: \`${power_state}\`.
- \`perf_event_paranoid=${perf_paranoid}\` foi apenas registrado; o script não altera privilégios nem parâmetros do kernel.

## Situação e limitações atuais

Este instantâneo não é uma campanha: não há aquecimento, réplicas nem medições em \`data/raw/\`. ${perf_limitation} A captura observou o estado de alimentação acima, portanto a campanha só deve começar após confirmar energia AC conforme o protocolo. Governor, Turbo, frequência e alimentação são registrados, mas não foram forçados pelo script.
EOF

printf 'Inventário salvo em %s\n' "${output_dir}"
printf 'Resumo atualizado em %s\n' "${summary_file}"
printf 'taskset=%s; perf=%s\n' "${taskset_result}" "${perf_result}"

if [[ "${taskset_result}" != "passed" ]]; then
    printf 'erro: teste de afinidade não confirmou o CPU alvo; consulte %s\n' \
        "${output_dir}/taskset-test.status" >&2
    exit 1
fi
