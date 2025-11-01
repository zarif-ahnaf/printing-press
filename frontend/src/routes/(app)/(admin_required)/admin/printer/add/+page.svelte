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

	let isSubmitting = $state(false);
	let name = $state('');
	let isColor = $state(true);
	let simplexCharge = $state('1.00');
	let duplexCharge = $state('0.75');
	let imageFile = $state<File | null>(null);

	async function handleSubmit(e: Event) {
		e.preventDefault();
		isSubmitting = true;

		const formData = new FormData();
		formData.append('name', name);
		formData.append('is_color', isColor.toString());
		if (simplexCharge) formData.append('simplex_charge', simplexCharge);
		if (duplexCharge) formData.append('duplex_charge', duplexCharge);
		if (imageFile) formData.append('image', imageFile);

		try {
			const res = await fetch('/api/admin/printers/add/', {
				method: 'POST',
				body: formData
				// ⚠️ Do NOT set Content-Type — browser must set boundary
			});

			const data: { message?: string; [key: string]: unknown } = await res.json();

			if (!res.ok) {
				const errMsg = (data?.message || data?.detail || 'Failed to add printer') as string;
				toast.error('Error', { description: errMsg });
				return;
			}

			toast.success('Printer added!', {
				description: `"${name}" is now ready for use.`
			});
			goto('/printers');
		} catch (err) {
			console.error(err);
			toast.error('Network error', {
				description: 'Could not reach the server.'
			});
		} finally {
			isSubmitting = false;
		}
	}

	function handleImageChange(e: Event) {
		const target = e.target as HTMLInputElement;
		imageFile = target.files?.[0] || null;
	}
</script>

<div class="container max-w-2xl py-8">
	<Card>
		<CardHeader>
			<CardTitle class="flex items-center gap-2">
				<Printer class="size-5" />
				Add New Printer
			</CardTitle>
			<CardDescription>Register a new printer with pricing and capabilities.</CardDescription>
		</CardHeader>
		<CardContent>
			<form class="space-y-6" onsubmit={handleSubmit}>
				<div class="space-y-2">
					<Label for="name">Printer Name *</Label>
					<Input id="name" placeholder="E.g., Epson L3250" bind:value={name} required />
				</div>

				<div class="flex items-center justify-between rounded-lg border p-4">
					<div class="space-y-0.5">
						<Label>Color Printer</Label>
						<p class="text-sm text-muted-foreground">
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
						<Label for="simplex">Simplex Charge (BDT)</Label>
						<Input
							id="simplex"
							type="number"
							step="0.01"
							min="0"
							placeholder="1.00"
							bind:value={simplexCharge}
						/>
						<p class="text-xs text-muted-foreground">Per single-sided page</p>
					</div>
					<div class="space-y-2">
						<Label for="duplex">Duplex Charge (BDT)</Label>
						<Input
							id="duplex"
							type="number"
							step="0.01"
							min="0"
							placeholder="0.75"
							bind:value={duplexCharge}
						/>
						<p class="text-xs text-muted-foreground">Per double-sided page</p>
					</div>
				</div>

				<div class="space-y-2">
					<Label for="image">Printer Image (Optional)</Label>
					<Input id="image" type="file" accept="image/*" onchange={handleImageChange} />
				</div>

				<Button
					type="submit"
					class={cn('w-full', isSubmitting && 'opacity-80')}
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
