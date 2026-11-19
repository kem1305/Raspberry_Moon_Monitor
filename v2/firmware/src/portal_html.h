// portal_html.h — setup page served by the gadget's own Wi-Fi access point.
#pragma once
#include <Arduino.h>

static const char PORTAL_HTML[] PROGMEM = R"HTML(<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Moon Monitor</title>
<style>
:root{color-scheme:dark}*{box-sizing:border-box}
body{margin:0;font:16px/1.45 system-ui,sans-serif;background:#0b0d17;color:#e6e9f5}
main{max-width:460px;margin:auto;padding:20px 16px 40px}
h1{font-size:22px;margin:8px 0 2px}h1 span{color:#ffd68c}p.s{margin:0 0 18px;color:#8e97bd;font-size:14px}
fieldset{border:1px solid #2a2f4a;border-radius:12px;margin:0 0 16px;padding:12px 14px 14px}
legend{padding:0 6px;color:#ffd68c;font-weight:600}
label{display:block;margin:10px 0 4px;font-size:14px;color:#b9c0de}
input,select,button{width:100%;padding:11px 12px;border-radius:9px;border:1px solid #343a5c;background:#141829;color:inherit;font:inherit}
input:focus,select:focus{outline:2px solid #6f7dff;border-color:transparent}
button{background:#ffd68c;color:#1a1408;border:0;font-weight:700;margin-top:6px;cursor:pointer}
button.g{background:#1d2238;color:#c9d0f0;border:1px solid #343a5c;font-weight:500}
small{display:block;color:#7c85ab;margin-top:5px;font-size:12.5px}
.row{display:flex;gap:10px}.row>*{flex:1}#msg{color:#ff9d8a;min-height:1.3em;margin:6px 0}
</style></head><body><main>
<h1>Moon <span>Monitor</span></h1><p class="s">Configuração inicial</p>
<form method="post" action="/save" id="f">
<fieldset><legend>Wi-Fi</legend>
<label for="ssid">Rede</label>
<select id="nets"><option value="">Procurando redes…</option></select>
<input id="ssid" name="ssid" maxlength="32" placeholder="Nome da rede (SSID)" value="%SSID%" required style="margin-top:8px">
<label for="pass">Senha</label>
<input id="pass" name="pass" type="password" maxlength="64" placeholder="%PASSHINT%" autocomplete="off">
<button type="button" class="g" id="scan">Procurar redes novamente</button>
</fieldset>
<fieldset><legend>Localização</legend>
<label for="coord">Latitude, longitude (graus decimais)</label>
<input id="coord" name="coord" inputmode="text" placeholder="-25.563, -51.486" value="%COORD%" required>
<small>No Google Maps, toque e segure no local e copie as coordenadas. Sul e oeste são negativos.</small>
</fieldset>
<fieldset><legend>Fuso horário</legend>
<label for="tzsel">Região</label>
<select id="tzsel"></select>
<label for="tz">Regra POSIX</label>
<input id="tz" name="tz" maxlength="60" value="%TZ%" required>
<small>Preenchido automaticamente pela região. Exemplo: <code>&lt;-03&gt;3</code> = UTC−3 sem horário de verão.</small>
</fieldset>
<fieldset><legend>Tela</legend>
<div class="row"><div><label for="rot">Rotação</label>
<select id="rot" name="rot"><option value="0">0°</option><option value="1">90°</option><option value="2">180°</option><option value="3">270°</option></select></div>
<div><label for="night">Apagar à noite</label>
<select id="night" name="night"><option value="0">Nunca</option><option value="1">Sim</option></select></div></div>
<div class="row"><div><label for="n0">Apaga às</label><input id="n0" name="n0" type="time" value="%N0%"></div>
<div><label for="n1">Acende às</label><input id="n1" name="n1" type="time" value="%N1%"></div></div>
<small>Com a tela apagada, um toque no botão a acende por 30 s.</small>
</fieldset>
<input type="hidden" name="epoch" id="epoch"><div id="msg"></div>
<button type="submit">Salvar e reiniciar</button>
</form></main><script>
const Z=[["America/Sao_Paulo","<-03>3"],["America/Bahia","<-03>3"],["America/Fortaleza","<-03>3"],["America/Recife","<-03>3"],["America/Belem","<-03>3"],
["America/Manaus","<-04>4"],["America/Cuiaba","<-04>4"],["America/Campo_Grande","<-04>4"],["America/Porto_Velho","<-04>4"],["America/Boa_Vista","<-04>4"],
["America/Rio_Branco","<-05>5"],["America/Noronha","<-02>2"],["America/Argentina/Buenos_Aires","<-03>3"],["America/Montevideo","<-03>3"],
["America/Asuncion","<-03>3"],["America/Santiago","<-04>4<-03>,M9.1.6/24,M4.1.6/24"],["America/La_Paz","<-04>4"],["America/Caracas","<-04>4"],
["America/Bogota","<-05>5"],["America/Lima","<-05>5"],["America/Mexico_City","CST6"],["America/New_York","EST5EDT,M3.2.0,M11.1.0"],
["America/Toronto","EST5EDT,M3.2.0,M11.1.0"],["America/Chicago","CST6CDT,M3.2.0,M11.1.0"],["America/Denver","MST7MDT,M3.2.0,M11.1.0"],
["America/Phoenix","MST7"],["America/Los_Angeles","PST8PDT,M3.2.0,M11.1.0"],["America/Anchorage","AKST9AKDT,M3.2.0,M11.1.0"],["Pacific/Honolulu","HST10"],
["Atlantic/Azores","<-01>1<+00>,M3.5.0/0,M10.5.0/1"],["Atlantic/Cape_Verde","<-01>1"],["Europe/Lisbon","WET0WEST,M3.5.0/1,M10.5.0"],
["Europe/London","GMT0BST,M3.5.0/1,M10.5.0"],["Europe/Madrid","CET-1CEST,M3.5.0,M10.5.0/3"],["Europe/Paris","CET-1CEST,M3.5.0,M10.5.0/3"],
["Europe/Berlin","CET-1CEST,M3.5.0,M10.5.0/3"],["Europe/Rome","CET-1CEST,M3.5.0,M10.5.0/3"],["Europe/Amsterdam","CET-1CEST,M3.5.0,M10.5.0/3"],
["Europe/Athens","EET-2EEST,M3.5.0/3,M10.5.0/4"],["Europe/Helsinki","EET-2EEST,M3.5.0/3,M10.5.0/4"],["Europe/Istanbul","<+03>-3"],["Europe/Moscow","MSK-3"],
["Africa/Luanda","WAT-1"],["Africa/Maputo","CAT-2"],["Africa/Johannesburg","SAST-2"],["Asia/Dubai","<+04>-4"],["Asia/Kolkata","IST-5:30"],
["Asia/Bangkok","<+07>-7"],["Asia/Shanghai","CST-8"],["Asia/Singapore","<+08>-8"],["Asia/Tokyo","JST-9"],["Asia/Seoul","KST-9"],
["Australia/Perth","AWST-8"],["Australia/Brisbane","AEST-10"],["Australia/Sydney","AEST-10AEDT,M10.1.0,M4.1.0/3"],
["Pacific/Auckland","NZST-12NZDT,M9.5.0,M4.1.0/3"],["UTC","UTC0"]];
const $=i=>document.getElementById(i),tz=$("tz"),sel=$("tzsel");
function fixed(){const m=-new Date().getTimezoneOffset(),a=Math.abs(m),h=Math.floor(a/60),mm=a%60,p=n=>String(n).padStart(2,"0");
return "<"+(m<0?"-":"+")+p(h)+(mm?p(mm):"")+">"+(m<0?"":"-")+h+(mm?":"+p(mm):"")}
Z.forEach(z=>sel.add(new Option(z[0].replace(/_/g," "),z[1])));sel.add(new Option("Outro (usar o relógio deste aparelho)","*"));
sel.onchange=()=>{tz.value=sel.value=="*"?fixed():sel.value};
(function(){const cur=tz.value;let name="";try{name=Intl.DateTimeFormat().resolvedOptions().timeZone}catch(e){}
let i=Z.findIndex(z=>z[0]==name);if(cur){const j=Z.findIndex(z=>z[1]==cur&&(i<0||z[0]==name));i=j>=0?j:Z.findIndex(z=>z[1]==cur);
if(i<0){sel.value="*";return}}if(i>=0){sel.selectedIndex=i;if(!cur)tz.value=Z[i][1]}else{sel.value="*";if(!cur)tz.value=fixed()}})();
$("rot").value="%ROT%";$("night").value="%NIGHT%";
function scan(){const n=$("nets");n.innerHTML="";n.add(new Option("Procurando redes…",""));
fetch("/scan").then(r=>r.json()).then(l=>{n.innerHTML="";n.add(new Option(l.length?"Escolha uma rede…":"Nenhuma rede encontrada",""));
l.forEach(w=>n.add(new Option(w.s+"  ("+w.r+" dBm"+(w.o?", aberta":"")+")",w.s)))}).catch(()=>{n.innerHTML="";n.add(new Option("Falha na busca",""))})}
$("nets").onchange=e=>{if(e.target.value){$("ssid").value=e.target.value;$("pass").focus()}};$("scan").onclick=scan;scan();
$("f").onsubmit=e=>{const raw=$("coord").value.trim(),c=raw.split(",");
const parts=raw.includes(";")?raw.split(";"):c.length==4?[c[0]+"."+c[1],c[2]+"."+c[3]]:raw.split(/[,\s]+/).filter(Boolean);
const m=parts.map(s=>parseFloat(s.trim().replace(",",".")));
if(m.length!=2||!(Math.abs(m[0])<=90)||!(Math.abs(m[1])<=180)){e.preventDefault();$("msg").textContent="Coordenadas inválidas. Use o formato: -25.563, -51.486";return}
$("coord").value=m[0]+", "+m[1];$("epoch").value=Math.floor(Date.now()/1000)};
</script></body></html>)HTML";

static const char SAVED_HTML[] PROGMEM = R"HTML(<!doctype html><html lang="pt-br"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Moon Monitor</title>
<style>body{margin:0;font:17px/1.5 system-ui,sans-serif;background:#0b0d17;color:#e6e9f5;text-align:center;padding:60px 24px}b{color:#ffd68c}</style>
</head><body><h2>Configuração salva</h2><p>O <b>Moon Monitor</b> vai reiniciar e conectar à sua rede.<br>
Se a senha estiver errada, ele reabre esta rede de configuração automaticamente.</p></body></html>)HTML";
