# Caderno de laboratório

## Convenções

Registrar cada decisão, teste, alteração de protocolo, anomalia e próximo passo com data, evidência e impacto nos dados. Não reescrever entradas antigas: acrescentar correções ou decisões posteriores.

## 2026-10-14 - Inicialização da Etapa 2

- Criada a estrutura inicial do trabalho e o repositório Git local em `etapa-2/`.
- Registrados os controles iniciais do AG em `config/experiment.yaml`.
- Ainda não há código, inventário do ambiente ou medições.
- Próximo passo: implementar o AG e testes determinísticos de correção.

## 2026-10-22 - Implementação e testes do AG

- Implementado AG geracional sequencial em `src/ga.cpp`, com OneMax, torneio de tamanho 2, crossover de um ponto, mutação bit-flip, duas populações pré-alocadas e `G` gerações sem parada antecipada.
- A região medida engloba apenas o laço geracional; inicialização da população, cálculo de checksum, melhor fitness e escrita CSV ficam fora dela.
- Adicionados `src/tests.cpp`, `scripts/build.sh` e `Makefile`. Os testes cobrem primitivas do AG, parâmetros inválidos, determinismo com a mesma semente e instrumentação por fases.
- Próximo passo: inventariar e controlar o ambiente de execução antes de qualquer campanha de medição.
