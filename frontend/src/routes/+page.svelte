<script lang="ts">
	import { is_logged_in } from '$lib/stores/auth.svelte';
</script>

{is_logged_in.value}
