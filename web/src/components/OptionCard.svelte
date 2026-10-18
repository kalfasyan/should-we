<script lang="ts">
  import { api, type Decision, type Me, type Option, type Scores } from '../lib/api';
  import { asLink, ratingWord } from '../lib/words';

  let {
    decision,
    me,
    option,
    saved,
    onchange,
  }: { decision: Decision; me: Me; option: Option; saved: Scores | undefined; onchange: () => void } = $props();

  // sliders start in the middle until you rate; your own moves are never
  // overwritten by the background refresh
  // svelte-ignore state_referenced_locally
  let scores = $state<Scores>(
    Object.fromEntries(decision.features.map((f) => [f.key, saved?.[f.key] ?? 2.5])),
  );
  let error = $state('');
  let editingNote = $state(false);
  // svelte-ignore state_referenced_locally
  let noteDraft = $state(option.note);
  let confirmRemove = $state(false);
  const link = $derived(asLink(option.note));

  async function save() {
    try {
      await api.rate(decision.id, me, option.id, $state.snapshot(scores));
      error = '';
      onchange();
    } catch (e) {
      error = (e as Error).message;
    }
  }

  async function saveNote() {
    try {
      await api.editNote(decision.id, me, option.id, noteDraft.trim());
      editingNote = false;
      onchange();
    } catch (e) {
      error = (e as Error).message;
    }
  }

  async function remove() {
    if (!confirmRemove) {
      confirmRemove = true;
      setTimeout(() => (confirmRemove = false), 3000);
      return;
    }
    try {
      await api.removeOption(decision.id, me, option.id);
      onchange();
    } catch (e) {
      error = (e as Error).message;
    }
  }
</script>

<article class="card flex flex-col gap-3">
  <div class="flex items-start justify-between gap-2">
    <div class="min-w-0">
      <h3 class="font-semibold break-words">{option.name}</h3>
      {#if !editingNote && option.note}
        {#if link}
          <a href={link} target="_blank" rel="noopener noreferrer" class="block truncate text-sm text-brand-600 underline">{link}</a>
        {:else}
          <p class="text-sm break-words text-slate-500">{option.note}</p>
        {/if}
      {/if}
    </div>
    <span class="shrink-0 rounded-full px-2 py-1 text-xs font-medium {saved
      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200'
      : 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200'}">{saved ? '✓ Rated' : 'Not rated yet'}</span
    >
  </div>

  {#each decision.features as f (f.key)}
    <label class="flex flex-col gap-1">
      <span class="flex justify-between text-sm">
        <span>{f.label}</span>
        <span class="font-medium {saved ? '' : 'text-slate-400'}">{scores[f.key]} · {ratingWord(scores[f.key])}</span>
      </span>
      <input type="range" min="0" max="5" step="0.5" bind:value={scores[f.key]} onchange={save} aria-label="{option.name}: {f.label}" />
    </label>
  {/each}

  {#if !saved}
    <button class="text-left text-sm text-brand-600" onclick={save}>Looks right? Save these ratings</button>
  {/if}

  {#if editingNote}
    <div class="flex gap-2">
      <input class="min-w-0 flex-1" bind:value={noteDraft} placeholder="Link or note" maxlength="500" />
      <button class="btn-secondary px-4 py-2 text-sm" onclick={saveNote}>Save</button>
    </div>
  {/if}

  <div class="flex gap-4 text-sm text-slate-500">
    {#if !editingNote}
      <button onclick={() => ((noteDraft = option.note), (editingNote = true))}>{option.note ? 'Edit note' : 'Add note'}</button>
    {/if}
    <button class={confirmRemove ? 'font-medium text-red-600' : ''} onclick={remove}
      >{confirmRemove ? 'Tap again to remove for everyone' : 'Remove'}</button
    >
  </div>
  {#if error}<p class="text-sm text-red-600">{error}</p>{/if}
</article>
