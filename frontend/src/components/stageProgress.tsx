const stages=[{name:'Discover',description:'Communication patterns'},{name:'Understand',description:'The received email'},{name:'Compose',description:'Your shared message'},{name:'Review',description:'Evidence and your decision'}];

export function StageProgress({stage,disabled,onNavigate,blockedStages=[]}:{stage:number;disabled:boolean;onNavigate:(stage:number)=>void;blockedStages?:number[]}) {
  // Position is navigation state only: visiting a stage never marks analysis or review complete.
  return <nav className="stageProgress" aria-label="Communication journey">{stages.map((item,index)=><button type="button" disabled={disabled||blockedStages.includes(index)} className={`stageStep ${stage===index?'isActive':''}`} aria-current={stage===index?'step':undefined} onClick={()=>onNavigate(index)} key={item.name}><span className="stageNumber">{index+1}</span><span><strong>{item.name}</strong><small>{item.description}</small></span></button>)}</nav>;
}
