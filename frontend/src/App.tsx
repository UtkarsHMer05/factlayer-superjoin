import {useEffect, useRef, useState} from 'react';
import {ArrowDownToLine, ArrowLeft, ArrowRight, Check, ChevronRight, FileText, Layers, Link2, Plus, Search, Upload, X, AlertTriangle, RefreshCw, ExternalLink, ScanText} from 'lucide-react';

type Obj = Record<string, any>;
type View = 'facts'|'relationships'|'documents'|'failures';
const names: Record<string,string> = {corroborates:'Corroborated',contradicts:'Likely contradiction',reconciles:'Context explained',insufficient_context:'Needs context',accepted:'Grounded',quarantined:'Quarantined'};
async function request(path:string, init?:RequestInit) {
  const r=await fetch('/api'+path,init);
  if(!r.ok){let message=`Request failed (${r.status})`;try{const d=await r.json();message=typeof d.detail==='string'?d.detail:JSON.stringify(d.detail)}catch{}throw new Error(message)}
  return r.json();
}
function Badge({label}:{label?: string}){const safeLabel=label||'unknown';return <span className={`badge ${safeLabel}`}>{names[safeLabel]||safeLabel.replaceAll('_',' ')}</span>}
function valueText(c:Obj){const v=c.value;return v?`${v.raw}${v.unit&& !v.raw.includes(v.unit)?` ${v.unit}`:''}${v.scale&&v.scale!=='one'?` · ${v.scale}`:''}`:'—'}

