<script lang="ts">
	import type { Snippet } from 'svelte';

	import { is_logged_in, is_fetched } from '$lib/stores/auth.svelte';
	import { LoaderCircle } from 'lucide-svelte';

	const { children }: { children: Snippet } = $props();
</script>

{#if is_fetched.value === false}
	<div class="flex h-screen flex-col items-center justify-center gap-4">
		<LoaderCircle class="h-8 w-8 animate-spin text-muted-foreground" />
		<p class="text-lg text-muted-foreground">Loading...</p>
	</div>
{:else if !is_logged_in.value}}
	<div class="height flex flex-col items-center justify-center">
		<h1 class="mb-4 text-3xl font-bold">Access Denied</h1>
		<p class="text-lg">You must be logged in to see this page.</p>
	</div>
{:else}
	{@render children?.()}
{/if}

<style>
	.height {
		height: calc(100vh - var(--spacing) * 16);
	}
</style>
