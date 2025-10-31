<script lang="ts">
	import { onDestroy } from 'svelte';

	// UI Components
	import {
		Table,
		TableBody,
		TableCell,
		TableHead,
		TableHeader,
		TableRow
	} from '$lib/components/ui/table';
	import { Button } from '$lib/components/ui/button';
	import { Badge } from '$lib/components/ui/badge';
	import { Alert, AlertDescription } from '$lib/components/ui/alert';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogFooter,
		DialogClose
	} from '$lib/components/ui/dialog';
	import {
		Tooltip,
		TooltipContent,
		TooltipProvider,
		TooltipTrigger
	} from '$lib/components/ui/tooltip';
	import {
		DropdownMenu,
		DropdownMenuContent,
		DropdownMenuItem,
		DropdownMenuSeparator,
		DropdownMenuTrigger
	} from '$lib/components/ui/dropdown-menu';
	import { Skeleton } from '$lib/components/ui/skeleton';

	// Lucide Icons
	import {
		FileText,
		LoaderCircle,
		Eye,
		ExternalLink,
		Repeat,
		FileText as FileTextIcon,
		Trash2,
		X,
		ArrowLeft,
		ChevronDown
	} from 'lucide-svelte';

	import { token } from '$lib/stores/token.svelte';
	import { createRefCountedCache } from '$lib/cache/createRefCountedCache';
	import { cn } from '$lib/utils';
	import { client } from '$lib/client';
	import { user_username } from '$lib/stores/auth.svelte';

	interface QueueItem {
		id: number;
		file: string;
		processed: boolean;
		created_at: string;
		user: string;
		user_id: number;
		isMerged?: boolean;
		mergedFrom?: string[];
		hidden?: boolean;
		pageCount?: number;
		mergedId?: string;
		page_type?: 'single-sided' | 'double-sided';
	}

	let queue = $state<QueueItem[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let unprocessingItem = $state<Record<number, boolean>>({});
	let expandedMergedItems = $state<Record<string, boolean>>({});
	let itemPrintMode = $state<Record<number, 'single-sided' | 'double-sided'>>({});

	const mergedPdfCache = createRefCountedCache<string>();
	const fetchedPdfCache = createRefCountedCache<string>();
	let previewUrl = $state<string | null>(null);
	let previewLoading = $state(false);

	async function fetchAndCachePdf(url: string): Promise<string> {
		if (url.startsWith('blob:')) return url;
		if (!fetchedPdfCache.has(url)) {
			const res = await fetch(url, {
				headers: { Authorization: `Bearer ${token.value}` }
			});
			if (!res.ok) throw new Error(`Failed to fetch PDF: ${url}`);
			const blob = await res.blob();
			const blobUrl = URL.createObjectURL(blob);
			fetchedPdfCache.set(url, blobUrl);
		}
		fetchedPdfCache.incrementRef(url);
		return fetchedPdfCache.get(url)!;
	}

	function releasePdfBlob(url: string): void {
		if (!url.startsWith('blob:')) return;

		for (const [key, blobUrl] of mergedPdfCache.entries()) {
			if (blobUrl === url) {
				if (mergedPdfCache.decrementRef(key)) URL.revokeObjectURL(url);
				return;
			}
		}
		for (const [key, blobUrl] of fetchedPdfCache.entries()) {
			if (blobUrl === url) {
				if (fetchedPdfCache.decrementRef(key)) URL.revokeObjectURL(url);
				return;
			}
		}
	}

	async function setPrintMode(item: QueueItem, mode: 'single-sided' | 'double-sided') {
		if (item.isMerged) return;
		unprocessingItem = { ...unprocessingItem, [item.id]: true };
		try {
			const { error } = await client.POST('/api/queue/{queue_id}/print-mode', {
				params: {
					path: {
						queue_id: item.id
					}
				},
				headers: {
					Authorization: `Bearer ${token.value}`
				},
				body: {
					page_type: mode
				}
			});

			if (error) {
				throw new Error(error || 'Failed to update print mode');
			}
			itemPrintMode[item.id] = mode;
		} catch (err) {
			error = err instanceof Error ? `Print mode error: ${err.message}` : 'Update failed';
		} finally {
			unprocessingItem = { ...unprocessingItem, [item.id]: false };
		}
	}

	async function deleteQueueItem(item: QueueItem) {
		if (item.isMerged) return;
		const { id } = item;
		unprocessingItem = { ...unprocessingItem, [id]: true };
		try {
			const { error } = await client.DELETE('/api/queue/{queue_id}/delete', {
				params: {
					path: {
						queue_id: id
					}
				},
				headers: {
					Authorization: `Bearer ${token.value}`
				}
			});
			if (error) {
				throw new Error(error || `Delete failed for ${id}`);
			}
			queue = queue.filter((i) => i.id !== id);
		} catch (err) {
			error = err instanceof Error ? `Delete error: ${err.message}` : 'Delete failed';
		} finally {
			unprocessingItem = { ...unprocessingItem, [id]: false };
		}
	}

	async function openPreview(url: string) {
		previewLoading = true;
		previewUrl = null;
		try {
			previewUrl = await fetchAndCachePdf(url);
		} catch (err) {
			error = err instanceof Error ? `Preview error: ${err.message}` : 'Failed to load preview';
			previewUrl = null;
		} finally {
			previewLoading = false;
		}
	}

	function closePreview() {
		previewUrl = null;
	}

	async function openInNewTab(url: string) {
		try {
			const finalUrl = await fetchAndCachePdf(url);
			const win = window.open(finalUrl, '_blank');
			if (!win) error = 'Popup blocked';
		} catch (err) {
			error = err instanceof Error ? `New tab error: ${err.message}` : 'Open failed';
		}
	}

	$effect(() => {
		async function fetchQueue() {
			try {
				const { data, error } = await client.GET('/api/user/queue/', {
					headers: { Authorization: `Bearer ${token.value}` }
				});

				if (error) throw new Error('Failed to fetch queue');

				queue = (data.queue || []).map((item: any) => ({
					...item,
					pageCount: item.page_count ?? undefined
				}));

				itemPrintMode = {};
				for (const item of queue) {
					itemPrintMode[item.id] =
						item.page_type === 'single-sided' ? 'single-sided' : 'double-sided';
				}
			} catch (err) {
				error = err instanceof Error ? err.message : 'Unknown error';
			} finally {
				loading = false;
			}
		}
		fetchQueue();
	});

	let totalPages = $state(0);

	$effect(() => {
		let total = 0;
		for (const item of queue) {
			if (item.hidden) continue;
			total += item.pageCount ?? 1;
		}
		totalPages = total;
	});

	function goBack() {
		window.history.back();
	}

	onDestroy(() => {
		for (const [_, url] of mergedPdfCache.entries()) URL.revokeObjectURL(url as string);
		for (const [_, url] of fetchedPdfCache.entries()) URL.revokeObjectURL(url as string);
		mergedPdfCache.evictAll();
		fetchedPdfCache.evictAll();
	});
</script>

<!-- Preview Dialog -->
<Dialog open={!!previewUrl} onOpenChange={(open) => !open && closePreview()}>
	<DialogContent class="flex max-h-[90vh] max-w-4xl flex-col p-0">
		<DialogHeader class="border-b px-6 py-4">
			<DialogTitle>PDF Preview</DialogTitle>
		</DialogHeader>
		<div class="flex-1 overflow-hidden bg-muted/30">
			{#if previewLoading}
				<div class="flex h-full items-center justify-center">
					<LoaderCircle class="h-8 w-8 animate-spin text-primary" />
				</div>
			{:else if previewUrl}
				<embed src={previewUrl} type="application/pdf" class="h-full min-h-[500px] w-full" />
			{:else}
				<div class="flex h-full items-center justify-center text-destructive">
					Failed to load preview
				</div>
			{/if}
		</div>
		<DialogFooter class="border-t bg-background px-6 py-4">
			<DialogClose><Button variant="outline">Close</Button></DialogClose>
		</DialogFooter>
	</DialogContent>
</Dialog>

<TooltipProvider>
	<div class="container mx-auto space-y-6 py-6">
		<div class="flex flex-wrap items-center justify-between gap-4">
			<h1 class="text-3xl font-bold tracking-tight">
				{#if loading}
					<Skeleton class="h-8 w-48" />
				{:else}
					PDF Processing Queue
					<span class="ml-2 text-sm font-normal text-muted-foreground">
						for {user_username.value} ({totalPages}
						{totalPages === 1 ? 'page' : 'pages'})
					</span>
				{/if}
			</h1>
			<Button variant="outline" size="sm" href="./upload">
				<ArrowLeft class="mr-2 h-4 w-4" />
				Back to Upload
			</Button>
		</div>

		{#if error}
			<Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>
		{/if}

		{#if loading}
			<div class="overflow-hidden rounded-lg border">
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>File</TableHead>
							<TableHead>Status</TableHead>
							<TableHead>Created</TableHead>
							<TableHead>Print Mode</TableHead>
							<TableHead class="text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{#each { length: 3 } as _, i}
							<TableRow>
								<TableCell>
									<Skeleton class="h-5 w-3/4" />
									<Skeleton class="mt-1 h-4 w-1/3" />
								</TableCell>
								<TableCell>
									<Skeleton class="h-5 w-16" />
								</TableCell>
								<TableCell>
									<Skeleton class="h-5 w-32" />
								</TableCell>
								<TableCell>
									<div class="flex items-center gap-2">
										<Skeleton class="h-8 w-8 rounded" />
										<Skeleton class="h-8 w-8 rounded" />
									</div>
								</TableCell>
								<TableCell class="text-right">
									<div class="flex justify-end gap-2">
										<Skeleton class="h-8 w-8 rounded" />
										<Skeleton class="h-8 w-8 rounded" />
										<Skeleton class="h-8 w-8 rounded" />
									</div>
								</TableCell>
							</TableRow>
						{/each}
					</TableBody>
				</Table>
			</div>
		{:else if queue.length === 0}
			<div class="py-12 text-center">
				<FileText class="mx-auto h-12 w-12 text-muted-foreground" />
				<h3 class="mt-2 text-lg font-medium">No items in your queue</h3>
			</div>
		{:else}
			<div class="overflow-hidden rounded-lg border">
				<Table>
					<TableHeader>
						<TableRow>
							<TableHead>File</TableHead>
							<TableHead>Status</TableHead>
							<TableHead>Created</TableHead>
							<TableHead>Print Mode</TableHead>
							<TableHead class="text-right">Actions</TableHead>
						</TableRow>
					</TableHeader>
					<TableBody>
						{#each queue as item}
							{#if !item.hidden}
								<TableRow
									class={cn(
										'transition-opacity duration-200 ease-in-out',
										unprocessingItem[item.id] && 'pointer-events-none opacity-70'
									)}
								>
									<TableCell class="font-medium">
										{#if item.isMerged && item.mergedFrom}
											<span class="inline-flex items-center gap-1.5">
												<span>Merged PDF</span>
												<Badge variant="outline" class="px-1.5 py-0 text-xs">
													{item.mergedFrom.length} files
												</Badge>
											</span>
										{:else}
											{item.file.split('/').pop()}
										{/if}
										{#if item.pageCount !== undefined && item.pageCount >= 0}
											<span class="ml-2 text-xs text-muted-foreground">({item.pageCount} pg)</span>
										{/if}
									</TableCell>
									<TableCell>
										{#if item.isMerged}
											<Badge variant="default">Merged</Badge>
										{:else if item.processed}
											<Badge variant="secondary">Processed</Badge>
										{:else}
											<Badge variant="destructive">Pending</Badge>
										{/if}
									</TableCell>
									<TableCell>{new Date(item.created_at).toLocaleString()}</TableCell>

									<TableCell>
										{#if !item.isMerged}
											<div class="flex items-center gap-2">
												<Tooltip>
													<TooltipTrigger>
														<Button
															variant={itemPrintMode[item.id] === 'double-sided'
																? 'default'
																: 'outline'}
															size="sm"
															class="h-8 w-8 p-0"
															onclick={() => setPrintMode(item, 'double-sided')}
															disabled={unprocessingItem[item.id]}
														>
															<Repeat class="h-4 w-4" />
														</Button>
													</TooltipTrigger>
													<TooltipContent>Duplex (free)</TooltipContent>
												</Tooltip>
												<Tooltip>
													<TooltipTrigger>
														<Button
															variant={itemPrintMode[item.id] === 'single-sided'
																? 'default'
																: 'outline'}
															size="sm"
															class="h-8 w-8 p-0"
															onclick={() => setPrintMode(item, 'single-sided')}
															disabled={unprocessingItem[item.id]}
														>
															<FileTextIcon class="h-4 w-4" />
														</Button>
													</TooltipTrigger>
													<TooltipContent>Simplex (1 taka per sheet)</TooltipContent>
												</Tooltip>
											</div>
										{:else}
											<span class="text-sm text-muted-foreground">
												{itemPrintMode[item.id] === 'single-sided' ? 'Simplex' : 'Duplex'}
											</span>
										{/if}
									</TableCell>

									<!-- Actions Cell -->
									<TableCell class="text-right">
										<!-- Desktop -->
										<div class="hidden justify-end gap-2 md:flex">
											<div class="flex rounded-md border border-input shadow-sm">
												<Tooltip>
													<TooltipTrigger>
														<Button
															variant="outline"
															size="sm"
															class="rounded-r-none border-r"
															onclick={() => openPreview(item.file)}
														>
															<Eye class="h-4 w-4" />
														</Button>
													</TooltipTrigger>
													<TooltipContent>Preview</TooltipContent>
												</Tooltip>
												<Tooltip>
													<TooltipTrigger>
														<Button
															variant="outline"
															size="sm"
															class="rounded-l-none"
															onclick={() => openInNewTab(item.file)}
														>
															<ExternalLink class="h-4 w-4" />
														</Button>
													</TooltipTrigger>
													<TooltipContent>Open in new tab</TooltipContent>
												</Tooltip>
											</div>

											{#if !item.isMerged}
												<Tooltip>
													<TooltipTrigger>
														<Button
															variant="destructive"
															size="sm"
															disabled={unprocessingItem[item.id]}
															onclick={() => deleteQueueItem(item)}
														>
															{#if unprocessingItem[item.id]}
																<LoaderCircle class="h-4 w-4 animate-spin" />
															{:else}
																<Trash2 class="h-4 w-4" />
															{/if}
														</Button>
													</TooltipTrigger>
													<TooltipContent>Delete from queue</TooltipContent>
												</Tooltip>
											{/if}

											{#if item.isMerged}
												<Tooltip>
													<TooltipTrigger>
														<Button
															variant="destructive"
															size="icon"
															onclick={() => {
																releasePdfBlob(item.file);
																queue = queue.filter((i) => i.mergedId !== item.mergedId);
															}}
														>
															<X class="h-4 w-4" />
														</Button>
													</TooltipTrigger>
													<TooltipContent>Unmerge</TooltipContent>
												</Tooltip>
											{/if}
										</div>

										<!-- Mobile -->
										<div class="md:hidden">
											<DropdownMenu>
												<DropdownMenuTrigger>
													<Button variant="outline" size="icon">
														<ChevronDown class="h-4 w-4" />
													</Button>
												</DropdownMenuTrigger>
												<DropdownMenuContent align="end" class="w-56">
													<DropdownMenuItem onclick={() => openPreview(item.file)}>
														<Eye class="mr-2 h-4 w-4" />
														Preview
													</DropdownMenuItem>
													<DropdownMenuItem onclick={() => openInNewTab(item.file)}>
														<ExternalLink class="mr-2 h-4 w-4" />
														Open in new tab
													</DropdownMenuItem>

													<DropdownMenuSeparator />

													{#if !item.isMerged}
														<DropdownMenuItem
															onclick={() => deleteQueueItem(item)}
															disabled={unprocessingItem[item.id]}
															class="text-destructive focus:text-destructive"
														>
															{#if unprocessingItem[item.id]}
																<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
																Deleting...
															{:else}
																<Trash2 class="mr-2 h-4 w-4" />
																Delete
															{/if}
														</DropdownMenuItem>
													{/if}

													{#if item.isMerged}
														<DropdownMenuItem
															onclick={() => {
																releasePdfBlob(item.file);
																queue = queue.filter((i) => i.mergedId !== item.mergedId);
															}}
															class="text-destructive focus:text-destructive"
														>
															<X class="mr-2 h-4 w-4" />
															Unmerge
														</DropdownMenuItem>
													{/if}
												</DropdownMenuContent>
											</DropdownMenu>
										</div>
									</TableCell>
								</TableRow>

								<!-- Expanded originals (read-only) -->
								{#if item.isMerged && item.mergedFrom && item.mergedId && expandedMergedItems[item.mergedId]}
									{#each item.mergedFrom as originalFile}
										{#if queue.find((q) => q.file === originalFile && !q.isMerged)}
											{@const original = queue.find((q) => q.file === originalFile && !q.isMerged)!}
											<TableRow class="bg-muted/30">
												<TableCell class="text-sm font-medium">
													<FileText class="mr-1 inline h-3 w-3" />
													{original.file.split('/').pop()}
													{#if original.pageCount !== undefined}
														<span class="ml-1 text-xs text-muted-foreground"
															>({original.pageCount} pg)</span
														>
													{/if}
												</TableCell>
												<TableCell>
													<Badge variant="outline">Original</Badge>
												</TableCell>
												<TableCell>{new Date(original.created_at).toLocaleString()}</TableCell>
												<TableCell>
													<span class="text-sm text-muted-foreground">Duplex</span>
												</TableCell>
												<TableCell class="text-right">
													<div class="flex justify-end gap-2">
														<Tooltip>
															<TooltipTrigger>
																<Button
																	variant="outline"
																	size="sm"
																	onclick={() => openPreview(original.file)}
																>
																	<Eye class="h-3 w-3" />
																</Button>
															</TooltipTrigger>
															<TooltipContent>Preview original</TooltipContent>
														</Tooltip>
														<Tooltip>
															<TooltipTrigger>
																<Button
																	variant="outline"
																	size="sm"
																	onclick={() => openInNewTab(original.file)}
																>
																	<ExternalLink class="h-3 w-3" />
																</Button>
															</TooltipTrigger>
															<TooltipContent>Open original</TooltipContent>
														</Tooltip>
													</div>
												</TableCell>
											</TableRow>
										{/if}
									{/each}
								{/if}
							{/if}
						{/each}
					</TableBody>
				</Table>
			</div>
		{/if}
	</div>
</TooltipProvider>
