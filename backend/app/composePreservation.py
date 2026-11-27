"""Compose-only fidelity warnings. Lexical checks never establish semantic equivalence."""
import re
from .contentReview import PassageMatcher,topicTokens
from .emailSchemas import Finding
from .textPassages import splitPassages


numberWords = {'one':'1','two':'2','both':'2','three':'3','four':'4','five':'5','six':'6','seven':'7','eight':'8','nine':'9','ten':'10','eleven':'11','twelve':'12'}
quantityPattern = r'\b('+'|'.join(numberWords)+r')\s+(?:[a-z]+\s+){0,2}(?:people|persons?|participants?|members?|employees?|teams?|ideas?|prototypes?|options?|shifts?|items?|issues?|problems?|reports?|days?|weeks?|months?|hours?|minutes?)\b'
weekdayPattern = r'\b(?:(?:last|next|this)\s+)?(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b'
timePattern = r'\b(1[0-2]|0?[1-9])(?::([0-5][0-9]))?\s*([ap])\.?m\.?\b'
tentativePattern = r"\b(?:plan(?:ning)?|intend(?:ing)?|hope|expect)\s+to\b"
offerPattern = r'\b(?:can|could|able to)\b'
firmPattern = r"\b(?:will|shall|must|guarantee|promise|commit)\b|\b(?:I|we)['’]ll\b|\b(?:is|are|has been|have been)\s+(?:now\s+)?scheduled\b"
completedPattern = r'\b(?:have|has|had)\s+(?:already\s+)?(?:sent|booked|approved|agreed|confirmed|completed|scheduled|arranged|delivered)\b'
pendingPattern = r"\b(?:pending|preliminary|estimated|proposed|unconfirmed|under review)\b|\bhaven['’]t\s+(?:yet\s+)?(?:agreed|booked|approved|confirmed)\b"
confirmedPattern = r'\b(?:is|are|was|were|has been|have been)\s+(?:now\s+)?(?:approved|confirmed|final|finalized|finalised|resolved|completed|booked)\b'
severityPattern = r'\b(?:critical|severe|urgent|mandatory|high[- ]priority)\b'
conditionalPattern = r'\b(?:if|unless|provided that|subject to)\b'
directivePattern = r'\b(?:please|must|need to|required to)\s+(?:approve|authorize|book|purchase|schedule|send|submit|deliver)\b'
fidelityStateWords=set('plan planning intend intending hope expect able sent send sending pending preliminary estimated proposed unconfirmed review approved confirmed final finalized resolved completed booked agree agreed decide decided critical severe urgent mandatory'.split())


def quantities(text: str) -> set[str]:
    # Only count words in measurable noun phrases, not "one another" or "one team".
    words={numberWords[match.group(1).lower()] for match in re.finditer(quantityPattern,text,re.I) if match.group().lower()!='one team' and match.group(1).lower()!='both'}
    return words | set(re.findall(r'\b\d+(?:[.,]\d+)*\b',text))


def timeMarkers(text: str) -> set[str]:
    markers={match.group().lower() for match in re.finditer(weekdayPattern,text,re.I)}
    for match in re.finditer(timePattern,text,re.I):
        hour=int(match.group(1))%12+(12 if match.group(3).lower()=='p' else 0)
        markers.add(f'{hour:02d}:{int(match.group(2) or 0):02d}')
    return markers


