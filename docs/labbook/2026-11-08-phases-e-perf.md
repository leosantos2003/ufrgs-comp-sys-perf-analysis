# Estado do projeto — campanhas `phases` e `perf`

**Data:** 2026-11-08  
**Estado associado:** implementação do item 7 do roteiro de execução: medir as partes internas do AG, verificar o custo dessa medição e não aceitar contadores de CPU pouco confiáveis. Commit: `feat: conclui campanhas phases e perf`

## Resumo em linguagem simples

Até este ponto, a campanha `baseline` media apenas o tempo total que o
algoritmo levava para completar suas gerações. Isso responde **quanto** tempo o
AG gastou, mas não mostra em qual parte ele gastou esse tempo.

Neste estado fizemos três coisas diferentes:

1. Executamos o modo `phases` 45 vezes: cinco repetições para cada uma das
   nove combinações de `N` e `L`. Nesse modo, além do relógio total, o programa
   anota separadamente o tempo gasto para avaliar indivíduos, escolher pais,
   fazer crossover, aplicar mutação e trocar a população.
2. Tentamos primeiro pedir todos os contadores de hardware de uma vez pelo
   `perf`. Eles ficaram ativos por apenas 91% do tempo. Seria como tentar medir
   seis coisas com menos instrumentos disponíveis e alternar alguns deles
   durante a tarefa: o número final deixa de ser comparável. A campanha foi
   corretamente interrompida antes de criar dados inválidos.
3. Como esses contadores são essenciais para o trabalho, separamos a coleta
   em dois grupos menores: um para **ciclos e instruções** (que permite
   calcular IPC) e outro para **referências e faltas de cache** (que permite
   calcular a taxa de faltas). Também corrigimos a afinidade: o `perf` passou
   a ser preso ao CPU 0 junto com o AG. Com isso, todos os contadores de cada
   grupo ficaram ativos por 100% do tempo e coletamos 90 observações válidas:
   45 de IPC e 45 de cache.

Também comparamos o tempo total do modo `phases` com o tempo da `baseline`
equivalente. A diferença observada ficou pequena, mas ela não prova sozinha o
custo dos relógios internos: as duas campanhas foram feitas em momentos
diferentes e o computador pode variar um pouco. Portanto, as fases serão
usadas para explicar a composição do tempo; a `baseline` continua sendo a
fonte principal para dizer qual configuração foi mais rápida ou mais lenta.

Em resumo: há dados completos para explicar **onde o AG passa o tempo**, uma
estimativa cautelosa do custo dessa explicação e agora há contadores de
hardware válidos. O IPC deve ser calculado apenas com ciclos e instruções da
mesma linha `ipc_user`; a taxa de faltas, apenas com referências e faltas da
mesma linha `cache_user`.

### Uma forma simples de pensar na coleta de hardware

Imagine que a CPU tem poucos mostradores físicos disponíveis. Queríamos ler
quatro mostradores do AG: quantos "passos" do relógio ele usou, quantas
instruções executou, quantas vezes procurou dados no cache e quantas dessas
procuras não estavam lá. Na primeira tentativa, pedimos todos de uma vez. Como
não havia mostradores suficientes, o sistema alternou alguns deles durante a
execução. Por isso apareceram 91%: não é que o AG trabalhou só 91%, e sim que
aquele mostrador observou só 91% do trabalho. Esse número não serve para uma
comparação precisa.

A solução foi tirar duas "fotos" separadas de execuções equivalentes. Uma foto
tem os dois mostradores necessários para IPC; a outra, os dois necessários
para cache. Também garantimos que quem liga os mostradores (`perf`) e o AG
fiquem no mesmo CPU desde o começo. Cada foto passou a cobrir 100% da execução.
Assim, temos números confiáveis, desde que cada cálculo use somente os dois
mostradores que aparecem juntos na mesma foto.

## Contexto do projeto neste estado

O projeto investiga como o tamanho da população (`N`) e o comprimento do cromossomo (`L`) afetam o custo computacional de um algoritmo genético (AG) sequencial para OneMax. O escopo é desempenho computacional, não qualidade da solução. Os controles permanecem congelados: `G=100`, uma thread, seleção por torneio de tamanho 2, crossover de um ponto com `p_c=0,90`, mutação bit-flip com `p_m=0,01` e sem término antecipado.

