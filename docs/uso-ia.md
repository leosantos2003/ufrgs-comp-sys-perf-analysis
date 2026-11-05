# Uso de IA no projeto

Este arquivo explica, de forma simples e factual, como a IA foi usada. IA ajuda a planejar, escrever e revisar, mas o grupo continua responsável por entender, testar e aceitar cada resultado.

## Como registrar um uso de IA

Para cada uso relevante, informe: qual ferramenta foi usada, como ela foi usada, quais dados recebeu, o que ela produziu, como o grupo escolheu aceitar, editar ou rejeitar a saída e como uma pessoa verificou o resultado. Escreva apenas fatos; não atribua à IA uma decisão que foi do grupo.

## Registro inicial — plano e estrutura

| Campo | Registro |
|---|---|
| Ferramenta | Codex, assistente de programação. |
| Como foi usada | Conversa iterativa, a pedido do grupo. O grupo decide o que será aproveitado. |
| Dados fornecidos | Enunciado, slides da Etapa 1 e materiais da disciplina disponíveis no diretório. |
| O que ajudou a produzir | Plano de implementação, README, `config/experiment.yaml` e modelos em `docs/`. |
| Como a saída foi avaliada | O grupo deve comparar as sugestões com o enunciado e com as decisões do trabalho antes de usá-las. |
| Verificação humana | Use o modelo ao final deste arquivo para registrar quem revisou, o que foi revisado e a decisão. |

## Revisão humana do registro inicial — pendente

| Campo | Registro |
|---|---|
| Pessoas que revisaram | Pendente. |
| O que foi revisado | Plano e estrutura inicial. |
| Como foi conferido | Pendente. |
| Comandos e resultado | Não se aplica enquanto a revisão não for realizada. |
| Decisão | Pendente. |
| Pendências ou limitações | Registrar a revisão antes de considerar este uso aceito. |

## Registro do agente — 2026-11-03: validação e documentação

| Campo | Registro |
|---|---|
| Ferramenta | Codex, assistente de programação. |
| Como foi usada | O grupo pediu alterações passo a passo; o agente propôs e aplicou mudanças, e os resultados foram verificados com comandos locais. |
| Dados fornecidos | Código-fonte, plano de implementação, README, enunciado e documentos do repositório. |
| O que ajudou a produzir | Referência simples e testes adicionais; mudanças em `src/ga.hpp`, `src/ga.cpp`, `src/tests.cpp`, `scripts/build.sh`, `README.md`, `AGENTS.md` e `docs/`. |
| Como a saída foi avaliada | Foram aceitas apenas mudanças que compilaram, passaram em `make test`, não apresentaram erro em `git diff --check` e foram revisadas pelo grupo. Uma referência com desempate incorreto foi corrigida antes de ser aceita. |
| Verificação automática | `make test`, `make run`, comparação de checksum entre `baseline` e `phases` e `git diff --check`. |
| Verificação humana | O solicitante informou que a revisão está de acordo. Registre os detalhes no modelo abaixo antes do commit. |

## Revisão humana do registro de 2026-11-03

**Data da revisão:** 2026-11-04

| Campo | Registro |
|---|---|
| Pessoas que revisaram | Leonardo |
| O que foi revisado | Implementação do AG |
| Como foi conferido | Leitura dos códigos e execução dos testes |
| Comandos e resultado | `make test` — passou, `./build/ag_bench --population 32 --length 16 --generations 10   --seed 20261022 --crossover 0.90 --mutation 0.01 --mode baseline` — 32,16,10,20261022,0.90000000000000002,0.01,baseline,171575,0,0,0,0,0,16,2855997894351129235, `./build/ag_bench --population 32 --length 16 --generations 10   --seed 20261022 --crossover 0.90 --mutation 0.01 --mode phases` — 32,16,10,20261022,0.90000000000000002,0.01,phases,193523,6904,30353,38655,113657,513,16,2855997894351129235 |
| Decisão | aceito |
| Pendências ou limitações | nenhuma |

