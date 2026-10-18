<script lang="ts">
  import { api, type Decision, type Me } from '../lib/api';
  import { LEVELS, levelOf } from '../lib/words';
  import OptionCard from './OptionCard.svelte';

  let {
    decision,
    me,
    onchange,
    onresults,
  }: { decision: Decision; me: Me; onchange: () => void; onresults: () => void } = $props();

  const person = $derived(decision.people.find((p) => p.id === me.id));
  // what you tapped, shown at once while the server catches up
  let tapped = $state<Record<string, number>>({});
  let error = $state('');

  const rated = $derived(decision.options.filter((o) => person?.ratings[o.id]).length);

  async function setLevel(key: string, value: number) {
    tapped[key] = value;
    try {
      await api.saveWeights(decision.id, me, { [key]: value });
      error = '';
      onchange();
    } catch (e) {
      error = (e as Error).message;
    }
  }

  let name = $state('');
  let note = $state('');
  let adding = $state(false);
  let addError = $state('');

  async function add(e: SubmitEvent) {
    e.preventDefault();
    if (!name.trim()) return (addError = 'Give the option a name.');
    adding = true;
    addError = '';
    try {
      await api.addOption(decision.id, me, name.trim(), note.trim());
      name = '';
      note = '';
      onchange();
    } catch (err) {
      addError = (err as Error).message;
    } finally {
      adding = false;
    }
  }
</script>

<section class="card flex flex-col gap-4">
  <div>
    <h2 class="text-lg font-semibold">1 · What matters to you?</h2>
    <p class="text-sm text-slate-500">Used for every option. Saved as you tap.</p>
  </div>
  {#each decision.features as f (f.key)}
    {@const current = tapped[f.key] ?? levelOf(person?.weights[f.key])}
    <div class="flex flex-col gap-2">
      <span class="font-medium">{f.label}</span>
      <div class="grid grid-cols-4 gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
        {#each LEVELS as l (l.value)}
          <button
            class="rounded-lg px-1 py-2 text-xs font-medium {current === l.value
              ? 'bg-brand-600 text-white shadow-sm'
              : 'text-slate-600 dark:text-slate-300'}"
            aria-pressed={current === l.value}
            onclick={() => setLevel(f.key, l.value)}>{l.label}</button
          >
        {/each}
      </div>
    </div>
  {/each}
  {#if error}<p class="text-sm text-red-600">{error}</p>{/if}
</section>

<section class="flex flex-col gap-3">
  <div class="px-1">
    <h2 class="text-lg font-semibold">2 · Rate the options</h2>
    {#if decision.options.length}
      <p class="text-sm {rated === decision.options.length ? 'text-emerald-600' : 'text-slate-500'}">
        You rated {rated} of {decision.options.length}.
        {#if rated === decision.options.length}
          All done! <button class="font-medium underline" onclick={onresults}>See the results</button>
        {:else}
          0 is bad, 5 is great. Saved as you go.
        {/if}
      </p>
    {:else}
      <p class="text-sm text-slate-500">No options yet. Add the first one below.</p>
    {/if}
  </div>

  {#each decision.options as o (o.id)}
    <OptionCard {decision} {me} option={o} saved={person?.ratings[o.id]} {onchange} />
  {/each}

  <form class="card flex flex-col gap-3" onsubmit={add}>
    <h3 class="font-semibold">Add an option</h3>
    <input bind:value={name} placeholder="Name, e.g. Flat on Main St" maxlength="120" />
    <input bind:value={note} placeholder="Link or note (optional)" maxlength="500" />
    {#if addError}<p class="text-sm text-red-600">{addError}</p>{/if}
    <button class="btn-secondary" disabled={adding}>{adding ? 'Adding…' : 'Add option'}</button>
  </form>
</section>