O estado anterior já tinha o DOE revisado `3 × 3`, a calibração de lote e uma campanha `baseline` completa de 90 observações. O executável já sabia medir as fases, mas ainda faltava uma forma padronizada de executar e guardar as 45 medições planejadas, compará-las com a baseline e impedir que uma coleta `perf` ruim entrasse nos resultados. A limitação conhecida era a multiplexação de contadores de hardware em `perf stat`; neste estado ela foi resolvida por um novo bloco de medição, sem alterar nem apagar a tentativa recusada.

## Significados

- **`baseline`:** medida principal. Ela cronometra somente o trabalho completo do AG, sem dividir esse trabalho em partes.
- **`phases`:** medida de diagnóstico. Ela acrescenta relógios internos para separar avaliação, seleção, crossover, mutação e substituição. O tempo total continua sendo registrado.
- **Overhead de instrumentação:** diferença percentual entre uma execução `phases` e uma `baseline` com a mesma receita (`N`, `L`, `G`, lote `B`, réplica e semente). Em termos simples, ela estima quanto os relógios extras podem ter mudado o tempo observado.
- **`perf`:** ferramenta do Linux que lê os mostradores internos da CPU. Ela conta coisas que o cronômetro comum não mostra, como ciclos de relógio, instruções e acessos à memória cache. O AG é executado sem os relógios de fase para não misturar as duas formas de medição.
- **IPC:** abreviação de *instructions per cycle*. Em linguagem simples, é a quantidade de instruções que a CPU completou para cada ciclo de relógio. Aqui ele é `instructions / cycles`; os dois números precisam vir da mesma linha.
- **Cache:** memória pequena e muito rápida perto da CPU. Uma **referência** é uma procura nessa memória; uma **falta** acontece quando o dado procurado não está nela e precisa ser buscado mais longe. A taxa de faltas é `cache_misses / cache_references`, usando os dois números da mesma linha.
- **`ipc_user`:** o conjunto de números que fica na mesma linha para calcular IPC: `cycles` e `instructions`, além de contagens de trocas de contexto e migrações. O sufixo `/u` significa que os dois primeiros contam o trabalho do programa AG, não o trabalho interno do sistema operacional.
- **`cache_user`:** o conjunto de números que fica na mesma linha para calcular a taxa de faltas: `cache-references` e `cache-misses`, mais os mesmos indicadores de qualidade. O `/u` tem o mesmo significado: observar o AG em vez de incluir trabalho do sistema operacional.
- **Multiplexação:** a CPU precisa revezar um mostrador porque recebeu mais pedidos do que consegue acompanhar de uma vez. Se o mostrador ficou ativo por menos de 100%, ele não é aceito nesta campanha para calcular IPC ou taxa de faltas.

## Como testar ou reproduzir este estado

Na raiz do repositório, estas verificações não produzem dados de desempenho:

```bash
python3 -m py_compile scripts/run_experiments.py scripts/generate_design.py scripts/calibrate_batch.py
make check-design
make check-phases
make check-perf
make test
make run
git diff --check
```

O resultado esperado inclui DOE válido com 225 linhas: 90 `baseline`, 45
`phases` e 90 `perf` (cinco réplicas para cada tratamento e cada um dos dois
grupos). Também devem passar os testes do AG e a linha CSV de demonstração.
Esses comandos validam código e planejamento, não os tempos da campanha.

Para uma nova campanha de fases, com energia AC e sem reutilizar um diretório existente:

```bash
make phases
```

O alvo usa `data/raw/baseline-2026-11-07T17_08_32-03_00/` como referência pareada por padrão. Outra referência exige `make phases PHASES_BASELINE=data/raw/baseline-<timestamp>`. Uma campanha válida cria um novo diretório `data/raw/phases-<timestamp>/`, um inventário associado e cinco sucessos por tratamento.

`make perf` segue esta sequência:

1. Confere se a máquina está na energia AC e se o AG realmente executa no CPU 0.
2. Faz uma execução de teste para `ipc_user` e outra para `cache_user`. Tanto
   o leitor dos contadores (`perf`) quanto o AG ficam presos ao CPU 0.
3. Aceita continuar apenas se todos os mostradores de cada teste ficaram ativos
   durante 100% da execução. Se aparecer, por exemplo, 99%, ele para e guarda
   os arquivos que explicam a recusa.
