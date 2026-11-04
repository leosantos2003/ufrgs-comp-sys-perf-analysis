# Estado do projeto — implementação inicial do AG

**Data:** 2026-10-22
**Estado associado:** implementação do AG sequencial e primeira suíte de testes.
**Commit de origem:** `bc6608e8190f190a2e43011c8942ac09836c6460` (`etapa2-ag-v1`).

## Contexto do projeto neste estado

O projeto passou a ter a primeira implementação executável do AG sequencial para OneMax. A pesquisa continua sendo sobre o custo computacional em função de `N` e `L`; nenhum resultado de otimização ou campanha de desempenho é produzido aqui. O AG usa genes `std::uint8_t`, duas populações pré-alocadas, seleção por torneio de tamanho 2, crossover de um ponto, mutação bit-flip e exatamente `G` gerações.

Este estado introduziu o binário de medição, o binário de testes e o build reproduzível. A inicialização, checksum e melhor fitness ficam fora da região cronometrada; o laço de gerações é a unidade que será medida futuramente.

## Significados

- **Fitness:** valor usado para escolher os pais; em OneMax é a quantidade de genes iguais a um e fica entre `0` e `L`.
- **Torneio de tamanho 2:** dois índices são sorteados e o maior fitness vence; em empate vence o menor índice, para manter determinismo.
- **Crossover de um ponto:** o filho recebe o prefixo de um pai e o sufixo do outro, separados por um corte entre `1` e `L - 1`.
- **Mutação bit-flip:** cada gene tem probabilidade `p_m` de alternar entre `0` e `1`.
- **Semente:** valor que inicializa `std::mt19937_64`; mesma configuração e semente devem produzir a mesma população final.
- **Checksum:** resumo numérico estável da população final, usado para detectar mudança acidental de comportamento e impedir eliminação do trabalho pelo compilador.
- **`baseline` e `phases`:** o primeiro mede apenas o laço completo; o segundo também acumula tempos por fase para diagnóstico.

## Como testar ou reproduzir este estado

Com esse estado do código ativo no diretório de trabalho, execute:

```bash
make test
make run
./build/ag_bench --help
```

`make test` deve compilar `ag_bench` e `ag_tests` e terminar com `Todos os testes do AG passaram.`; ele cobre as primitivas, parâmetros inválidos, determinismo e modo por fases disponíveis naquele momento. `make run` deve emitir cabeçalho e uma linha CSV. Os tempos variam entre execuções e não devem ser usados como evidência de desempenho neste estágio.

## Mudanças e decisões

- Implementado AG geracional sequencial em `src/ga.cpp`, com OneMax, torneio de tamanho 2, crossover de um ponto, mutação bit-flip, duas populações pré-alocadas e `G` gerações sem parada antecipada.
- A região medida engloba apenas o laço geracional; inicialização da população, cálculo de checksum, melhor fitness e escrita CSV ficam fora dela.
- Adicionados `src/tests.cpp`, `scripts/build.sh` e `Makefile`.

## Evidência e impacto

- Os testes cobriam primitivas do AG, parâmetros inválidos, determinismo com a mesma semente e instrumentação por fases.
- Ainda não havia campanha de medição; portanto, não existem dados experimentais afetados.

## Limitações e próximo passo

- A validação de determinismo ainda não comparava a execução contra uma referência independente em instâncias pequenas.
- Próximo passo: complementar a validação de correção e inventariar/controlar o ambiente antes de qualquer campanha de medição.