export default function App(){
  const [collections,setCollections]=useState<Obj[]>([]),[cid,setCid]=useState(''),[view,setView]=useState<View>('facts');
  const [docs,setDocs]=useState<Obj[]>([]),[items,setItems]=useState<Obj[]>([]),[total,setTotal]=useState(0),[offset,setOffset]=useState(0);
  const [query,setQuery]=useState(''),[filter,setFilter]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false),[loading,setLoading]=useState(false);
  const [detail,setDetail]=useState<Obj|null>(null),[source,setSource]=useState<Obj|null>(null),[health,setHealth]=useState<Obj>({});
  const [newName,setNewName]=useState(''),[adding,setAdding]=useState(false),[tick,setTick]=useState(0);
  const fileRef=useRef<HTMLInputElement>(null),requestVersion=useRef(0);
  const active=collections.find(c=>c.id===cid);
  useEffect(()=>{request('/health').then(setHealth).catch(e=>setError(e.message));},[]);
  useEffect(()=>{let valid=true;request('/collections').then(c=>{if(valid){setCollections(c);setCid(old=>old||c[0]?.id||'')}}).catch(e=>setError(e.message));return()=>{valid=false}},[tick]);
  useEffect(()=>{if(!cid)return;let valid=true;request(`/collections/${cid}/documents`).then(d=>{if(valid)setDocs(d)}).catch(e=>setError(e.message));return()=>{valid=false}},[cid,tick]);
  useEffect(()=>{if(!docs.some(d=>['queued','processing'].includes(d.status)))return;const t=setInterval(()=>setTick(x=>x+1),3000);return()=>clearInterval(t)},[docs]);
  useEffect(()=>{
    const version=++requestVersion.current;
    if(!cid){setItems([]);return}
    setLoading(true);
    const t=setTimeout(()=>{
      const path=view==='facts'?`facts?q=${encodeURIComponent(query)}&status=${filter||'accepted'}&offset=${offset}`:
        view==='relationships'?`relationships?label=${filter}&offset=${offset}`:view;
      request(`/collections/${cid}/${path}`).then(d=>{if(version===requestVersion.current){setItems(Array.isArray(d)?d:d.items);setTotal(Array.isArray(d)?d.length:d.total)}})
        .catch(e=>{if(version===requestVersion.current)setError(e.message)}).finally(()=>{if(version===requestVersion.current)setLoading(false)});
    },150);
    return()=>clearTimeout(t);
  },[cid,view,query,filter,offset,tick]);
  function navigate(v:View){setView(v);setOffset(0);setFilter('');setQuery('');setItems([]);setTotal(0);setLoading(true);setDetail(null);setSource(null)}
  async function create(){if(!newName.trim())return;try{const c=await request('/collections',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:newName.trim()})});setCid(c.id);setTick(x=>x+1);setAdding(false);setNewName('')}catch(e){setError((e as Error).message)}}
  async function upload(files:FileList|null){if(!files||!cid)return;setBusy(true);setError('');try{for(const file of Array.from(files)){const body=new FormData();body.append('file',file);await request(`/collections/${cid}/documents`,{method:'POST',body})}setTick(x=>x+1);navigate('documents')}catch(e){setError((e as Error).message)}finally{setBusy(false);if(fileRef.current)fileRef.current.value=''}}
  async function inspect(item:Obj){try{const d=await request(`/${view==='relationships'?'relationships':'facts'}/${item.id}`);setDetail(d);setSource(null)}catch(e){setError((e as Error).message)}}
  async function showSource(docId:string,page:number,anchors:Obj[]=[]){try{const p=await request(`/documents/${docId}/pages/${page}`);setSource({docId,page,anchors,pageCount:docs.find(d=>d.id===docId)?.page_count||page,...p})}catch(e){setError((e as Error).message)}}
  async function resume(doc:Obj){try{await request(`/jobs/${doc.job_id}/resume`,{method:'POST'});setTick(x=>x+1)}catch(e){setError((e as Error).message)}}
  const subtitle={facts:'Every assertion has a place in the source.',relationships:'See where the evidence agrees, differs, or needs context.',documents:'Your source material, with processing coverage.',failures:'Uncertainty stays visible. Nothing is silently repaired.'}[view];
  return <div className="app">
    <aside className="sidebar">
      <a className="brand" href="/" aria-label="FactLayer home"><Layers size={26}/><span>FactLayer<span className="brand-dot">.</span></span></a>
      <div className="collection-control"><label htmlFor="collection">Knowledge collection</label><select id="collection" value={cid} onChange={e=>{setCid(e.target.value);setItems([]);setTotal(0);setLoading(true);setDetail(null);setSource(null);setOffset(0)}}><option value="" disabled>Select a collection</option>{collections.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select><button className="quiet add-collection" onClick={()=>setAdding(!adding)}><Plus size={15}/>New collection</button>
      {adding&&<form className="create-form" onSubmit={e=>{e.preventDefault();create()}}><label className="sr-only" htmlFor="new-name">Collection name</label><input autoFocus id="new-name" value={newName} maxLength={100} onChange={e=>setNewName(e.target.value)} placeholder="Collection name"/><button className="icon-button" aria-label="Create collection" disabled={!newName.trim()}><Check size={17}/></button></form>}</div>
      <nav aria-label="Main navigation">{([['facts',ScanText,'Facts',active?.facts],['relationships',Link2,'Relationships',active?.relationships],['documents',FileText,'Documents',active?.documents],['failures',AlertTriangle,'Failures & coverage',null]] as const).map(([v,Icon,title,count])=><button key={v} className={view===v?'nav active':'nav'} onClick={()=>navigate(v)}><Icon size={18}/><span>{title}</span>{count!=null&&<small>{count}</small>}</button>)}</nav>
      <div className="sidebar-note"><div className="status-dot"/>Evidence workspace<p>Claims stay connected to their original evidence.</p><span>{health.mode==='sample'?'Saved results':health.model||'Connecting…'}</span></div>
    </aside>
    <main>
      <header className="topbar"><span><span className="muted">Workspace</span><ChevronRight size={14}/>{active?.name||'Get started'}</span><a className="quiet" href="/docs" target="_blank" rel="noreferrer">API reference<ExternalLink size={14}/></a></header>
      <div className="main-content">
        <div className="page-title"><div><h1>{view==='failures'?'Failures & coverage':view[0].toUpperCase()+view.slice(1)}</h1><p>{subtitle}</p></div><div className="actions">{cid&&<a className="icon-button" aria-label="Export collection JSON" href={`/api/collections/${cid}/export`}><ArrowDownToLine size={18}/></a>}<button className="primary" disabled={!cid||busy||health.mode==='sample'} onClick={()=>fileRef.current?.click()}><Upload size={17}/>{busy?'Uploading…':'Upload PDFs'}</button><input ref={fileRef} type="file" accept="application/pdf,.pdf" multiple hidden onChange={e=>upload(e.target.files)}/></div></div>
        {error&&<div role="alert" className="error-banner"><AlertTriangle size={18}/><span>{error}</span><button className="icon-button" aria-label="Dismiss error" onClick={()=>setError('')}><X size={16}/></button></div>}
        {health.mode==='sample'&&<div className="notice">Saved results · These are previously generated pipeline outputs. Upload processing is disabled in this mode.</div>}
        {!cid?<div className="empty"><Layers size={36}/><h2>Start with your evidence.</h2><p>Create a collection, then upload PDFs to discover facts and compare their sources.</p><button className="primary" onClick={()=>setAdding(true)}><Plus size={16}/>Create a collection</button></div>:<>
          {(view==='facts'||view==='relationships')&&<div className="toolbar">{view==='facts'?<label className="search"><Search size={17}/><input aria-label="Search facts" placeholder="Search an entity, fact, or value…" value={query} onChange={e=>{setQuery(e.target.value);setOffset(0)}}/></label>:<span className="toolbar-label">Compare assertions across your sources</span>}<select aria-label="Filter results" value={filter} onChange={e=>{setFilter(e.target.value);setOffset(0)}}>{view==='facts'?<><option value="">Grounded facts</option><option value="quarantined">Quarantined claims</option></>:<><option value="">All relationships</option>{Object.entries(names).filter(([k])=>!['accepted','quarantined'].includes(k)).map(([k,v])=><option key={k} value={k}>{v}</option>)}</>}</select></div>}
          <div className="results-line" aria-live="polite"><span>{loading?'Loading…':`${total} ${view==='failures'?'reported issues':view}`}</span><button className="quiet" onClick={()=>setTick(x=>x+1)}><RefreshCw size={13}/>Refresh</button></div>
          {items.length===0&&!loading?<div className="empty"><ScanText size={36}/><h2>{docs.length?'No results here yet.':'Bring your documents together.'}</h2><p>{docs.length?'Check Documents for processing progress, or Failures & coverage for pages that need attention. Try clearing a filter if results are hidden.':'Upload two or more PDFs to begin comparing evidence. Your original sources will remain available alongside every fact.'}</p>{docs.length>0&&<button className="secondary" onClick={()=>navigate('documents')}>View documents<ArrowRight size={16}/></button>}</div>:null}
          {view==='facts'&&items.length>0&&<div className="fact-table"><div className="table-head"><span>Assertion</span><span>Value & context</span><span>Source</span></div>{items.map(r=><button className="fact-row" key={r.id} onClick={()=>inspect(r)}><div><span className="entity">{r.data.subject}</span><strong>{r.data.predicate}</strong><p>{r.data.assertion}</p></div><div><span className="value">{valueText(r.data)}</span><span className="context-line">{Object.entries(r.data.context||{}).filter(([,v])=>v).slice(0,3).map(([k,v])=>`${k.replaceAll('_',' ')}: ${v}`).join(' · ')||'Context not established'}</span></div><div className="source-cell"><FileText size={15}/><span>{docs.find(d=>d.id===r.document_id)?.filename||'PDF'}<small>PDF page {r.page}</small></span><ChevronRight size={16}/></div></button>)}</div>}
          {view==='relationships'&&<div className="relationship-list">{items.map(r=><button className="relationship-row" key={r.id} onClick={()=>inspect(r)}><div className="relationship-heading"><Badge label={r.label}/><span>{r.left?.data?.subject}</span><ChevronRight size={17}/></div><h3>{r.left?.data?.predicate}</h3><div className="pair"><span>{r.left&&valueText(r.left.data)}</span><Link2 size={16}/><span>{r.right&&valueText(r.right.data)}</span></div><p>{r.data.explanation}</p></button>)}</div>}
          {view==='documents'&&<div className="document-list">{items.map(d=><article key={d.id} className="document-row"><div className="file-icon"><FileText size={24}/></div><div className="document-info"><h3>{d.filename}</h3><p>{d.page_count} PDF pages · {d.parsed_pages} parsed · {d.extracted_pages} extracted · {d.facts} grounded facts</p><progress aria-label={`${d.filename} extraction coverage`} max={d.page_count} value={d.extracted_pages}/><JobSummary id={d.job_id} tick={tick}/></div><div className="document-actions"><Badge label={d.status}/>{health.mode!=='sample'&&['partial','failed'].includes(d.status)&&<button className="quiet" onClick={()=>resume(d)}><RefreshCw size={14}/>Resume</button>}<button className="quiet" onClick={()=>showSource(d.id,1)}>View source<ExternalLink size={14}/></button></div></article>)}</div>}
          {view==='failures'&&<div className="failure-list">{items.map(f=><article key={f.id} className="failure-row"><AlertTriangle size={19}/><div><div className="failure-heading"><Badge label={f.stage}/><span>{f.filename} · {f.page?`PDF page ${f.page}`:'document'}</span></div><h3>{f.message}</h3>{f.data.handling&&<p>{f.data.handling}</p>}{f.data.assertion&&<p>Candidate: {f.data.assertion}</p>}<button className="quiet" onClick={()=>showSource(f.document_id,f.page||1)}>Inspect source<ArrowRight size={14}/></button></div></article>)}</div>}
          {(view==='facts'||view==='relationships')&&total>50&&<div className="pagination"><button className="secondary" disabled={!offset} onClick={()=>setOffset(x=>Math.max(0,x-50))}><ArrowLeft size={15}/>Previous</button><span>{offset+1}–{Math.min(offset+50,total)} of {total}</span><button className="secondary" disabled={offset+50>=total} onClick={()=>setOffset(x=>x+50)}>Next<ArrowRight size={15}/></button></div>}
        </>}
        <footer>Source first. Conclusions second.<span>Fact Knowledge Layer / Superjoin assignment</span></footer>
      </div>
    </main>
    {detail&&<aside className="detail-panel" aria-label="Evidence detail"><div className="panel-header"><h2>{detail.left?'Compare evidence':'Inspect assertion'}</h2><button className="icon-button" aria-label="Close detail" onClick={()=>{setDetail(null);setSource(null)}}><X size={19}/></button></div>{detail.left?<><div className="verdict"><Badge label={detail.label}/><p>{detail.data.explanation}</p>{detail.data.calculation&&<dl>{Object.entries(detail.data.calculation).map(([k,v])=><div key={k}><dt>{k.replaceAll('_',' ')}</dt><dd>{String(v)}</dd></div>)}</dl>}</div><ClaimDetail fact={detail.left} showSource={showSource}/><ClaimDetail fact={detail.right} showSource={showSource}/></>:<ClaimDetail fact={detail} showSource={showSource}/>}</aside>}
    {source&&<SourcePanel source={source} close={()=>setSource(null)} navigate={showSource}/>}
  </div>
}

