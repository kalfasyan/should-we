<script lang="ts">
  import { onMount } from 'svelte';
  import { api, ApiError, type Decision, type Me } from '../lib/api';
  import { getMe, setMe, remember, forget, setTemplate } from '../lib/local';
  import { go } from '../lib/route.svelte';
  import Join from './Join.svelte';
  import Rate from './Rate.svelte';
  import Results from './Results.svelte';

  let { id }: { id: string } = $props();

  let data = $state<Decision | null>(null);
  let missing = $state(false);
  let error = $state('');
  // the page is re-created for each decision id (see App.svelte)
  // svelte-ignore state_referenced_locally
  let me = $state<Me | null>(getMe(id));
  let peeking = $state(false);
  let tab = $state<'rate' | 'results'>('rate');
  let copied = $state(false);

  async function load() {
    try {
      data = await api.get(id);
      error = '';
      remember({ id, title: data.title });
      // this browser's person was removed or the data was reset
      if (me && !data.people.some((p) => p.id === me!.id)) me = null;
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        missing = true;
        forget(id);
      } else error = (e as Error).message;
    }
  }

  onMount(() => {
    load();
    // keep everyone's answers fresh while the page is open
    const timer = setInterval(() => document.visibilityState === 'visible' && load(), 5000);
    const onVisible = () => document.visibilityState === 'visible' && load();
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      clearInterval(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
  });

  function joined(m: Me) {
    setMe(id, m);
    me = m;
    peeking = false;
    tab = 'rate';
    load();
  }

  // a fresh decision with the same points, and your priorities if you joined
  function startLikeThis() {
    if (!data) return;
    const person = me && data.people.find((p) => p.id === me!.id);
    setTemplate({
      from: data.title,
      title: data.title,
      points: data.features.map((f) => f.label),
      name: person?.name,
      weights: person ? Object.fromEntries(data.features.map((f) => [f.label, person.weights[f.key] ?? 3])) : undefined,
    });
    go('/');
  }

  async function share() {
    const url = window.location.origin + `/d/${id}`;
    if (navigator.share) {
      try {
        await navigator.share({ title: data?.title, text: `Help decide: ${data?.title}`, url });
        return;
      } catch {
        // cancelled or unsupported: fall back to copying
      }
    }
    try {
      await navigator.clipboard.writeText(url);
    } catch {
      window.prompt('Copy this link', url);
    }
    copied = true;
    setTimeout(() => (copied = false), 2000);
  }
</script>

{#if missing}
  <main class="mx-auto flex min-h-dvh max-w-md flex-col items-center justify-center gap-3 px-6 text-center">
    <h1 class="text-xl font-semibold">This decision doesn't exist</h1>
    <p class="text-slate-500">The link may be mistyped, or the decision was removed.</p>
    <button class="btn-primary" onclick={() => go('/')}>Start a new one</button>
  </main>
{:else if !data}
  <main class="flex min-h-dvh items-center justify-center text-slate-500">{error || 'Loading…'}</main>
{:else if !me && !peeking}
  <Join decision={data} onjoined={joined} onpeek={() => ((peeking = true), (tab = 'results'))} />
{:else}
  <div class="mx-auto flex min-h-dvh max-w-md flex-col gap-4 px-4 pt-4 pb-10">
    <header class="flex items-start gap-3">
      <button class="mt-1 text-2xl leading-none text-slate-400" aria-label="Home" onclick={() => go('/')}>‹</button>
      <div class="min-w-0 flex-1">
        <h1 class="text-xl font-bold break-words">{data.title}</h1>
        <p class="text-sm text-slate-500">
          {[me && `You're ${me.name}`, `${data.people.length} ${data.people.length === 1 ? 'person' : 'people'} in`]
            .filter(Boolean)
            .join(' · ')}
        </p>
      </div>
      <button class="btn-secondary px-4 py-2 text-sm" onclick={share}>{copied ? 'Copied!' : 'Share'}</button>
    </header>

    {#if error}
      <div class="rounded-xl bg-amber-100 px-4 py-2 text-sm text-amber-900 dark:bg-amber-900/40 dark:text-amber-100">{error}</div>
    {/if}

    {#if me && data.people.length <= 1}
      <div class="card flex flex-col gap-3 border-brand-500 bg-brand-50 dark:bg-brand-700/20">
        <p class="font-medium">Send this link to the people deciding with you.</p>
        <p class="text-sm text-slate-600 dark:text-slate-300">They pick a name, say what matters to them and rate the options. No accounts.</p>
        <button class="btn-primary" onclick={share}>{copied ? 'Link copied!' : 'Share the link'}</button>
      </div>
    {/if}

    {#if me}
      <div class="grid grid-cols-2 rounded-2xl bg-slate-200 p-1 dark:bg-slate-800" role="tablist">
        {#each [['rate', 'Your ratings'], ['results', 'Results']] as [t, label] (t)}
          <button
            role="tab"
            aria-selected={tab === t}
            class="rounded-xl py-2 text-sm font-semibold {tab === t ? 'bg-white shadow-sm dark:bg-slate-950' : 'text-slate-500'}"
            onclick={() => (tab = t as 'rate' | 'results')}>{label}</button
          >
        {/each}
      </div>
    {/if}

    {#if me && tab === 'rate'}
      <Rate decision={data} {me} onchange={load} onresults={() => (tab = 'results')} />
    {:else}
      <Results decision={data} />
      {#if !me}
        <button class="btn-primary" onclick={() => (peeking = false)}>Join to rate</button>
      {/if}
    {/if}

    <button class="mt-4 text-sm text-slate-500 underline" onclick={startLikeThis}>Start a new decision like this one</button>
  </div>
{/if}
