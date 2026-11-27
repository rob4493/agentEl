import React, {useEffect, useRef, useState} from 'react';
import {createRoot} from 'react-dom/client';
import fixture from '../../evaluation/fixtures/stagingEmail.json';
import {initialReader,editReceived,receiveAnalysis,reviewReader,currentReaderContext,analyzeReceivedEmail,canContinueToCompose} from './services/readerState';
import type {WritingStyle} from './services/readerState';
import {ApiError, postJson} from './services/api';
import {initialReview, changeDraft, validateDraft, approveDraft, rejectDraft, clearApproval, hasCurrentValidation, canCopyApprovedDraft} from './services/reviewState';
import {AudienceFields, AdditionalPreferences} from './components/preparationFields';
import {ServiceStatus} from './components/serviceStatus';
import {BetaAccess} from './components/betaAccess';
import {ComposeContext,AdaptationNotes} from './components/composeContext';
import {createComposeRequest,requestAdaptation} from './services/composeState';
import {DiscoverScreen, UnderstandScreen, ReviewSummary} from './components/journeyScreens';
import {StageProgress} from './components/stageProgress';
import {ReviewPanel} from './components/reviewPanel';
import {ChangeSummary} from './components/changeSummary';
import {WorkspaceIcon} from './components/workspaceIcon';
import type {AudienceContext, AmbiguityQuestion, AnalysisResult, ImprovementResult, ValidationResult, SemanticReviewResult, AdaptationResult} from './types/contracts';
import './styles.css';
import './discoverTheme.css';
import './composeTheme.css';
import './workspaceTheme.css';
const DemoScenarios=import.meta.env.DEV?React.lazy(()=>import('./components/demoScenarios')):null;

