<script lang="ts">
  import { api, type Decision, type Me } from '../lib/api';

  let { decision, onjoined, onpeek }: { decision: Decision; onjoined: (m: Me) => void; onpeek: () => void } = $props();

  let name = $state('');
  let error = $state('');
  let busy = $state(false);

  async function join(e: SubmitEvent) {
    e.preventDefault();
    if (!name.trim()) return (error = 'Enter your name.');
    busy = true;
    error = '';
    try {
      onjoined(await api.join(decision.id, name.trim()));
    } catch (err) {
      error = (err as Error).message;
    } finally {
      busy = false;
    }
  }
</script>

<main class="mx-auto flex min-h-dvh max-w-md flex-col justify-center gap-5 px-4 py-10">
  <div class="text-center">
    <p class="text-sm font-medium text-brand-600">You're invited to help decide</p>
    <h1 class="mt-1 text-2xl font-bold break-words">{decision.title}</h1>
  </div>

  <ol class="card flex flex-col gap-2 text-sm">
    <li><b>1.</b> Say how much each point matters to you: {decision.features.map((f) => f.label).join(', ')}.</li>
    <li><b>2.</b> Rate each option, and add your own.</li>
    <li><b>3.</b> See everyone's answers combined into one ranking.</li>
  </ol>

  <form class="flex flex-col gap-3" onsubmit={join}>
    <label class="flex flex-col gap-1">
      <span class="text-sm font-medium">Your name</span>
      <!-- svelte-ignore a11y_autofocus -->
      <input bind:value={name} placeholder="e.g. Alice" maxlength="40" autocomplete="given-name" autofocus />
    </label>
    {#if error}<p class="text-sm text-red-600">{error}</p>{/if}
    <button class="btn-primary" disabled={busy}>{busy ? 'Joining…' : 'Join'}</button>
  </form>

  {#if decision.people.length}
    <p class="text-center text-sm text-slate-500">
      Already in: {decision.people.map((p) => p.name).join(', ')}.
      <button class="underline" onclick={onpeek}>See the results so far</button>
    </p>
  {/if}
</main>