def reviewAdaptationFidelity(original: str, adapted: str, existing: list[Finding]) -> list[Finding]:
    findings=[]
    categories={finding.category for finding in existing}
    def add(category, explanation, source='', output=''):
        # Keep existing safeguards, but do not stack an equivalent new warning
        # on the same generated passage. Wording-only warnings are not equivalents.
        equivalents={'commitmentStrengthChanged':{'unsupportedCommitment'},'decisionStatusChanged':{'statusChanged','uncertaintyChanged'}}
        if output and any(finding.category in equivalents.get(category,set()) and finding.generatedText==output for finding in existing):
            return
        if category not in categories:
            categories.add(category)
            findings.append(Finding(category=category,severity='warning',explanation=explanation,sourceEvidence=source,generatedText=output))
    # Digit changes already have a base warning. Add coverage for spelled-out
    # quantities without requiring exact sentence wording or numeric typography.
    sourceQuantities=quantities(original);outputQuantities=quantities(adapted)
    # "Both" can restate an explicit two, but is not itself a reliable new
    # quantity claim (a comparison can retain both options without that word).
    if '2' in sourceQuantities and re.search(r'\bboth\b',adapted,re.I):outputQuantities.add('2')
    if '2' in outputQuantities and re.search(r'\bboth\b',original,re.I):sourceQuantities.add('2')
    if 'numericalChange' not in categories and sourceQuantities!=outputQuantities:
        missing=sorted(sourceQuantities-outputQuantities);added=sorted(outputQuantities-sourceQuantities)
        add('quantityChanged','A quantity may have been added, removed or changed, including a number written as a word. Verify the amounts and what each refers to.',missing[0] if missing else '',added[0] if added else '')
    sourceTimes=timeMarkers(original);outputTimes=timeMarkers(adapted)
    if sourceTimes!=outputTimes:
        missing=sorted(sourceTimes-outputTimes);added=sorted(outputTimes-sourceTimes)
        add('timingChanged','A weekday, relative week or clock time may have changed. Check both the timing and the action it belongs to.',missing[0] if missing else '',added[0] if added else '')
    lines=[line.strip() for line in original.splitlines() if line.strip()]
    if len(lines)>=2 and re.fullmatch(r'(?:best(?: regards)?|kind regards|regards|thanks(?: again)?|thank you|sincerely)[,!]?',lines[-2],re.I):
        signature=lines[-1]
        if len(signature)<=80 and re.fullmatch(r"[^\W\d_][\w .,'’\-]*",signature) and not re.search(r'\b'+re.escape(signature.strip('., '))+r'\b',adapted,re.I):
            add('senderIdentityChanged','The sender name from your original sign-off is missing or changed. Restore the intended sender identity.',signature)
    candidates=splitPassages(adapted)
    matcher=PassageMatcher(candidates)
    for source in splitPassages(original):
        output=matcher.match(source)
        if not output:
            # Short status statements can share only their object after a tense
            # change. Require a unique topical candidate; abstain on ambiguity.
            topics=topicTokens(source)-fidelityStateWords
            related=[candidate for candidate in candidates if topics & (topicTokens(candidate)-fidelityStateWords)]
            if len(related)==1:
                output=related[0]
        if not output or source==output:
            continue
        # Compare related passages only. These are possible changes, not a
        # claim about scope or intent; unrelated promises must not mask a plan.
        sourceTentative=bool(re.search(tentativePattern,source,re.I))
        sourceOffer=bool(re.search(offerPattern,source,re.I))
        sourceFirm=bool(re.search(firmPattern,source,re.I))
        outputFirm=bool(re.search(firmPattern,output,re.I))
        outputCompleted=bool(re.search(completedPattern,output,re.I))
        lostTentative=sourceTentative and not re.search(tentativePattern,output,re.I)
        lostOffer=sourceOffer and not re.search(offerPattern,output,re.I)
        if ((lostTentative or lostOffer) and (outputFirm or outputCompleted) and not sourceFirm
            or sourceFirm and not outputFirm and re.search(tentativePattern+'|'+offerPattern,output,re.I)):
            add('commitmentStrengthChanged','A related passage may change a plan or offer into a firm commitment, obligation or completed action, or weaken a firm commitment. Check the original level of commitment.',source,output)
        if re.search(pendingPattern,source,re.I) and re.search(confirmedPattern+'|'+completedPattern,output,re.I) and not re.search(pendingPattern,output,re.I):
            add('decisionStatusChanged','A pending, proposed, preliminary or estimated status may have become confirmed, final or complete. Verify its status and approval requirements.',source,output)
        if re.search(conditionalPattern,source,re.I) and not re.search(conditionalPattern,output,re.I) and 'qualificationChanged' not in categories:
            add('conditionChanged','A related passage may have lost a condition. Verify that the offer, action or approval is still conditional in the same way.',source,output)
        optionalCondition=r"\bif\s+(?:you(?:['’]d| would)?\s+(?:like|want)|desired|needed)\b"
        approvalCondition=r'\b(?:if|once|after)\s+(?:(?:you|we)\s+)?(?:approve|approved|approval)\b'
        if re.search(optionalCondition,source,re.I) and re.search(approvalCondition,output,re.I) and not re.search(approvalCondition,source,re.I):
            add('conditionChanged','An optional offer may now depend on approval instead of the original preference or need. Verify that the condition has not changed.',source,output)
        if re.search(r'\b(?:I|we)\s+(?:can|could)\b',source,re.I) and lostOffer and re.search(directivePattern,output,re.I):
            add('offerChangedToRequirement','A conditional offer may have become a required action or decision. Check that quote timing or availability has not become an approval deadline.',source,output)
    for output in candidates:
        match=re.search(severityPattern,output,re.I)
        if match and not re.search(r'\b'+re.escape(match.group())+r'\b',original,re.I):
            add('addedSeverity','A severity or urgency label was introduced without the same wording in the source. Verify whether that stronger characterization is intended.',output=output)
    return findings
