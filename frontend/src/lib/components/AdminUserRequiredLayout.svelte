<script lang="ts">
	import type { Snippet } from 'svelte';

	import { is_admin_user } from '$lib/stores/auth.svelte';

	const { children }: { children: Snippet } = $props();
</script>

{#if !is_admin_user.value}
	<div class="flex h-screen flex-col items-center justify-center">
		<h1 class="mb-4 text-3xl font-bold">Access Denied</h1>
		<p class="text-lg">You do not have permission to view this page.</p>
	</div>
{:else}
	{@render children?.()}
{/if}
