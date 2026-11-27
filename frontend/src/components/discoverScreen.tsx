import {useRef,useState} from 'react';
export const researchQuotation="\"Research has shown that each of us has a preferred interactional style when communicating. These four distinct reader communication styles (e.g., Expressive, Driver, Amiable, and Analytical) are deeply rooted in the field of behavioral psychology and are adapted from the statistical and clinical work of industrial psychologists David Merrill and Roger Reid in 'Social Styles Theory'\" (Sanchez and Bullock, 2021, p. 98).";

// Educational characteristics supplied from the reader-style reference, not diagnostic criteria or model findings.
export const communicationStyles=[
  {name:'Expressive',description:'Ideas, energy and the bigger picture.',characteristics:[
    "Look for opportunities to recognize achievements",
    "Seek to inspire",
    "Use an energetic and enthusiastic tone",
    "Paint the big picture / vision before going into detail",
    "Present ideas creatively",
    "Provide lots of visual stimulus",
    "Use \"action\" language",
    "Use color"
]},
  {name:'Amiable',description:'Consideration, connection and collaboration.',characteristics:[
    "Highlight the positive benefits to people",
    "Write about the relationship in terms of \"one team\"",
    "Offer personal commitments",
    "Provide solutions to minimize the effects of change on people",
    "Be friendly, warm, cooperative and patient",
    "Show empathy to those affected by the recommendations"
]},
  {name:'Driver',description:'Clear actions and a direct path forward.',characteristics:[
    "Focus on results, outcomes and the bottom line",
    "Provide only necessary detail",
    "Provide options to make the decision easy",
    "Emphasize company / organizational context",
    "State specific action required of decision maker",
    "Keep it short and succinct",
    "Make definitive statements",
    "Avoid using excessive emotion"
]},
  {name:'Analytical',description:'Details, structure and precise information.',characteristics:[
    "Structure and logic is important",
    "Have all the facts in order",
    "Use appropriate technical terms",
    "Provide all necessary details",
    "Use evidence to prove any claim",
    "Explain the process step by step – show the logic",
    "Talk specifically – not in generalizations"
]},
];

// Small decorative line icons complement the labels; names and pressed states convey selection without color.
export function StyleGlyph({name}:{name:string}) {
  const paths:Record<string,string[]>={
    Expressive:['M4 10h4l12-5v14L8 14H4Z','m8 14 2 7h3l-2-6M22 9v6'],
    Amiable:['M12 21 3 12a5 5 0 0 1 7-7l2 2 2-2a5 5 0 0 1 7 7Z'],
    Driver:['M4 12h16m-7-7 7 7-7 7','M4 6h4M4 18h4'],
    Analytical:['M4 20V4M4 20h17','M8 16v-4M13 16V8M18 16V5'],
  };
  return <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name].map((path,index)=><path key={index} d={path}/>)}</svg>;
}

export function adjacentStyle(current:string,direction:number) {
  const index=communicationStyles.findIndex(style=>style.name===current);
  return communicationStyles[(index+direction+communicationStyles.length)%communicationStyles.length].name;
}

// Horizontal intent must be clear; vertical reading gestures never change styles.
export function swipeDirection(deltaX:number,deltaY:number) {
  return Math.abs(deltaX)>=60&&Math.abs(deltaX)>Math.abs(deltaY)*1.5?(deltaX<0?1:-1):0;
}

