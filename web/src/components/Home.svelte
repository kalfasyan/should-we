<script lang="ts">
  import { api } from '../lib/api';
  import { go } from '../lib/route.svelte';
  import { forget, recents, remember, setMe, takeTemplate } from '../lib/local';
  import { EXAMPLES } from '../lib/words';
  import Points from './Points.svelte';

  const template = takeTemplate();
  let title = $state(template?.title ?? '');
  let points = $state<string[]>(template ? [...template.points] : []);
  let draft = $state('');
  let error = $state('');
  let busy = $state(false);
  let past = $state(recents());
  let editor: Points;

  function useExample(e: (typeof EXAMPLES)[number]) {
    title = e.title;
    points = [...e.features];
  }

  function hide(id: string) {
    forget(id);
    past = recents();
  }

  async function create(ev: SubmitEvent) {
    ev.preventDefault();
    editor.addDraft();
    error = '';
    if (!title.trim()) return (error = 'Say what you are deciding.');
    if (points.length === 0) return (error = 'Add at least one thing that matters.');
    busy = true;
    try {
      const { id } = await api.create(title.trim(), points);
      remember({ id, title: title.trim() });
      if (template?.name) {
        // join as the same person, with the same priorities for the points that stayed
        const me = await api.join(id, template.name);
        setMe(id, me);
        const d = await api.get(id);
        const weights = Object.fromEntries(
          d.features.filter((f) => template.weights?.[f.label] !== undefined).map((f) => [f.key, template.weights![f.label]]),
        );
        if (Object.keys(weights).length) await api.saveWeights(id, me, weights);
      }
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

    {#if template}
      <p class="rounded-xl bg-brand-50 px-3 py-2 text-sm text-brand-700 dark:bg-brand-700/30 dark:text-brand-100">
        Copied from “{template.from}”. Change anything you like.
        {#if template.name}You'll join as {template.name} with the same priorities.{/if}
        Options and ratings start empty.
      </p>
    {:else}
      <div class="flex gap-2 overflow-x-auto pb-1" aria-label="Examples">
        {#each EXAMPLES as e (e.name)}
          <button type="button" class="chip" onclick={() => useExample(e)}>{e.name}</button>
        {/each}
      </div>
    {/if}

    <label class="flex flex-col gap-1">
      <span class="text-sm font-medium">What are you deciding?</span>
      <input bind:value={title} placeholder="Which apartment should we rent?" maxlength="120" />
    </label>

    <div class="flex flex-col gap-2">
      <span class="text-sm font-medium">What matters when choosing?</span>
      <Points bind:this={editor} bind:points bind:draft />
    </div>

    {#if error}<p class="text-sm text-red-600">{error}</p>{/if}
    <button class="btn-primary" disabled={busy}>{busy ? 'Creating…' : 'Create and get the link'}</button>
  </form>

  {#if past.length}
    <section class="flex flex-col gap-2">
      <h2 class="px-1 text-sm font-medium text-slate-500">Your decisions</h2>
      {#each past as r (r.id)}
        <div class="card flex items-center gap-2 py-1 pr-1">
          <a href="/d/{r.id}" class="flex min-w-0 flex-1 items-center justify-between py-2" onclick={(e) => (e.preventDefault(), go(`/d/${r.id}`))}>
            <span class="truncate font-medium">{r.title}</span>
            <span class="text-slate-400">›</span>
          </a>
          <button class="px-3 py-2 text-lg leading-none text-slate-400" aria-label="Hide {r.title} from this list" title="Hide from this list" onclick={() => hide(r.id)}>×</button>
        </div>
      {/each}
    </section>
  {/if}

  <footer class="mt-auto text-center text-xs text-slate-400">should-we v{__APP_VERSION__}</footer>
</main>
