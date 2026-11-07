# Estado do projeto — piloto de três pontos e calibração de lote

**Data:** 2026-11-05  
**Estado associado:** implementação e execução do item 5 do roteiro: piloto pequeno, médio e grande para manter `G`, definir a grade final e calibrar o lote de medição `B` por configuração. Commit: `feat(experimento): adiciona piloto de três pontos e calibração de lote`

## Contexto do projeto neste estado

O projeto investiga como `N`, o tamanho da população, e `L`, o comprimento do cromossomo, afetam o custo computacional de um algoritmo genético (AG) sequencial para OneMax. O escopo continua sendo desempenho computacional: cada AG executa exatamente `G` gerações, sem término antecipado.

Antes deste estado, o repositório já tinha o AG C++ determinístico, testes, build reprodutível, inventário de ambiente, controles em `config/experiment.yaml` e o DOE inicial `4 × 4` de 320 linhas com `B=1`. Não havia ainda ferramenta para executar o piloto, agregar execuções completas quando a duração fosse curta ou decidir `B` sem modificar `G` seletivamente. Também não havia observações de desempenho em `data/raw/`.

## Significados

- **Piloto de três pontos:** execução `baseline` em cargas `small`, `medium` e `large`, declaradas na configuração e pertencentes à grade candidata. Na grade final, os pontos são `128 × 64`, `512 × 1024` e `2048 × 1024`; seus produtos `N × L` são estritamente crescentes. O extremo inicial `8192 × 4096` é evidência preservada para a exclusão da grade anterior.
- **`G`:** número fixo de gerações de cada execução completa do AG; neste estado permanece `100` em todos os pontos e em todas as repetições de um lote.
- **`batch` (`B`):** número de execuções completas e idênticas agregadas em uma única observação. A inicialização e o checksum de cada AG ficam fora de sua região cronometrada; `elapsed_ns` é a soma dos laços de gerações medidos. Portanto, o trabalho normalizado futuro é `B × N × L × G`.
- **Calibração por configuração:** para cada ponto, a ferramenta mede três réplicas com `B=1`, calcula `ceil(0,5 s / mediana)` e faz uma execução de verificação com o `B` recomendado. `B` é detalhe de medição, não fator primário nem fonte nova de aleatoriedade: cada execução do lote conserva a mesma semente do registro.
- **Saída bruta:** cada chamada ao binário tem arquivos de comando, status, `stdout` CSV e `stderr`, além de `observations.csv`, `summary.csv` e `recommendation.md` no diretório `data/raw/pilot-<timestamp>/`.

## Como interpretar o lote e os tempos

`B` não muda o problema que o AG resolve, nem diminui o número de gerações para tornar uma configuração mais rápida. Ele apenas junta várias execuções completas na mesma chamada cronometrada quando uma execução isolada é curta demais para medir com estabilidade. Por exemplo, no ponto pequeno uma execução com `B=1` durou cerca de 5,44 ms. A verificação com `B=92` executou 92 AGs completos, com os mesmos valores de `N`, `L`, `G=100` e semente, e por isso acumulou cerca de meio segundo de trabalho.

Há dois tempos que devem aparecer juntos na interpretação:

- **Tempo bruto do lote (`T`):** o valor `elapsed_ns` registrado literalmente pelo programa para aquela chamada. Ele responde: “quanto tempo levou esta chamada inteira?”.
- **Tempo equivalente de um AG:** `T / B`. Ele responde: “quanto teria levado, em média, uma das execuções completas que compõem esta chamada?”. Sem essa divisão, seria incorreto comparar diretamente o tempo de uma chamada com 92 AGs ao de uma chamada com 1 AG.

Quando for necessário comparar o custo de uma geração, a conversão é `T / (B × G)`. Essas divisões não são uma normalização estatística que altera ou descarta os dados: são apenas conversões explícitas de unidade, como transformar metros em centímetros. O CSV bruto continua guardando `T` e `B`, para que qualquer pessoa possa refazer as contas. Para evitar incômodo com uma apresentação excessivamente “normalizada”, a tabela de resultados deve mostrar primeiro `T` e `B`, depois `T / B` com a fórmula declarada; vazão, como `(B × N × L × G) / T`, é métrica secundária, não substituta do tempo bruto.