## Registro do agente — 2026-11-04: inventário de ambiente e pré-condições

| Campo | Registro |
|---|---|
| Ferramenta | Codex, assistente de programação. |
| Como foi usada | O grupo solicitou a implementação do item 3 do roteiro; o agente inspecionou o repositório e o ambiente local, propôs o script de captura, aplicou as alterações e executou as verificações locais. |
| Dados fornecidos | Plano de implementação, configuração da campanha, código C++, documentação e saídas locais de `lscpu`, `taskset`, `perf` e sysfs. |
| O que ajudou a produzir | `scripts/capture_environment.sh`, alvo `make environment`, registro de `core_id` no CSV do executável, inventários em `data/metadata/`, resumo em `docs/environment.md`, documentação associada e a organização sequencial deste registro de uso de IA. Após a configuração persistente feita pelo proprietário, também ajudou a resolver os aliases da PMU para `cpu_core/*` e a detectar multiplexação. |
| Como a saída foi avaliada | A seleção do CPU 0 foi baseada na topologia SMT observada e mantida explícita na configuração. A indisponibilidade inicial de `perf` foi preservada como limitação; depois de o proprietário configurar `perf_event_paranoid=0`, o agente confirmou a coleta e rejeitou os contadores do pré-teste por multiplexação, sem atribuir causalidade ao `nmi_watchdog` nem modificá-lo. |
| Verificação automática | `bash -n scripts/capture_environment.sh`, `make test`, `make run`, `make environment` e `git diff --check`. A primeira tentativa de alteração foi recusada por `sudo` ao exigir senha; posteriormente, o proprietário configurou a regra persistente e o agente confirmou `perf_event_paranoid=0`, afinidade válida e multiplexação no pré-teste. |
| Verificação humana | Aceita pelo proprietário na seção de revisão humana abaixo. A afinidade e a regra persistente de `perf` foram verificadas; a inferência de P-core, a alimentação AC e a multiplexação seguem registradas como limites para campanhas futuras. |

## Revisão humana do registro de 2026-11-04

| Campo | Registro |
|---|---|
| Pessoas que revisaram | Proprietário da máquina (nome não registrado). |
| O que foi revisado | Inventário de ambiente, afinidade de CPU, limitação de `perf` e documentação associada. |
| Como foi conferido | Ler .sh e arquivos gerados, rodar comandos, ler environment.md, liberar permissão do perf |
| Comandos e resultado | `make test` e `make run` — passaram, `make environment` — taskset=passed, `sudo tee /etc/sysctl.d/99-ag-perf.conf >/dev/null <<'EOF'` -> `kernel.perf_event_paranoid = 0` -> `EOF` -> `sudo sysctl -p /etc/sysctl.d/99-ag-perf.conf` -> `cat /proc/sys/kernel/perf_event_paranoid` |
| Decisão | aceito |
| Pendências ou limitações | A decisão de acesso ao `perf` foi concluída: `/etc/sysctl.d/99-ag-perf.conf` mantém `kernel.perf_event_paranoid = 0`. A inferência de P-core deve ser revalidada se plataforma, firmware ou kernel mudar. A campanha deve aguardar energia AC e não pode usar os contadores enquanto a cadeia atual estiver multiplexada. |

## Registro do agente — 2026-11-04: correção da associação de commit

| Campo | Registro |
|---|---|
| Ferramenta | Codex, assistente de programação. |
| Como foi usada | A pedido do grupo, o agente conferiu o histórico Git e registrou a associação omitida entre o estado de validação independente e seu commit. |
| Dados fornecidos | O arquivo `docs/labbook/2026-11-03-validacao-independente.md`, o protocolo do labbook e o histórico local do Git. |
| O que ajudou a produzir | Registro complementar `docs/labbook/2026-11-04-correcao-associacao-validacao.md` e link correspondente no índice do labbook. |
| Como a saída foi avaliada | A associação foi conferida com `git show --stat --oneline 7de2a3e`, que inclui o registro de 2026-11-03 no commit `test: fortalece validação independente do AG`. |
| Verificação automática | `git diff --check` e inspeção do commit `7de2a3e`. |
| Verificação humana | Pendente: o grupo deve confirmar que a correção documental descreve o commit pretendido. |

