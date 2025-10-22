<script lang="ts">
	import LoginRequiredLayout from '$lib/components/LoginRequiredLayout.svelte';
	const { children } = $props();
</script>

<LoginRequiredLayout>
	{@render children()}
</LoginRequiredLayout>
