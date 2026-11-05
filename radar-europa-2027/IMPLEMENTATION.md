# Radar Europa 2027 — plano e registro

Especificação: missão fornecida pelo usuário em 05/11/2026. Execução autônoma autorizada, inclusive publicação, exclusivamente na branch radar-europa-2027.

Arquitetura: Python/requests no repositório privado; snapshot público com lista explícita de campos; GitHub Pages existente sem mudança de fonte. Segredos somente em Actions Secrets. API de produção por padrão; teste nunca publicado como tarifa real.

1. Testar normalização de voos, distinção direto/conexão doméstica, histórico, alertas sem repetição, cotas e falhas sem perda do último resultado.
2. Implementar scanner importável, varredura rotativa de datas/durações com limite mensal conservador configurável, OAuth, tentativas limitadas, estado privado e exportação pública.
3. Implementar workflow em push/manual/schedule e sincronização com token de acesso restrito ao repositório público. Persistir estado antes de sincronizar. Sem mudanças em master: schedule permanecerá bloqueado pela exigência da plataforma.
4. Reformular painel com filtros, comparação de períodos, histórico SVG acessível, estados verdadeiros e layout responsivo.
5. Executar testes, publicar branches autorizadas, verificar execução e Pages. Credenciais ausentes serão documentadas como bloqueio, nunca substituídas por dados simulados.

Diagnóstico: nenhum Actions Secret em site ou youtube; Pages de youtube ativo na branch radar-europa-2027; site sem Pages; scanner não reconhecido entre workflows, sem schedule; nenhuma sincronização; destinatário embutido apenas no backend privado (remover do código atual). Não houve consulta real.

Riscos a verificar: falha de autenticação, 429/cota, resposta inválida, execução parcialmente falha, teste confundido com produção, e-mail repetido, publicação de estado privado.

Execu??o: checkout dedicado em branches do Radar, sem altera??o de master. Revis?o independente encontrou e corrigiu compara??o entre viagens diferentes, estrutura JSON inv?lida e corte de alertas. Regress?es adicionadas, 14 testes Python aprovados. 2 testes Node e QA de navegador (inclusive falha de leitura, ranking, filtros, SVG e escape de HTML) aprovados. Chave deploy exclusiva do p?blico criada e guardada no secret PUBLIC_DATA_SSH_KEY do backend; chave tempor?ria removida. Nenhum e-mail encontrado no hist?rico de arquivos p?blicos do Radar.

Apura??o recorrente: uma vaga por rodada (quando j? existem oportunidades e o lote permite) revisita uma viagem da watchlist; as demais vagas exploram novas combina??es. A watchlist privada guarda a melhor combina??o conhecida por rota/temporada. Isso permite detectar quedas compar?veis sem aguardar a volta de toda a varredura.