## Revisão humana do registro de 2026-11-04 — correção da associação

| Campo | Registro |
|---|---|
| Pessoas que revisaram | Pendente. |
| O que foi revisado | Associação entre a validação independente de 2026-11-03 e o commit `7de2a3e`. |
| Como foi conferido | Pendente. |
| Comandos e resultado | Pendente. |
| Decisão | Pendente. |
| Pendências ou limitações | Registrar a confirmação humana antes do próximo commit. |

## Registro do agente — 2026-11-04: DOE piloto

| Campo | Registro |
|---|---|
| Ferramenta | Codex, assistente de programação. |
| Como foi usada | O grupo solicitou a implementação do item 4 do roteiro. O agente leu a configuração e o plano, implementou o gerador determinístico e seus alvos de validação, materializou o CSV e executou verificações locais. |
| Dados fornecidos | `plano-implementacao-etapa-2.md`, `config/experiment.yaml`, README, Makefile, documentos de ambiente e a estrutura existente do repositório. |
| O que ajudou a produzir | `scripts/generate_design.py`, `config/design.csv`, a seção `design.initial_design` da configuração, alvos `make design` e `make check-design`, documentação estável no README e registro deste estado no labbook. |
| Como a saída foi avaliada | O grupo deve conferir que os níveis, réplicas, `B=1`, CPU alvo e a intenção de `perf` representam o piloto desejado. O CSV foi aceito pelo verificador determinístico somente quando coincidiu exatamente com os valores derivados da configuração. |
| Verificação automática | `make design`, `make check-design`, inspeção programática de contagens, tratamentos, sementes, ordens e identificadores, `make test` e `git diff --check`. |
| Verificação humana | Pendente: o grupo deve revisar o script, `config/design.csv`, os limites de `B` e `perf`, e registrar a decisão abaixo antes do commit. |

## Revisão humana do registro de 2026-11-04 — DOE piloto

| Campo | Registro |
|---|---|
| Pessoas que revisaram | Leonardo |
| O que foi revisado | Gerador de DOE, `config/design.csv`, metadados iniciais de desenho e documentação associada. |
| Como foi conferido | Ler config/experiment.yaml, scripts/generate_design.py, executar comandos, conferir config/design.csv |
| Comandos e resultado | `make check-design` — DOE válido: ... (320 execuções planejadas), `Todos os testes do AG passaram.` — Todos os testes do AG passaram., `git diff --check`, 'baseline': 160, 'phases': 80, 'perf': 80, Tratamentos: 16 |
| Decisão | aceito |
| Pendências ou limitações | `B=1` ainda, linhas `perf` não são contadores válidos enquanto houver multiplexação |

## Modelo para o próximo par de registros

Para cada novo uso, acrescente primeiro o registro do agente e, imediatamente abaixo, a revisão humana correspondente. Copie e preencha o bloco de revisão abaixo.

### AAAA-MM-DD — revisão humana do registro de AAAA-MM-DD

| Campo | Preencher |
|---|---|
| Pessoas que revisaram | [nome(s)] |
| O que foi revisado | [artefatos e escopo] |
| Como foi conferido | [leitura, execução ou outro método] |
| Comandos e resultado | [comandos e resultado observado] |
| Decisão | [aceito, rejeitado ou pendente] |
| Pendências ou limitações | [itens restantes] |

Uma revisão só deve ser marcada como aceita depois que as pessoas responsáveis entenderem o resultado e concordarem que ele está correto para o projeto.
