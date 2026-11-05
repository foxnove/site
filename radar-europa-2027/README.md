# Radar Europa 2027 ? backend privado

Painel: https://foxnove.github.io/youtube/radar-europa-2027/

## Opera??o
`python -m unittest discover -s radar-europa-2027 -p "test_*.py"`
`python radar-europa-2027/amadeus_scan.py`

Python 3.10+ e requests 2.32+. Configura??o de rotas, janelas, dura??es, teto de pre?o e limites em config.json. Busca rotativa por data/dura??o: n?o cobre todas as combina??es a cada rodada. Default conservador: 2 pesquisas por execu??o e teto local de 400 chamadas HTTP/m?s incluindo OAuth e tentativas. Conferir a cota real da conta antes de ativar; o teto local n?o comprova gratuidade e n?o considera chamadas feitas por outros aplicativos. N?o aumentar sem conferir os termos e a franquia. Hist?rico e alertas em private/state.json, somente neste reposit?rio privado. Dados v?lidos por 24h; o frontend tamb?m verifica idade. Ofertas n?o s?o reservas e precisam de reconfirma??o.

## Secrets obrigat?rios neste reposit?rio
- AMADEUS_CLIENT_ID e AMADEUS_CLIENT_SECRET: aplicativo com acesso ? produ??o. Cadastro oficial https://developers.amadeus.com/register ; documenta??o https://amadeus4dev.github.io/developer-guides/ . N?o contratar plano ou aceitar cobran?a sem autoriza??o.
- SMTP_USER, SMTP_APP_PASSWORD e ALERT_TO: remetente Gmail, senha de app e destinat?rio privado. Senhas de app requerem configura??o da conta Google: https://support.google.com/accounts/answer/185833 . Nenhum destinat?rio no c?digo ou JSON p?blico.
- PUBLIC_DATA_SSH_KEY: chave de deploy com escrita limitada SOMENTE ao reposit?rio foxnove/youtube. Criada e armazenada como secret pelo agente; sem acesso ao backend ou ? administra??o. A a??o checkout faz verifica??o estrita do host GitHub.

Configurar em https://github.com/foxnove/site/settings/secrets/actions . Segredos n?o s?o recuper?veis pelo c?digo ou pelo agente. N?o colocar no chat ou nos arquivos versionados.

## Automa??o e publica??o
Workflow .github/workflows/radar-europa-2027.yml executa em push de c?digo nesta branch. Aceita execu??o manual e possui cron a cada 6h (minuto 17 UTC). O GitHub s? agenda workflows existentes na branch padr?o: como master n?o pode ser alterada, o cron fica PENDENTE. N?o trocar a branch padr?o, pois h? projetos antigos. Para ativar ? necess?ria autoriza??o espec?fica para um pequeno workflow despachante em master, ou um agendador externo autorizado. Enquanto isso, um commit de c?digo dispara teste e diagn?stico nesta branch.

O workflow salva estado privado antes de sincronizar somente docs/data.json com o caminho radar-europa-2027/data.json da branch p?blica. A rotina p?blica usa lista expl?cita de campos; n?o publica o estado de deduplica??o, credenciais, endere?os ou respostas brutas. Falha do scanner publica o estado real e faz o job falhar, sem alegar sucesso. GitHub Pages permanece no reposit?rio p?blico; workflow antigo de Pages privado n?o ? usado.

AMADEUS_ENV=test mant?m sa?da e estado separados em private/test-*.json; n?o envia e-mail nem sincroniza dados de teste como ofertas de produ??o. Produ??o ? o padr?o. HTTP 429/5xx t?m tentativas limitadas, timeout e respeito a Retry-After limitado. Erros p?blicos s?o c?digos, nunca corpos de respostas.

A Amadeus n?o fornece links de compra neste endpoint: o painel e e-mails n?o inventam links. Travelpayouts foi investigada como alternativa: requer conta/token e fornece cache, n?o substitui consulta de disponibilidade ao vivo sem credenciais (https://travelpayouts.github.io/slate/).

## Diagn?stico inicial
05/11/2026: nenhum Actions Secret em site ou youtube. Pages p?blico ativo; backend sem Pages. Nenhuma autentica??o ou consulta real confirmada. Endere?o antes embutido no backend removido do estado atual; hist?rico privado preservado. Verifica??o no hist?rico p?blico deve permanecer sem endere?os ou segredos.

## Valida??o da implementa??o
14 testes Python e 2 testes Node passaram, al?m de testes de navegador em desktop e larguras 320/375/390 px. Casos cobrem autentica??o ausente, isolamento de teste/produ??o, 429, teto mensal, payload inv?lido, deduplica??o e quedas somente no mesmo itiner?rio. Nenhuma autentica??o real ou envio real foi executado por aus?ncia de credenciais. Um em cada tr?s tipos de pesquisa usa nonStop=true para priorizar voos sem escala; demais pesquisas permitem conex?es internacionais. Alertas pendentes ficam no estado privado e expiram em 24h; n?o s?o descartados pelo limite de 20 ofertas. O m?nimo hist?rico mostrado no card ? do mesmo itiner?rio; gr?fico ? agregado por rota/per?odo.

Apura??o recorrente: uma vaga por rodada (quando j? existem oportunidades e o lote permite) revisita uma viagem da watchlist; as demais vagas exploram novas combina??es. A watchlist privada guarda a melhor combina??o conhecida por rota/temporada. Isso permite detectar quedas compar?veis sem aguardar a volta de toda a varredura.
