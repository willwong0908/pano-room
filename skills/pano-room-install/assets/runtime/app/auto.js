(async function phoneTest() {
 const token=diagParams.get('autotest'), id=diagParams.get('id');
 const api='/api/playback-test/'+token;
 const panel=document.createElement('section'), label=document.createElement('p'), action=document.createElement('button');
 panel.style.cssText='margin:8px 0 12px';action.className='dialog-primary';
 panel.append(label,action);el('stage').before(panel);
 label.textContent='自动测试准备中…';action.hidden=true;
 const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
 const report={version:2,status:'准备',device:navigator.userAgent.slice(0,180),id,started:new Date().toISOString(),rounds:[]};
 async function save() {
  const r=await fetch(api,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(report),cache:'no-store',signal:AbortSignal.timeout(6000)});
  if(!r.ok)throw Error('NAS 未收到报告');
 }
 let active=null, running=false;
 autoDraw=(stamp,path,start)=>{
  const s=active;
  if(!s || stamp===s.stamp || v.seeking || Math.abs(stamp-v.currentTime)>2)return;
  const now=performance.now(),ahead=bufferedHere();
  if(s.last!==null){
   const gap=now-s.last;
   if(gap>100)s.gaps++;
   if(gap>s.max){s.max=gap;s.before=s.ahead;s.after=ahead}
  } else s.first=now;
  s.last=now;s.ahead=ahead;s.stamp=stamp;s.frames++;s.path=autoFlat?'原生画面':path;
  s.cost.push(now-start);
 };
 v.addEventListener('waiting',()=>{if(active)active.waits++});
 const n=x=>Math.round(x*100)/100;
 async function round(name,from,seconds,setup) {
  label.textContent=name+' · 测试中，请保持页面在前台';
  report.status=name;
  const begin=performance.now(), s={frames:0,max:0,gaps:0,waits:0,last:null,first:null,cost:[],ahead:0,before:0,after:0};
  let error=null, path;
  try {
   setup();
   active=s;
   while(true) {
    if(document.hidden) throw Error('页面进入后台');
    if(v.error)throw Error('媒体错误 '+v.error.code);
    if(performance.now()-begin>20000)throw Error('本轮等待超过 20 秒');
    if(s.frames && !v.seeking && v.currentTime>=from+seconds)break;
    await delay(80);
   }
  }catch(e){error=e.message}
  finally{active=null;path=streamer?'HLS.js':(v.currentSrc.includes('/source/')?'MP4':'系统 HLS')}
  const sorted=s.cost.sort((a,b)=>a-b);
  const result={name,mode:path,upload:s.path,frames:s.frames,firstFrameMs:s.first===null?null:Math.round(s.first-begin),
   wallFps:n(s.frames*1000/(performance.now()-begin)),endBufferSeconds:n(bufferedHere()),paused:v.paused,ready:v.readyState,playerMessage:el('err').textContent.slice(0,120),fps:s.frames>1?n((s.frames-1)*1000/(s.last-s.first)):null, longestMs:Math.round(s.max),over100:s.gaps,
   aheadBefore:n(s.before),aheadAfter:n(s.after),waiting:s.waits,drawP95:sorted.length?n(sorted[Math.ceil(sorted.length*.95)-1]):null,
   secondsPlayed:n(v.currentTime-from),wallSeconds:n((performance.now()-begin)/1000),error};
  report.rounds.push(result);
  await save().catch(()=>{});
  if(document.hidden)throw Error('页面进入后台，测试中止');
 }
 function nativeSource(pano,raw) {
  v.pause();releaseStream();autoFlat=!pano;c.style.visibility=pano?'visible':'hidden';
  policy=raw?null:new BufferPolicy();
  v.src=raw?'/source/'+id:'/hls/'+id+'/index.m3u8';v.preload='auto';v.load();startPlayback();
 }
 async function run() {
  if(running)return;
  running=true;action.hidden=true;
  try {
   await round('1 · 正式全景',0,5,()=>{startPlayback()});
   await round('2 · 跳至 40 秒',40,4,()=>{
    const slider=el('seek');slider.value=40;slider.dispatchEvent(new Event('input'));slider.dispatchEvent(new Event('change'));
    if(!intent)startPlayback();
   });
   await round('3 · 同源分段平面',0,5,()=>{
    v.pause();releaseStream();autoFlat=true;c.style.visibility='hidden';openStream(id,selection);
    startPlayback();
   });
   await round('4 · 原片全景直读',0,5,()=>nativeSource(true,true));
   await round('原片平面直读',0,5,()=>nativeSource(false,true));
   report.status='完成';
  }catch(e){report.status=e.message}
  finally{intent=false;v.pause();releaseStream();active=null;autoFlat=false;c.style.visibility='visible'}
  try{await save();label.textContent=report.status+' · 报告已传回极空间，可以关闭页面。'}
  catch{label.textContent='测试已结束，报告回传失败。';action.textContent='重传报告';action.hidden=false;action.onclick=async()=>{try{await save();label.textContent='报告已传回极空间';action.hidden=true}catch{label.textContent='连接失败，请重试'}}}
 }
 // Prime the actual production element. Audible playback may require one gesture on iOS.
 const started=performance.now();
 while(!selectedId || el('play').disabled || (!streamer && !v.currentSrc && !v.src)){
  if(performance.now()-started>18000){el('player').hidden=false;label.textContent='测试片未就绪，请重新打开链接';report.status=label.textContent;await save().catch(()=>{});return}
  await delay(100);
 }
 await save().catch(()=>{});
 label.textContent='保持屏幕亮起，测试会自动跳转并回传结果。';
 action.textContent='开始自动测试';action.hidden=false;action.onclick=run;
})().catch(err=>{el('err').textContent='测试无法启动：'+err.message});