As `B` execuções internas também não contam como `B` réplicas estatísticas da campanha. Elas são repetições deliberadamente iguais do trabalho de uma única linha do DOE: usam a mesma semente e os mesmos controles, e servem somente para ampliar a duração observada. A réplica experimental continua sendo a linha externa do DOE, que recebe sua própria semente e posição na ordem aleatorizada.

As três medições iniciais de cada ponto e a conta aplicada foram:

| Ponto (`N × L`) | Tempos com `B=1` (ns) | Mediana (ns) | Cálculo de `B` | `B` escolhido |
|---|---|---:|---|---:|
| `128 × 64` | 5.479.856; 5.441.504; 5.443.880 | 5.443.880 | `ceil(500.000.000 / 5.443.880)` | 92 |
| `512 × 1024` | 318.658.168; 322.129.101; 321.762.067 | 321.762.067 | `ceil(500.000.000 / 321.762.067)` | 2 |
| `2048 × 1024` | 1.306.748.753; 1.305.748.709; 1.307.830.420 | 1.306.748.753 | `max(1, ceil(500.000.000 / 1.306.748.753))` | 1 |

Na verificação do piloto revisado, os três casos foram estes:

| Ponto (`N × L`) | `B` | Tempo bruto do lote `T` | Tempo equivalente por AG `T / B` |
|---|---:|---:|---:|
| `128 × 64` | 92 | 517.369.329 ns (517,369 ms) | 5,624 ms |
| `512 × 1024` | 2 | 656.353.588 ns (656,354 ms) | 328,177 ms |
| `2048 × 1024` | 1 | 1.336.551.575 ns (1,337 s) | 1.336,552 ms |

Uma rodada completa **do piloto** teve 13 chamadas `baseline`, todas com afinidade no núcleo 0 e após confirmação de energia AC: um aquecimento no ponto pequeno com `B=1`, três réplicas medidas com `B=1` em cada um dos três pontos (nove chamadas), e uma verificação com o `B` calculado em cada ponto (três chamadas). A semente do piloto foi `20261105`. Para cada conjunto de três réplicas, foi usada a mediana; em seguida, aplicou-se `B = ceil(0,5 s / mediana)`, com mínimo de 1. O aquecimento não entra no cálculo. A única função dessas verificações é confirmar que o lote escolhido deixa a chamada entre 0,5 e 2 s; elas não são a campanha final nem estimam sozinhas um resultado de desempenho.

A campanha principal ainda não foi iniciada. A grade é o fatorial completo de `N={128, 512, 2048}` e `L={64, 256, 1024}`: nove combinações. Para cada combinação, o DOE atual prevê dez réplicas `baseline`, cinco `phases` e cinco `perf` (180 linhas no total); cada uma dessas linhas tem uma semente externa e uma posição na ordem aleatorizada. O `B=1` presente hoje em `config/design.csv` é provisório: antes da campanha, as seis combinações que não são âncoras do piloto precisam receber a mesma calibração. Qualquer decisão de abandonar o lote ou de usar outro critério exigirá alterar a configuração e criar uma nova evidência de medição, em vez de reinterpretar silenciosamente os dados já coletados.

## Como testar ou reproduzir este estado

Na raiz do repositório, execute:

```bash
make test
make run
./build/ag_bench --header --population 16 --length 16 --generations 5 \
  --batch 3 --seed 20261105 --crossover 0.90 --mutation 0.01 --mode baseline
make check-design
make check-pilot
git diff --check
```

Os testes devem terminar com `Todos os testes do AG passaram.`. O comando direto deve emitir uma linha CSV com `batch=3`; é somente um smoke test da interface, sem afinidade de campanha, aquecimento ou valor de desempenho interpretável. `make design` e `make check-design` devem produzir e validar 180 linhas do DOE `3 × 3`; `make check-pilot` valida a configuração, mostra os três comandos `taskset` e não escreve em `data/raw/`.

Após uma nova captura de ambiente que confirme energia AC, o piloto real é reproduzido com:

```bash
make environment
make pilot
```

O segundo comando exige AC confirmada, valida o `core_id` emitido pelo binário contra `environment_controls.target_core` e preserva a saída literal de cada invocação. Ele deliberadamente não regrava configuração nem DOE. Uma saída fora de 0,5--2 s faz `make pilot` falhar para bloquear o avanço, mas conserva o diretório bruto para decisão documentada.

## Mudanças e decisões

