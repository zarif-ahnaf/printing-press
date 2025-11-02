<!-- src/routes/printers/[id]/+page.svelte -->
<script lang="ts">
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import {
		Printer,
		Palette,
		DollarSign,
		Info,
		AlertCircle,
		CheckCircle,
		Archive,
		Edit3,
		Save,
		X
	} from 'lucide-svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Switch } from '$lib/components/ui/switch';
	import { Label } from '$lib/components/ui/label';
	import { client } from '$lib/client';
	import { cn } from '$lib/utils';
	import { token } from '$lib/stores/token.svelte';

	// Define the shape
	type PrinterSchema = {
		id: number;
		name: string;
		is_color: boolean;
		simplex_charge: number;
		duplex_charge: number;
		image?: string | null;
		decomissioned: boolean;
	};

	// Use $state for reactivity — Svelte 5 style
	let printer = $state<PrinterSchema | null>(null);
	let isLoading = $state(true);
	let isEditing = $state(false);
	let error = $state<string | null>(null);
	let isSaving = $state(false);

	async function fetchPrinter(id: number) {
		isLoading = true;
		error = null;
		try {
			const { data, error: fetchError } = await client.GET('/api/printers/{printer_id}', {
				params: { path: { printer_id: id } }
			});
			if (fetchError) throw new Error(fetchError);
			printer = data;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Unknown error';
		} finally {
			isLoading = false;
		}
	}

	async function savePrinter() {
		if (!printer) return;
		isSaving = true;
		error = null;
		try {
			const { data, error: saveError } = await client.PATCH('/api/admin/printers/{printer_id}', {
				headers: {
					Authorization: `Bearer ${token.value}`
				},
				params: { path: { printer_id: printer.id } },
				body: {
					name: printer.name,
					is_color: printer.is_color,
					simplex_charge: printer.simplex_charge,
					duplex_charge: printer.duplex_charge,
					decomissioned: printer.decomissioned,
					image: printer.image as any
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
			if (saveError) throw new Error(saveError);
			printer = data;
			isEditing = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to save changes';
		} finally {
			isSaving = false;
		}
	}

	function cancelEdit() {
		// Refetch to discard local changes (or keep a snapshot if needed)
		if (printer) {
			fetchPrinter(printer.id);
			isEditing = false;
		}
	}

	onMount(() => {
		const id = Number(page.params.id);
		if (isNaN(id)) {
			error = 'Invalid printer ID';
			isLoading = false;
		} else {
			fetchPrinter(id);
		}
	});
</script>

<div class="bg-background p-6">
	<div class="mx-auto max-w-5xl">
		{#if isLoading}
			<!-- Skeletons (same as before) -->
			<div class="space-y-8">
				<div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
					<div class="flex items-center gap-4">
						<Skeleton class="h-12 w-12 rounded-xl" />
						<div class="space-y-2">
							<Skeleton class="h-7 w-64" />
							<Skeleton class="h-4 w-24" />
						</div>
					</div>
					<Skeleton class="h-7 w-32 rounded-full" />
				</div>
				<div class="grid grid-cols-1 gap-8 lg:grid-cols-3">
					<div class="lg:col-span-1">
						<Skeleton class="aspect-4/5 w-full rounded-xl" />
					</div>
					<div class="space-y-6 lg:col-span-2">
						<Skeleton class="h-32 w-full rounded-xl" />
						<Skeleton class="h-32 w-full rounded-xl" />
					</div>
				</div>
			</div>
		{:else if error}
			<div
				class="flex items-start gap-4 rounded-xl border border-destructive/50 bg-destructive/10 p-6"
			>
				<AlertCircle class="mt-0.5 h-6 w-6 shrink-0 text-destructive" />
				<div>
					<h2 class="text-xl font-bold text-foreground">Error</h2>
					<p class="mt-1 text-muted-foreground">{error}</p>
				</div>
			</div>
		{:else if printer}
			<div
				class="relative overflow-hidden rounded-2xl border border-border bg-card p-8 shadow-xl backdrop-blur-xl"
			>
				{#if printer.image}
					<div
						class="absolute inset-0 z-0 opacity-60"
						style="top: 10%; left: 5%; width: 48%; height: 60%;"
					>
						<div
							class="h-full w-full rounded-xl"
							style="
								background: linear-gradient(135deg, var(--primary)/0.4, var(--accent)/0.3);
								filter: blur(24px);
								transform: scale(1.1);
							"
						></div>
					</div>
				{/if}

				<div class="relative z-10">
					<div class="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
						<div class="flex items-center gap-4">
							<div class="rounded-xl bg-primary/10 p-3">
								<Printer class="h-8 w-8 text-primary" />
							</div>
							{#if isEditing}
								<Input
									bind:value={printer.name}
									class="w-auto border-none bg-transparent px-0 text-2xl font-bold focus:ring-0"
								/>
							{:else}
								<div>
									<h1 class="text-3xl font-bold text-foreground">{printer.name}</h1>
									<p class="text-muted-foreground">ID: #{printer.id}</p>
								</div>
							{/if}
						</div>

						<div class="flex items-center gap-2">
							{#if isEditing}
								<Button variant="outline" size="sm" onclick={cancelEdit} disabled={isSaving}>
									<X class="mr-2 h-4 w-4" /> Cancel
								</Button>
								<Button size="sm" onclick={savePrinter} disabled={isSaving}>
									<Save class="mr-2 h-4 w-4" />
									{isSaving ? 'Saving...' : 'Save'}
								</Button>
							{:else}
								<Button size="sm" variant="outline" onclick={() => (isEditing = true)}>
									<Edit3 class="mr-2 h-4 w-4" /> Edit
								</Button>
							{/if}
						</div>
					</div>

					<div class="grid grid-cols-1 gap-8 lg:grid-cols-3">
						<div class="lg:col-span-1">
							{#if printer.image}
								<div
									class="group relative flex aspect-4/5 items-center justify-center overflow-hidden rounded-xl bg-muted"
								>
									<img
										src={printer.image}
										alt={printer.name}
										class="h-full w-full object-cover"
										loading="lazy"
									/>
									<div
										class="absolute inset-0 rounded-xl opacity-0 transition-opacity group-hover:opacity-30"
										style="background: radial-gradient(circle, var(--primary)/0.6, transparent 70%);"
									></div>
								</div>
							{:else}
								<div class="flex aspect-4/5 items-center justify-center rounded-xl bg-muted p-8">
									<Printer class="h-16 w-16 text-muted-foreground" />
								</div>
							{/if}
						</div>

						<div class="space-y-6 lg:col-span-2">
							<div class="rounded-xl bg-muted/50 p-6">
								<div class="mb-4 flex items-center gap-2">
									<Info class="h-5 w-5 text-primary" />
									<h2 class="text-xl font-semibold text-foreground">Specifications</h2>
								</div>
								<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
									<div>
										<Label class="text-sm text-muted-foreground">Color Support</Label>
										{#if isEditing}
											<div class="mt-2 flex items-center gap-2">
												<Switch bind:checked={printer.is_color} />
												<span class="text-sm text-foreground">
													{printer.is_color ? 'Full Color' : 'Grayscale Only'}
												</span>
											</div>
										{:else}
											<div class="mt-1 flex items-center gap-2">
												<Palette class="h-4 w-4 text-accent-foreground" />
												<span class="font-medium text-foreground">
													{printer.is_color ? 'Full Color' : 'Grayscale Only'}
												</span>
											</div>
										{/if}
									</div>
									<div>
										<Label class="text-sm text-muted-foreground">Status</Label>
										{#if isEditing}
											<div class="mt-2 flex items-center gap-2">
												<Switch bind:checked={printer.decomissioned} />
												<span class="text-sm text-foreground">
													{!printer.decomissioned ? 'Operational' : 'Decommissioned'}
												</span>
											</div>
										{:else}
											<span class="font-medium text-foreground">
												{printer.decomissioned ? 'Decommissioned' : 'Operational'}
											</span>
										{/if}
									</div>
								</div>
							</div>

							<div class="rounded-xl bg-muted/50 p-6">
								<div class="mb-4 flex items-center gap-2">
									<DollarSign class="text-success h-5 w-5" />
									<h2 class="text-xl font-semibold text-foreground">Pricing</h2>
								</div>
								<div class="grid grid-cols-2 gap-4">
									<div class="rounded-lg bg-primary/5 p-4">
										<Label class="text-sm text-primary/80">Simplex (Single-sided)</Label>
										{#if isEditing}
											<Input
												type="number"
												step="0.01"
												min="0"
												bind:value={printer.simplex_charge}
												class="mt-1 w-full"
											/>
										{:else}
											<p class="mt-1 text-xl font-bold text-foreground">
												{printer.simplex_charge.toFixed(2)} BDT
											</p>
										{/if}
									</div>
									<div class="rounded-lg bg-primary/5 p-4">
										<Label class="text-sm text-secondary-foreground">Duplex (Double-sided)</Label>
										{#if isEditing}
											<Input
												type="number"
												step="0.01"
												min="0"
												bind:value={printer.duplex_charge}
												class="mt-1 w-full"
											/>
										{:else}
											<p class="mt-1 text-xl font-bold text-foreground">
												{printer.duplex_charge.toFixed(2)} BDT
											</p>
										{/if}
									</div>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		{/if}
	</div>
</div>
