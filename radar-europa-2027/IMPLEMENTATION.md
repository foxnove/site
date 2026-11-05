# Radar Europa 2027 — plano e registro

Especificação: missão fornecida pelo usuário em 05/11/2026. Execução autônoma autorizada, inclusive publicação, exclusivamente nas branches e diretórios do Radar.

Arquitetura: Python/requests no repositório privado; snapshot público com lista explícita de campos; GitHub Pages existente sem mudança de fonte. Segredos somente em Actions Secrets. Produção por padrão; teste não aparece como tarifa real.

1. Testar normalização, conexões domésticas, histórico, deduplicação, cotas e persistência de falhas.
2. Implementar scanner importável, datas/durações flexíveis, varredura rotativa, watchlist recorrente, OAuth, limite mensal e tentativas limitadas.
3. Implementar workflow e sincronização com chave exclusiva do repositório público; persistir estado antes de publicar. Preservar master: cron fica pendente por exigência do GitHub.
4. Reformular painel com filtros, comparação, histórico SVG, estados reais e layout responsivo.
5. Executar testes, publicar branches autorizadas e verificar execução/Pages. Documentar credenciais ausentes sem inventar resultados.

Diagnóstico: inicialmente nenhum Actions Secret; Pages de youtube ativo na branch do Radar; site sem Pages; scanner sem cron, não reconhecido entre workflows, sem sincronização; destinatário embutido apenas no backend privado.

Registro final: 14 testes Python e 2 testes Node aprovados. QA de navegador incluiu desktop, 320/375/390 px, filtros, gráfico, erro de leitura e escape de HTML. Revisão independente encontrou e corrigiu comparação entre itinerários distintos, JSON com estrutura inválida e corte de alertas. Chave de deploy restrita ao público criada e protegida no secret PUBLIC_DATA_SSH_KEY. Execução em Actions comprovou persistência e sincronização; diagnóstico credentials_missing publicado. Pages confirmado em produção. Destinatário removido do código atual, nenhum e-mail no histórico de arquivos públicos. Nenhuma alteração em master ou visibilidade.

Pendências externas: credenciais Amadeus de produção, SMTP/Gmail e destinatário; autorização de um workflow despachante na branch padrão ou agendador externo para ativar cron. Nenhuma consulta real de tarifa ou envio real de e-mail realizado.
