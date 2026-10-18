<script lang="ts">
  // The chips editor for "what matters": used when starting a decision and when editing one.
  let { points = $bindable(), draft = $bindable('') }: { points: string[]; draft?: string } = $props();

  export function addDraft() {
    const p = draft.trim();
    if (p && !points.some((x) => x.toLowerCase() === p.toLowerCase())) points = [...points, p];
    draft = '';
  }
</script>

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
        addDraft();
      }
    }}
  />
  <button type="button" class="btn-secondary px-4 py-3" onclick={addDraft} disabled={!draft.trim()}>Add</button>
</div>
