# Problemas encontrados, soluções e limites

Registre um problema real por linha. Diga o que aconteceu, como vocês investigaram e o que ainda pode afetar o trabalho. Não apague tentativas que não deram certo: elas ajudam a explicar as decisões do grupo.

| Data | O que aconteceu (e prova) | Por que importa | O que imaginamos | O que fizemos | Resultado | O que ainda falta ou limita |
|---|---|---|---|---|---|---|
| - | Nenhum problema registrado no início do projeto. | - | - | - | - | - |
| 2026-11-03 | O teste contra a referência deu checksums diferentes: esperado `14512338016235060269`; obtido `4589409489150679678`. | Não seria seguro aceitar a validação independente sem entender a diferença. Nenhum dado de campanha foi afetado. | A referência podia estar aplicando alguma regra do AG de outro modo. | Revisamos a seleção e o desempate do torneio. A referência foi ajustada para escolher o menor índice em caso de empate, como o AG faz. | `make test` passou. A referência agora testa quatro casos pequenos, com probabilidades zero, um e intermediárias. | A referência não é uma prova formal e cobre poucos tamanhos e sementes. O resultado também depende da versão da biblioteca padrão usada no teste. |

## Modelo para próximos registros

| Data | O que aconteceu (e prova) | Por que importa | O que imaginamos | O que fizemos | Resultado | O que ainda falta ou limita |
|---|---|---|---|---|---|---|
| AAAA-MM-DD | Mensagem de erro, comando, arquivo ou medida que mostra o problema. | Efeito nos testes, dados ou conclusão. | Causa provável. | Tentativas feitas, inclusive as que falharam. | O que funcionou ou não funcionou. | Risco que continua ou próximo passo. |
