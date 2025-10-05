<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import {
		Card,
		CardContent,
		CardDescription,
		CardHeader,
		CardTitle
	} from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { toast } from 'svelte-sonner';

	let username = '';
	let password = '';
	let loading = false;

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		loading = true;

		const formData = new FormData();
		formData.append('username', username);
		formData.append('password', password);

		try {
			const res = await fetch('/api/user/login', {
				method: 'POST',
				body: new URLSearchParams(formData as any), // converts to x-www-form-urlencoded
				headers: {
					'Content-Type': 'application/x-www-form-urlencoded'
				}
			});

			const data = await res.json();

			if (res.ok) {
				// Save token (e.g., in localStorage or cookie)
				localStorage.setItem('auth_token', data.token);
				// Redirect to dashboard or home
				window.location.href = '/dashboard'; // or use goto() from $app/navigation
			} else {
				toast({
					title: 'Login failed',
					description: 'Invalid username or password.',
					variant: 'destructive'
				});
			}
		} catch (err) {
			toast({
				title: 'Network error',
				description: 'Could not reach the server.',
				variant: 'destructive'
			});
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-background p-4">
	<Card class="w-full max-w-sm">
		<CardHeader>
			<CardTitle class="text-2xl">Login</CardTitle>
			<CardDescription>Enter your credentials to access your account.</CardDescription>
		</CardHeader>
		<CardContent>
			<form on:submit={handleSubmit} class="space-y-4">
				<div class="space-y-2">
					<Label for="username">Username</Label>
					<Input id="username" type="text" bind:value={username} required autocomplete="username" />
				</div>
				<div class="space-y-2">
					<Label for="password">Password</Label>
					<Input
						id="password"
						type="password"
						bind:value={password}
						required
						autocomplete="current-password"
					/>
				</div>
				<Button type="submit" class="w-full" disabled={loading}>
					{loading ? 'Signing in...' : 'Sign In'}
				</Button>
			</form>
		</CardContent>
	</Card>
</div>
