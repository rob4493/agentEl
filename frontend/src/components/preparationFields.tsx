import type {AudienceContext} from '../types/contracts';

export const audienceSuggestions=['Mixed professional group','Technical team','Management / leadership','Nontechnical audience'];
export const goalSuggestions=['Share an update','Request feedback','Request a decision','Explain an issue'];
type ContextProps={audience:AudienceContext;disabled:boolean;onChange:(next:AudienceContext)=>void};

// Suggestions write into the same editable field; no hidden category can override custom text.
export function updateContext(audience:AudienceContext,key:keyof AudienceContext,value:string):AudienceContext {
  return {...audience,[key]:value};
}

export function AudienceFields({audience,disabled,onChange}:ContextProps) {
  return <div className="audienceBody primaryFields">{([
    ['group','Audience',500,audienceSuggestions],
    ['communicationObjectives','Communication goal',1000,goalSuggestions],
  ] as const).map(([key,label,limit,suggestions])=><div key={key}><label htmlFor={key}>{label}</label><div className="suggestionGroup" role="group" aria-label={`${label} suggestions`}>{suggestions.map(value=><button type="button" className="suggestionChip" disabled={disabled} aria-pressed={audience[key]===value} key={value} onClick={()=>onChange(updateContext(audience,key,value))}>{value}</button>)}</div><input id={key} aria-label={label} disabled={disabled} maxLength={limit} value={audience[key]} onChange={event=>onChange(updateContext(audience,key,event.target.value))}/><p className="fieldHint">Choose a suggestion or write your own {key==='group'?'audience description':'objective'}.</p></div>)}</div>;
}

export function AdditionalPreferences({audience,disabled,onChange}:ContextProps) {
  return <details className="audienceExtras preparationExtras"><summary>Additional preferences (optional)<small>Technical background, communication preferences and details to preserve</small></summary><div className="extraFields">{([
    ['technicalBackground','General technical background',1000],
    ['preferences','Known communication preferences',1000],
    ['requiredDetails','Details Ritmo must preserve (optional)',2000],
  ] as const).map(([key,label,limit])=><label key={key}>{label}<input disabled={disabled} maxLength={limit} value={audience[key]} aria-describedby={key==='requiredDetails'?'preservationHelp':undefined} onChange={event=>onChange(updateContext(audience,key,event.target.value))}/></label>)}</div><div className="fieldHint" id="preservationHelp"><p>Highlight specific details or wording that should not be removed or changed. Ritmo still reviews the entire original message for important information.</p><p><strong>Example only:</strong> Keep software version 2.4.1, clarify that deployment is in staging rather than production, and preserve the unresolved CSV export timeout issue.</p></div><p className="fieldHint">A role, nationality or location does not establish ability, English proficiency or personality.</p></details>;
}
