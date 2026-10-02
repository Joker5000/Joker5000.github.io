const game=document.getElementById("game");
const stampMachine=document.getElementById("stampMachine");
const stampPull=document.getElementById("stampPull");
const passport=document.getElementById("passport");
const stampZone=document.getElementById("stampZone");
const passportStamp=document.getElementById("passportStamp");
const returnDocs=document.getElementById("returnDocs");

function fit(){
  const s=Math.min(window.innerWidth/1600,window.innerHeight/900,1);
  document.documentElement.style.setProperty("--scale",s);
}
fit();window.addEventListener("resize",fit);

function overlap(a,b){
  const x=a.getBoundingClientRect(),y=b.getBoundingClientRect();
  return x.left<y.right&&x.right>y.left&&x.top<y.bottom&&x.bottom>y.top;
}
function refreshStampZone(){
  passport.classList.toggle("ready",overlap(passport,stampZone));
}
stampPull.addEventListener("click",()=>stampMachine.classList.toggle("open"));

document.querySelectorAll(".draggable").forEach(el=>{
  let sx=0,sy=0,l=0,t=0,drag=false;
  el.addEventListener("pointerdown",e=>{
    if(e.target.closest(".messages-list"))return;
    drag=true;sx=e.clientX;sy=e.clientY;l=el.offsetLeft;t=el.offsetTop;
    el.setPointerCapture(e.pointerId);el.style.zIndex=40;
  });
  el.addEventListener("pointermove",e=>{
    if(!drag)return;
    const scale=parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--scale"))||1;
    el.style.left=l+(e.clientX-sx)/scale+"px";
    el.style.top=t+(e.clientY-sy)/scale+"px";
    el.style.right="auto";
    refreshStampZone();
  });
  el.addEventListener("pointerup",()=>{drag=false;refreshStampZone()});
});

async function stamp(action,button){
  if(!passport.classList.contains("ready")){
    stampMachine.querySelector(".stamp-caption").textContent="СНАЧАЛА ПОЛОЖИТЕ ПАСПОРТ ПОД ШТАМП";
    return;
  }
  button.classList.add("hit");
  await new Promise(r=>setTimeout(r,220));
  passportStamp.className="passport-stamp show "+action;
  passportStamp.textContent=action==="allow"?"ПОМИЛОВАН":action==="warn"?"ПРЕДУПРЕЖДЁН":"БАН";
  returnDocs.classList.add("active");
  stampMachine.classList.remove("open");
  document.querySelectorAll(".stamp-head").forEach(b=>b.disabled=true);
}

document.querySelectorAll(".stamp-head").forEach(btn=>{
  btn.addEventListener("click",()=>{
    const action=btn.dataset.action;
    if(action==="ban"&&!confirm("Подтвердить реальный бан пользователя?"))return;
    stamp(action,btn);
  });
});

returnDocs.addEventListener("click",()=>{
  if(!returnDocs.classList.contains("active"))return;
  document.querySelectorAll(".paper").forEach((el,i)=>{
    setTimeout(()=>{
      el.style.transition="transform .45s steps(7,end),opacity .3s";
      el.style.transform="translate(-430px,-280px) scale(.75)";
      el.style.opacity="0";
    },i*110);
  });
  setTimeout(()=>{
    document.querySelector(".speech").textContent="Следующий!";
    passportStamp.className="passport-stamp";
    returnDocs.classList.remove("active");
  },700);
});

refreshStampZone();