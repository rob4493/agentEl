import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {describe,it,expect} from 'vitest';
import {DiscoverScreen,swipeDirection,communicationStyles,researchQuotation,adjacentStyle} from './discoverScreen';

describe('Discover communication characteristics',()=>{
  it('preserves every supplied handout bullet exactly and in order',()=>{
    expect(communicationStyles.map(style=>style.name)).toEqual(['Expressive','Amiable','Driver','Analytical']);
    expect(communicationStyles.map(style=>style.characteristics)).toEqual([
    [
        "Look for opportunities to recognize achievements",
        "Seek to inspire",
        "Use an energetic and enthusiastic tone",
        "Paint the big picture / vision before going into detail",
        "Present ideas creatively",
        "Provide lots of visual stimulus",
        "Use \"action\" language",
        "Use color"
    ],
    [
        "Highlight the positive benefits to people",
        "Write about the relationship in terms of \"one team\"",
        "Offer personal commitments",
        "Provide solutions to minimize the effects of change on people",
        "Be friendly, warm, cooperative and patient",
        "Show empathy to those affected by the recommendations"
    ],
    [
        "Focus on results, outcomes and the bottom line",
        "Provide only necessary detail",
        "Provide options to make the decision easy",
        "Emphasize company / organizational context",
        "State specific action required of decision maker",
        "Keep it short and succinct",
        "Make definitive statements",
        "Avoid using excessive emotion"
    ],
    [
        "Structure and logic is important",
        "Have all the facts in order",
        "Use appropriate technical terms",
        "Provide all necessary details",
        "Use evidence to prove any claim",
        "Explain the process step by step – show the logic",
        "Talk specifically – not in generalizations"
    ]
]);
  });
  it('preserves the exact supplied research quotation and citation',()=>{
    expect(researchQuotation).toBe("\"Research has shown that each of us has a preferred interactional style when communicating. These four distinct reader communication styles (e.g., Expressive, Driver, Amiable, and Analytical) are deeply rooted in the field of behavioral psychology and are adapted from the statistical and clinical work of industrial psychologists David Merrill and Roger Reid in 'Social Styles Theory'\" (Sanchez and Bullock, 2021, p. 98).");
    const html=renderToStaticMarkup(<DiscoverScreen onStart={()=>{}}/>);
    expect(html).toContain('Targeting the Reader.');
    expect(html).toContain('Write the way your reader reads best.');
    expect(html).toContain('Social Styles &amp; Human-Centered AI (HCAI) Tool');
    expect(html).toContain(researchQuotation.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll("'",'&#x27;'));
  });
  it('cycles in both directions without a redundant selector grid',()=>{
    expect(adjacentStyle('Expressive',-1)).toBe('Analytical');
    expect(adjacentStyle('Analytical',1)).toBe('Expressive');
    expect(adjacentStyle('Amiable',1)).toBe('Driver');
    const html=renderToStaticMarkup(<DiscoverScreen onStart={()=>{}}/>);
    expect(html).not.toContain('class="styleCards"');expect(html).toContain('aria-roledescription="carousel"');expect(html).toContain('1 of 4');
    expect(html).toContain('Previous style');expect(html).toContain('Next style');
    expect(html).toContain('communicationPerspectives.svg');
  });
  it('renders one readable list, accessible selectors and the educational disclaimer without email examples',()=>{
    const html=renderToStaticMarkup(<DiscoverScreen onStart={()=>{}}/>);
    expect(html).toContain('Writing for Different Readers');expect(html).toContain('How to write for this reader');expect(html).toContain('When your reader prefers this style, these choices help your message land.');
    expect(html).toContain('Select a style to see how to write for that reader.');
    expect(html).not.toContain('characteristics you may notice');
    expect(html).toContain('tabindex="0"');
    expect(html.match(/aria-controls="styleCharacteristics"/g)).toHaveLength(2);
    expect(html.match(/<li>/g)).toHaveLength(8);
    expect(html).toContain('aria-live="polite"');
    for(const characteristic of communicationStyles[0].characteristics) expect(html).toContain(characteristic.replaceAll('&','&amp;').replaceAll('"','&quot;'));
    expect(html).not.toContain('Expresses empathy for those affected by decisions.');
    for(const removed of ['One Message. Four Approaches.','Original facts','Friday','Thursday','Both facts retained','Educational example']) expect(html).not.toContain(removed);
    expect(html).toContain('not fixed personality types');expect(html).toContain('multiple styles');expect(html).toContain('Get Started');
  });
});

 it('only treats deliberate horizontal swipes as carousel navigation',()=>{
  expect(swipeDirection(-100,8)).toBe(1);expect(swipeDirection(90,10)).toBe(-1);
  expect(swipeDirection(30,0)).toBe(0);expect(swipeDirection(80,100)).toBe(0);expect(swipeDirection(60,50)).toBe(0);
 });
