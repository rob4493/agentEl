import {useState} from 'react';
import examples from '../dev/composeExamples.json';

export default function DemoScenarios({disabled,hasDraft,onIncoming,onDraft}:{disabled:boolean;hasDraft:boolean;onIncoming:(value:string)=>void;onDraft:(value:string)=>void}) {
  const [id,setId]=useState(examples.scenarios[0].id);
  const example=examples.scenarios.find(x=>x.id===id)!;
  return <details className="panel composeDemo"><summary>Development-only demonstration examples</summary><p className="fieldHint">{examples.notice}</p><label>Example<select value={id} disabled={disabled} onChange={event=>setId(event.target.value)}>{examples.scenarios.map(x=><option key={x.id} value={x.id}>{x.title}</option>)}</select></label><p>Intended demonstration style: <strong>{example.intendedStyle}</strong>. Select it yourself using the normal reader-style controls; loading does not analyze or confirm a style.</p><div className="actionGroup"><button className="button secondaryButton" disabled={disabled} onClick={()=>onIncoming(example.receivedEmail)}>Load incoming example</button><button className="button secondaryButton" disabled={disabled||hasDraft} onClick={()=>{if(!hasDraft)onDraft(example.starterDraft);}}>Use synthetic starter response</button></div>{hasDraft&&<p className="fieldHint">Your response is retained. A starter can only be loaded into an empty editor.</p>}</details>;
}