function App() {
  const [stage,setStage] = useState(0);
  const [reader,setReader] = useState(initialReader);
  const [receivedEmail,setReceivedEmail] = useState('');
  const screenRef = useRef<HTMLDivElement>(null);
  useEffect(()=>{screenRef.current?.focus();window.scrollTo({top:0});},[stage]);
  const [originalDraft,setOriginal] = useState('');
  const [audience,setAudience] = useState<AudienceContext>({...fixture.audience,communicationObjectives:'Make the message clear while preserving meaning',requiredDetails:''});
  const [questions,setQuestions] = useState<AmbiguityQuestion[]>([]);
  const [answers,setAnswers] = useState<Record<string,string>>({});
  const [analysis,setAnalysis] = useState<AnalysisResult|null>(null);
  const [improvedDraft,setImproved] = useState('');
  const [result,setResult] = useState<ImprovementResult|null>(null);
  const [adaptation,setAdaptation] = useState<AdaptationResult|null>(null);
  const [adaptationEdited,setAdaptationEdited] = useState(false);
  const requestLock = useRef(false);
  const [validation,setValidation] = useState<ValidationResult|null>(null);
  const [semantic,setSemantic] = useState<SemanticReviewResult|null>(null);
  const [review,setReview] = useState(initialReview);
  const [pendingAction,setPendingAction] = useState<'improve'|'adapt'|'validate'|'semantic'|'reader'|null>(null);
  const [message,setMessage] = useState('');
  const draftRef = useRef<HTMLTextAreaElement>(null);
  const clarificationRef = useRef<HTMLHeadingElement>(null);
  const busy=pendingAction!==null;
  const clarifications = questions.filter(question=>answers[question.ambiguityId]?.trim()).map(question=>({ambiguityId:question.ambiguityId,sourcePassage:question.sourcePassage,answer:answers[question.ambiguityId].trim()}));
  useEffect(()=>{if(stage===2&&questions.length) clarificationRef.current?.focus();},[questions.length,stage]);

  // Keep the original revision safeguards: every content/context edit invalidates all previous review results.
  function invalidate(rejected=false) {setReview(state=>rejected?rejectDraft(state):changeDraft(state));setValidation(null);setSemantic(null);setMessage('');}
  function discardOutput(rejected=false) {setAdaptation(null);setAdaptationEdited(false);setResult(null);setImproved('');setAnalysis(null);invalidate(rejected);}
  function changeAudience(next:AudienceContext) {setAudience(next);setQuestions([]);setAnswers({});discardOutput();}
  function changeSource(value:string) {setOriginal(value);setQuestions([]);setAnswers({});discardOutput();}
  function startAction(action:NonNullable<typeof pendingAction>) {if(requestLock.current)return false;requestLock.current=true;setPendingAction(action);return true;}
  function finishAction() {requestLock.current=false;setPendingAction(null);}
  async function analyzeReader() {
    if(!startAction('reader'))return;setReader(initialReader);discardOutput();
    try {setReader(receiveAnalysis(await analyzeReceivedEmail(receivedEmail)));}
    catch(error) {setReader({...initialReader,error:error instanceof Error?error.message:'Local backend unavailable. Please try again.'});}
    finally {finishAction();}
  }
  function changeIncoming(value:string) {setReceivedEmail(value);setReader(state=>editReceived(state));setQuestions([]);setAnswers({});discardOutput();}
  function chooseReader(style:WritingStyle|null) {setReader(state=>reviewReader(state,style));discardOutput();}
  const readerContext=currentReaderContext(receivedEmail,reader);
  const readerConfirmed=canContinueToCompose(reader);
  function navigateStage(next:number) {if(stage===1&&next>=2&&!readerConfirmed)return;setStage(next);}
  function reportError(error:unknown) {
    if(error instanceof ApiError && error.questions.length) setQuestions(error.questions);
    setMessage(error instanceof Error ? error.message : 'Backend unavailable.');
  }
  async function improve() {
    if(!startAction('improve'))return;discardOutput();
    try {
      const request = {originalDraft,audience,clarifications,communicationMode:'shared'};
      // Preflight is deterministic; the server independently enforces clarification before a single generation call.
      const checked = await postJson<AnalysisResult>('analyze',request);
      setAnalysis(checked);
      if(checked.ambiguities.length) {setQuestions(current=>[...current,...checked.ambiguities.filter(question=>!current.some(item=>item.ambiguityId===question.ambiguityId))]);setMessage('Clarify the action or deadline, then prepare and improve again.');return;}
      const next = await postJson<ImprovementResult>('improve',request);
      setResult(next);setAnalysis(next.analysis);setImproved(next.improvedDraft);setValidation(next.validation);setReview(state=>validateDraft(state));
    } catch(error) {reportError(error);}
    finally {finishAction();}
  }
  async function adaptResponse() {
    if(!startAction('adapt'))return;
    try {
      const request=createComposeRequest(receivedEmail,originalDraft,reader,audience,clarifications);
      discardOutput();
      const next=await requestAdaptation(request);
      setAdaptation(next);setAdaptationEdited(false);setResult(next);setAnalysis(next.analysis);setImproved(next.improvedDraft);setValidation(next.validation);setReview(state=>validateDraft(state));
      setMessage('Adaptation ready. Your original response is unchanged. Continue to Review, check the full message and decide what to use.');
    } catch(error) {reportError(error);}
    finally {finishAction();}
  }
  async function revalidate() {
    if(!startAction('validate'))return;invalidate();
    try {setValidation(await postJson<ValidationResult>(adaptation?'adaptResponse/validate':'validate',{originalDraft,improvedDraft,audience,clarifications,...(adaptation?{receivedEmail}:{})}));setReview(state=>validateDraft(state));}
    catch(error) {reportError(error);}
    finally {finishAction();}
  }
  async function requestSemanticReview() {
    if(!startAction('semantic'))return;setSemantic(null);setMessage('');setReview(state=>clearApproval(state));
    try {setSemantic(await postJson<SemanticReviewResult>('review',{originalDraft,improvedDraft,audience,clarifications}));}
    catch(error) {reportError(error);}
    finally {finishAction();}
  }
  async function copyApproved() {
    // Guard the handler as well as the button, so only the currently validated and explicitly approved revision is copied.
    if(busy||!result||!validation||!improvedDraft.trim()||!canCopyApprovedDraft(review)) return;
    try {await navigator.clipboard.writeText(improvedDraft);setMessage('Approved draft copied.');}
    catch {setMessage('Clipboard unavailable. Select and copy the approved draft manually.');}
  }
  const canApprove=Boolean(result&&validation&&improvedDraft.trim()&&!busy&&hasCurrentValidation(review)&&!review.approved);
  const canCopy=Boolean(result&&validation&&improvedDraft.trim()&&!busy&&canCopyApprovedDraft(review));
  const draftActions = <section className="workflowActions panel" aria-label="Draft actions"><div className="actionGroup"><button className="button secondaryButton" disabled={busy||!result} onClick={()=>{setStage(2);requestAnimationFrame(()=>draftRef.current?.focus());}}><WorkspaceIcon name="edit"/>Edit</button><button className="button secondaryButton" disabled={busy||!result} onClick={()=>{setStage(2);void (adaptation?adaptResponse():improve());}}><WorkspaceIcon name="refresh"/>Regenerate</button><button className="button secondaryButton" disabled={busy||!result||!improvedDraft.trim()} onClick={revalidate}>{pendingAction==='validate'?<span className="spinner"/>:<WorkspaceIcon name="shield"/>}{pendingAction==='validate'?'Revalidating…':'Revalidate'}</button><button className="button secondaryButton rejectButton" disabled={busy||!result} onClick={()=>{discardOutput(true);setMessage('Draft rejected. Your original and audience context are retained.');}}><WorkspaceIcon name="close"/>Reject</button></div><div className="actionGroup approvalActions"><button className="button primaryButton" disabled={!canApprove} onClick={()=>setReview(state=>approveDraft(state))}><WorkspaceIcon name="check"/>{review.approved?'Approved':'Approve'}</button><button className="button secondaryButton" disabled={!canCopy} onClick={copyApproved}><WorkspaceIcon name="copy"/>Copy approved</button></div><p className="approvalHint">Approval applies to this exact draft. Any edit or regeneration requires fresh review.</p></section>;
  const reviewPanel = <ReviewPanel analysis={analysis} questions={questions} answers={answers} result={result} validation={validation} semantic={semantic} busy={busy} reviewing={pendingAction==='semantic'} onSemanticReview={requestSemanticReview}/>;
  const changeSummary = <ChangeSummary changes={validation?.changeDetails||[]} hasResult={Boolean(result)} hasValidation={Boolean(validation)} isMock={Boolean(result?.isMock)}/>;
  return <div className={`appShell discoverActive unifiedWorkspace ${stage===1?'readerActive':''}`}>
    <header className="appHeader"><button className="brand brandButton" disabled={busy} onClick={()=>setStage(0)} aria-label="Ritmo — Discover"><img src="/brand/ritmoMonogram.svg" alt=""/><span className="brandName">Ritmo</span></button><span className="headerDivider"/><div className="workspaceName">Communication Workspace<small>Communication learning platform</small></div><details className="discoverService"><summary>Service status</summary><ServiceStatus/></details></header>
    <main className="workspace">
      <StageProgress stage={stage} disabled={busy} blockedStages={stage===1&&!readerConfirmed?[2,3]:[]} onNavigate={navigateStage}/>
      <div ref={screenRef} tabIndex={-1} className="screenContent" aria-label={['Discover','Understand the reader','Compose and adapt','Review and summary'][stage]}>
      {stage===0&&<DiscoverScreen onStart={()=>setStage(1)}/>}
      {stage===1&&<><UnderstandScreen receivedEmail={receivedEmail} reader={reader} analyzing={pendingAction==='reader'} disabled={busy} onAnalyze={analyzeReader} onReview={chooseReader} onChange={changeIncoming}/>{DemoScenarios&&<React.Suspense fallback={null}><DemoScenarios disabled={busy} hasDraft={originalDraft.length>0} onIncoming={changeIncoming} onDraft={value=>{if(!originalDraft.length)changeSource(value);}}/></React.Suspense>}</>}
      {stage===2&&<>
      <div className="composeWorkspace">
        <div className="editorColumn">
<section className="workspaceIntro composeIntro" id="improve"><div><p className="eyebrow">STAGE 3 · COMPOSE</p><h1>Your response.<br/><span>Your meaning.</span></h1><p>Write what you want to say, then adapt how it connects with your reader.</p></div><span className="modeBadge">English · Review required</span></section>
          <ComposeContext receivedEmail={receivedEmail} selectedStyle={readerContext?.selectedStyle||null} modelStyle={reader.outdated?null:reader.result?.primaryStyle||null} disabled={busy} onSelect={chooseReader}/>
          {DemoScenarios&&<React.Suspense fallback={null}><DemoScenarios disabled={busy} hasDraft={originalDraft.length>0} onIncoming={changeIncoming} onDraft={value=>{if(!originalDraft.length)changeSource(value);}}/></React.Suspense>}
          <details className="audienceCard panel composePreferences" id="prepare"><summary>Audience and writing preferences</summary><AudienceFields audience={audience} disabled={busy} onChange={changeAudience}/></details>
          {questions.length>0&&<section className="clarificationCard panel" id="clarifications"><div className="clarificationHeading"><WorkspaceIcon name="alert"/><div><h2 ref={clarificationRef} tabIndex={-1}>Clarify before generation</h2><p>Your answers are sender-confirmed context. The original draft stays intact.</p></div></div>{questions.map((question,index)=><label key={question.ambiguityId}><span className="questionNumber">{index+1}.</span> {question.question}<blockquote>{question.sourcePassage}</blockquote><input disabled={busy} maxLength={1000} value={answers[question.ambiguityId]||''} onChange={event=>{setAnswers({...answers,[question.ambiguityId]:event.target.value});discardOutput();}}/></label>)}</section>}
          <div className="draftGrid">
            <section className="draftPanel panel"><div className="draftHeading"><WorkspaceIcon name="document"/><h2>Your original response</h2><span className="inputBadge">Input</span></div><label className="visuallyHidden" htmlFor="original">Your original response</label><div className="draftInput"><textarea id="original" disabled={busy} maxLength={20000} value={originalDraft} onChange={event=>changeSource(event.target.value)} placeholder="Write your response here. Include the facts, questions and commitments you want to preserve…" spellCheck/></div><div className="draftFooter"><button className="textButton" disabled={busy||originalDraft.length>0} title="Examples load only into an empty response editor" onClick={()=>{if(!originalDraft.length)changeSource(fixture.originalDraft);}}>Load example</button><span className="characterCount">{originalDraft.length.toLocaleString()} / 20,000</span></div><AdditionalPreferences audience={audience} disabled={busy} onChange={changeAudience}/><div className="generateRow"><p>Your original response stays unchanged.</p><button className="button secondaryButton" disabled={busy||!originalDraft.trim()||!audience.group.trim()} onClick={improve}>Improve clarity only</button><button className="button primaryButton" disabled={busy||!originalDraft.trim()||!readerContext?.selectedStyle||!audience.group.trim()} onClick={adaptResponse}>{pendingAction==='adapt'?<span className="spinner"/>:<WorkspaceIcon name="spark"/>}{pendingAction==='adapt'?'Adapting…':'Adapt my response'}</button></div></section>
            <section className={`draftPanel improvedPanel panel ${result?'hasResult':''}`}><div className="draftHeading"><WorkspaceIcon name="spark"/><h2>{adaptation?'Suggested adaptation':'Suggested response'}</h2><span className={`outputBadge ${result?.isMock?'mockBadge':''}`}>{result?(adaptationEdited?'Edited by you':result.isMock?'Mock demo':'AI generated'):'Awaiting draft'}</span></div><label className="visuallyHidden" htmlFor="improved">Improved message — review and edit</label><div className="draftInput"><textarea ref={draftRef} id="improved" disabled={busy||!result} maxLength={20000} value={improvedDraft} onChange={event=>{setImproved(event.target.value);setAdaptationEdited(true);invalidate();}} placeholder={(pendingAction==='improve'||pendingAction==='adapt')?'':'Your suggested message will appear here.\n\nReview every fact, uncertainty, deadline and requested action before approving.'} spellCheck/>{(pendingAction==='improve'||pendingAction==='adapt')&&<div className="generatingState" role="status"><span className="spinner"/><strong>{pendingAction==='adapt'?'Adapting your response':'Improving clarity'}</strong><span>Facts and findings will be ready for your review.</span></div>}</div><div className="draftFooter"><span className={`draftState ${review.approved?'isApproved':''}`}>{review.approved?<><WorkspaceIcon name="check"/>Approved by you</>:validation?'Checks completed · Human review required':result?'Edited · Revalidate before approval':'Your review comes next'}</span><span className="characterCount">{improvedDraft.length.toLocaleString()} / 20,000</span></div><div className="outputNotice"><WorkspaceIcon name="info"/><p>{result?.isMock?'Mock demonstration: paragraph spacing only. This is not an AI rewrite.':'AI drafts and automated checks can miss or change meaning. Your approval is always required.'}</p></div></section>
          </div>
          <div className="workspaceMessage" role="status" aria-live="polite">{message&&<p className="inlineNotice"><WorkspaceIcon name="info"/>{message}</p>}</div>
          {adaptation&&<AdaptationNotes result={adaptation} edited={adaptationEdited}/>}
          {changeSummary}
          {draftActions}
          {result&&<details className="processingDetails"><summary>Processing details</summary><p>Preparation: {result.processingMilliseconds.preparation} ms · Generation: {(result.processingMilliseconds.generation/1000).toFixed(1)} s · Deterministic review: {result.processingMilliseconds.deterministicReview} ms</p></details>}
        </div>
        <details className="composeChecks"><summary>Checks and preservation warnings</summary>{reviewPanel}</details>
      </div>
      </>}
      {stage===3&&<ReviewSummary originalDraft={originalDraft} improvedDraft={improvedDraft} hasResult={Boolean(result)} hasValidation={Boolean(validation)} targetStyle={adaptation?.targetStyle} factCount={analysis?.facts.length||0} findingCount={validation?.findings.length||0} isMock={Boolean(result?.isMock)} comparison={changeSummary} findings={<div onClick={event=>{if((event.target as HTMLElement).closest('a[href="#clarifications"]')) {event.preventDefault();setStage(2);}}}>{reviewPanel}</div>} actions={<><div className="workspaceMessage" role="status">{message}</div>{draftActions}</>}/>}
      </div>
      {stage>0&&<nav className="journeyNavigation" aria-label="Stage navigation"><button className="button secondaryButton" disabled={busy} onClick={()=>setStage(stage-1)}>← Back to {['Discover','Understand','Compose'][stage-1]}</button>{stage<3&&<button className="button primaryButton" disabled={busy||(stage===1&&!readerConfirmed)} onClick={()=>navigateStage(stage+1)}>Continue to {stage===1?'Compose':'Review'} →</button>}</nav>}
      <footer className="workspaceFooter"><span>Ritmo · Human-centered communication</span><span>Independent prototype · No United Nations affiliation or endorsement · No email sending</span></footer>
    </main>
  </div>;
}
createRoot(document.getElementById('root')!).render(<React.StrictMode><BetaAccess><App/></BetaAccess></React.StrictMode>);
