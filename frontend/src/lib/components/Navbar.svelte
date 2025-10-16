<script lang="ts">
	import { Button } from '$lib/components/ui/button';
	import { Avatar, AvatarFallback, AvatarImage } from '$lib/components/ui/avatar';
	import {
		DropdownMenu,
		DropdownMenuContent,
		DropdownMenuItem,
		DropdownMenuTrigger
	} from '$lib/components/ui/dropdown-menu';
	import { first_name, last_name, user_email } from '$lib/stores/auth.svelte';
	import { sha256 } from '$lib/functions/sha265';
	import { navbar_state } from '$lib/stores/navbar.svelte';

	let initials = $state('');
	$effect(() => {
		initials =
			`${first_name.value?.charAt(0) ?? ''}${last_name.value?.charAt(0) ?? ''}`.toUpperCase();
	});

	let hashed_email = $state('');
	$effect(() => {
		if (user_email.value) {
			console.log(user_email.value);
			sha256(user_email.value).then((hash) => {
				hashed_email = hash;
			});
		}
	});
</script>

{#if navbar_state.visible}
	<nav class="sticky top-0 z-50 w-full bg-background shadow-sm">
		<div class="mx-auto px-4 sm:px-6 lg:px-8">
			<div class="flex h-16 items-center justify-between">
				<div class="flex-shrink-0">
					<a href="/" class="text-xl font-bold text-foreground">MyBrand</a>
				</div>

				<div class="hidden items-center space-x-4 md:flex">
					<!-- Replace `true` with your auth condition when needed -->
					{#if true}
						<DropdownMenu>
							<DropdownMenuTrigger>
								<Button variant="ghost" class="relative h-10 w-10 p-0">
									<Avatar class="h-10 w-10">
										<AvatarImage
											src="https://seccdn.libravatar.org/avatar/{hashed_email}?size=512"
											alt="Avatar of {initials}"
										/>
										<AvatarFallback>{initials}</AvatarFallback>
									</Avatar>
								</Button>
							</DropdownMenuTrigger>
							<DropdownMenuContent align="end">
								<DropdownMenuItem>
									<a href="/logout">Logout</a>
								</DropdownMenuItem>
							</DropdownMenuContent>
						</DropdownMenu>
					{:else}
						<Button variant="default">
							<a href="/login">Login</a>
						</Button>
					{/if}
				</div>
			</div>
		</div>
	</nav>
{/if}
