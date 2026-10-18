<script lang="ts">
  import { route, decisionId } from './lib/route.svelte';
  import Home from './components/Home.svelte';
  import DecisionPage from './components/DecisionPage.svelte';

  const id = $derived(decisionId(route.path));
</script>

{#if id}
  {#key id}
    <DecisionPage {id} />
  {/key}
{:else}
  <Home />
{/if}
