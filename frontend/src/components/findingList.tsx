import type {Finding} from '../types/contracts';

export function FindingList({findings}:{findings:Finding[]}) {
  return <>{findings.map((finding,index)=><article className="finding" key={index}><span className="findingCategory">{finding.category.replace(/([a-z])([A-Z])/g,'$1 $2')}</span><p>{finding.explanation}</p>{finding.sourceEvidence&&<><span className="evidenceLabel">Source or confirmed context</span><blockquote>{finding.sourceEvidence}</blockquote></>}{finding.generatedText&&<details><summary>Generated evidence</summary><blockquote>{finding.generatedText}</blockquote></details>}<small>{finding.suggestedAction}</small></article>)}</>;
}