- Acrescentada a seção `design.measurement_batch.pilot` à fonte de verdade, com três pontos, três réplicas, sementes determinísticas e limite explícito de `B=1.000.000`. Os três níveis pertencem aos níveis candidatos de `N` e `L`; a ordem do produto `N × L` é validada pelo script.
- Implementado `scripts/calibrate_batch.py`, usando apenas a biblioteca padrão e o leitor de configuração já usado pelo gerador do DOE. Ele requer energia AC, executa o binário via `taskset`, valida cabeçalho, parâmetros e `core_id`, preserva saídas e produz uma recomendação que exige revisão humana.
- Adicionado `--batch B` a `ag_bench`. Para `B>1`, o programa repete AGs completos com os mesmos controles, `G` e semente, soma os tempos e fases e combina os checksums. Para `B=1`, o caminho e o checksum anteriores são preservados.
- Documentada uma leitura acessível de `B`: tempo bruto do lote, tempo equivalente por AG e, se necessário, por geração são apresentados como unidades diferentes do mesmo registro. A documentação agora explicita os três valores verificados, as 13 chamadas do piloto e por que os valores brutos permanecem visíveis.
- Criados os alvos `make pilot` e `make check-pilot`; o segundo usa `--dry-run`, sem executar o AG ou gravar dados. O README documenta a semântica de `B`, o bloqueio por AC e o fluxo de decisão.
- A tentativa inicial em `data/raw/pilot-2026-11-05T11_41_49-03_00/` foi interrompida externamente no ponto grande e foi preservada como incompleta. O script passou a atualizar `observations.csv` depois de cada execução e a registrar o término no manifesto.
- O primeiro piloto completo (`data/raw/pilot-2026-11-05T11_44_03-03_00/`) manteve `G=100`, mas o extremo `8192 × 4096` excedeu 2 s já com `B=1`. Antes da campanha, a grade foi reduzida para `N={128,512,2048}` e `L={64,256,1024}`; `design.combinations` passou a 9 e `make design` regenerou `config/design.csv` com 180 linhas. As medições da grade anterior não foram incorporadas à grade revisada.
- O inventário atualizado com AC foi preservado em `data/metadata/environment-2026-11-05T11_48_04-03_00/`. O piloto completo da grade revisada está em `data/raw/pilot-2026-11-05T11_48_11-03_00/`; ele não alterou `data/processed/`, `figures/` ou `results/`.

## Evidência e impacto

- `make test` passou, incluindo a validação de `batch=0`, determinismo de lote e equivalência de resultado entre `baseline` e `phases` no lote.
- `make run` passou e o smoke test explícito com `--batch 3` emitiu o campo `batch=3`. Seus tempos não são resultado de desempenho: foi executado sem afinidade de campanha e não foi persistido como dado bruto.
- O inventário de 11:48 confirmou `taskset=passed`, `core_id=0` e AC `online=1`. `perf` continua `passed_with_multiplexing` e não foi usado no piloto `baseline`.
- No piloto inicial completo, as medianas com `B=1` foram 5.499.001 ns (`small`), 324.834.702 ns (`medium`) e 21.996.341.085 ns (`large=8192 × 4096`); a verificação do extremo foi 23.285.324.319 ns. A grade `4 × 4` foi rejeitada antes da campanha.
- No piloto revisado, as verificações foram 517.369.329 ns para `128 × 64` com `B=92`, 656.353.588 ns para `512 × 1024` com `B=2` e 1.336.551.575 ns para `2048 × 1024` com `B=1`. As 13 chamadas registraram `core_id=0` e `exit_status=0`; a grade `3 × 3` e `G=100` atendem ao protocolo nos pontos testados.
- `make design`, `make check-design` e `make check-pilot` validaram o DOE revisado; `git diff --check` não reportou erros de espaço nas verificações deste estado.

## Limitações e próximo passo

- A grade final é `3 × 3` e `G=100`, mas os valores `B=92`, `B=2` e `B=1` foram observados apenas nos três pontos. A calibração definitiva precisa abranger cada configuração curta da grade escolhida antes de substituir o `B=1` provisório de `config/design.csv`.
- O script exige confirmação de AC. Antes de executá-lo, repetir `make environment`; manter registradas as limitações de governor, Turbo e dos contadores `perf` já identificadas. O piloto mede apenas `baseline` e não torna os contadores multiplexados válidos.
- Os diretórios brutos da tentativa interrompida e da grade `4 × 4` rejeitada permanecem no repositório com sua condição explícita. Não usar seus tempos para comparar a grade final; eles evidenciam somente a decisão de exclusão e a evolução do protocolo.
