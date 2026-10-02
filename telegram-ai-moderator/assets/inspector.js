var activePassport=null;
function overlap(a,b){var x=a.getBoundingClientRect(),y=b.getBoundingClientRect();return x.left<y.right&&x.right>y.left&&x.top<y.bottom&&x.bottom>y.top}
function refreshPassportZone(){var p=document.querySelector('.passport'),z=document.querySelector('.stamp-zone');if(!p||!z)return;var ok=overlap(p,z);p.classList.toggle('stamp-ready',ok);activePassport=ok?p:null}
document.querySelectorAll('.drag').forEach(function(el){
 var sx=0,sy=0,l=0,t=0,go=false;
 el.onpointerdown=function(e){if(e.target.closest('.scroll'))return;go=true;sx=e.clientX;sy=e.clientY;l=el.offsetLeft;t=el.offsetTop;el.setPointerCapture(e.pointerId);el.style.zIndex=15};
 el.onpointermove=function(e){if(!go)return;el.style.left=(l+e.clientX-sx)+'px';el.style.top=(t+e.clientY-sy)+'px';refreshPassportZone()};
 el.onpointerup=function(){go=false;refreshPassportZone()}
});
function toggleStampDrawer(){document.querySelector('.stamp-housing').classList.toggle('open')}
async function stampDecision(id,action,label,button){
 if(!activePassport){alert('Положите паспорт в зону штампа.');return}
 button.classList.add('down');
 var mark=activePassport.querySelector('.passport-mark');
 mark.className='passport-mark '+(action==='allow'?'allow':'warn')+' show';
 mark.textContent=label;
 setTimeout(async function(){
   await fetch('/case/'+id+'/'+action,{method:'POST'});
   document.querySelector('.stamp-housing').classList.remove('open');
   setTimeout(function(){location.reload()},650)
 },260)
}
function banConfirm(id){
 if(!activePassport){alert('Положите паспорт в зону решения.');return}
 if(confirm('Реально забанить пользователя в Telegram?')){
   var mark=activePassport.querySelector('.passport-mark');
   mark.className='passport-mark ban show';mark.textContent='ДОПУСК АННУЛИРОВАН';
   fetch('/case/'+id+'/ban',{method:'POST'}).then(function(){setTimeout(function(){location.reload()},700)})
 }
}
refreshPassportZone();