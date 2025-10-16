<script lang="ts">
	import type { Snippet } from 'svelte';

	import { is_admin_user } from '$lib/stores/auth.svelte';

	const { children }: { children: Snippet } = $props();
</script>

{#if !is_admin_user.value}
	<h1 class="mb-4 text-3xl font-bold">Access Denied</h1>
	<p class="text-lg">You do not have permission to view this page.</p>
{:else}
	{@render children?.()}
{/if}
