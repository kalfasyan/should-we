// Talks to the should-we API served by the same PocketBase that serves this app.

export type Feature = { key: string; label: string };
export type Weights = Record<string, number>;
export type Scores = Record<string, number>;
export type Person = { id: string; name: string; weights: Weights; ratings: Record<string, Scores> };
export type Option = { id: string; name: string; note: string; added_by: string };
export type Result = {
  option: string;
  score: number;
  rated_by: number;
  split: boolean;
  by_person: { person: string; score: number }[];
};
export type Decision = {
  id: string;
  title: string;
  features: Feature[];
  people: Person[];
  options: Option[];
  results: Result[];
};

/** Who this browser is in one decision; the token proves it to the server. */
export type Me = { id: string; name: string; token: string };

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}

async function call<T>(method: string, path: string, body?: unknown, me?: Me): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (me) {
    headers['X-Person-Id'] = me.id;
    headers['X-Person-Token'] = me.token;
  }
  let res: Response;
  try {
    res = await fetch(`/api/sw${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Can't reach the server. Check your connection.", 0);
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(data.message || 'Something went wrong. Try again.', res.status);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  create: (title: string, features: string[]) =>
    call<{ id: string }>('POST', '/decisions', { title, features }),
  get: (id: string) => call<Decision>('GET', `/decisions/${id}`),
  saveFeatures: (id: string, me: Me, features: string[]) =>
    call<void>('PUT', `/decisions/${id}/features`, { features }, me),
  join: (id: string, name: string) => call<Me>('POST', `/decisions/${id}/people`, { name }),
  saveWeights: (id: string, me: Me, weights: Weights) =>
    call<void>('PUT', `/decisions/${id}/people/${me.id}/weights`, weights, me),
  rate: (id: string, me: Me, option: string, scores: Scores) =>
    call<void>('PUT', `/decisions/${id}/people/${me.id}/ratings/${option}`, scores, me),
  addOption: (id: string, me: Me, name: string, note: string) =>
    call<Option>('POST', `/decisions/${id}/options`, { name, note }, me),
  editNote: (id: string, me: Me, option: string, note: string) =>
    call<void>('PATCH', `/decisions/${id}/options/${option}`, { note }, me),
  removeOption: (id: string, me: Me, option: string) =>
    call<void>('DELETE', `/decisions/${id}/options/${option}`, undefined, me),
};
