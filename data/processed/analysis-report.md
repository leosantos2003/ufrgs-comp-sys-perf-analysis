## Ambiente e desenho observados

| campanha | modo | captura | CPU | L1d | L2 | L3 | núcleo | energia |
|---|---|---|---|---|---|---|---|---|
| baseline-2026-11-07T17_08_32-03_00 | baseline | 2026-11-07T17:08:32-03:00 | 13th Gen Intel(R) Core(TM) i7-1355U | 352 KiB (10 instances) | 6.5 MiB (4 instances) | 12 MiB (1 instance) | 0 | AC type=Mains online=1 status=UNAVAILABLE BAT0 type=Battery online=UNAVAILABLE status=Not charging |
| phases-2026-11-08T00_39_18-03_00 | phases | 2026-11-08T00:39:18-03:00 | 13th Gen Intel(R) Core(TM) i7-1355U | 352 KiB (10 instances) | 6.5 MiB (4 instances) | 12 MiB (1 instance) | 0 | AC type=Mains online=1 status=UNAVAILABLE BAT0 type=Battery online=UNAVAILABLE status=Not charging |
| perf-2026-11-08T01_45_16-03_00 | perf | 2026-11-08T01:45:16-03:00 | 13th Gen Intel(R) Core(TM) i7-1355U | 352 KiB (10 instances) | 6.5 MiB (4 instances) | 12 MiB (1 instance) | 0 | AC type=Mains online=1 status=UNAVAILABLE BAT0 type=Battery online=UNAVAILABLE status=Not charging |

As capacidades de cache acima vieram do inventário capturado antes das campanhas. Elas são referências visuais do ambiente, não uma prova de que uma transição observada foi causada por cache.

| N | L | G | B | baseline | phases | IPC | cache |
|---|---|---|---|---|---|---|---|
| 128 | 64 | 100 | 92 | 10 | 5 | 5 | 5 |
| 128 | 256 | 100 | 25 | 10 | 5 | 5 | 5 |
| 128 | 1024 | 100 | 7 | 10 | 5 | 5 | 5 |
| 512 | 64 | 100 | 23 | 10 | 5 | 5 | 5 |
| 512 | 256 | 100 | 7 | 10 | 5 | 5 | 5 |
| 512 | 1024 | 100 | 2 | 10 | 5 | 5 | 5 |
| 2048 | 64 | 100 | 6 | 10 | 5 | 5 | 5 |
| 2048 | 256 | 100 | 2 | 10 | 5 | 5 | 5 |
| 2048 | 1024 | 100 | 1 | 10 | 5 | 5 | 5 |

As contagens totalizam 90 observações `baseline`, 45 `phases`, 45 de `ipc_user` e 45 de `cache_user`. IPC sempre combina `instructions/cycles` na mesma linha `ipc_user`; a taxa de cache sempre combina `cache_misses/cache_references` na mesma linha `cache_user`.

## Tempo e vazão: medida primária baseline

| N | L | n | mediana T_g (ns) | média T_g (ns) | DP T_g | CV T_g (%) | mediana Q (Mgenes/s) | CV Q (%) |
|---|---|---|---|---|---|---|---|---|
| 128 | 64 | 10 | 56 278.7 | 56 472.9 | 783.7 | 1.39 | 145.56 | 1.39 |
| 128 | 256 | 10 | 209 569.0 | 209 955.3 | 1 978.8 | 0.94 | 156.36 | 0.94 |
| 128 | 1024 | 10 | 825 266.0 | 823 922.0 | 23 921.0 | 2.90 | 158.82 | 2.83 |
| 512 | 64 | 10 | 228 837.3 | 229 064.1 | 2 113.9 | 0.92 | 143.19 | 0.91 |
| 512 | 256 | 10 | 845 295.4 | 842 187.4 | 14 369.6 | 1.71 | 155.06 | 1.73 |
| 512 | 1024 | 10 | 3 306 489.8 | 3 317 761.6 | 58 894.4 | 1.78 | 158.56 | 1.73 |
| 2048 | 64 | 10 | 912 139.4 | 908 665.0 | 9 311.8 | 1.02 | 143.70 | 1.04 |
| 2048 | 256 | 10 | 3 387 563.3 | 3 378 798.6 | 28 152.5 | 0.83 | 154.77 | 0.84 |
| 2048 | 1024 | 10 | 13 187 296.3 | 13 192 815.9 | 132 204.4 | 1.00 | 159.03 | 1.00 |

![Medianas de T_g por N e L: o tempo sobe de 56 microssegundos a 13,2 milissegundos](../figures/tempo-geracao-heatmap.svg)

![Vazão baseline em painéis por L, com ponto mediano e intervalo bootstrap](../figures/vazao-workset.svg)

A maior mediana de vazão foi 159.03 Mgenes/s em `N=2048`, `L=1024`; a menor foi 143.19 Mgenes/s em `N=512`, `L=64`. Esses são fatos descritivos das réplicas `baseline`, não uma inferência causal sobre a microarquitetura.

