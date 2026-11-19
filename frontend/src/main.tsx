import React, {useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import fixture from '../../evaluation/fixtures/stagingEmail.json';
import {ApiError, postJson} from './services/api';
import {initialReview, changeDraft, validateDraft, approveDraft, rejectDraft, clearApproval} from './services/reviewState';
import {FindingList} from './components/findingList';
import type {AudienceContext, AmbiguityQuestion, AnalysisResult, ImprovementResult, ValidationResult, SemanticReviewResult} from './types/contracts';
import './styles.css';

function App() {
  const [originalDraft,setOriginal] = useState('');
  const [audience,setAudience] = useState<AudienceContext>({...fixture.audience,communicationObjectives:'Make the message clear while preserving meaning',requiredDetails:''});
  const [questions,setQuestions] = useState<AmbiguityQuestion[]>([]);
  const [answers,setAnswers] = useState<Record<string,string>>({});
  const [analysis,setAnalysis] = useState<AnalysisResult|null>(null);
  const [improvedDraft,setImproved] = useState('');
  const [result,setResult] = useState<ImprovementResult|null>(null);
  const [validation,setValidation] = useState<ValidationResult|null>(null);
  const [semantic,setSemantic] = useState<SemanticReviewResult|null>(null);
  const [review,setReview] = useState(initialReview);
  const [busy,setBusy] = useState(false);
  const [message,setMessage] = useState('');
  const draftRef = useRef<HTMLTextAreaElement>(null);
  const clarifications = questions.filter(question=>answers[question.ambiguityId]?.trim()).map(question=>({ambiguityId:question.ambiguityId,sourcePassage:question.sourcePassage,answer:answers[question.ambiguityId].trim()}));
  function invalidate(rejected=false) {setReview(state=>rejected?rejectDraft(state):changeDraft(state));setValidation(null);setSemantic(null);setMessage('');}
  function discardOutput(rejected=false) {setResult(null);setImproved('');setAnalysis(null);invalidate(rejected);}
  function changeSource(value:string) {setOriginal(value);setQuestions([]);setAnswers({});discardOutput();}
  function reportError(error:unknown) {
    if(error instanceof ApiError && error.questions.length) setQuestions(error.questions);
    setMessage(error instanceof Error ? error.message : 'Backend unavailable.');
  }
  async function improve() {
    setBusy(true);discardOutput();
    try {
      const request = {originalDraft,audience,clarifications,communicationMode:'shared'};
      // This deterministic preflight never invokes a model. The backend independently enforces the same gate.
      const checked = await postJson<AnalysisResult>('analyze',request);
      setAnalysis(checked);
      if(checked.ambiguities.length) {setQuestions(current=>[...current,...checked.ambiguities.filter(question=>!current.some(item=>item.ambiguityId===question.ambiguityId))]);setMessage('Please clarify the action or deadline below, then confirm and improve again.');return;}
      const next = await postJson<ImprovementResult>('improve',request);
      setResult(next);setAnalysis(next.analysis);setImproved(next.improvedDraft);setValidation(next.validation);setReview(state=>validateDraft(state));
    } catch(error) {reportError(error);}
    finally {setBusy(false);}
  }
  async function revalidate() {
    setBusy(true);invalidate();
    try {setValidation(await postJson<ValidationResult>('validate',{originalDraft,improvedDraft,audience,clarifications}));setReview(state=>validateDraft(state));}
    catch(error) {reportError(error);}
    finally {setBusy(false);}
  }
  async function requestSemanticReview() {
    setBusy(true);setSemantic(null);setMessage('');setReview(state=>clearApproval(state));
    try {setSemantic(await postJson<SemanticReviewResult>('review',{originalDraft,improvedDraft,audience,clarifications}));}
    catch(error) {reportError(error);}
    finally {setBusy(false);}
  }
  const wordingFindings = validation?.findings.filter(finding=>['sourcePassageChanged','unsupportedOrReworded'].includes(finding.category))||[];
  const contentFindings = validation?.findings.filter(finding=>!['sourcePassageChanged','unsupportedOrReworded'].includes(finding.category))||[];
  return <div className="shell">
    <header><a className="brand" href="#">◈ Agent EL</a><span className="pill">Mode B · Shared Communication</span></header>
    <main>
      <div className="intro"><p className="eyebrow">HUMAN-CENTERED COMMUNICATION</p><h1>Different backgrounds.<br/>One shared message.</h1><p>Make your English email clearer for everyone, while keeping the details that matter.</p></div>
      <ol className="stages" aria-label="Communication workflow"><li>Confirm</li><li>Improve and Compare</li><li>Decide</li></ol>
      <aside className="notice">{result?.isMock ? 'Mock demonstration · Paragraph spacing only, not an AI rewrite.' : result ? 'AI-generated draft · Review every fact before approval.' : 'Local workspace · Mock demonstrations are labeled when used.'} Checks and optional AI review cannot guarantee meaning preservation.</aside>
      <section className="audience card"><h2>01 / Confirm</h2><p>Describe the shared audience and your goals. Use what you know; a role or nationality does not establish ability, language proficiency or personality.</p><div className="settings">{([
        ['group','Who the group includes',500],['technicalBackground','General technical background',1000],['communicationObjectives','Communication objectives',1000],['preferences','Known communication preferences',1000],['requiredDetails','Required details or terminology',2000],
      ] as const).map(([key,label,limit])=><label key={key}>{label}<input disabled={busy} maxLength={limit} value={audience[key]} onChange={event=>{setAudience({...audience,[key]:event.target.value});discardOutput();}}/></label>)}</div></section>
      <h2 className="stageHeading">02 / Improve and Compare</h2>
      <div className="drafts">
        <section className="card"><div className="sectionHead"><h2>Original English email</h2><button className="quiet" disabled={busy} onClick={()=>changeSource(fixture.originalDraft)}>Load example</button></div><label htmlFor="original">Paste your English email</label><textarea id="original" disabled={busy} maxLength={20000} value={originalDraft} onChange={event=>changeSource(event.target.value)} placeholder="Start with the message you want to share…"/><div className="sectionHead"><small>{originalDraft.length.toLocaleString()} / 20,000 characters</small><button disabled={busy||!originalDraft.trim()||!audience.group.trim()} onClick={improve}>{busy?'Working…':'Confirm & improve →'}</button></div></section>
        <section className="card"><div className="sectionHead"><h2>Improved draft</h2><span className="pill">{result ? (result.isMock?'MOCK DEMONSTRATION':'Ollama · AI-generated draft') : 'Awaiting draft'}</span></div><label htmlFor="improved">Review and edit before approval</label><textarea ref={draftRef} id="improved" disabled={busy||!result} maxLength={20000} value={improvedDraft} onChange={event=>{setImproved(event.target.value);invalidate();}} placeholder="Your draft will appear here for comparison."/><small>{review.approved?'Approved by you':validation?'Deterministic checks completed · Human review required':'Validation required after any change'}</small>{result&&<p><small>Preparation: {result.processingMilliseconds.preparation} ms · Generation: {(result.processingMilliseconds.generation/1000).toFixed(1)} s · Deterministic review: {result.processingMilliseconds.deterministicReview} ms</small></p>}</section>
      </div>
      <div role="status" aria-live="polite" className="message">{message}</div>
      {questions.length>0&&<section className="card clarification"><h2>Clarify before generation</h2><p>These phrases may affect actions, deadlines or approval. Your answers are sender-confirmed context; source text is retained.</p>{questions.map(question=><label key={question.ambiguityId}><blockquote>{question.sourcePassage}</blockquote>{question.question}<input disabled={busy} maxLength={1000} value={answers[question.ambiguityId]||''} onChange={event=>{setAnswers({...answers,[question.ambiguityId]:event.target.value});discardOutput();}}/></label>)}</section>}
      {result&&<section className="card decision"><h2>03 / Decide</h2><p>Inspect the comparison and warnings. You can edit, reject, regenerate, or explicitly approve this exact draft.</p><div className="actions"><button disabled={busy} onClick={()=>draftRef.current?.focus()}>Edit draft</button><button disabled={busy||!improvedDraft.trim()} onClick={revalidate}>Revalidate after editing</button><button disabled={busy} onClick={improve}>Regenerate draft</button><button className="quiet" disabled={busy} onClick={()=>{discardOutput(true);setMessage('Draft rejected. Your source and audience context are retained for another attempt.');}}>Reject draft</button><button disabled={busy||!validation||review.approved} onClick={()=>setReview(state=>approveDraft(state))}>I reviewed & approve</button><button disabled={!review.approved||busy} onClick={async()=>{try{await navigator.clipboard.writeText(improvedDraft);setMessage('Approved draft copied.');}catch{setMessage('Clipboard unavailable. Select and copy the approved draft manually.');}}}>Copy approved draft</button></div><small>Approval is your judgment. Every source, context or draft edit revokes previous approval and checks. Nothing is sent.</small></section>}
      {(result||analysis)&&<div className="reviewGrid"><section className="card"><h2>Source facts and confirmed context</h2><p>{analysis?.limitations.join(' ')}</p><details><summary>Inspect {analysis?.facts.length||0} source passages</summary>{analysis?.facts.map(fact=><article key={fact.factId}><span className="factLabel">{fact.categories.join(', ')} · {fact.origin}</span><blockquote>{fact.sourcePassage}</blockquote></article>)}</details>{!!analysis?.confirmedContext.length&&<details open><summary>Sender-confirmed context</summary>{analysis.confirmedContext.map(fact=><article key={fact.factId}><p>{fact.description}</p><small>Evidence source: {fact.evidenceSource}</small><blockquote>{fact.sourcePassage}</blockquote></article>)}</details>}{validation&&<details open><summary>Observable communication changes</summary>{validation.changeDetails.length?validation.changeDetails.map((change,index)=><article key={index}><strong>{change.whatChanged}</strong><p>{change.whyHelpful}</p><small>Source evidence</small><blockquote>{change.sourceEvidence}</blockquote>{change.generatedEvidence&&<><small>Generated evidence</small><blockquote>{change.generatedEvidence}</blockquote></>}<small>Requires human review · Observable comparison, not model reasoning</small></article>):<p>No selected structural or important wording difference detected. Review the full comparison.</p>}</details>}</section>
      <section className="card"><h2>Meaning & review</h2><p className="notice">{validation?.limitation||'Draft changed. Revalidate before approval. Previous findings and explanations are invalid.'}</p>{validation&&<><h3>Deterministic content findings ({contentFindings.length})</h3>{contentFindings.length?<FindingList findings={contentFindings}/>:<p>No targeted content warning was found. Checks are limited and may miss errors.</p>}<details><summary>Exact wording checks ({wordingFindings.length})</summary><p>Legitimate paraphrases also trigger these conservative warnings.</p><FindingList findings={wordingFindings}/></details></>}{result&&<div className="semantic"><h3>Optional AI meaning review (experimental)</h3><p>One extra local model call. The same model can repeat or miss errors; this is not an independent accuracy check.</p><button disabled={busy||!validation||result.isMock} onClick={requestSemanticReview}>Request AI meaning review</button>{result.isMock&&<p>Unavailable in mock mode.</p>}{semantic&&<><p>AI review {semantic.reviewStatus} · {(semantic.elapsedMilliseconds/1000).toFixed(1)} s</p>{semantic.limitations.map(text=><p key={text}>{text}</p>)}<FindingList findings={semantic.findings}/></>}</div>}</section></div>}
      <footer>Independent prototype · No United Nations affiliation or endorsement. Drafts are not stored by the application. Mode C personalization is planned.</footer>
    </main>
  </div>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>);
