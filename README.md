# Etapa 2 — avaliação de desempenho de um algoritmo genético

Este repositório contém os artefatos executáveis, dados e documentação da Etapa 2 de INF01146 — Avaliação de Desempenho. Este README descreve o projeto de forma estável; o estado de cada mudança, decisão e validação pertence ao [caderno de laboratório](docs/labbook.md).

## Pergunta e escopo

> Como o tamanho da população (`N`) e o comprimento do cromossomo (`L`) afetam o desempenho computacional de um algoritmo genético sequencial?

O objeto de estudo é um algoritmo genético geracional, sequencial, para OneMax, com genes `std::uint8_t`, seleção por torneio de tamanho 2, crossover de um ponto e mutação bit-flip. O estudo mede custo computacional — não qualidade de otimização — e toda execução completa exatamente `G` gerações, sem término antecipado.

`N` e `L` são os únicos fatores primários. As demais decisões do algoritmo são controles documentados em [config/experiment.yaml](config/experiment.yaml); uma alteração exige registro no caderno, nova validação e início de um novo bloco de medições.

## Organização e cadeia reprodutível

```text
src/             implementação do AG, executável e testes
scripts/         build e automação da campanha
config/          controles do AG e desenho experimental congelado
data/raw/         saídas originais, uma observação por execução
data/metadata/    inventário de hardware, software e controles
data/processed/   dados derivados, sempre reconstruíveis
analysis/         caderno executável que gera tabelas e figuras
figures/          figuras geradas pelo caderno
results/          relatórios renderizados
docs/             ambiente, labbook, dificuldades e uso de IA
```

A cadeia obrigatória é: código e configuração → desenho experimental → dados brutos e metadados → dados tratados → análise e figuras. Nenhuma etapa deve depender de edição manual de CSV, planilha ou interface não documentada.

## Uso local

Pré-requisitos: GNU Make e compilador compatível com C++20.

```bash
make build      # gera build/ag_bench e build/ag_tests
make test       # compila e executa a suíte determinística
make run        # executa uma configuração demonstrativa
make design     # gera e valida o DOE piloto em config/design.csv
make check-design # valida o DOE existente sem regravá-lo
make check-pilot # valida o piloto pequeno/médio/grande sem medir
make pilot       # executa o piloto e grava as evidências em data/raw/
make check-calibrate-remaining # valida a calibração das combinações restantes, sem medir
make calibrate-remaining # calibra B nas combinações restantes e grava as evidências
./build/ag_bench --help
```

`make design` materializa o fatorial completo definido em
`config/experiment.yaml`. O CSV contém somente execuções planejadas: uma
linha por execução, identificadores, modo de medição, tratamento `N × L`,
réplica, semente, lote, CPU alvo e uma ordem global aleatorizada. A
aleatorização e as sementes são determinísticas a partir de
`design.design_random_seed`. Antes de todos os lotes serem congelados, o
lote inicial `B=1` é provisório; depois disso, o gerador usa o mapa
`design.measurement_batch.frozen_batches`, com um valor por tratamento
`N × L`. O comando não mede o AG nem escreve em `data/raw/`.

`ag_bench` emite uma linha CSV por execução. A região cronometrada contém somente o laço de `G` gerações; inicialização, checksum e escrita da saída ficam fora dela. Os argumentos usados numa campanha devem reproduzir os controles congelados em `config/experiment.yaml`.

Antes da campanha, `make pilot` executa uma execução de aquecimento e três réplicas `baseline` nos três pontos configurados (`small`, `medium`, `large`), sempre sob `taskset` no CPU configurado e somente com energia AC confirmada. Para cada ponto, ele mede primeiro com `B=1`, recomenda `B = ceil(0,5 s / mediana)` e verifica o lote recomendado. As saídas literais de cada chamada, uma tabela de observações e uma recomendação ficam em um novo diretório `data/raw/pilot-<timestamp>/`. O comando não muda `G`, os níveis de `N`/`L`, `experiment.yaml` ou `design.csv`: a decisão de aceitar a grade e congelar `B` por configuração exige revisão humana e novo DOE. `make check-pilot` somente valida a configuração e mostra os comandos planejados.

O argumento `--batch B` do executável agrega `B` execuções completas idênticas do AG; cada uma mantém os mesmos `G` gerações e a mesma semente. O `elapsed_ns` publicado é a soma dos trechos medidos dessas execuções, e as métricas normalizadas futuras devem usar `B × N × L × G` como trabalho total.

Depois do piloto de três pontos, `make calibrate-remaining` aplica o mesmo
protocolo às combinações da grade que ainda não foram calibradas: um
aquecimento, três réplicas com `B=1` por combinação e uma verificação com o
lote calculado. Ele também exige AC, afinidade com o CPU configurado e
preserva cada comando e saída em um novo diretório de `data/raw/`. Após a
revisão humana, o grupo transfere os lotes escolhidos para `frozen_batches` e
executa `make design` para congelar o DOE.

Antes de uma campanha, capture o ambiente e verifique a afinidade configurada:

```bash
make environment
```

O alvo lê o CPU lógico `target_core` de `config/experiment.yaml`, executa um teste curto sob `taskset`, registra o `core_id` efetivo informado pelo binário e grava um instantâneo em `data/metadata/environment-<timestamp>/`. Ele também testa os eventos solicitados com `perf stat`, sem mudar privilégios ou controles do sistema; indisponibilidade de `perf` fica registrada no instantâneo e em `docs/environment.md`, mas não transforma esse teste curto em dado de desempenho.

## Garantias de validação

O alvo `make test` verifica as primitivas OneMax, torneio, crossover e mutação; parâmetros inválidos; mutação com sequência pseudoaleatória controlada; determinismo por semente; população e limites de fitness após cada geração; equivalência com uma referência simples em instâncias pequenas; e preservação do resultado entre os modos `baseline` e `phases`.

Os testes comprovam correção funcional nas instâncias cobertas; não constituem uma medição de desempenho. Medições só são válidas quando acompanhadas da afinidade de CPU, inventário de ambiente e metadados definidos no plano experimental.

## Protocolo de documentação

- [docs/labbook.md](docs/labbook.md) é o índice e protocolo do diário. A partir de sua adoção, cada commit que altera o estado do projeto inclui um novo arquivo imutável em `docs/labbook/`.
- [docs/difficulties.md](docs/difficulties.md) preserva problemas, evidências, tentativas e limitações, inclusive os resolvidos.
- [docs/environment.md](docs/environment.md) resume o ambiente efetivamente medido e aponta para os inventários brutos.
- [docs/uso-ia.md](docs/uso-ia.md) registra uso de IA de forma factual e a validação humana necessária.

O plano de implementação em [plano-implementacao-etapa-2.md](plano-implementacao-etapa-2.md) define entregas, critérios e protocolo experimental completos.