## Contadores de hardware

| N | L | métrica | n | mediana | IC bootstrap 95% |
|---|---|---|---|---|---|
| 128 | 64 | IPC | 5 | 1.887 | [1.874, 1.898] |
| 128 | 64 | cache misses (%) | 5 | 67.165 | [59.924, 75.917] |
| 128 | 256 | IPC | 5 | 1.891 | [1.823, 1.893] |
| 128 | 256 | cache misses (%) | 5 | 57.848 | [40.990, 74.916] |
| 128 | 1024 | IPC | 5 | 1.895 | [1.891, 1.899] |
| 128 | 1024 | cache misses (%) | 5 | 75.123 | [30.680, 77.382] |
| 512 | 64 | IPC | 5 | 1.892 | [1.877, 1.894] |
| 512 | 64 | cache misses (%) | 5 | 70.899 | [44.725, 79.365] |
| 512 | 256 | IPC | 5 | 1.839 | [1.792, 1.888] |
| 512 | 256 | cache misses (%) | 5 | 64.173 | [12.544, 74.784] |
| 512 | 1024 | IPC | 5 | 1.896 | [1.873, 1.898] |
| 512 | 1024 | cache misses (%) | 5 | 20.781 | [17.128, 27.470] |
| 2048 | 64 | IPC | 5 | 1.883 | [1.821, 1.893] |
| 2048 | 64 | cache misses (%) | 5 | 46.609 | [15.145, 49.475] |
| 2048 | 256 | IPC | 5 | 1.872 | [1.815, 1.894] |
| 2048 | 256 | cache misses (%) | 5 | 13.399 | [12.605, 24.803] |
| 2048 | 1024 | IPC | 5 | 1.888 | [1.887, 1.890] |
| 2048 | 1024 | cache misses (%) | 5 | 22.658 | [21.857, 35.215] |

Os três gráficos de resposta usam painéis por `L`, com escala vertical comum e
somente os níveis de `N` efetivamente medidos. Assim, os pontos não insinuam
uma interpolação entre os níveis experimentais, e cada painel dispensa uma
legenda de cores.

![IPC em painéis por L, com ponto mediano e intervalo bootstrap](../figures/ipc-workset.svg)

![Taxa de cache miss em painéis por L, com ponto mediano e intervalo bootstrap](../figures/cache-miss-workset.svg)

A maior mediana de taxa de cache miss foi 75.123% em `N=128`, `L=1024`. Uma queda de vazão que coincida com essa taxa é evidência **compatível** com pressão de memória, mas os contadores e o tempo foram coletados em campanhas distintas e não demonstram causalidade isoladamente.

## Fases e custo da instrumentação

| N | L | pares | overhead mediano (%) | cobertura mediana das fases (%) |
|---|---|---|---|---|
| 128 | 64 | 5 | 1.13 | 99.90 |
| 128 | 256 | 5 | -0.01 | 99.96 |
| 128 | 1024 | 5 | -1.68 | 99.99 |
| 512 | 64 | 5 | -1.41 | 99.96 |
| 512 | 256 | 5 | 0.54 | 99.96 |
| 512 | 1024 | 5 | -0.07 | 99.98 |
| 2048 | 64 | 5 | 2.51 | 100.00 |
| 2048 | 256 | 5 | 0.04 | 100.00 |
| 2048 | 1024 | 5 | 1.69 | 100.00 |

A tabela conserva medianas por tratamento. No gráfico empilhado, entretanto,
cada parcela é a **média** das cinco réplicas: essa escolha faz as seis
parcelas somarem exatamente 100% e evita apresentar uma pequena diferença
entre soma de medianas e o total como se fosse tempo não explicado.

![Composição média do tempo por fase: mutação domina em todos os tratamentos](../figures/composicao-fases.svg)

![Overhead do modo phases em pares baseline, com mediana e intervalo bootstrap](../figures/overhead-fases.svg)

O maior valor absoluto de overhead mediano foi 2.51% em `N=2048`, `L=64`. A decomposição continua diagnóstica: os pares usam a mesma configuração e semente, mas as campanhas foram feitas em instantes diferentes.

## Variabilidade, anomalias e limites

![Coeficiente de variação de T_g entre 10 réplicas baseline por tratamento](../figures/variabilidade-baseline.svg)

Nenhuma réplica baseline ultrapassou o limiar descritivo de 10% da mediana de `T_g`. O limiar apenas sinaliza investigação; não é uma regra de exclusão.

Os intervalos nos gráficos de vazão, IPC e cache são ICs bootstrap de 95% para a mediana, gerados com 5.000 reamostragens determinísticas por tratamento. Eles descrevem a incerteza sob as réplicas observadas; não compensam variação ambiental não medida e não devem ser lidos como generalização para outras máquinas.
