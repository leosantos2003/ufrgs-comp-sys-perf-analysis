# Estado do projeto — inventário de ambiente e pré-condições

**Data:** 2026-11-04
**Estado associado:** implementação do item 3 do roteiro de execução; inventário automatizado e testes de afinidade e `perf`.

## Contexto do projeto neste estado

O projeto investiga como `N`, o tamanho da população, e `L`, o comprimento do cromossomo, afetam o custo computacional de um algoritmo genético (AG) sequencial para OneMax. O estudo mede desempenho computacional, não a qualidade da solução; cada execução completa exatamente `G` gerações.

Antes deste estado já existiam o AG C++ determinístico, testes funcionais, build reprodutível e os controles congelados em `config/experiment.yaml`. Ainda não havia um inventário automático da máquina, escolha confirmada de CPU lógico, verificação de afinidade ou dados de campanha. Não havia desenho fatorial materializado nem observações em `data/raw/`.

## Significados

- **CPU lógico / `core_id`:** identificador que o Linux atribui a uma unidade de execução. O executável agora o informa após a região cronometrada; sob afinidade ele deve coincidir com o CPU alvo.
- **P-core:** núcleo de desempenho de uma CPU Intel híbrida. Nesta plataforma, a classificação foi inferida porque os CPUs lógicos 0--3 possuem pares SMT e os demais têm uma única thread; o kernel não expôs uma etiqueta direta de tipo de núcleo.
- **`taskset`:** ferramenta que restringe a afinidade de CPU de um processo. Uma campanha futura deve usar o CPU lógico selecionado durante toda a execução.
- **`perf stat`:** ferramenta de contadores de hardware e de eventos do sistema. Sua presença não prova que a coleta seja permitida ou que seus eventos tenham semântica válida.
- **`perf_event_paranoid`:** controle do kernel que limita o acesso de usuários sem privilégios ao subsistema de monitoramento de desempenho.
- **Instantâneo de ambiente:** diretório imutável em `data/metadata/environment-<timestamp>/` com saídas brutas, comandos e status; ele não é uma medição de desempenho.

## Como testar ou reproduzir este estado

Na raiz do projeto, execute:

```bash
make test
make run
make environment
```

`make test` deve terminar com `Todos os testes do AG passaram.`; ele verifica a correção funcional, não desempenho. `make run` deve produzir CSV com a coluna `core_id`; o valor pode variar sem afinidade explícita. `make environment` recompila o binário, lê `environment_controls.target_core` e cria um novo diretório de inventário. O resultado esperado nesta máquina é `taskset=passed` com `observed_core=0`. Após a configuração persistente de `perf_event_paranoid=0` pelo proprietário, o `perf` deve executar; o script só considera uma cadeia pronta para campanha quando os eventos não têm marcadores de indisponibilidade e reportam 100,00% de execução.

Para inspeção pontual do instantâneo deste estado:

```bash
sed -n '1,160p' data/metadata/environment-2026-11-04T14_17_21-03_00/taskset-test.status
sed -n '1,160p' data/metadata/environment-2026-11-04T14_17_21-03_00/perf-test.stderr
```

Esses comandos são pré-condições e smoke tests; não têm aquecimento, réplicas ou duração suficiente para inferir tempo, vazão ou contadores da campanha.

## Mudanças e decisões

- A revisão humana em `docs/uso-ia.md` foi atualizada após a configuração persistente de acesso ao `perf`; as condições restantes foram classificadas como limites para campanhas futuras, não como pendências do item 3.