4. Faz um aquecimento para cada grupo e, então, mede as 90 linhas planejadas.

Assim, a campanha não tenta "consertar" depois um número incompleto: ela só
guarda dados de hardware quando a condição de medição já foi comprovada.

Para consultar a coleta já feita, estes arquivos respondem perguntas simples:

| Arquivo | Pergunta respondida |
|---|---|
| `summary.csv` | As cinco repetições de cada combinação terminaram? |
| `observations.csv` | Qual foi o tempo total e o tempo de cada fase em cada repetição? |
| `phase-overhead.csv` | Quanto uma repetição `phases` diferiu da sua `baseline` equivalente? |
| `phase-overhead-summary.csv` | Qual é o resumo dessa diferença por combinação de `N` e `L`? |
| `data/raw/perf-2026-11-08T01_45_16-03_00/summary.csv` | Cada tratamento teve cinco sucessos nos dois grupos de contadores? |
| `data/raw/perf-2026-11-08T01_45_16-03_00/observations.csv` | Quais são os contadores brutos e o percentual ativo de cada execução? |
| `*.command`, `*.stdout.csv`, `*.status` | Qual comando foi executado e qual saída original ele produziu? |
| `data/metadata/environment-.../` | Em que estado estavam CPU, energia, afinidade e ferramentas antes da coleta? |

## Mudanças e decisões

- O executor passou a entender os três tipos de linha do DOE: `baseline`, `phases` e `perf`. Em todos os casos ele segue a ordem aleatória já decidida, faz um aquecimento separado e guarda os arquivos originais de cada chamada.
- Foram adicionados quatro comandos mais claros: `make phases` e `make check-phases`, para medir ou somente conferir o plano das fases; `make perf` e `make check-perf`, para o mesmo processo com os contadores da CPU.
- Antes de começar as fases, o executor confere se existe uma baseline correspondente para cada uma das cinco sementes. Depois de medir, ele confere que o programa usou os parâmetros esperados, ficou no CPU correto, teve tempo positivo e que as cinco partes medidas não somam mais que o tempo total.
- O executor produz os dois CSVs de overhead por código. Assim, ninguém precisa copiar tempos para uma planilha ou calcular percentuais manualmente.
- A configuração passou a declarar duas leituras de hardware: `ipc_user` mantém juntos ciclos e instruções; `cache_user` mantém juntas referências e faltas de cache. Cada leitura também anota trocas de contexto e migrações, que ajudam a perceber interferências externas. Isso altera o DOE de 180 para 225 linhas e abre um novo bloco de medições de `perf`.
- Os quatro contadores principais usam o sufixo `/u`: eles contam o trabalho feito pelo programa AG, em vez de misturar nele o trabalho interno do sistema operacional. Os dois indicadores de qualidade continuam sendo do sistema inteiro.
- Antes de iniciar `perf`, o executor testa de verdade cada leitura com os mesmos argumentos de uma linha planejada. O `taskset` agora prende tanto o `perf` quanto o AG ao CPU selecionado desde o início. Só então o executor aceita guardar ciclos, instruções e eventos de cache. Essa regra evita que um número parcialmente observado pareça confiável.
- O Makefile e o README foram atualizados para explicar esses comandos. O resumo de ambiente também é atualizado para apontar para o inventário mais recente, inclusive quando uma campanha é interrompida por segurança.

## Evidência e impacto

### O que deu certo nas fases

A campanha `phases` foi concluída em `data/raw/phases-2026-11-08T00_39_18-03_00/`, com inventário em `data/metadata/environment-phases-2026-11-08T00_39_18-03_00/`. Ela ocorreu com energia AC e no CPU lógico 0. Foram planejadas 45 medições e as 45 terminaram com sucesso: cinco para cada uma das nove combinações de população e cromossomo. Não houve medição repetida, descartada ou corrigida manualmente.

O arquivo `summary.csv` confirma cinco sucessos, zero falhas e zero inválidas por combinação. A auditoria também confirmou que não há identificadores duplicados, que todas as medições reportaram `core_id=0`, que os tempos são positivos e que a soma dos tempos das cinco etapas não ultrapassa o tempo total. Isso mostra que os arquivos estão coerentes para a análise; não significa ainda que uma fase seja a causa de qualquer diferença de desempenho.

