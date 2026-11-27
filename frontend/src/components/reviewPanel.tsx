import type {AnalysisResult,AmbiguityQuestion,ImprovementResult,SemanticReviewResult,ValidationResult} from '../types/contracts';
import {FindingList} from './findingList';
import {WorkspaceIcon} from './workspaceIcon';

function readableLabel(value:string) {return value.replace(/([a-z])([A-Z])/g,'$1 $2');}

interface ReviewPanelProps {
  analysis:AnalysisResult|null;
  questions:AmbiguityQuestion[];
  answers:Record<string,string>;
  result:ImprovementResult|null;
  validation:ValidationResult|null;
  semantic:SemanticReviewResult|null;
  busy:boolean;
  reviewing:boolean;
  onSemanticReview:()=>void;
}

export function ReviewPanel({analysis,questions,answers,result,validation,semantic,busy,reviewing,onSemanticReview}:ReviewPanelProps) {
  const unresolved=questions.filter(question=>!answers[question.ambiguityId]?.trim());
  const wording=validation?.findings.filter(finding=>['sourcePassageChanged','unsupportedOrReworded'].includes(finding.category))||[];
  const content=validation?.findings.filter(finding=>!['sourcePassageChanged','unsupportedOrReworded'].includes(finding.category))||[];
  return <aside className="reviewPanel panel" id="review" aria-labelledby="reviewTitle">
    <div className="reviewHeading"><span className="iconTile"><WorkspaceIcon name="shield"/></span><div><h2 id="reviewTitle">Review & validation</h2><p>Check the evidence. You make the decision.</p></div></div>
    {content.length>0&&<a className="reviewAlert" href="#validationFindings"><WorkspaceIcon name="alert"/><span>{content.length} content {content.length===1?'warning needs':'warnings need'} your review.</span></a>}
    {result&&!validation&&<p className="inlineNotice warningNotice">Draft changed. Previous checks and approval are invalid. Revalidate before approving.</p>}
    <details className="reviewSection factsSection"><summary><WorkspaceIcon name="document"/><span><strong>Extracted facts</strong><small>Source passages and confirmed context</small></span><span className="countBadge">{analysis?analysis.facts.length:'—'}</span><WorkspaceIcon name="chevron" className="disclosureIcon"/></summary><div className="reviewBody">{analysis?<><p>{analysis.limitations.join(' ')}</p>{analysis.facts.map(fact=><article key={fact.factId}><span className="evidenceLabel">{fact.categories.map(readableLabel).join(' · ')} · {readableLabel(fact.origin)}</span><blockquote>{fact.sourcePassage}</blockquote></article>)}{!!analysis.confirmedContext.length&&<><h3>Sender-confirmed context</h3>{analysis.confirmedContext.map(fact=><article key={fact.factId}><p>{fact.description}</p><span className="evidenceLabel">{fact.evidenceSource==='clarification'?'Your clarification':'Your audience details'}</span><blockquote>{fact.sourcePassage}</blockquote></article>)}</>}</>:<p>Source passages will appear after you prepare and improve a draft.</p>}</div></details>
    <details className="reviewSection ambiguitySection" open={unresolved.length>0}><summary><WorkspaceIcon name="alert"/><span><strong>Ambiguities</strong><small>Actions, deadlines and approval details</small></span><span className="countBadge">{questions.length||analysis?unresolved.length:'—'}</span><WorkspaceIcon name="chevron" className="disclosureIcon"/></summary><div className="reviewBody">{unresolved.length?<><p>Clarify these details before generation; the agent will not guess.</p>{unresolved.map(question=><article key={question.ambiguityId}><blockquote>{question.sourcePassage}</blockquote><p>{question.question}</p></article>)}<a className="textLink" href="#clarifications">Answer clarification questions →</a></>:questions.length?<p>{questions.length} sender {questions.length===1?'clarification is':'clarifications are'} retained with the draft. Reconfirm after changing context.</p>:<p>{analysis?'No selected ambiguity rule was triggered. Other unclear wording can still require your judgment.':'Selected material ambiguity checks run before generation.'}</p>}</div></details>
    <details className="reviewSection validationSection" id="validationFindings" open={content.length>0}><summary><WorkspaceIcon name="shield"/><span><strong>Validation findings</strong><small>{validation?'Deterministic checks · Review required':'Checks pending or invalidated'}</small></span><span className="countBadge">{validation?validation.findings.length:'—'}</span><WorkspaceIcon name="chevron" className="disclosureIcon"/></summary><div className="reviewBody">{validation?<><p>{validation.limitation}</p><h3>Content warnings ({content.length})</h3>{content.length?<FindingList findings={content}/>:<p>No targeted content warning was found. Limited checks can miss important changes.</p>}<details className="wordingDetails"><summary>Exact wording checks ({wording.length})</summary><p>Legitimate paraphrases also trigger these conservative warnings.</p><FindingList findings={wording}/></details></>:<p>Generate a draft, or revalidate after editing, to see current findings. Previous findings do not apply to a changed draft.</p>}</div></details>
    <details className="reviewSection semanticSection" open={Boolean(semantic)||reviewing}><summary><WorkspaceIcon name="flask"/><span><strong>AI meaning review <span className="betaBadge">Beta</span></strong><small>Experimental · Not an accuracy guarantee</small></span><WorkspaceIcon name="chevron" className="disclosureIcon"/></summary><div className="reviewBody"><p>Optional extra local inference using the same model. It can repeat errors, miss changes or misclassify findings. This is not independent semantic validation.</p><button className="button secondaryButton" disabled={busy||!validation||!result||result.isMock} onClick={onSemanticReview}><WorkspaceIcon name="flask"/>{reviewing?'Reviewing…':'Request AI review'}</button>{result?.isMock&&<p className="fieldHint">Unavailable in mock mode.</p>}{!result&&<p className="fieldHint">Available after local AI generation and current deterministic checks.</p>}{semantic&&<><p className="semanticStatus">AI review {semantic.reviewStatus} · {(semantic.elapsedMilliseconds/1000).toFixed(1)} s</p>{semantic.limitations.map(text=><p key={text}>{text}</p>)}<FindingList findings={semantic.findings}/>{!semantic.findings.length&&<p>No accepted model findings to display. This does not verify meaning.</p>}</>}</div></details>
    <div className="reviewNote"><WorkspaceIcon name="info"/><div><strong>Your judgment comes first</strong><p>Automated checks support your review. Verify the final message, then explicitly approve it before copying.</p></div></div>
  </aside>;
}
