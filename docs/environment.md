# Ambiente experimental

Este resumo foi gerado por `scripts/capture_environment.sh` a partir do instantâneo bruto em [`data/metadata/environment-2026-11-08T01_53_41-03_00`](../data/metadata/environment-2026-11-08T01_53_41-03_00). Ele descreve a plataforma observada em **2026-11-08T01:53:41-03:00**, e não substitui uma nova captura antes de uma campanha.

## Plataforma e CPU selecionado

- Processador informado pelo sistema: `13th Gen Intel(R) Core(TM) i7-1355U`.
- Kernel observado: `7.0.0-42-generic`; inventários de CPU, caches, memória e sistema estão no instantâneo bruto.
- CPU lógico alvo: **0**. Nesta máquina, ele pertence ao núcleo físico `0` e tem irmãos lógicos `0-1`.
- A escolha de P-core é uma inferência da topologia: neste instantâneo, os CPUs 0,1,2,3 têm SMT, enquanto os demais têm uma única thread; o sistema não expôs um atributo explícito de tipo de núcleo. Se a plataforma, BIOS ou kernel mudar, a seleção precisa ser confirmada novamente.

## Pré-condições da campanha

- Teste de afinidade: **passed**. `taskset -c 0` executou o binário de teste e ele reportou `core_id=0`; os arquivos `taskset-test.*` preservam comando, saída e status.
- Ferramentas inventariadas: `taskset`, `perf`, `g++` e `/usr/bin/time`; suas versões, ajuda/lista de eventos e status estão no instantâneo.
- Testes de `perf stat` por grupo: **passed_without_multiplexing** (status 0); os grupos configurados (ipc_user=passed_without_multiplexing;cache_user=passed_without_multiplexing) foram aceitos e todos reportaram 100.00%, sem multiplexação. A carga de verificação foi `N=2048, L=1024, G=100, B=1`; ela vem do DOE, mas não é dado de desempenho. As saídas literais estão em `perf-test-<grupo>.stderr`.
- Controle observado no CPU 0: governor `powersave`, preferência energética `balance_performance`; `intel_pstate/no_turbo`, `nmi_watchdog` e o estado da alimentação estão em `kernel-controls.txt` e `power-state.txt`.
- Alimentação no momento do instantâneo: `AC type=Mains online=1 status=UNAVAILABLE;BAT0 type=Battery online=UNAVAILABLE status=Not charging`.
- `perf_event_paranoid=0` foi apenas registrado; o script não altera privilégios nem parâmetros do kernel.

## Situação e limitações atuais

Este instantâneo não é uma campanha: não há aquecimento, réplicas nem medições em `data/raw/`. Os contadores estão disponíveis para a futura campanha no P-core, mas este teste de verificação não é uma observação de desempenho e não deve ser analisado como tal. A captura observou o estado de alimentação acima, portanto a campanha só deve começar após confirmar energia AC conforme o protocolo. Governor, Turbo, frequência e alimentação são registrados, mas não foram forçados pelo script.
