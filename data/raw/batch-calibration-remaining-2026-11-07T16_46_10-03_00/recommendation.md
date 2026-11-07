# Recomendação gerada pelo piloto de lote

Este arquivo é derivado automaticamente das saídas brutas do diretório atual. Ele não altera `config/experiment.yaml` nem `config/design.csv`.

- `G` confirmado durante o piloto: `100` gerações por execução completa.
- Faixa-alvo agregada: `0.5` a `2` s.
- Cada B recomendado repete a mesma configuração e semente; B não muda N, L, G, taxas do AG ou o número de threads.

| ponto | N | L | mediana com B=1 (ns) | B recomendado | verificação (ns) | situação |
|---|---:|---:|---:|---:|---:|---|
| n128_l256 | 128 | 256 | 20138424 | 25 | 535373525 | within_target |
| n128_l1024 | 128 | 1024 | 78315481 | 7 | 579912211 | within_target |
| n512_l64 | 512 | 64 | 21873371 | 23 | 532054252 | within_target |
| n512_l256 | 512 | 256 | 81934018 | 7 | 595555551 | within_target |
| n2048_l64 | 2048 | 64 | 87529930 | 6 | 560261767 | within_target |
| n2048_l256 | 2048 | 256 | 350875124 | 2 | 697584822 | within_target |

## Decisão ainda necessária

Revisar `summary.csv`, `observations.csv` e cada par `*.command`/`*.stdout.csv` antes de congelar a grade final e os valores de B por configuração. Se algum ponto grande exceder a faixa já com B=1, não reduza G apenas naquele tratamento: revise a grade antes da campanha. Depois da decisão, atualize os controles por código, gere um novo DOE e inicie um novo bloco de medições.