function JobSummary({id,tick}:{id:string,tick:number}){const [job,setJob]=useState<Obj|null>(null);useEffect(()=>{let valid=true;request(`/jobs/${id}`).then(j=>{if(valid)setJob(j)}).catch(()=>{});return()=>{valid=false}},[id,tick]);return job?.message?<p className="job-message">{job.message}</p>:null}
function ClaimDetail({fact,showSource}:{fact:Obj,showSource:(doc:string,page:number,anchors?:Obj[])=>void}){const c=fact.data;return <section className="claim-detail"><span className="entity">{c.subject}</span><h3>{c.predicate}</h3><p className="detail-value">{valueText(c)}</p><p>{c.assertion}</p><dl>{Object.entries(c.context||{}).filter(([,v])=>v).map(([k,v])=><div key={k}><dt>{k.replaceAll('_',' ')}</dt><dd>{String(v)}</dd></div>)}</dl>{c.rejection&&<div className="notice">Quarantined: {c.rejection}</div>}<div className="evidence-heading"><h4>Source evidence</h4><span>PDF page {fact.page}</span></div>{(c.anchors||[]).map((a:Obj,i:number)=><blockquote key={i}>{a.quote}</blockquote>)}<p className="source-name">{fact.document?.filename}</p>{Object.entries(c.context_anchors||{}).map(([name,anchors])=><div key={name}><small>{name}</small>{(anchors as Obj[]).map((a:Obj,i:number)=><button className="quiet" key={i} onClick={()=>showSource(fact.document_id,a.page,[a])}>Context evidence · PDF page {a.page}<ExternalLink size={13}/></button>)}</div>)}<button className="secondary" onClick={()=>showSource(fact.document_id,fact.page,[...(c.anchors||[]),...Object.values(c.context_anchors||{}).flat()])}><FileText size={16}/>Open highlighted page</button><p className="grounding-note">{c.grounding_limit||'This candidate has not passed source grounding.'}</p></section>}
function SourcePanel({source,close,navigate}:{source:Obj,close:()=>void,navigate:(doc:string,page:number,anchors?:Obj[])=>void}){
  const [zoom,setZoom]=useState(100);
  const dialog=useRef<HTMLDivElement>(null);
  useEffect(()=>setZoom(100),[source.docId,source.page]);
  const previousFocus=useRef(document.activeElement as HTMLElement);
  useEffect(()=>()=>previousFocus.current?.focus(),[]);
  function keyboard(e:React.KeyboardEvent){
    if(e.key==='Escape')close();
    if(e.key!=='Tab')return;
    const controls=Array.from(dialog.current?.querySelectorAll<HTMLElement>('button:not(:disabled),a,select,input')||[]);
    const first=controls[0],last=controls[controls.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus()}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus()}
  }
  return <div ref={dialog} className="source-overlay" role="dialog" aria-modal="true" aria-label="Source PDF page" onKeyDown={keyboard}>
    <div className="source-top"><div><h2>Original evidence</h2><span>Uploaded PDF · page {source.page} of {source.pageCount}</span></div>
      <div className="actions">
        <button className="icon-button" aria-label="Previous source page" disabled={source.page<=1} onClick={()=>navigate(source.docId,source.page-1,source.anchors)}><ArrowLeft size={17}/></button>
        <label>Page <input className="page-number" aria-label="Source page number" type="number" min={1} max={source.pageCount} key={source.page} defaultValue={source.page} onKeyDown={e=>{if(e.key==='Enter'){const n=Number(e.currentTarget.value);if(n>=1&&n<=source.pageCount)navigate(source.docId,n,source.anchors)}}}/></label>
        <button className="icon-button" aria-label="Next source page" disabled={source.page>=source.pageCount} onClick={()=>navigate(source.docId,source.page+1,source.anchors)}><ArrowRight size={17}/></button>
        <label>Zoom <select value={zoom} onChange={e=>setZoom(Number(e.target.value))}><option>100</option><option>150</option><option>200</option></select>%</label>
        <a className="secondary" href={`/api/documents/${source.docId}/source`} target="_blank" rel="noreferrer">Original PDF<ExternalLink size={14}/></a>
        <button autoFocus className="icon-button" aria-label="Close source" onClick={close}><X size={21}/></button>
      </div>
    </div>
    <div className="page-scroll"><div className="page-canvas" style={{width:`${zoom}%`}}>
      <img src={`/api/documents/${source.docId}/pages/${source.page}/image`} alt={`Original PDF page ${source.page}`}/>
      <svg viewBox={`0 0 ${source.width} ${source.height}`} aria-label="Evidence highlights">{source.anchors.filter((a:Obj)=>a.page===source.page).flatMap((a:Obj,i:number)=>(a.boxes||[]).map((b:number[],j:number)=><rect key={`${i}-${j}`} x={b[0]} y={b[1]} width={b[2]-b[0]} height={b[3]-b[1]}/>))}</svg>
    </div></div>
  </div>
}
