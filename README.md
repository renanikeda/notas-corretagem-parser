# Corretagem Parser
Classe para parsear Notas de Corretagem / Proventos em PDF das corretoras XP e Rico para facilitar a declaração de IR, calculando preço médio, lucros e prejuízos, JCP, Dividendos, CNPJ dos Fundos e Ações, etc.
A classe ParseCorretagem recebe um caminho para parsear cada nota de cada ano (é bom ter o histórico), é que o caminho root recebido tenha a seguinte estrutura: {root_path}/{broker}/{year}/Notas de Corretagem/[pdf files] e {root_path}/{broker}/{year}/Proventos/[pdf files].

Se há ativos que foram subscritos (FIIs e FI Infra) é preciso colocar no root um arquivo subscricao.csv no formato: Asset; Price; Amount; Date, exemplo: HGRU11; 126.17; 12; 01/08/2024.

O projeto tem como escopo somente renda variável, listados como Ações, ETFs, FIIs e FI Infra, qualquer sugestão sinta-se a vontade.

