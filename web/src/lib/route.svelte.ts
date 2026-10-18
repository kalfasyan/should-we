// Two screens: "/" to start or reopen a decision, "/d/<id>" for one decision.
export const route = $state({ path: window.location.pathname });

window.addEventListener('popstate', () => (route.path = window.location.pathname));

export function go(path: string) {
  history.pushState({}, '', path);
  route.path = path;
  window.scrollTo(0, 0);
}

export function decisionId(path: string): string | null {
  return /^\/d\/([a-z0-9]{15})\/?$/.exec(path)?.[1] ?? null;
}
