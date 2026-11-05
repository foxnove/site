'use strict';
const destinations={LIS:'Lisboa',MAD:'Madri',CDG:'Paris · Charles de Gaulle',ORY:'Paris · Orly',OPO:'Porto',FCO:'Roma',MXP:'Milão',BCN:'Barcelona',FRA:'Frankfurt',AMS:'Amsterdã',ZAG:'Zagreb',TIA:'Tirana',TBS:'Tbilisi',BRU:'Bruxelas',DUB:'Dublin',LHR:'Londres',VIE:'Viena'};
function validOffers(data,now=Date.now()){
 if(data.environment!=='production')return [];
 return (Array.isArray(data.offers)?data.offers:[]).filter(o=>o&&typeof o.price==='number'&&Number.isFinite(o.price)&&o.price>0&&o.currency==='BRL'&&destinations[o.destination]&&/^2027-\d{2}-\d{2}$/.test(o.departure)&&/^2027-\d{2}-\d{2}$/.test(o.return)&&Number.isFinite(Date.parse(o.checked_at))&&now-Date.parse(o.checked_at)<=86400000&&now-Date.parse(o.checked_at)>=-300000);
}
function filterOffers(offers,f){return offers.filter(o=>(!f.destination||o.destination===f.destination)&&(!f.month||o.departure.slice(5,7)===f.month)&&(!f.max||o.price<=Number(f.max))&&(!f.direct||(o.return_details_available===false?o.outbound_direct===true:o.direct===true))&&(!f.noDomestic||(o.return_details_available===false?o.outbound_domestic_connection===false:o.domestic_connection===false))).sort((a,b)=>a.price-b.price)}
if(typeof module!=='undefined')module.exports={validOffers,filterOffers};
if(typeof document!=='undefined'){
 const $=id=>document.getElementById(id);
 const money=n=>new Intl.NumberFormat('pt-BR',{style:'currency',currency:'BRL',maximumFractionDigits:0}).format(n);
 const date=s=>s&&Number.isFinite(Date.parse(s))?new Intl.DateTimeFormat('pt-BR',{dateStyle:'short',timeStyle:'short',timeZone:'America/Sao_Paulo'}).format(new Date(s)):'Não realizada';
 const day=s=>new Intl.DateTimeFormat('pt-BR',{day:'2-digit',month:'short',timeZone:'UTC'}).format(new Date(s+'T12:00:00Z'));
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const states={credentials_missing:'Credenciais pendentes',ok:'Última consulta concluída',partial:'Consulta parcial',error:'Falha na consulta',quota_exhausted:'Limite de consultas atingido',cooldown:'Intervalo de economia',test:'Ambiente de testes'};
 const emailStates={not_configured:'Configuração pendente',ready:'Configurado · envio não testado',sent:'Último envio confirmado',no_new_promotions:'Sem nova promoção para enviar',send_failed:'Falha no envio'};
 const errors={credentials_missing:'Credenciais de produção ausentes',monthly_budget_reached:'Teto mensal de buscas atingido',daily_budget_reached:'Teto diário de buscas atingido',account_quota_exhausted:'Franquia gratuita indisponível',free_plan_required:'A busca foi bloqueada para evitar uso de plano pago',account_quota_unverified:'Não foi possível confirmar a franquia gratuita',serpapi_error:'A SerpApi não concluiu a pesquisa',http_401:'Autenticação recusada',http_403:'Acesso à API recusado',http_429:'Limite de requisições da API',network_unavailable:'API indisponível ou sem conexão',invalid_json:'Resposta inválida da API',invalid_offer:'Oferta descartada por dados inválidos'};
 let data={},offers=[],history=[],loading=false;
 Object.entries(destinations).forEach(([code,city])=>{const o=document.createElement('option');o.value=code;o.textContent=city+' · '+code;$('destination').append(o)});
 function drawOffers(){
  const filtered=filterOffers(offers,{destination:$('destination').value,month:$('month').value,max:$('max-price').value,direct:$('direct').checked,noDomestic:$('no-domestic').checked});
  $('filtered-count').textContent=filtered.length;
  $('empty').hidden=filtered.length>0;
  $('empty').querySelector('h3').textContent=offers.length?'Nenhuma oferta com esses filtros':'Nenhuma tarifa válida disponível';
  $('empty').querySelector('p').textContent=offers.length?'Ajuste os filtros para ver outras passagens.':'As ofertas aparecem após uma consulta de produção e permanecem válidas no painel por até 24 horas. Nenhum preço é simulado.';
  $('offer-list').innerHTML=filtered.map(o=>{
   const connections=Array.isArray(o.connections)?o.connections.map(x=>Array.isArray(x)?x.join(' → '):'').filter(Boolean).join(' / '):'';
   const duration=Array.isArray(o.durations)?o.durations.map(x=>x?String(x).replace(/^PT/,'').toLowerCase():'a confirmar').join(' / '):'Não informada';
   const bags=Array.isArray(o.baggage)&&o.baggage.length?o.baggage.map(b=>b.quantity!==undefined?`${b.quantity} peça(s)`:`${b.weight??'—'} ${b.weightUnit??''}`).filter((x,i,a)=>a.indexOf(x)===i).join(' / '):'Não informada pela API';
   const route=o.return_details_available===false?(o.outbound_direct?'Ida sem escalas · volta a confirmar':o.outbound_domestic_connection?'Ida com conexão no Brasil · volta a confirmar':'Ida com conexão internacional · volta a confirmar'):(o.direct?'Direto · ida e volta':o.domestic_connection?'Com conexão doméstica no Brasil':'Conexão internacional · sem conexão doméstica');
   let source='';try{const u=new URL(o.source_url);if(u.protocol==='https:'&&['www.google.com','google.com'].includes(u.hostname)&&u.pathname.startsWith('/travel/flights'))source=`<p><a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">Consultar no Google Flights ↗</a></p>`}catch{}
   return `<article class="offer"><div class="offer-top"><span class="route-code">SSA → ${esc(o.destination)}</span>${o.promotion?'<span class="deal">⚑ Promoção no radar</span>':''}</div><h3>${esc(destinations[o.destination])}</h3><div class="price">${money(o.price)}</div><div class="caption">POR PESSOA · IDA E VOLTA</div><div class="offer-info"><p>${esc(day(o.departure))} → ${esc(day(o.return))} · ${Math.round((Date.parse(o.return)-Date.parse(o.departure))/86400000)} dias</p><p>${esc((o.airline_names||o.airlines||[]).join(' · '))}</p><p class="route-tag">${route}</p><p>Escalas ida / volta: ${esc((o.stops||[]).map(n=>n==null?'a confirmar':n).join(' / '))}${connections?' · '+esc(connections):''}</p><p>Duração ida / volta: ${esc(duration)}<br>Bagagem despachada: ${esc(bags)}</p><p>${o.change_percent!=null?'Variação: '+esc(o.change_percent)+'% · ':''}Menor histórico: ${money(o.historical_low||o.price)}</p><p>Consultado em ${esc(date(o.checked_at))}</p>${source}<small>Reconfirme preço e condições.${o.return_details_available===false?' Preço de ida e volta; detalhes da volta não consultados para economizar buscas.':''}</small></div></article>`;
  }).join('');
 }
 function drawChart(){
  const selection=$('history-route').value;
  const [code,period='ambos']=selection.split('|');
  const groups=['fev-mar','jul-ago'].filter(p=>period==='ambos'||p===period).map(p=>({
    period:p,rows:history.filter(h=>h.destination===code&&h.period===p).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at)).slice(-40)
  })).filter(g=>g.rows.length);
  const all=groups.flatMap(g=>g.rows).sort((a,b)=>Date.parse(a.at)-Date.parse(b.at));
  $('history-table').innerHTML=all.map(h=>`<tr><td>${esc(date(h.at))}</td><td>SSA → ${esc(h.destination)}</td><td>${esc(h.period)}</td><td>${money(h.price)}</td></tr>`).join('');
  if(!all.length){$('chart').innerHTML='<div class="chart-empty">Ainda não há consultas para esse período.<small>Os dados aparecerão após novas verificações.</small></div>';return}
  const min=Math.min(...all.map(h=>h.price)),max=Math.max(...all.map(h=>h.price)),spread=Math.max(200,max-min);
  const first=Math.min(...all.map(h=>Date.parse(h.at))),last=Math.max(...all.map(h=>Date.parse(h.at)));
  const palette={'fev-mar':'#a6efbb','jul-ago':'#f1c784'};
  const lines=groups.map(g=>{
    const points=g.rows.map(h=>[55+(last===first?205:(Date.parse(h.at)-first)/(last-first)*410),125-(h.price-min)/spread*95]);
    const color=palette[g.period];
    return `<polyline points="${points.map(p=>p.join(',')).join(' ')}" fill="none" stroke="${color}" stroke-width="2"/>${points.map(([x,y],i)=>`<circle cx="${x}" cy="${y}" r="3.5" fill="${color}"><title>${esc(g.period)} · ${esc(date(g.rows[i].at))}: ${esc(money(g.rows[i].price))}</title></circle>`).join('')}`;
  }).join('');
  const legend=groups.map((g,i)=>`<circle cx="${55+i*145}" cy="12" r="4" fill="${palette[g.period]}"/><text x="${65+i*145}" y="15" class="chart-label">${g.period==='fev-mar'?'Fev / Mar':'Jul / Ago'}</text>`).join('');
  $('chart').innerHTML=`<svg viewBox="0 0 500 165" role="img" aria-label="Histórico de ${esc(destinations[code]||code)}: ${all.length} consultas, ${groups.length} período(s)"><title>Comparação de tarifas por período. Detalhes na tabela abaixo.</title>${legend}<text x="0" y="35" class="chart-label">${esc(money(max))}</text><text x="0" y="130" class="chart-label">${esc(money(min))}</text>${lines}<text x="55" y="155" class="chart-label">${esc(date(all[0].at))}</text><text x="465" y="155" text-anchor="end" class="chart-label">${esc(date(all.at(-1).at))}</text></svg>`;
 }
 function render(){
  offers=validOffers(data);
  history=(Array.isArray(data.history)?data.history:[]).filter(h=>h&&destinations[h.destination]&&['fev-mar','jul-ago'].includes(h.period)&&Number.isFinite(h.price)&&h.price>0&&Number.isFinite(Date.parse(h.at)));
  const status=states[data.status]||'Estado não confirmado';
  const stale=data.last_success_at&&Date.now()-Date.parse(data.last_success_at)>86400000;
  $('api-badge').textContent=stale&&data.status==='ok'?'Dados desatualizados':status;
  $('api-badge').classList.toggle('healthy',['ok','cooldown'].includes(data.status)&&!!data.last_success_at&&!stale);
  $('api-state').textContent=(data.provider==='serpapi'?'SerpApi · Google Flights · ':'')+status+' · '+(data.environment==='production'?'produção':data.environment==='test'?'testes':'ambiente não confirmado');
  $('count').textContent=offers.length;
  $('count-caption').textContent=offers.length?'Consultadas nas últimas 24 horas':'Nenhuma oferta válida disponível';
  $('best').textContent=offers.length?money(Math.min(...offers.map(o=>o.price))):'—';
  $('threshold').textContent=money(Number.isFinite(data.max_brl)?data.max_brl:4500);
  $('updated').textContent=date(data.last_success_at||data.updated_at);
  $('attempt').textContent=date(data.last_attempt_at);
  $('scheduler').textContent=data.scheduler?.status==='active'?'Agendamento ativo · a cada 6 horas':'Pendente · exige workflow na branch padrão';
  $('email-state').textContent=emailStates[data.email_status]||'Não confirmado';
  $('quota').textContent=data.quota?`${data.quota.used} / ${data.quota.limit} · ${data.quota.month}`:'Não disponível';
  $('coverage').textContent=data.coverage?`${data.successful_queries||0} pesquisas concluídas / ${data.coverage.combinations} combinações · amostragem rotativa`:'Nenhuma consulta confirmada';
  $('errors').textContent=(data.errors||[]).map(e=>errors[e.code]||(/^(http_\d{3}|invalid_[a-z_]+)$/.test(e.code)?e.code:'Erro na consulta')).filter((x,i,a)=>a.indexOf(x)===i).join(' · ');
  let title='Monitoramento aguardando configuração',text='O painel está publicado. A consulta de tarifas depende das credenciais de produção; o envio de alertas e a execução automática ainda precisam ser ativados.';
  if(data.status==='ok'){title=stale?'Última consulta desatualizada':'Última consulta de produção concluída';text=stale?'As tarifas antigas não são apresentadas como ofertas válidas. Aguarde uma nova consulta.':`${data.successful_queries||0} pesquisas concluídas na rodada. A lista cobre uma amostra das datas e rotas, sujeita à disponibilidade e alteração de preços.`}
  else if(data.status==='partial'){title='Consulta parcialmente concluída';text='Parte das pesquisas falhou. Apenas ofertas válidas verificadas nas últimas 24 horas são exibidas.'}
  else if(['error','quota_exhausted'].includes(data.status)){title='Monitoramento interrompido';text='A última tentativa não foi concluída. Consulte o estado do sistema abaixo. Ofertas antigas expiram após 24 horas.'}
  else if(data.status==='cooldown'){title='Intervalo de economia de buscas';text='A última pesquisa ocorreu há menos de 6 horas. O radar preserva as ofertas válidas e aguarda o próximo intervalo, sem consumir outra busca.'}
  else if(data.status==='test'){title='Ambiente de testes';text='Resultados de teste não são apresentados como tarifas reais de produção.'}
  $('notice-title').textContent=title;$('notice-text').textContent=text;
  for(const [period,id] of [['fev-mar','season-one'],['jul-ago','season-two']]){const rows=offers.filter(o=>o.period===period);$(id).textContent=rows.length?money(Math.min(...rows.map(o=>o.price))):'—'}
  const previous=$('history-route').value;$('history-route').replaceChildren();
  const codes=[...new Set(history.map(h=>h.destination))].sort((a,b)=>destinations[a].localeCompare(destinations[b],'pt-BR'));
  if(!codes.length){const option=document.createElement('option');option.textContent='Aguardando histórico';$('history-route').append(option)}
  codes.forEach(code=>{
    for(const [period,label] of [['ambos','Ambos os períodos'],['fev-mar','Fevereiro / Março'],['jul-ago','Julho / Agosto']]){
      const option=document.createElement('option');option.value=code+'|'+period;option.textContent=destinations[code]+' · '+label;$('history-route').append(option);
    }
  });
  if([...$('history-route').options].some(o=>o.value===previous))$('history-route').value=previous;
  else if(codes.length)$('history-route').value=codes[0]+'|ambos';
  drawOffers();drawChart();
 }
 async function load(){
  if(loading)return;loading=true;$('refresh').disabled=true;$('refresh').textContent='Lendo painel…';
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
  try{const response=await fetch('./data.json?t='+Date.now(),{cache:'no-store',signal:controller.signal});if(!response.ok)throw Error('HTTP');const parsed=await response.json();if(!parsed||typeof parsed!=='object'||!Array.isArray(parsed.offers))throw Error('schema');data=parsed;render()}
  catch{$('api-badge').textContent='Falha ao ler os dados';$('api-badge').classList.remove('healthy');$('notice-title').textContent='Não foi possível atualizar o painel';$('notice-text').textContent='Verifique a conexão e tente novamente. Esta leitura não iniciou uma consulta de voos.';offers=validOffers(data);drawOffers();$('count').textContent=offers.length;$('best').textContent=offers.length?money(Math.min(...offers.map(o=>o.price))):'—'}
  finally{clearTimeout(timer);loading=false;$('refresh').disabled=false;$('refresh').textContent='↻ Atualizar painel'}
 }
 $('filters').addEventListener('submit',e=>e.preventDefault());$('filters').addEventListener('input',drawOffers);$('history-route').addEventListener('change',drawChart);$('refresh').addEventListener('click',load);
 load();setInterval(()=>{if(!document.hidden)load()},300000);
}
