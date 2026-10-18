<script lang="ts">
  import { api } from '../lib/api';
  import { go } from '../lib/route.svelte';
  import { recents, remember } from '../lib/local';
  import { EXAMPLES } from '../lib/words';

  let title = $state('');
  let points = $state<string[]>([]);
  let draft = $state('');
  let error = $state('');
  let busy = $state(false);
  const past = recents();

  function addPoint() {
    const p = draft.trim();
    if (p && !points.some((x) => x.toLowerCase() === p.toLowerCase())) points = [...points, p];
    draft = '';
  }

  function useExample(e: (typeof EXAMPLES)[number]) {
    title = e.title;
    points = [...e.features];
  }

  async function create(ev: SubmitEvent) {
    ev.preventDefault();
    addPoint();
    error = '';
    if (!title.trim()) return (error = 'Say what you are deciding.');
    if (points.length === 0) return (error = 'Add at least one thing that matters.');
    busy = true;
    try {
      const { id } = await api.create(title.trim(), points);
      remember({ id, title: title.trim() });
      go(`/d/${id}`);
    } catch (e) {
      error = (e as Error).message;
    } finally {
      busy = false;
    }
  }
</script>

<main class="mx-auto flex min-h-dvh max-w-md flex-col gap-6 px-4 pt-10 pb-8">
  <header class="text-center">
    <img src="/icons/icon-192.png" alt="" class="mx-auto mb-3 h-16 w-16 rounded-2xl" />
    <h1 class="text-3xl font-bold">should-we</h1>
    <p class="mt-2 text-slate-600 dark:text-slate-400">
      Pick one option together. Everyone says what matters to them and rates the options. You get one ranking.
    </p>
  </header>

  <form class="card flex flex-col gap-4" onsubmit={create}>
    <h2 class="text-lg font-semibold">Start a decision</h2>

    <div class="flex gap-2 overflow-x-auto pb-1" aria-label="Examples">
      {#each EXAMPLES as e (e.name)}
        <button type="button" class="chip" onclick={() => useExample(e)}>{e.name}</button>
      {/each}
    </div>

    <label class="flex flex-col gap-1">
      <span class="text-sm font-medium">What are you deciding?</span>
      <input bind:value={title} placeholder="Which apartment should we rent?" maxlength="120" />
    </label>

    <div class="flex flex-col gap-2">
      <span class="text-sm font-medium">What matters when choosing?</span>
      {#if points.length}
        <ul class="flex flex-wrap gap-2">
          {#each points as p (p)}
            <li class="flex items-center gap-1 rounded-full bg-brand-50 py-1 pr-1 pl-3 text-sm text-brand-700 dark:bg-brand-700/30 dark:text-brand-100">
              {p}
              <button
                type="button"
                class="rounded-full px-2 text-base leading-none"
                aria-label="Remove {p}"
                onclick={() => (points = points.filter((x) => x !== p))}>×</button
              >
            </li>
          {/each}
        </ul>
      {/if}
      <div class="flex gap-2">
        <input
          class="min-w-0 flex-1"
          bind:value={draft}
          placeholder={points.length ? 'Add another' : 'Price, location, size…'}
          maxlength="60"
          onkeydown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault();
              addPoint();
            }
          }}
        />
        <button type="button" class="btn-secondary px-4 py-3" onclick={addPoint} disabled={!draft.trim()}>Add</button>
      </div>
    </div>

    {#if error}<p class="text-sm text-red-600">{error}</p>{/if}
    <button class="btn-primary" disabled={busy}>{busy ? 'Creating…' : 'Create and get the link'}</button>
  </form>

  {#if past.length}
    <section class="flex flex-col gap-2">
      <h2 class="px-1 text-sm font-medium text-slate-500">Your decisions</h2>
      {#each past as r (r.id)}
        <a href="/d/{r.id}" class="card flex items-center justify-between py-3" onclick={(e) => (e.preventDefault(), go(`/d/${r.id}`))}>
          <span class="truncate font-medium">{r.title}</span>
          <span class="text-slate-400">›</span>
        </a>
      {/each}
    </section>
  {/if}

  <footer class="mt-auto text-center text-xs text-slate-400">should-we v{__APP_VERSION__}</footer>
</main>
