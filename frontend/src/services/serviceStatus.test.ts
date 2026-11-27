import {expect,test} from 'vitest';
import {describeBackend} from './serviceStatus';

test('backend health does not imply an Ollama connection or model readiness',()=>{
  const status=describeBackend({status:'ok',provider:'ollama',modelConnection:'notChecked',semanticValidation:'unavailable'});
  expect(status.label).toBe('Backend available');
  expect(status.detail).toContain('Ollama selected');
  expect(status.detail).toContain('not checked');
  expect(status.detail).not.toContain('Connected');
});
test('mock mode remains visibly a demonstration',()=>{
  expect(describeBackend({status:'ok',provider:'mock',modelConnection:'notChecked',semanticValidation:'unavailable'}).detail).toContain('Spacing demonstration only');
});
test('missing or failed health is unavailable, never an available service',()=>{
  expect(describeBackend(null).label).toBe('Backend unavailable');
  expect(describeBackend({status:'error',provider:'ollama',modelConnection:'notChecked',semanticValidation:'unavailable'}).label).toBe('Backend unavailable');
});