export function DiscoverScreen({onStart}:{onStart:()=>void}) {
  const [selectedStyle,setSelectedStyle]=useState('Expressive');
  const gesture=useRef<{x:number;y:number;id:number}|null>(null);
  const selected=communicationStyles.find(style=>style.name===selectedStyle)!;
  return <section className="journeyScreen discoverScreen" aria-labelledby="discoverTitle">
    <div className="discoverLead academicLead perspectiveHero"><img className="perspectiveIllustration" src="/brand/communicationPerspectives.svg" alt="" aria-hidden="true"/><div className="discoverHero"><p className="eyebrow">Social Styles &amp; Human-Centered AI (HCAI) Tool</p><h1 id="discoverTitle">Targeting the Reader.<br/><span>Write the way your reader reads best.</span></h1><p>At work, every message lands with a reader who has a preferred way to receive information. Matching your reader's style helps them understand your message and makes your communication more effective.</p><button className="button primaryButton" onClick={onStart}>Get Started <span aria-hidden="true">→</span></button></div><aside className="researchReference" aria-labelledby="researchReferenceTitle"><p id="researchReferenceTitle" className="researchLabel">Research reference</p><blockquote>{researchQuotation}</blockquote></aside></div>
    <section className="discoverExplorer" aria-labelledby="approachesTitle"><div className="explorerHeading"><div><p className="eyebrow">Select a style. Notice the difference.</p><h2 id="approachesTitle">Writing for Different Readers</h2><p className="styleIntroduction">Select a style to see how to write for that reader.</p></div></div>

      <section className={`featuredCarousel style${selected.name}`} aria-roledescription="carousel" aria-label="Communication styles">
        <div id="styleCharacteristics" className="styleCharacteristics" tabIndex={0} aria-label="Featured communication style. Use left and right arrow keys to browse."
          onKeyDown={event=>{if(event.target!==event.currentTarget)return;const direction=event.key==='ArrowRight'?1:event.key==='ArrowLeft'?-1:0;if(direction){event.preventDefault();setSelectedStyle(current=>adjacentStyle(current,direction));}}}
          onPointerDown={event=>{if(event.pointerType==='touch')gesture.current={x:event.clientX,y:event.clientY,id:event.pointerId};}}
          onPointerCancel={()=>{gesture.current=null;}}
          onPointerUp={event=>{const start=gesture.current;gesture.current=null;if(!start||start.id!==event.pointerId)return;const direction=swipeDirection(event.clientX-start.x,event.clientY-start.y);if(direction)setSelectedStyle(current=>adjacentStyle(current,direction));}}>
          <div className="featuredStyleContent" aria-live="polite" aria-atomic="true">
            <div className="characteristicsHeading"><span className="characteristicsIcon"><StyleGlyph name={selected.name}/></span><div><p>How to write for this reader</p><h3>{selected.name}</h3><p className="selectedStyleDescription">{selected.description}</p><span>When your reader prefers this style, these choices help your message land.</span></div></div>
            <ul>{selected.characteristics.map(characteristic=><li key={characteristic}>{characteristic}</li>)}</ul>
          </div>
        </div>
        <div className="carouselNavigation" role="group" aria-label="Featured style navigation"><button type="button" aria-controls="styleCharacteristics" onClick={()=>setSelectedStyle(current=>adjacentStyle(current,-1))}><span aria-hidden="true">←</span> Previous style</button><span className="carouselPosition" aria-label={`Style ${communicationStyles.findIndex(style=>style.name===selectedStyle)+1} of 4`}>{communicationStyles.findIndex(style=>style.name===selectedStyle)+1} of 4</span><button type="button" aria-controls="styleCharacteristics" onClick={()=>setSelectedStyle(current=>adjacentStyle(current,1))}>Next style <span aria-hidden="true">→</span></button></div>
      </section>
    </section><p className="journeyCaution">These characteristics describe patterns of communication, not fixed personality types. A person may demonstrate characteristics of multiple styles depending on the situation.</p>
    <details className="discoverNotes"><summary>About this preview</summary><p>The characteristics are based on the supplied “Targeting the Reader Communication Style” reference by Professor Raul Sanchez. This is educational guidance, not diagnostic criteria or an analysis of a particular person. Selecting a style does not run AI analysis.</p><p>Available today: received-email writing observations with local Ollama, user-reviewed style selection, response style adaptation, English draft improvement, source comparison, limited automated checks and human approval. Planned: writer-style observations and personalized learning summaries. Automated checks do not guarantee preserved meaning.</p></details>
  </section>;
}
