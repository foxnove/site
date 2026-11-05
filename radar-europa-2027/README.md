# Radar Europa 2027 — backend privado

Painel: https://foxnove.github.io/youtube/radar-europa-2027/

## Operação

Python 3.10+ e requests 2.32+. Executar a partir da raiz:

```sh
python -m unittest discover -s radar-europa-2027 -p 'test_*.py'
python radar-europa-2027/amadeus_scan.py
```

Configuração em config.json: origem SSA; janelas 20/02–31/03 e 01/07–31/08/2027; durações 14, 18, 21 e 24 dias, editáveis. Destinos pedidos e quatro aeroportos adicionais. Teto de promoção R$ 4.500 e redução significativa de 10%, configuráveis.

A busca é uma amostra rotativa, não uma varredura completa a cada rodada. Limite inicial: duas pesquisas por execução e 400 chamadas HTTP/mês, incluindo OAuth e tentativas. Conferir a franquia real da conta antes de ativar. Esse teto local não garante gratuidade e não contabiliza chamadas de outros aplicativos. Não contratar serviços nem aceitar cobranças sem autorização.

Uma vaga por rodada revisita a watchlist de oportunidades conhecidas, quando disponível; as demais exploram novas datas. Parte da exploração exige nonStop=true, priorizando voos sem escala. A watchlist guarda a melhor combinação conhecida por rota/temporada. Variações e quedas usam o mesmo itinerário; o gráfico agrega mínimos por rota/temporada. O painel expira ofertas após 24h.

Histórico, observações, consumo, watchlist, fila de alertas e deduplicação ficam em private/state.json, SOMENTE no repositório privado. Alertas pendentes expiram em 24h. O endpoint não fornece link de compra: não são inventados links. A busca não é reserva ou garantia de preço.

## Secrets necessários no backend

Configurar em https://github.com/foxnove/site/settings/secrets/actions . Não enviar valores no chat ou colocar em arquivos versionados.

- AMADEUS_CLIENT_ID e AMADEUS_CLIENT_SECRET: aplicativo com acesso à produção. Cadastro oficial: https://developers.amadeus.com/register . Documentação: https://amadeus4dev.github.io/developer-guides/ . Verificar condições e franquia; não cadastrar cartão ou contratar serviço sem autorização.
- SMTP_USER: remetente Gmail.
- SMTP_APP_PASSWORD: senha de app do Google, quando disponível para a conta. Configuração oficial: https://support.google.com/accounts/answer/185833 . Não usar a senha normal da conta.
- ALERT_TO: destinatário privado dos alertas.
- PUBLIC_DATA_SSH_KEY: já criado e configurado pelo agente. Chave de deploy com escrita limitada ao repositório foxnove/youtube; sem acesso ao backend ou à administração. A chave temporária foi removida e o checkout verifica o host GitHub.

## Automação e publicação

Workflow .github/workflows/radar-europa-2027.yml: execução em push de código na branch do Radar, execução manual e cron de seis horas, minuto 17 UTC. O GitHub exige o arquivo na branch padrão para cron e execução manual. Como master deve permanecer intocada, a agenda está PENDENTE. Não alterar a branch padrão de projetos antigos. Ativação exige autorização específica para acrescentar um workflow despachante na branch padrão ou configurar um agendador externo.

O workflow salva estado privado, faz checkout da branch pública usando a chave exclusiva e sincroniza somente o snapshot por lista explícita de campos. Falha de API publica o diagnóstico e termina sinalizando indisponibilidade. O Pages continua no repositório youtube e não depende de hospedagem paga. A publicação legada do backend privado foi desativada.

AMADEUS_ENV=production é o padrão. AMADEV_ENV não é usado. Para testar, AMADEUS_ENV=test mantém arquivos e estado separados em private/test-*.json; não envia e-mails nem sobrescreve o snapshot de produção. HTTP 429/5xx têm tentativas limitadas, timeout e Retry-After limitado. Erros públicos contêm códigos, nunca corpos de resposta.

Travelpayouts foi investigada como alternativa: também exige conta/token e fornece dados de cache, não substituindo consulta ao vivo sem credenciais: https://travelpayouts.github.io/slate/ .

## Validação em 05/11/2026

- 14 testes Python e 2 testes Node aprovados; testes isolados de ranking, filtros, SVG, escape de HTML e erros de rede.
- Navegador em desktop e larguras 320, 375 e 390 px: sem erros de JavaScript ou rolagem horizontal; site publicado validado em desktop/iPhone.
- Execução real do GitHub Actions confirmou testes, persistência privada e sincronização pública. Run: https://github.com/foxnove/site/actions/runs/41968789165 . O job sinalizou API indisponível por ausência de credenciais.
- Pages público: deploy https://github.com/foxnove/youtube/actions/runs/41968816724 concluído com sucesso.
- Nenhuma autenticação Amadeus, tarifa de produção ou mensagem Gmail real confirmada. Zero tarifas verificadas.
- Destinatário fixo removido do código privado atual; histórico privado preservado. Nenhum endereço encontrado no histórico dos arquivos públicos do Radar. Branches master e visibilidade dos repositórios preservadas.
