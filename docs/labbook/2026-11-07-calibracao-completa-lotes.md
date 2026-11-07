# Estado do projeto — calibração completa de lotes e DOE definitivo

**Data:** 2026-11-07  
**Estado associado:** fechamento do item 5 do roteiro: confirmação do piloto, calibração das seis combinações restantes, congelamento de `B` por tratamento e regeneração do DOE. Commit: `feat(experimento): adiciona piloto de três pontos e calibração de lote`

## Contexto do projeto neste estado

O projeto mede como a população `N` e o comprimento do cromossomo `L` afetam o custo computacional de um algoritmo genético (AG) sequencial para OneMax. Cada AG continua executando exatamente `G=100` gerações; não há término antecipado, mudança seletiva de `G` ou paralelismo.

O estado de 2026-11-05 implementou o lote de medição, reduziu a grade para o fatorial `3 × 3` e validou os pontos âncora `128 × 64`, `512 × 1024` e `2048 × 1024`. Contudo, o DOE ainda tinha `B=1` provisório e faltava calibrar as outras seis combinações. Antes deste estado, uma repetição do piloto em 2026-11-07 já havia sido preservada em `data/raw/pilot-2026-11-07T15_00_26-03_00/`.

## Significados

- **`N` e `L`:** fatores primários; a grade é `N={128,512,2048}` por `L={64,256,1024}`, totalizando nove tratamentos.
- **`G=100`:** gerações de cada AG completo. Ele permanece igual em todos os tratamentos e nas repetições internas de um lote.
- **Lote (`B`):** número de AGs completos, com a mesma configuração e semente, agregados em uma chamada. O tempo bruto registrado é `T`; a conversão transparente para uma execução é `T / B` e, para uma geração, `T / (B × G)`. As `B` execuções internas não são réplicas estatísticas.
- **Réplica externa:** linha do DOE com semente e posição aleatorizada próprias. Cada tratamento terá dez réplicas `baseline`, cinco `phases` e cinco `perf`.
- **Calibração complementar:** aplicação do mesmo protocolo do piloto às seis combinações que não são âncoras: um aquecimento, três medições com `B=1` por tratamento, mediana, `B=ceil(0,5 s / mediana)` e uma verificação com o `B` calculado.
- **DOE definitivo:** `config/design.csv` gerado por código a partir de `config/experiment.yaml`. O mapa `design.measurement_batch.frozen_batches` é a fonte de verdade de `B` por tratamento; o `batch: 1` legado só seria usado se esse mapa não existisse.

## Como testar ou reproduzir este estado

Na raiz do repositório, execute:

```bash
make test
make run
./build/ag_bench --header --population 16 --length 16 --generations 5 \
  --batch 3 --seed 20261105 --crossover 0.90 --mutation 0.01 --mode baseline
make check-pilot
make check-calibrate-remaining
make check-design
git diff --check
```

Os testes devem terminar com `Todos os testes do AG passaram.`. Os dois comandos de validação de calibração apenas mostram as chamadas `taskset` e não escrevem em `data/raw/`; o primeiro cobre os três pontos âncora e o segundo as seis combinações restantes. `make check-design` deve informar 180 execuções planejadas. Os comandos `make run` e a chamada direta são smoke tests sem afinidade de campanha e não são dados de desempenho.

Para reproduzir uma nova calibração complementar — somente se uma nova coleta for desejada — primeiro capture um novo ambiente com AC e então execute:

```bash
make environment
make calibrate-remaining
```

Isso cria outro diretório bruto; não substitui os diretórios deste estado. Uma campanha principal deve ler o DOE já congelado e manter a ordem aleatorizada, não repetir esta calibração como se fosse réplica de desempenho.

## Mudanças e decisões

