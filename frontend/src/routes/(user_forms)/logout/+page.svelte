<script lang="ts">
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui/button';
	import {
		Card,
		CardContent,
		CardHeader,
		CardTitle,
		CardDescription
	} from '$lib/components/ui/card';
	import { LogOut } from 'lucide-svelte';
	import { token } from '$lib/stores/token.svelte';
	import { client } from '$lib/client';

	let next = $state('/login');

	onMount(async () => {
		// Clear auth state
		token.set(null);
		// Send logout request to backend
		await client.DELETE('/api/user/logout/').catch((error) => {
			console.error('Error during logout request:', error);
		});

		// Parse and validate `next` from URL
		const urlParams = new URLSearchParams(window.location.search);
		const nextParam = urlParams.get('next');
		if (nextParam && isValidRedirectPath(nextParam)) {
			next = nextParam;
		}
	});

	function isValidRedirectPath(path: string): boolean {
		try {
			const url = new URL(path, window.location.origin);
			return url.origin === window.location.origin && path.startsWith('/');
		} catch {
			return false;
		}
	}

	function handleRedirect() {
		window.location.href = next;
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-background p-4">
	<Card class="w-full max-w-sm text-center">
		<CardHeader class="items-center">
			<div class="mb-3 rounded-full bg-destructive/10 p-2 text-destructive">
				<LogOut size={24} />
			</div>
			<CardTitle class="text-2xl">Signed Out</CardTitle>
			<CardDescription>You’ve been successfully logged out.</CardDescription>
		</CardHeader>
		<CardContent class="space-y-4">
			<p class="text-sm text-muted-foreground">
				Your session has ended. All credentials have been cleared from this device.
			</p>
			<Button variant="default" class="w-full" onclick={handleRedirect}>
				{next === '/login' ? 'Sign In Again' : 'Go to Destination'}
			</Button>
		</CardContent>
	</Card>
</div>
