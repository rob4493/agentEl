import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {expect,it,vi} from 'vitest';
vi.mock('../services/api',()=>({apiConfiguration:{betaEnabled:true},apiFetch:vi.fn()}));
import {BetaAccess} from './betaAccess';

it('shows a private beta password entry before mounting draft content',()=>{
  const html=renderToStaticMarkup(<BetaAccess><div>PRIVATE DRAFT TEST MARKER</div></BetaAccess>);
  expect(html).toContain('Ritmo private beta');expect(html).toContain('type="password"');
  expect(html).toContain('Cloudflare');expect(html).not.toContain('PRIVATE DRAFT TEST MARKER');
  expect(html).not.toContain('localStorage');
});
