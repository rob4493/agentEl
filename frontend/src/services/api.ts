import type {AmbiguityQuestion} from '../types/contracts';

export class ApiError extends Error {
  questions: AmbiguityQuestion[];
  constructor(message: string, questions: AmbiguityQuestion[] = []) {super(message);this.questions = questions;}
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`/api/${path}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    if (error?.detail?.code === 'clarificationRequired') throw new ApiError('Clarify the material ambiguity before generation.', error.detail.questions);
    throw new ApiError(typeof error?.detail === 'string' ? error.detail : `Request failed (${response.status}). Check input and backend availability.`);
  }
  return response.json();
}