- Implementado `scripts/capture_environment.sh` e o alvo `make environment`. O script guarda versão do SO, kernel, topologia e caches via `lscpu`, memória, carga, versões de `g++`, `perf` e `/usr/bin/time`, estado Git, hash/flags do binário, controles de frequência/Turbo, alimentação, lista de eventos `perf` e os comandos literais executados.
- O script lê o CPU alvo da configuração, executa um AG mínimo via `taskset -c <CPU>` e valida a afinidade pela coluna `core_id` emitida pelo próprio programa. Falha de afinidade faz o script retornar erro; falha de `perf` é documentada e preservada, sem modificar controles do sistema.
- Adicionada a coluna `core_id` ao CSV de `ag_bench`, capturada após o trecho medido. Assim, sua leitura não entra em `elapsed_ns`.
- Fixado `environment_controls.target_core: 0` em `config/experiment.yaml`. A escolha é o CPU lógico 0, inferido como P-core pelo par SMT `0-1`; ela foi feita antes de qualquer dado de campanha.
- Atualizado `docs/environment.md` por código a partir do instantâneo mais recente e adicionadas instruções de pré-condição ao README.
- Reorganizado `docs/uso-ia.md` em pares sequenciais: cada registro do agente é seguido da revisão humana correspondente, identificando explicitamente revisões pendentes sem atribuir aceitação inexistente.
- Após autorização explícita, o proprietário configurou persistentemente `/etc/sysctl.d/99-ag-perf.conf` com `kernel.perf_event_paranoid = 0`. O script continua somente lendo esse controle; ele não cria nem altera arquivos fora do repositório.
- A cadeia genérica de eventos em CPU híbrida gerou instâncias `cpu_atom` não utilizáveis. O pré-teste passou a usar os nomes literais `cpu_core/cycles/`, `cpu_core/instructions/`, `cpu_core/cache-references/` e `cpu_core/cache-misses/`, com `context-switches` e `cpu-migrations`; o status agora também registra se há multiplexação.

## Evidência e impacto

- `make test` passou e `make run` produziu uma linha CSV com `core_id=0` na execução observada; ambos são smoke tests, não resultados de desempenho.
- O instantâneo corrente é `data/metadata/environment-2026-11-04T14_17_21-03_00/`: identifica Intel Core i7-1355U, kernel `7.0.0-42-generic`, governor `powersave`, preferência energética `balance_power`, `intel_pstate/no_turbo=0`, `nmi_watchdog=1` e `perf_event_paranoid=0` no momento da captura.
- `taskset-test.status` registra `taskset_result=passed` e `observed_core=0` para o CPU alvo 0.
- O bloqueio histórico por `perf_event_paranoid=4` foi preservado no instantâneo das 11:30. Depois da configuração persistente autorizada, `perf stat` retornou status 0; porém os quatro eventos de hardware `cpu_core/*` executaram por 63,00%, enquanto os dois eventos de software executaram por 100,00%. O estado `passed_with_multiplexing` impede tratar esses números como contadores válidos de campanha.
- `power-state.txt` registrou AC offline e bateria descarregando. Não foi iniciada campanha e nenhum arquivo em `data/raw/` foi criado ou alterado.
- A primeira tentativa de captura parou ao ler `target_core`; a correção está registrada em `docs/difficulties.md`. O primeiro e o segundo instantâneos bem-sucedidos desta revisão (`environment-2026-11-04T11_27_45-03_00` e `environment-2026-11-04T11_28_53-03_00`) foram preservados como metadata bruta, e o resumo aponta para a captura posterior corrigida.
- A tentativa não interativa inicial foi preservada como falha de autenticação. O proprietário realizou depois a alteração persistente localmente; `cat /etc/sysctl.d/99-ag-perf.conf` e `/proc/sys/kernel/perf_event_paranoid` confirmaram, respectivamente, a regra e o valor efetivo `0`.

## Limitações e próximo passo

- A designação de P-core é inferida da topologia SMT, não de uma etiqueta exposta pelo sistema. Revalidar se a plataforma, firmware, kernel ou CPU alvo mudar.
- A liberação persistente de `perf_event_paranoid=0` vale globalmente para usuários não privilegiados e é uma decisão explícita do proprietário. Não alterar `nmi_watchdog`, governor ou Turbo sem nova autorização e sem registrar estado anterior, alteração e restauração. Enquanto houver multiplexação, a futura campanha deve declarar a ausência de contadores, em vez de inventar métricas de hardware.
- A captura ocorreu fora da energia AC. Repetir o inventário com a máquina alimentada, minimizar carga concorrente e registrar o novo estado antes da campanha de desempenho.
- Próximo passo: após resolver ou registrar essas condições, materializar o DOE piloto do item 4 sem modificar os controles do AG.
