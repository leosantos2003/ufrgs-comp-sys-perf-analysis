# Recomendação gerada pelo piloto de lote

Este arquivo é derivado automaticamente das saídas brutas do diretório atual. Ele não altera `config/experiment.yaml` nem `config/design.csv`.

- `G` confirmado durante o piloto: `100` gerações por execução completa.
- Faixa-alvo agregada: `0.5` a `2` s.
- Cada B recomendado repete a mesma configuração e semente; B não muda N, L, G, taxas do AG ou o número de threads.

| ponto | N | L | mediana com B=1 (ns) | B recomendado | verificação (ns) | situação |
|---|---:|---:|---:|---:|---:|---|
| small | 128 | 64 | 5507824 | 91 | 561665853 | within_target |
| medium | 512 | 1024 | 326257623 | 2 | 706201249 | within_target |
| large | 8192 | 4096 | 21708705476 | 1 | 22966647640 | above_target |

## Decisão ainda necessária

Revisar `summary.csv`, `observations.csv` e cada par `*.command`/`*.stdout.csv` antes de congelar a grade final e os valores de B por configuração. Se algum ponto grande exceder a faixa já com B=1, não reduza G apenas naquele tratamento: revise a grade antes da campanha. Depois da decisão, atualize os controles por código, gere um novo DOE e inicie um novo bloco de medições.

**Atenção:** ao menos uma verificação ficou fora da faixa. A campanha não deve ser iniciada sem decisão documentada sobre a grade ou a calibração.
