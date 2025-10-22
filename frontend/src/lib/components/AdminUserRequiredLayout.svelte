<script lang="ts">
	import type { Snippet } from 'svelte';
	import { is_admin_user, is_fetched } from '$lib/stores/auth.svelte';
	import { LoaderCircle } from 'lucide-svelte';

	const { children }: { children: Snippet } = $props();
</script>

{#if is_fetched.value === false}
	<div class="flex h-screen flex-col items-center justify-center gap-4">
		<LoaderCircle class="h-8 w-8 animate-spin text-muted-foreground" />
		<p class="text-lg text-muted-foreground">Loading...</p>
	</div>
{:else if !is_admin_user.value}
	<div
		class="flex h-[calc(100vh-var(--spacing)*16)] flex-col items-center justify-center px-4 text-center"
	>
		<h1 class="mb-2 text-3xl font-bold tracking-tight">Access Denied</h1>
		<p class="text-muted-foreground">You don’t have permission to view this page.</p>
	</div>
{:else}
	{@render children?.()}
{/if}
