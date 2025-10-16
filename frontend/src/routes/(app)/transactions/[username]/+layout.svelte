<script lang="ts">
	import AdminUserRequiredLayout from '$lib/components/AdminUserRequiredLayout.svelte';
	const { children } = $props();
</script>

<AdminUserRequiredLayout>
	{@render children()}
</AdminUserRequiredLayout>
