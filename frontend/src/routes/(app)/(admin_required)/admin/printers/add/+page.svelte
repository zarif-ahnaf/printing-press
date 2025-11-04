<script lang="ts">
	import { LoaderCircle, Printer } from 'lucide-svelte';
	import { goto } from '$app/navigation';
	import { cn } from '$lib/utils';
	import { Button } from '$lib/components/ui/button';
	import { toast } from 'svelte-sonner';
	import {
		Card,
		CardHeader,
		CardContent,
		CardTitle,
		CardDescription
	} from '$lib/components/ui/card';
	import { Switch } from '$lib/components/ui/switch';
	import { Label } from '$lib/components/ui/label';
	import { Input } from '$lib/components/ui/input';
	import { client } from '$lib/client';
	import { token } from '$lib/stores/token.svelte';

	let isSubmitting = $state(false);
	let name = $state('');
	let isColor = $state(true);
	let simplexCharge = $state('');
	let duplexCharge = $state('');
	let imageFile = $state<File | null>(null);
	let imageUrl = $state<string | null>(null);

	async function handleSubmit(e: Event) {
		e.preventDefault();
		if (!name.trim()) {
			toast.error('Validation', { description: 'Printer name is required.' });
			return;
		}

		isSubmitting = true;

		try {
			const { data, error } = await client.POST('/api/admin/printers/add/', {
				headers: {
					Authorization: `Bearer ${token.value}`
				},
				body: {
					name: name.trim(),
					is_color: Boolean(isColor),
					simplex_charge: Number(simplexCharge),
					duplex_charge: Number(duplexCharge),
					image: imageFile as any // Override type for file upload
				},
				bodySerializer(body: Record<string, any>) {
					const fd = new FormData();
					for (const [key, value] of Object.entries(body)) {
						if (value instanceof File) {
							fd.append(key, value);
						} else if (value !== undefined && value !== null) {
							fd.append(key, String(value));
						} else {
							fd.append(key, '');
						}
					}
					return fd;
				}
			});

			if (error) {
				const errMsg = error || 'An unknown error occurred while adding the printer.';
				toast.error('Error', { description: String(errMsg) });
				return;
			}

			toast.success('Printer added!', {
				description: `"${name}" is now ready for use.`
			});
			goto(`./${data.id}`);
		} catch (err) {
			console.error(err);
			toast.error('Network error', {
				description: 'Could not reach the server.'
			});
		} finally {
			isSubmitting = false;
			if (imageUrl) {
				URL.revokeObjectURL(imageUrl);
				imageUrl = null;
			}
		}
	}

	function handleImageChange(e: Event) {
		const target = e.target as HTMLInputElement;
		const file = target.files?.[0] || null;
		imageFile = file;

		if (imageUrl) {
			URL.revokeObjectURL(imageUrl);
		}

		if (file) {
			imageUrl = URL.createObjectURL(file);
		} else {
			imageUrl = null;
		}
	}
</script>

<div class="flex min-h-[calc(100vh-4rem)] items-center justify-center p-4">
	<Card class="w-full max-w-md overflow-hidden rounded-xl border bg-card shadow-lg">
		<CardHeader class="space-y-2 text-center">
			<div
				class="mx-auto flex size-12 items-center justify-center rounded-lg bg-primary/10 text-primary"
			>
				<Printer class="size-6" />
			</div>
			<CardTitle class="text-xl font-semibold">Add New Printer</CardTitle>
			<CardDescription class="text-muted-foreground">
				Register a new printer with pricing and capabilities.
			</CardDescription>
		</CardHeader>
		<CardContent>
			<form class="space-y-5" onsubmit={handleSubmit}>
				<div class="space-y-2">
					<Label for="name" class="text-sm font-medium">Printer Name *</Label>
					<Input
						id="name"
						placeholder="E.g., Epson L3250"
						bind:value={name}
						required
						class="h-10"
					/>
				</div>

				<div
					class={cn(
						'flex items-center justify-between rounded-lg border p-4 transition-colors',
						isColor ? 'border-primary/30 bg-primary/5' : 'border-border'
					)}
				>
					<div class="space-y-0.5">
						<Label class="text-sm font-medium">Color Printer</Label>
						<p class="text-xs text-muted-foreground">
							{isColor ? 'Supports full-color printing' : 'Grayscale only'}
						</p>
					</div>
					<Switch
						aria-label="Toggle color capability"
						bind:checked={isColor}
						class="data-[state=checked]:bg-primary"
					/>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div class="space-y-2">
						<Label for="simplex" class="text-sm font-medium">Simplex Charge (BDT)</Label>
						<Input
							id="simplex"
							type="number"
							step="0.01"
							min="0"
							placeholder="e.g. 1.00"
							bind:value={simplexCharge}
							class="h-10"
						/>
						<p class="text-xs text-muted-foreground">Per single-sided page</p>
					</div>
					<div class="space-y-2">
						<Label for="duplex" class="text-sm font-medium">Duplex Charge (BDT)</Label>
						<Input
							id="duplex"
							type="number"
							step="0.01"
							min="0"
							placeholder="e.g. 0.75"
							bind:value={duplexCharge}
							class="h-10"
						/>
						<p class="text-xs text-muted-foreground">Per double-sided page</p>
					</div>
				</div>

				<div class="space-y-2">
					<Label for="image" class="text-sm font-medium">Printer Image (Optional)</Label>
					<Input
						id="image"
						type="file"
						accept="image/*"
						onchange={handleImageChange}
						class="h-10"
					/>
				</div>

				{#if imageUrl}
					<div class="space-y-2">
						<Label class="text-sm font-medium">Preview</Label>
						<div class="flex justify-center">
							<img
								src={imageUrl}
								alt="Printer preview"
								class="max-h-40 w-auto rounded-md border object-contain"
							/>
						</div>
					</div>
				{/if}

				<Button
					type="submit"
					class={cn('w-full py-2.5 text-sm font-medium', isSubmitting && 'opacity-80')}
					disabled={isSubmitting}
				>
					{#if isSubmitting}
						<LoaderCircle class="mr-2 size-4 animate-spin" />
						Creating...
					{:else}
						Add Printer
					{/if}
				</Button>
			</form>
		</CardContent>
	</Card>
</div>
