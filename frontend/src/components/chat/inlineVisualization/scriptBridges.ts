/** Parent ↔ sandbox postMessage protocol for inline visualization iframes. */
export const MSG_SET = 'kn-inline-set';
export const MSG_HEIGHT = 'kn-inline-height';
export const MSG_WIDGET_ERROR = 'kn-inline-widget-error';

export const MORPHDOM_SRC =
    'https://cdn.jsdelivr.net/npm/morphdom@2.7.4/dist/morphdom-umd.min.js';

export const bridgeScripts = {
    reportError(errorEventType: string): string {
        return `window._knReportWidgetError=function(msg,src,line,col,err){
try{
if(window.parent)window.parent.postMessage({
type:'${errorEventType}',
message:String(msg!=null?msg:''),
source:String(src!=null?src:''),
line:Number(line)||0,
col:Number(col)||0,
stack:err&&err.stack?String(err.stack):''
},'*');
}catch(e){}
};
window.addEventListener('error',function(ev){
try{
var el=ev.target;
if(el&&el.nodeName){
var tag=String(el.nodeName).toUpperCase();
if(tag==='IMG'||tag==='LINK')return;
}
var m=ev.message||(ev.error&&ev.error.message)||'';
if(!m&&el&&String(el.nodeName).toUpperCase()==='SCRIPT')m='Script failed to load or execute';
window._knReportWidgetError(m,ev.filename||'',ev.lineno||0,ev.colno||0,ev.error);
}catch(e){}
},true);
window.addEventListener('unhandledrejection',function(ev){
try{
var r=ev.reason;
var m=r&&(r.message!=null?r.message:String(r))||'Unhandled rejection';
window._knReportWidgetError(m,'',0,0,r instanceof Error?r:null);
}catch(e){}
});`;
    },

    resizeNotifier(heightEventType: string): string {
        return `(function(){
function knNotifyHeight(){
  requestAnimationFrame(function(){
    try{
      var de=document.documentElement,bo=document.body;
      var h=Math.max(de.scrollHeight,bo.scrollHeight);
      if(window.parent)window.parent.postMessage({type:'${heightEventType}',height:h},'*');
    }catch(e){}
  });
}
window.addEventListener('load',knNotifyHeight);
if(typeof ResizeObserver!=='undefined'){
  try{new ResizeObserver(knNotifyHeight).observe(document.body);}catch(e){}
}
knNotifyHeight();
})();`;
    },

    streamListener(setMsgType: string, heightMsgType: string): string {
        return `(function(){
var T='${setMsgType}';
window._knMorphReady=false;
window._knPending=null;
window._knNotifyHeight=function(){
requestAnimationFrame(function(){
try{
var de=document.documentElement,bo=document.body;
var h=Math.max(de.scrollHeight,bo.scrollHeight);
if(window.parent)window.parent.postMessage({type:'${heightMsgType}',height:h},'*');
}catch(e){}
});
};
window._knSetContent=function(html){
if(!window._knMorphReady){window._knPending=html;return;}
var root=document.getElementById('kn-root');
if(!root)return;
var target=document.createElement('div');
target.id='kn-root';
target.innerHTML=html||'';
morphdom(root,target,{
onBeforeElUpdated:function(from,to){if(from.isEqualNode(to))return false;return true;}
});
window._knNotifyHeight();
};
window._knRunScripts=function(){
document.querySelectorAll('#kn-root script').forEach(function(old){
try{
if(old.src){
var s=document.createElement('script');
s.src=old.src;
var rp=old.parentNode;
if(rp)rp.replaceChild(s,old);
}else{
var code=old.textContent;
var p=old.parentNode;
if(!p)return;
p.removeChild(old);
try{(0,eval)(code);}catch(e){try{if(window._knReportWidgetError)window._knReportWidgetError(e&&e.message?e.message:String(e),'',0,0,e);}catch(x){}}
}
}catch(e){try{if(window._knReportWidgetError)window._knReportWidgetError(e&&e.message?e.message:String(e),'',0,0,e);}catch(x){}}
});
window._knNotifyHeight();
};
window.addEventListener('message',function(e){
if(!e.data||e.data.type!==T)return;
if(e.data.replaceRoot){
var rr=document.getElementById('kn-root');
if(rr){rr.innerHTML='';}
}
window._knSetContent(e.data.html||'');
if(e.data.runScripts)window._knRunScripts();
});
try{
if(typeof ResizeObserver!=='undefined'){
new ResizeObserver(function(){window._knNotifyHeight();}).observe(document.body);
}
}catch(e){}
window._knNotifyHeight();
})();`;
    },

    morphOnload(): string {
        return "window._knMorphReady=true;if(window._knPending){window._knSetContent(window._knPending);window._knPending=null;}else{window._knNotifyHeight();}";
    },
} as const;
