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
	import { LOGIN_URL } from '$lib/constants/backend';
	import { Eye, EyeOff } from 'lucide-svelte';
	import { token } from '$lib/stores/token.svelte';
	import { is_logged_in } from '$lib/stores/auth.svelte';

	let username = $state('');
	let password = $state('');
	let loading = $state(false);
	let showPassword = $state(false);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		loading = true;

		try {
			const formData = new FormData();
			formData.append('username', username);
			formData.append('password', password);

			const res = await fetch(LOGIN_URL, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					username: username.trim(),
					password: password.trim()
				})
			});

			let data: { token?: string } = {};
			data = await res.json();

			if (res.ok && typeof data.token === 'string') {
				token.set(data.token);
				toast.success('Login successful!');
				setTimeout(() => {
					window.location.href = '/dashboard';
				}, 1000);
			} else {
				toast.error('Invalid username or password.');
			}
		} catch (err) {
			console.error('Login network error:', err);
			toast.error('Network error. Please try again.');
		} finally {
			loading = false;
		}
	}
	function togglePasswordVisibility() {
		showPassword = !showPassword;
	}
</script>

{#if is_logged_in}
	<div class="flex min-h-screen items-center justify-center bg-background p-4">
		<Card class="w-full max-w-sm">
			<CardHeader>
				<CardTitle class="text-2xl">Already Logged In</CardTitle>
				<CardDescription>You’re authenticated.</CardDescription>
			</CardHeader>
			<CardContent class="space-y-4 text-center">
				<p class="text-sm text-muted-foreground">Go to your dashboard or continue working.</p>
				<Button onclick={() => (window.location.href = '/dashboard')} class="w-full">
					Go to Dashboard
				</Button>
			</CardContent>
		</Card>
	</div>
{:else}
	<div class="flex min-h-screen items-center justify-center bg-background p-4">
		<Card class="w-full max-w-sm">
			<CardHeader>
				<CardTitle class="text-2xl">Login</CardTitle>
				<CardDescription>Enter your credentials to access your account.</CardDescription>
			</CardHeader>
			<CardContent>
				<form onsubmit={handleSubmit} class="space-y-4">
					<div class="space-y-2">
						<Label for="username">Username</Label>
						<Input
							id="username"
							type="text"
							bind:value={username}
							required
							autocomplete="username"
						/>
					</div>
					<div class="space-y-2">
						<Label for="password">Password</Label>
						<div class="relative">
							<Input
								id="password"
								type={showPassword ? 'text' : 'password'}
								bind:value={password}
								required
								autocomplete="current-password"
								class="pr-10"
							/>
							<button
								type="button"
								onclick={togglePasswordVisibility}
								class="absolute inset-y-0 right-0 flex items-center pr-3 text-muted-foreground hover:text-foreground focus:outline-none"
								aria-label={showPassword ? 'Hide password' : 'Show password'}
							>
								{#if showPassword}
									<EyeOff size={20} />
								{:else}
									<Eye size={20} />
								{/if}
							</button>
						</div>
					</div>
					<Button type="submit" class="w-full" disabled={loading}>
						{loading ? 'Signing in...' : 'Sign In'}
					</Button>
				</form>
			</CardContent>
		</Card>
	</div>
{/if}
