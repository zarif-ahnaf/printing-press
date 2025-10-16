<script lang="ts">
	import { navbar_state } from '$lib/stores/navbar.svelte';

	const { children } = $props();

	$effect.pre(() => {
		navbar_state.hide();
	});
</script>

{@render children?.()}
