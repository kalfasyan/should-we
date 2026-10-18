<script lang="ts">
  import type { Decision } from '../lib/api';
  import { asLink, formatScore } from '../lib/words';

  let { decision }: { decision: Decision } = $props();

  const names = $derived(Object.fromEntries(decision.people.map((p) => [p.id, p.name])));
  const options = $derived(Object.fromEntries(decision.options.map((o) => [o.id, o])));
  const total = $derived(decision.options.length);
  let open = $state<string | null>(null);
</script>

{#if total === 0}
  <p class="card text-slate-500">No options yet. Once people add and rate options, the ranking shows up here.</p>
{:else}
  <ol class="flex flex-col gap-3">
    {#each decision.results as r, i (r.option)}
      {@const o = options[r.option]}
      {@const link = asLink(o.note)}
      <li class="card flex flex-col gap-2 {i === 0 && r.rated_by ? 'border-brand-500 ring-1 ring-brand-500' : ''}">
        <button class="flex items-center gap-3 text-left" onclick={() => (open = open === r.option ? null : r.option)}>
          <span class="w-8 shrink-0 text-center text-lg font-bold text-slate-400">{r.rated_by ? (i === 0 ? '🏆' : i + 1) : '–'}</span>
          <span class="min-w-0 flex-1">
            <span class="block font-semibold break-words">{o.name}</span>
            <span class="block text-xs text-slate-500">
              {#if r.rated_by}
                Rated by {r.rated_by} of {decision.people.length}{#if r.split} · 🤔 opinions split{/if}
              {:else}
                Nobody rated this yet
              {/if}
            </span>
          </span>
          {#if r.rated_by}
            <span class="text-right"><span class="text-2xl font-bold">{formatScore(r.score)}</span><span class="text-sm text-slate-400">/5</span></span>
          {/if}
        </button>
        {#if r.rated_by}
          <div class="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div class="h-full rounded-full bg-brand-600" style="width: {(r.score / 5) * 100}%"></div>
          </div>
        {/if}
        {#if open === r.option}
          <div class="flex flex-col gap-1 border-t border-slate-100 pt-2 text-sm dark:border-slate-800">
            {#if link}
              <a href={link} target="_blank" rel="noopener noreferrer" class="truncate text-brand-600 underline">{link}</a>
            {:else if o.note}
              <p class="text-slate-500">{o.note}</p>
            {/if}
            {#each r.by_person as p (p.person)}
              <div class="flex justify-between"><span>{names[p.person]}</span><span class="font-medium">{formatScore(p.score)}</span></div>
            {/each}
            {#each decision.people.filter((p) => !r.by_person.some((b) => b.person === p.id)) as p (p.id)}
              <div class="flex justify-between text-slate-400"><span>{p.name}</span><span>not rated</span></div>
            {/each}
          </div>
        {/if}
      </li>
    {/each}
  </ol>
  <p class="px-1 text-xs text-slate-500">
    Each person's ratings are weighted by what matters to them, then everyone's scores are averaged. Tap an option to see who gave what.
  </p>
{/if}
