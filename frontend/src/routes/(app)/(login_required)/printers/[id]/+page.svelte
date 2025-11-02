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
		Archive
	} from 'lucide-svelte';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { client } from '$lib/client';

	type PrinterOutSchema = {
		id: number;
		name: string;
		is_color: boolean;
		simplex_charge: number;
		duplex_charge: number;
		image?: string | null;
		decomissioned: boolean;
	};

	let printer: PrinterOutSchema | null = null;
	let isLoading = true;
	let error: string | null = null;

	async function fetchPrinter(id: number) {
		try {
			const { data, error } = await client.GET('/api/printers/{printer_id}', {
				params: {
					path: {
						printer_id: id
					}
				},
				headers: { 'Content-Type': 'application/json' }
			});

			if (error) throw new Error(error);
			printer = data;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Unknown error';
		} finally {
			isLoading = false;
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
			<div class="space-y-8">
				<!-- Header skeleton -->
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

				<!-- Main content grid skeleton -->
				<div class="grid grid-cols-1 gap-8 lg:grid-cols-3">
					<!-- Image area -->
					<div class="lg:col-span-1">
						<Skeleton class="aspect-4/5 w-full rounded-xl" />
					</div>

					<!-- Details area -->
					<div class="space-y-6 lg:col-span-2">
						<!-- Specs card -->
						<Skeleton class="h-32 w-full rounded-xl" />
						<!-- Pricing card -->
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
					<h2 class="text-xl font-bold text-foreground">Error Loading Printer</h2>
					<p class="mt-1 text-muted-foreground">{error}</p>
				</div>
			</div>
		{:else if printer}
			<div
				class="relative overflow-hidden rounded-2xl border border-border bg-card p-8 shadow-xl backdrop-blur-xl"
			>
				<!-- Glow behind printer image only -->
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
							<div>
								<h1 class="text-3xl font-bold text-foreground">{printer.name}</h1>
								<p class="text-muted-foreground">ID: #{printer.id}</p>
							</div>
						</div>

						<span
							class={`inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-medium ${
								printer.decomissioned
									? 'bg-destructive/20 text-destructive'
									: 'bg-success/20 text-success'
							}`}
						>
							{#if printer.decomissioned}
								<Archive class="h-4 w-4" />
								Decommissioned
							{:else}
								<CheckCircle class="h-4 w-4" />
								Active
							{/if}
						</span>
					</div>

					<div class="grid grid-cols-1 gap-8 lg:grid-cols-3">
						<!-- Image / Placeholder -->
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
									<!-- Subtle inner glow overlay -->
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

						<!-- Details -->
						<div class="space-y-6 lg:col-span-2">
							<div class="rounded-xl bg-muted/50 p-6">
								<div class="mb-4 flex items-center gap-2">
									<Info class="h-5 w-5 text-primary" />
									<h2 class="text-xl font-semibold text-foreground">Specifications</h2>
								</div>
								<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
									<div>
										<p class="text-sm text-muted-foreground">Color Support</p>
										<div class="mt-1 flex items-center gap-2">
											<Palette class="h-4 w-4 text-accent-foreground" />
											<span class="font-medium text-foreground">
												{printer.is_color ? 'Full Color' : 'Grayscale Only'}
											</span>
										</div>
									</div>
									<div>
										<p class="text-sm text-muted-foreground">Status</p>
										<span class="font-medium text-foreground">
											{printer.decomissioned ? 'Decommissioned' : 'Operational'}
										</span>
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
										<p class="text-sm text-primary/80">Simplex (Single-sided)</p>
										<p class="mt-1 text-xl font-bold text-foreground">
											{printer.simplex_charge.toFixed(2)} BDT
										</p>
									</div>
									<div class="rounded-lg bg-primary/5 p-4">
										<p class="text-sm text-secondary-foreground">Duplex (Double-sided)</p>
										<p class="mt-1 text-xl font-bold text-foreground">
											{printer.duplex_charge.toFixed(2)} BDT
										</p>
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
