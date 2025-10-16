<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import { Toaster } from '$lib/components/ui/sonner/index.js';
	import { ModeWatcher } from 'mode-watcher';
	import { USER_ENDPOINT } from '$lib/constants/backend';
	import { token } from '$lib/stores/token.svelte';
	import { is_admin_user, is_logged_in } from '$lib/stores/auth.svelte';

	let { children } = $props();

	$effect.pre(() => {
		const currentToken = token.value;

		if (currentToken) {
			fetch(USER_ENDPOINT, {
				headers: {
					Authorization: `Bearer ${currentToken}`
				}
			})
				.then(async (res) => {
					if (res.ok) {
						is_logged_in.set(true);
						const data = await res.json();
						is_admin_user.set(data?.is_superuser);
					} else {
						is_logged_in.set(false);
						is_admin_user.set(null);
						token.set(null);
					}
				})
				.catch(() => {
					is_logged_in.set(false);
					is_admin_user.set(null);
				});
		} else {
			is_logged_in.set(false);
			is_admin_user.set(null);
		}
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<ModeWatcher />
<Toaster />

{@render children?.()}
