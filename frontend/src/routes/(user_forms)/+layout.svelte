<script lang="ts">
	import { navbar_state } from '$lib/stores/navbar.svelte';

	const { children } = $props();

	let oldState = $state(navbar_state.state);

	$effect.pre(() => {
		navbar_state.hide();

		return () => {
			if (oldState === 'visible') {
				navbar_state.show();
			} else if (oldState === 'hidden') {
				navbar_state.hide();
			}
		};
	});
</script>

{@render children?.()}
