# Radar Europa 2027

## Abrir o painel
**[Ver o código do painel (index.html)](./docs/index.html)** — este link abre o arquivo no GitHub, **não** um site em execução.

**[Ver o README e o projeto no GitHub](https://github.com/foxnove/site/tree/radar-europa-2027/radar-europa-2027)**

**Status: ainda não publicado.** Não há URL pública funcional para abrir o aplicativo. O repositório é privado e o projeto está em uma branch isolada para não alterar outros sites.

## Monitoramento
O script `amadeus_scan.py` está integrado à API Amadeus Flight Offers Search, mas ainda precisa de credenciais de produção (`AMADEUS_CLIENT_ID` e `AMADEUS_CLIENT_SECRET`) cadastradas nos segredos do repositório. Sem elas, **não consulta preços reais**. A rotina de GitHub Actions foi criada para execução manual, mas ainda não está agendada. Alertas de Gmail também precisam dos segredos `SMTP_USER` e `SMTP_APP_PASSWORD`.

## Configuração
- Origem: Salvador (SSA).
- Janelas: 20/02–31/03 e 01/07–31/08/2027.
- Destinos e limite de preço: [config.json](./config.json).
- Destinatário previsto: diego.fox001@gmail.com.

## API
[Amadeus for Developers](https://developers.amadeus.com/) — cadastrar aplicativo, obter credenciais e verificar limites, cobertura e preços. **Não compartilhe chaves no código ou por mensagens.**

**Importante:** GitHub Pages para repositórios privados depende das condições do plano/conta. Publicar Pages pode tornar o site acessível publicamente mesmo quando o código é privado. Não foi ativado.
