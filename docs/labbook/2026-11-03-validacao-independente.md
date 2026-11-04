# Estado do projeto — validação independente do AG

**Data:** 2026-11-03
**Estado associado:** conclusão da validação funcional prevista para o item 2 do roteiro.

## Contexto do projeto neste estado

Este estado conclui a validação funcional do AG da Etapa 2. O projeto investiga como `N`, o tamanho da população, e `L`, o comprimento do cromossomo, afetam o desempenho computacional de um AG sequencial para OneMax. A qualidade da solução não é variável de resposta; cada execução deve completar `G` gerações, sem convergência antecipada.

O código já implementa o AG, o executável CSV, o build reprodutível e os testes de correção. Ainda não existem inventário de ambiente, desenho fatorial materializado, afinidade de CPU confirmada ou dados de campanha. Portanto, esta validação atesta comportamento funcional, não desempenho experimental.

## Significados

- **AG geracional:** a população corrente é avaliada, gera uma população sucessora e então é substituída integralmente a cada geração.
- **OneMax e fitness:** o fitness é a soma dos genes binários; para um cromossomo de comprimento `L`, sempre vale `0 <= fitness <= L`.
- **`N`, `L` e `G`:** `N` é o número de indivíduos, `L` o número de genes por indivíduo e `G` o número fixo de gerações. Somente `N` e `L` são fatores do estudo.
- **`p_c` e `p_m`:** probabilidades controladas de crossover e mutação. Elas não devem variar entre tratamentos da mesma campanha.
- **Semente e determinismo:** a semente inicializa `std::mt19937_64`; para a mesma configuração e biblioteca padrão, ela reproduz a evolução e o checksum final.
- **Checksum e melhor fitness:** saídas calculadas após a região medida. O checksum identifica a população final; o melhor fitness é o maior fitness nela encontrado.
- **`baseline`:** mede o laço de gerações inteiro com um relógio monotônico.
- **`phases`:** mede o mesmo laço, adicionando acumuladores para avaliação, seleção, crossover, mutação e substituição; é diagnóstico, não a fonte primária de tempo.

## Como testar ou reproduzir este estado

Na raiz do projeto, execute a verificação funcional completa:

```bash
make test
```

O resultado esperado é `Todos os testes do AG passaram.` A suíte testa OneMax, torneio e desempate, crossover, mutação nos limites e com sequência controlada, configuração inválida, determinismo, equivalência com a referência simples, população e fitness após cada geração e a coerência entre `baseline` e `phases`.

Como smoke test do executável, execute:

```bash
make run
./build/ag_bench --population 32 --length 16 --generations 10 \
  --seed 20261022 --crossover 0.90 --mutation 0.01 --mode baseline
./build/ag_bench --population 32 --length 16 --generations 10 \
  --seed 20261022 --crossover 0.90 --mutation 0.01 --mode phases
```

As duas últimas linhas devem ter `best_fitness=16` e checksum `2855997894351129235`; `elapsed_ns` pode e deve variar. Esses comandos verificam integração e determinismo, mas não substituem o protocolo de afinidade, aquecimento e réplicas necessário para medir desempenho.

## Mudanças e decisões

- Adicionada, exclusivamente ao binário de testes, uma observação da população após cada geração; o executável de medição não contém esse gancho.
- Implementada uma referência simples e independente das primitivas de produção em `src/tests.cpp` para instâncias pequenas e sementes fixas.
- Incluídos testes de mutação com sequência pseudoaleatória controlada e bits esperados, tamanho da população e binariedade/limites de fitness após cada geração, além da equivalência de checksum e melhor fitness com a referência.
- Convertido o labbook para um arquivo por estado de commit; este índice define o protocolo para os próximos commits.
- Reescrito o README como descrição estável do projeto, sem seção de estado corrente ou próximo passo.
- Adicionado `AGENTS.md` na raiz com instruções obrigatórias para agentes e contribuidores sobre leitura das fontes de verdade, criação de um labbook por estado, registro de dificuldades e IA, testes e limites de commits.
- Simplificados `docs/difficulties.md` e `docs/uso-ia.md`; o primeiro agora usa perguntas diretas e um modelo de nova linha, e o segundo inclui um modelo copiável para registrar a verificação humana.

## Evidência e impacto

- Executado `make test` no diretório raiz: compilação concluída e saída `Todos os testes do AG passaram.`
- Executado `make run`: o binário produziu uma linha CSV válida para a configuração demonstrativa.
- Em uma configuração pequena fixa (`N=32`, `L=16`, `G=10`, semente `20261022`), `baseline` e `phases` produziram o mesmo `best_fitness` (`16`) e checksum (`2855997894351129235`); os tempos foram tratados somente como smoke test, não como medição de desempenho.
- A primeira execução da referência divergiu por implementar incorretamente o desempate de torneio. A evidência levou à correção para o menor índice, regra já definida pelo AG de produção; a suíte passou após a correção.
- Não foram criados ou alterados dados de campanha; não há impacto sobre medições.

## Limitações e próximo passo

- A referência é um modelo de teste para instâncias pequenas, não uma prova formal da implementação nem uma fonte de métricas de desempenho.
- Próximo passo: realizar o inventário do ambiente, confirmar afinidade de CPU e testar `perf` conforme o roteiro.