- Adicionado `--remaining-grid` a `scripts/calibrate_batch.py` e os alvos `make calibrate-remaining` e `make check-calibrate-remaining`. O modo deriva, por código, as seis combinações do fatorial que não são os três pontos âncora e mantém o mesmo protocolo de AC, afinidade, aquecimento, três réplicas e verificação.
- O gerador passou a aceitar `design.measurement_batch.frozen_batches`. Quando o mapa existe, ele exige exatamente os nove tratamentos e grava o `B` correspondente em cada linha do DOE; assim não há edição manual de `config/design.csv`.
- A coleta adicional de 15:00 em `data/raw/pilot-2026-11-07T15_00_26-03_00/` repetiu o piloto de três pontos. Ela recomendou `B=91`, `2` e `1`, respectivamente, e todas as verificações ficaram na faixa. Para `128 × 64`, o grupo decidiu congelar **`B=92`**, valor verificado em 2026-11-05, em vez de substituir a decisão pela recomendação pontual de 91.
- A coleta complementar em `data/raw/batch-calibration-remaining-2026-11-07T16_46_10-03_00/` forneceu os seis valores ainda ausentes. O inventário imediatamente anterior está em `data/metadata/environment-2026-11-07T16_46_06-03_00/`.
- `config/experiment.yaml` passou a conter o mapa completo de lotes congelados e o bloco do DOE passou de `pilot` para `main`. `make design` regenerou o CSV determinístico de 180 linhas. Nenhum dado bruto, inclusive o piloto de 2026-11-05 que recomendou 92, foi alterado ou removido.

## Evidência e impacto

O inventário de 16:46 confirmou energia AC, afinidade válida no CPU lógico 0 e `perf=passed_with_multiplexing`; os contadores de hardware continuam fora da análise. A calibração complementar terminou com `status=completed`, 25 observações e `observed_core=0` em todas: um aquecimento, 18 medições com `B=1` e seis verificações.

| Tratamento (`N × L`) | Mediana com `B=1` (ns) | `B` calculado/decidido | Verificação do lote (ns) | Situação |
|---|---:|---:|---:|---|
| `128 × 64` | 5.443.880 (piloto de 05/11) | 92 (decisão humana) | 517.369.329 | dentro da faixa |
| `128 × 256` | 20.138.424 | 25 | 535.373.525 | dentro da faixa |
| `128 × 1024` | 78.315.481 | 7 | 579.912.211 | dentro da faixa |
| `512 × 64` | 21.873.371 | 23 | 532.054.252 | dentro da faixa |
| `512 × 256` | 81.934.018 | 7 | 595.555.551 | dentro da faixa |
| `512 × 1024` | 321.762.067 (piloto de 05/11) | 2 | 656.353.588 | dentro da faixa |
| `2048 × 64` | 87.529.930 | 6 | 560.261.767 | dentro da faixa |
| `2048 × 256` | 350.875.124 | 2 | 697.584.822 | dentro da faixa |
| `2048 × 1024` | 1.306.748.753 (piloto de 05/11) | 1 | 1.336.551.575 | dentro da faixa |

O DOE definitivo contém 20 linhas por tratamento, portanto 90 linhas `baseline`, 45 `phases` e 45 `perf`, totalizando 180. Os lotes presentes nessas linhas são `92`, `25`, `7`, `23`, `7`, `2`, `6`, `2` e `1`, na ordem da tabela. `make test`, `make design`, `make check-design`, `make check-pilot`, `make check-calibrate-remaining` e a compilação sintática dos dois scripts Python passaram neste estado.

## Limitações e próximo passo

- A decisão de `B=92` para `128 × 64` é explícita e reproduzível pela evidência de 05/11; a repetição de 07/11, que sugeriu 91, evidencia variação normal de tempo e não deve ser apresentada como contradição ou apagada.
- A calibração define a duração dos lotes, mas não é a campanha de desempenho. Ainda falta executar as 90 réplicas `baseline` do DOE definitivo e, depois, as campanhas `phases` e `perf` conforme a viabilidade dos contadores.
- A cadeia atual de `perf` voltou a apresentar multiplexação no inventário de 16:46. Não usar ciclos, instruções ou métricas de cache dessa cadeia até reduzir/agrupar os eventos e obter uma nova validação sem multiplexação.
- A campanha deve começar somente com novo inventário que confirme as condições de ambiente e deve preservar qualquer falha ou medição inválida. A revisão humana deste novo estado de calibração ainda precisa ser registrada antes de um commit que o inclua.
