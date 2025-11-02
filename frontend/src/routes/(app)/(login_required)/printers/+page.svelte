<script lang="ts">
	import {
		Table,
		TableBody,
		TableCell,
		TableHead,
		TableHeader,
		TableRow
	} from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { Button } from '$lib/components/ui/button';
	import {
		AlertDialog,
		AlertDialogAction,
		AlertDialogCancel,
		AlertDialogContent,
		AlertDialogDescription,
		AlertDialogFooter,
		AlertDialogHeader,
		AlertDialogTitle,
		AlertDialogTrigger
	} from '$lib/components/ui/alert-dialog';
	import {
		Tooltip,
		TooltipContent,
		TooltipProvider,
		TooltipTrigger
	} from '$lib/components/ui/tooltip';
	import { Skeleton } from '$lib/components/ui/skeleton';
	import { Printer, Settings, Archive, RotateCcw, Trash2 } from 'lucide-svelte';
	import { onMount } from 'svelte';
	import { is_admin_user } from '$lib/stores/auth.svelte';
	import { client } from '$lib/client';
	import { token } from '$lib/stores/token.svelte';
	import { toast } from 'svelte-sonner';

	type PrinterItem = {
		id: number;
		name: string;
		is_color: boolean;
		simplex_charge: number;
		duplex_charge: number;
		image?: string | null;
		decomissioned: boolean;
	};

	let printers = $state<PrinterItem[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	const fetchPrinters = async () => {
		try {
			const { data, error } = await client.GET('/api/printers/', {
				headers: { Authorization: `Bearer ${token.value}` }
			});
			if (data === undefined) throw new Error('No data received');
			if (error) throw new Error('Failed to load printers');
			printers = data;
		} catch (err) {
			error = (err as Error).message;
			toast.error(error);
		} finally {
			loading = false;
		}
	};

	const handleDecommission = async (id: number) => {
		try {
			const { data, error } = await client.DELETE(`/api/admin/printers/{printer_id}/decomission`, {
				params: { path: { printer_id: id } },
				headers: { Authorization: `Bearer ${token.value}` }
			});
			if (data?.decomissioned) {
				printers = printers.map((p) => (p.id === id ? { ...p, decomissioned: true } : p));
				toast.success('Printer decommissioned');
			} else {
				throw new Error(error || 'Unknown error');
			}
		} catch (err) {
			toast.error((err as Error).message || 'Failed to decommission printer');
		}
	};

	const handleRecommission = async (id: number) => {
		try {
			const { data, error } = await client.POST(`/api/admin/printers/{printer_id}/decomission`, {
				params: { path: { printer_id: id } },
				headers: { Authorization: `Bearer ${token.value}` }
			});
			if (data?.decomissioned === false) {
				printers = printers.map((p) => (p.id === id ? { ...p, decomissioned: false } : p));
				toast.success('Printer recommissioned');
			} else {
				throw new Error(error || 'Unknown error');
			}
		} catch (err) {
			toast.error((err as Error).message || 'Failed to recommission printer');
		}
	};

	const handleDelete = async (id: number) => {
		try {
			const { data, error } = await client.POST('/api/admin/printers/remove/{id}', {
				params: { path: { id: id } },
				headers: { Authorization: `Bearer ${token.value}` }
			});
			if (data?.id) {
				printers = printers.filter((p) => p.id !== id);
				toast.success('Printer deleted');
			} else {
				throw new Error(error || 'Unknown error');
			}
		} catch (err) {
			toast.error((err as Error).message || 'Failed to delete printer');
		}
	};

	onMount(async () => {
		await fetchPrinters();
	});
</script>

<div class="container py-6">
	<TooltipProvider>
		{#if error}
			<div class="mb-6 rounded-md bg-destructive/10 p-4 text-destructive">{error}</div>
		{:else if loading}
			<div class="mb-6">
				<div class="mb-6 flex items-center justify-between">
					<Skeleton class="h-8 w-48" />
					{#if is_admin_user.value}
						<Skeleton class="h-9 w-28" />
					{/if}
				</div>

				<Table>
					<TableHeader>
						<TableRow>
							<TableHead><Skeleton class="h-6 w-full" /></TableHead>
							<TableHead><Skeleton class="h-6 w-full" /></TableHead>
							<TableHead><Skeleton class="h-6 w-full" /></TableHead>
							<TableHead><Skeleton class="h-6 w-full" /></TableHead>
							<TableHead><Skeleton class="h-6 w-full" /></TableHead>
							{#if is_admin_user.value}
								<TableHead class="text-right"><Skeleton class="h-6 w-full" /></TableHead>
							{/if}
						</TableRow>
					</TableHeader>
					<TableBody>
						{#each { length: 5 } as _, i}
							<TableRow>
								<TableCell>
									<div class="flex items-center gap-3">
										<Skeleton class="h-10 w-10 rounded-md" />
										<Skeleton class="h-5 w-32" />
									</div>
								</TableCell>
								<TableCell><Skeleton class="h-6 w-16" /></TableCell>
								<TableCell><Skeleton class="h-5 w-12" /></TableCell>
								<TableCell><Skeleton class="h-5 w-12" /></TableCell>
								<TableCell><Skeleton class="h-6 w-24" /></TableCell>
								{#if is_admin_user.value}
									<TableCell class="text-right">
										<div class="flex justify-end gap-2">
											<Skeleton class="size-8 rounded-full" />
											<Skeleton class="size-8 rounded-full" />
											<Skeleton class="size-8 rounded-full" />
										</div>
									</TableCell>
								{/if}
							</TableRow>
						{/each}
					</TableBody>
				</Table>
			</div>
		{:else}
			<div class="mb-6 flex items-center justify-between">
				<h1 class="text-2xl font-bold">Printers</h1>
				{#if is_admin_user.value}
					<Button variant="default" disabled>Add Printer</Button>
				{/if}
			</div>

			<Table>
				<TableHeader>
					<TableRow>
						<TableHead>Printer</TableHead>
						<TableHead>Type</TableHead>
						<TableHead>Simplex (৳)</TableHead>
						<TableHead>Duplex (৳)</TableHead>
						<TableHead>Status</TableHead>
						{#if is_admin_user.value}
							<TableHead class="text-right">Actions</TableHead>
						{/if}
					</TableRow>
				</TableHeader>
				<TableBody>
					{#each printers as printer}
						<TableRow>
							<TableCell>
								<div class="flex items-center gap-3">
									{#if printer.image}
										<img
											src={printer.image}
											alt={printer.name}
											class="h-10 w-10 rounded-md border object-cover"
										/>
									{:else}
										<div
											class="flex h-10 w-10 items-center justify-center rounded-md border bg-muted"
										>
											<Printer class="h-5 w-5 text-muted-foreground" />
										</div>
									{/if}
									<Tooltip>
										<TooltipTrigger>
											<span class="inline-block max-w-40 truncate font-medium">{printer.name}</span>
										</TooltipTrigger>
										<TooltipContent side="top">
											{printer.name}
										</TooltipContent>
									</Tooltip>
								</div>
							</TableCell>
							<TableCell>
								<Badge variant={printer.is_color ? 'default' : 'secondary'}>
									{printer.is_color ? 'Color' : 'B&W'}
								</Badge>
							</TableCell>
							<TableCell class="font-mono">৳{printer.simplex_charge.toFixed(2)}</TableCell>
							<TableCell class="font-mono">৳{printer.duplex_charge.toFixed(2)}</TableCell>
							<TableCell>
								{#if printer.decomissioned}
									<Tooltip>
										<TooltipTrigger>
											<Badge variant="destructive">
												<Archive class="mr-1 h-3 w-3" />
												Decommissioned
											</Badge>
										</TooltipTrigger>
										<TooltipContent>Not available for new print jobs.</TooltipContent>
									</Tooltip>
								{:else}
									<Tooltip>
										<TooltipTrigger>
											<Badge variant="default">
												<Printer class="mr-1 h-3 w-3" />
												Active
											</Badge>
										</TooltipTrigger>
										<TooltipContent>Available for printing.</TooltipContent>
									</Tooltip>
								{/if}
							</TableCell>
							{#if is_admin_user.value}
								<TableCell class="text-right">
									<div class="flex items-center justify-end gap-2">
										<Tooltip>
											<TooltipTrigger>
												<Button variant="ghost" size="icon" href="/printers/{printer.id}">
													<Settings class="h-4 w-4" />
												</Button>
											</TooltipTrigger>
											<TooltipContent>Edit printer settings</TooltipContent>
										</Tooltip>

										{#if printer.decomissioned}
											<AlertDialog>
												<AlertDialogTrigger>
													<Tooltip>
														<TooltipTrigger>
															<Button variant="ghost" size="icon">
																<RotateCcw class="h-4 w-4" />
															</Button>
														</TooltipTrigger>
														<TooltipContent>Recommission printer</TooltipContent>
													</Tooltip>
												</AlertDialogTrigger>
												<AlertDialogContent>
													<AlertDialogHeader>
														<AlertDialogTitle>Recommission printer?</AlertDialogTitle>
														<AlertDialogDescription>
															This will make the printer available again for printing.
														</AlertDialogDescription>
													</AlertDialogHeader>
													<AlertDialogFooter>
														<AlertDialogCancel>Cancel</AlertDialogCancel>
														<AlertDialogAction onclick={() => handleRecommission(printer.id)}>
															Recommission
														</AlertDialogAction>
													</AlertDialogFooter>
												</AlertDialogContent>
											</AlertDialog>
										{:else}
											<AlertDialog>
												<AlertDialogTrigger>
													<Tooltip>
														<TooltipTrigger>
															<Button variant="ghost" size="icon">
																<Archive class="h-4 w-4" />
															</Button>
														</TooltipTrigger>
														<TooltipContent>Decommission printer</TooltipContent>
													</Tooltip>
												</AlertDialogTrigger>
												<AlertDialogContent>
													<AlertDialogHeader>
														<AlertDialogTitle>Decommission printer?</AlertDialogTitle>
														<AlertDialogDescription>
															This printer will no longer be available for new print jobs.
														</AlertDialogDescription>
													</AlertDialogHeader>
													<AlertDialogFooter>
														<AlertDialogCancel>Cancel</AlertDialogCancel>
														<AlertDialogAction onclick={() => handleDecommission(printer.id)}>
															Decommission
														</AlertDialogAction>
													</AlertDialogFooter>
												</AlertDialogContent>
											</AlertDialog>
										{/if}

										<AlertDialog>
											<AlertDialogTrigger>
												<Tooltip>
													<TooltipTrigger>
														<Button variant="ghost" size="icon">
															<Trash2 class="h-4 w-4 text-destructive" />
														</Button>
													</TooltipTrigger>
													<TooltipContent>Delete printer permanently</TooltipContent>
												</Tooltip>
											</AlertDialogTrigger>
											<AlertDialogContent>
												<AlertDialogHeader>
													<AlertDialogTitle>Delete printer permanently?</AlertDialogTitle>
													<AlertDialogDescription>
														This action cannot be undone. All associated data will be lost.
													</AlertDialogDescription>
												</AlertDialogHeader>
												<AlertDialogFooter>
													<AlertDialogCancel>Cancel</AlertDialogCancel>
													<AlertDialogAction
														class="text-destructive-foreground bg-destructive hover:bg-destructive/90"
														onclick={() => handleDelete(printer.id)}
													>
														Delete
													</AlertDialogAction>
												</AlertDialogFooter>
											</AlertDialogContent>
										</AlertDialog>
									</div>
								</TableCell>
							{/if}
						</TableRow>
					{:else}
						<TableRow>
							<TableCell
								colspan={is_admin_user.value ? 6 : 5}
								class="text-center py-8 text-muted-foreground"
							>
								No printers found.
							</TableCell>
						</TableRow>
					{/each}
				</TableBody>
			</Table>
		{/if}
	</TooltipProvider>
</div>
