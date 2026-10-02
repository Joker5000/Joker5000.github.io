const InspectorGame={
 state:"boot",caseId:null,passport:null,drawer:null,zone:null,
 init(caseId){
  this.caseId=caseId;
  this.passport=document.querySelector(".passport");
  this.drawer=document.querySelector(".stamp-housing");
  this.zone=document.querySelector(".stamp-zone");
  this.bindDrag();
  this.bindDesk();
  requestAnimationFrame(()=>this.transition("arrival"));
 },
 transition(next){
  this.state=next;
  document.body.dataset.gameState=next;
  const npc=document.querySelector(".traveler");
  const docs=document.querySelectorAll(".doc");
  if(next==="arrival"){
   npc?.classList.add("walking-in");
   setTimeout(()=>this.transition("documents"),900);
  }else if(next==="documents"){
   npc?.classList.add("at-window");
   docs.forEach((d,i)=>setTimeout(()=>d.classList.add("issued"),220+i*170));
   setTimeout(()=>this.transition("inspection"),850);
  }else if(next==="inspection"){
   document.querySelector(".callout")?.classList.add("visible");
  }else if(next==="stamped"){
   document.querySelectorAll(".stamp").forEach(b=>b.disabled=true);
   setTimeout(()=>this.transition("return"),650);
  }else if(next==="return"){
   document.querySelector(".return-slot")?.classList.add("active");
  }else if(next==="exit"){
   npc?.classList.add("walking-out");
   setTimeout(()=>location.href="/inspector",1000);
  }
 },
 bindDesk(){
  document.querySelector(".stamp-handle")?.addEventListener("click",()=>this.drawer.classList.toggle("open"));
  document.querySelector(".return-slot")?.addEventListener("click",()=>{
    if(!["return","stamped"].includes(this.state))return;
    document.querySelectorAll(".doc").forEach(d=>d.classList.add("returned"));
    this.transition("exit");
  });
 },
 bindDrag(){
  document.querySelectorAll(".drag").forEach(el=>{
   let sx=0,sy=0,l=0,t=0,go=false;
   el.addEventListener("pointerdown",e=>{
    if(e.target.closest(".scroll"))return;
    go=true;sx=e.clientX;sy=e.clientY;l=el.offsetLeft;t=el.offsetTop;
    el.setPointerCapture(e.pointerId);el.style.zIndex=30;
   });
   el.addEventListener("pointermove",e=>{
    if(!go)return;
    el.style.left=(l+e.clientX-sx)+"px";el.style.top=(t+e.clientY-sy)+"px";
    this.refreshStampZone();
   });
   el.addEventListener("pointerup",()=>{go=false;this.refreshStampZone()});
  });
 },
 refreshStampZone(){
  if(!this.passport||!this.zone)return;
  const a=this.passport.getBoundingClientRect(),b=this.zone.getBoundingClientRect();
  const ok=a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;
  this.passport.classList.toggle("stamp-ready",ok);
 },
 async stamp(action,label,button){
  if(!this.passport.classList.contains("stamp-ready")){
   document.querySelector(".hint").textContent="ПОЛОЖИТЕ ПАСПОРТ ПОД ШТАМП";
   return;
  }
  button.classList.add("down");
  const mark=this.passport.querySelector(".passport-mark");
  mark.className="passport-mark "+(action==="allow"?"allow":"warn")+" show";
  mark.textContent=label;
  await new Promise(r=>setTimeout(r,300));
  const res=await fetch("/case/"+this.caseId+"/"+action,{method:"POST",redirect:"manual"});
  this.drawer.classList.remove("open");
  this.transition("stamped");
 },
 async ban(){
  if(!this.passport.classList.contains("stamp-ready")){
   document.querySelector(".hint").textContent="ПОЛОЖИТЕ ПАСПОРТ В ЗОНУ РЕШЕНИЯ";
   return;
  }
  if(!confirm("Применить реальный бан в Telegram?"))return;
  const mark=this.passport.querySelector(".passport-mark");
  mark.className="passport-mark ban show";mark.textContent="ДОПУСК АННУЛИРОВАН";
  await fetch("/case/"+this.caseId+"/ban",{method:"POST",redirect:"manual"});
  this.transition("stamped");
 }
};