O sumário pareado de overhead registrou medianas por tratamento entre **-1,68%** e **2,51%**. Um valor positivo quer dizer que a versão com relógios internos demorou mais naquela comparação; um valor negativo não quer dizer que medir tornou o programa magicamente mais rápido, apenas que a variação normal do computador foi maior que ou comparável ao efeito observado. Por isso, a conclusão segura é que não apareceu um aumento grande de tempo neste teste. As fases servem para decompor o trabalho; a `baseline` continua sendo a fonte primária para comparar tempo e vazão.

### A primeira tentativa de `perf` foi interrompida

`make perf` criou `data/raw/perf-2026-11-08T00_40_14-03_00/` e o inventário `data/metadata/environment-perf-2026-11-08T00_40_14-03_00/`, mas parou antes mesmo do aquecimento. O teste informou `passed_with_multiplexing`: `cycles`, `instructions`, `cache-references` e `cache-misses` ficaram ativos por 91,00% da execução; somente os dois eventos de sistema ficaram em 100,00%.

O manifesto marca `status=failed` e guarda o motivo literal. Isso não significa que o AG falhou. Significa que a ferramenta de medição não conseguiu observar todos os contadores como o protocolo exige. A decisão correta foi não criar nenhuma observação `perf`, nem calcular IPC ou taxas de cache a partir desses números incompletos. Esse diretório permanece preservado como evidência da limitação original.

### Como os contadores se tornaram válidos

Separar os quatro contadores em dois pares foi o primeiro passo, mas não
resolveu tudo. Uma verificação curta e depois um teste longo, com apenas o AG
preso ao CPU 0, ainda mostraram 60--99% em alguns eventos. A explicação prática
é que o leitor dos mostradores, o `perf`, podia começar em outro CPU antes de o
AG ser preso ao CPU 0. Depois de prender os dois desde o começo com
`taskset -c 0`, três testes seguidos para cada grupo ficaram em 100% para todos
os seus contadores.

A nova campanha está em `data/raw/perf-2026-11-08T01_45_16-03_00/`, com
inventário em `data/metadata/environment-perf-2026-11-08T01_45_16-03_00/`.
Ela ocorreu com AC online, CPU lógico 0, `perf_event_paranoid=0` registrado e
dois pré-testes aprovados. Foram planejadas 90 observações e as 90 terminaram
com sucesso: para cada uma das nove combinações de `N` e `L`, há cinco linhas
`ipc_user` e cinco linhas `cache_user`. A auditoria leu o CSV com o parser de
CSV, encontrou 90 identificadores únicos, zero falhas, zero valores de
`core_id` diferentes de 0, zero indicadores de multiplexação e os campos de
contador corretos para cada grupo.

Na prática, cada uma das nove combinações de `N` e `L` ganhou cinco "fotos" de
IPC e cinco "fotos" de cache. Isso permite calcular IPC em cada uma das 45
linhas `ipc_user` e taxa de faltas em cada uma das 45 linhas `cache_user`.
Não permite tratar as duas fotos como se fossem uma execução única: por
exemplo, ciclos de uma linha `ipc_user` não podem ser combinados com faltas de
uma linha `cache_user` para produzir uma nova razão.

## Limitações e próximo passo

- A comparação de overhead usa a mesma semente e os mesmos parâmetros, mas a baseline de referência foi coletada em outro momento. Ela mostra a diferença que foi observada, não separa perfeitamente o efeito dos relógios de mudanças normais no computador. A análise deve deixar isso claro.
- A campanha válida de `perf` mede os eventos de hardware apenas enquanto o programa AG está trabalhando. Ela não pretende medir o trabalho interno do sistema operacional; trocas de contexto e migrações são guardadas só como sinais de qualidade da medição.
- Há 45 fotos de IPC e 45 de cache, não 45 execuções contendo os quatro contadores de hardware ao mesmo tempo. Não se deve preencher colunas vazias, juntar pedaços de execuções diferentes ou criar razões entre grupos.
- Governor, Turbo e frequência foram registrados, não forçados. O algoritmo e seu binário não mudaram; o inventário também preserva o diff pendente do executor que existia no momento das coletas.
- O próximo passo é o item 8: criar o validador de dados e o caderno executável. Ele deverá ler `baseline`, `phases`, `ipc_user` e `cache_user`, calcular cada razão somente no seu grupo e mostrar a composição do tempo.
