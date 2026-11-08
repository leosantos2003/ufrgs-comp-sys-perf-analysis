# Estado do projeto — campanha baseline completa

**Data:** 2026-11-07  
**Estado associado:** implementação e execução do item 6 do roteiro: campanha `baseline` completa no DOE definitivo de nove tratamentos. Commit: `feat(experimento): executa campanha baseline completa`

## Resumo em linguagem simples

Este registro conta a primeira coleta principal de tempos do projeto. Nós
queremos descobrir como duas escolhas afetam o custo de processamento do
algoritmo:

- `N`: quantidade de indivíduos da população;
- `L`: quantidade de genes de cada cromossomo.

Testamos as nove combinações possíveis entre `N={128,512,2048}` e
`L={64,256,1024}`. Cada combinação foi repetida dez vezes, portanto foram
planejadas e concluídas **90 medições**. Houve ainda uma execução de
aquecimento: ela prepara o programa e o computador, mas não conta como
resultado.

As 90 medições terminaram com sucesso, sempre no mesmo núcleo lógico da CPU
(núcleo 0), com energia AC confirmada. Para cada uma, foram guardados o comando
usado, a resposta original do programa e seu status. Isto prova que a coleta
foi feita como planejado; **não prova ainda** qual caso é mais rápido ou a
causa de uma eventual diferença. Essa interpretação ficará para o caderno de
análise.

## Contexto do projeto neste estado

O projeto investiga como o tamanho da população (`N`) e o comprimento do cromossomo (`L`) afetam o custo computacional de um algoritmo genético (AG) sequencial para OneMax. O escopo é desempenho computacional; qualidade da solução não é variável-resposta. Cada execução completa preserva os controles congelados: `G=100`, uma thread, torneio de tamanho 2, crossover de um ponto com `p_c=0,90`, mutação bit-flip com `p_m=0,01` e sem término antecipado.

O estado anterior concluiu o piloto e a calibração de lote. Ele congelou o fatorial revisado `3 × 3`, com `N={128,512,2048}`, `L={64,256,1024}` e um lote `B` explícito por tratamento, materializado em `config/design.csv`. Ainda não havia executor de campanha nem réplicas principais. A redução da grade inicial `4 × 4` está justificada pelos pilotos preservados; portanto, este estado atende ao item 6 pelo desenho revisado: nove tratamentos e dez réplicas `baseline` por tratamento, totalizando 90 observações.

## Significados

- **`baseline`:** modo primário de medição. O relógio monotônico do executável envolve somente o laço completo de gerações; os acumuladores de fase permanecem zerados.
- **Tratamento:** uma combinação de `N` e `L`, por exemplo `512 × 256`. Há nove tratamentos nesta grade.
- **Réplica externa:** uma repetição independente de um tratamento. Cada uma tem sua própria semente e lugar na ordem aleatória. As dez réplicas permitem verificar depois se os tempos variam muito ou pouco.
- **Lote (`B`):** alguns casos são tão rápidos que o cronômetro ficaria impreciso em uma só execução. Neles, uma medição reúne `B` execuções completas iguais. Isso não significa que há `B` réplicas: a réplica continua sendo uma linha do DOE. Para comparar casos, a análise futura dividirá o tempo pelo tamanho do lote quando necessário.
- **Aquecimento:** uma execução extra, feita antes das medições, para não misturar o custo de carregar programa e bibliotecas com os resultados. Ela foi preservada, mas não aparece em `observations.csv` como réplica planejada.
- **Observação válida:** uma medição que terminou com `status=success`, usou os parâmetros previstos, confirmou `core_id=0`, teve tempo positivo e registrou uso de memória. Uma falha ou mudança de núcleo seria guardada com o motivo, e não repetida silenciosamente.

## O que `make baseline` fez na prática

O comando novo não apenas executa o programa 90 vezes. Antes e durante a
coleta, ele:

1. Confere se o arquivo de planejamento (`design.csv`) corresponde exatamente
   às configurações congeladas;
2. Confirma energia AC e registra o computador, o compilador, o binário e a
   afinidade de CPU;
3. Faz um aquecimento que não entra no resultado;
4. Executa as 90 medições na ordem aleatória já planejada;
5. Guarda, para cada medição, o comando, a saída CSV, mensagens de erro, uso
   máximo de memória e status;
6. Interrompe a campanha se detectar falha, formato inesperado ou núcleo de
   CPU diferente do previsto, em vez de repetir uma linha sem explicação.

Essa ordem aleatória é importante: sem ela, casos maiores poderiam coincidir
sempre com uma máquina mais quente ou mais ocupada, o que confundiria a
comparação.

## Como testar ou reproduzir este estado

Na raiz do repositório, os testes do executor e do DOE não medem desempenho nem escrevem dados brutos:

```bash
python3 -m py_compile scripts/run_experiments.py
make check-design
make check-baseline
make test
```

O resultado esperado inclui `DOE válido ... (180 execuções planejadas)`, a mensagem de campanha validada com `linhas=90`, `tratamentos=9` e `réplicas/tratamento=10`, e `Todos os testes do AG passaram.`. Essas verificações comprovam a consistência do planejador, mas não substituem a coleta.

Para iniciar outra campanha — deliberadamente em outro diretório, nunca sobrescrevendo a atual — execute:

```bash
make baseline
```

O alvo recompila o binário, confirma AC, cria um inventário em `data/metadata/`, faz um aquecimento e percorre as linhas `baseline` do DOE por `order` crescente. Uma campanha completa deve produzir `status=completed` no manifesto e `summary.csv` com `planned=10`, `success=10`, `failed=0` e `invalid=0` nas nove combinações. A reprodução mede uma nova condição temporal da máquina; ela não deve ser anexada ou tratada como idêntica à coleta deste estado.

Para auditar os artefatos deste estado, inspecione `data/raw/baseline-2026-11-07T17_08_32-03_00/manifest.txt`, `summary.csv` e `observations.csv`, e o instantâneo vinculado em `data/metadata/environment-baseline-2026-11-07T17_08_32-03_00/`. A auditoria automatizada local confirmou 90 `run_id` e 90 ordens únicos, todos presentes no subconjunto `baseline` do DOE, todos com `status=success`, `core_id=0`, tempo e RSS positivos e fases zeradas. `git diff --check` verifica somente espaços em mudanças pendentes; ele não revalida tempos.

Uma forma rápida de ler esses arquivos é:

| Arquivo | Pergunta que ele responde |
|---|---|
| `manifest.txt` | Quando a campanha ocorreu e qual configuração/binário foram usados? |
| `summary.csv` | Cada tratamento tem mesmo número de sucessos? Neste estado, cada um tem 10. |
| `observations.csv` | Qual foi o registro de cada uma das 90 medições? |
| `*.command`, `*.stdout.csv`, `*.stderr.txt` | O que foi chamado e qual foi a saída original daquela medição? |
| diretório `data/metadata/environment-baseline-.../` | Em que computador e sob quais controles a campanha foi iniciada? |

## Mudanças e decisões

- Adicionado `scripts/run_experiments.py`, executor específico e conservador da campanha `baseline`. Antes de medir, ele reconstrói o DOE determinístico em memória e exige igualdade literal com `config/design.csv`; lê a configuração congelada; exige AC; e cria um novo inventário por `scripts/capture_environment.sh`.
- Para cada linha, o executor registra a chamada literal (`*.command`), CSV original do binário, stderr, status e máximo RSS coletado por `/usr/bin/time`, além de `observations.csv` rastreável, `summary.csv` e um manifesto com hashes de configuração, DOE e binário, compilador e commit.
- O executor valida o resultado contra a linha planejada, inclusive `N`, `L`, `G`, `B`, semente, probabilidades, modo, tempo positivo e CPU efetivo. Em falha, erro de formato ou afinidade, ele grava a evidência e encerra a campanha, sem reexecutar a linha.
- Adicionados os alvos `make check-baseline` (sem escrita) e `make baseline` e a documentação de uso estável no README.
- Executada uma vez a campanha completa em `data/raw/baseline-2026-11-07T17_08_32-03_00/`. O aquecimento foi preservado separadamente; não foi incluído entre as observações planejadas.

## Evidência e impacto

O manifesto da campanha informa `status=completed`, com início às `2026-11-07T17:08:32-03:00` e fim às `2026-11-07T17:09:33-03:00`. Ele vincula os hashes SHA-256 de `experiment.yaml`, `design.csv` e `ag_bench`, o commit `14e300400c5271c7d11b97c35a70aec9065892d8` e os flags de compilação. O inventário imediatamente anterior confirmou AC online e `taskset_result=passed`, com `observed_core=0`.

`summary.csv` registra dez sucessos e nenhuma falha ou observação inválida em cada um dos tratamentos `128×64`, `128×256`, `128×1024`, `512×64`, `512×256`, `512×1024`, `2048×64`, `2048×256` e `2048×1024`. A auditoria pós-coleta conferiu que as 90 linhas do CSV bruto correspondem, na ordem, às 90 linhas `baseline` do DOE e que todos os 91 processos do AG — um aquecimento e 90 medições — terminaram com status zero.

Esses fatos estabelecem a campanha como a fonte de dados primária para tempos e vazão. Eles não são, por si só, uma conclusão de desempenho: a normalização, a variabilidade entre réplicas, as tabelas e qualquer interpretação ficam para o caderno de análise.

Em outras palavras: sabemos que a coleta deu certo e que os dados estão
completos; ainda não afirmamos que um tamanho de população ou cromossomo é
melhor. Essa resposta depende de resumir e comparar as dez repetições de cada
tratamento de maneira apropriada.

## Limitações e próximo passo

- `phases` ainda não foi executado, portanto não há decomposição de fases nem quantificação do overhead de instrumentação nesta campanha.
- O inventário pré-campanha ainda classifica a cadeia atual de `perf` como `passed_with_multiplexing`; nenhum contador de hardware foi coletado ou deve ser inferido a partir destes dados `baseline`.
- Governor, Turbo e frequência foram registrados, não forçados. A campanha mede o estado documentado de 07/11 e uma repetição futura exige outro bloco bruto e análise explícita de comparabilidade.
- O próximo passo é avaliar o modo `phases` e resolver ou documentar definitivamente a limitação de `perf`, antes de produzir a análise preliminar. A revisão humana deste estado deve ser preenchida em `docs/uso-ia.md` antes de um commit.
