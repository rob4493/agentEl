import type {Finding} from '../types/contracts';

export function FindingList({findings}:{findings:Finding[]}) {
  return <>{findings.map((finding,index)=><article key={index}><strong>{finding.category}</strong><p>{finding.explanation}</p>{finding.sourceEvidence&&<><small>Source or confirmed context</small><blockquote>{finding.sourceEvidence}</blockquote></>}{finding.generatedText&&<details><summary>Generated evidence</summary><blockquote>{finding.generatedText}</blockquote></details>}<small>{finding.suggestedAction}</small></article>)}</>;
}
