# Radar Europa 2027 — backend privado

Fonte ativa: SerpApi / Google Flights. Entrada: `python radar-europa-2027/serpapi_scan.py`.

- Secret: SERPAPI_API_KEY, somente neste repositório privado.
- Economia: uma busca por rodada, intervalo mínimo de 6h, limites rígidos de 6/dia e 180/mês. Contadores reservados antes da busca e persistidos em private/state.json. Sem tentativas automáticas ou consultas adicionais de volta/reserva.
- A API gratuita de conta confirma plano de preço zero, saldo do plano e consumo antes de pesquisar. Créditos extras não são usados. Cache padrão da SerpApi permanece permitido.
- Viagem e rotas em config.json; prioridades LIS, MAD, CDG, FCO e MXP. Datas/janelas e durações existentes preservadas. Watchlist e exploração se alternam.
- Preços são de ida e volta por pessoa em BRL. A resposta inicial detalha apenas a ida; a volta fica explicitamente a confirmar no painel/e-mail. Link Google Flights vem da resposta e é validado; nunca um link de compra inventado.
- Gmail depende de SMTP_USER, SMTP_APP_PASSWORD e ALERT_TO nos Secrets. Deduplicação e fila existentes preservadas.
- PUBLIC_DATA_SSH_KEY já protege a sincronização exclusiva com foxnove/youtube. Exportação pública usa campos permitidos, sem respostas brutas ou credenciais.
- Workflow reutilizável na branch radar-europa-2027; agendador mínimo na branch padrão executa esse código a cada 6h. Nenhum merge completo ou alteração em projetos antigos.
- Scripts Amadeus preservados como legado e testes de regressão; não são chamados pelo monitor ativo.

Testes locais: `python -m unittest discover -s radar-europa-2027 -p 'test_*.py'`.
Documentação: https://serpapi.com/google-flights-api e https://serpapi.com/account-api .
