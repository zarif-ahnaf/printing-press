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
	import { Checkbox } from '$lib/components/ui/checkbox';
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

	// Lucide Icons
	import {
		FileText,
		Printer,
		Merge,
		LoaderCircle,
		Eye,
		X,
		ExternalLink,
		ChevronRight,
		ChevronDown,
		CheckCircle,
		CreditCard,
		Repeat
	} from 'lucide-svelte';

	import { CHARGE_ENDPOINT, MERGE_ENDPOINT, QUEUE_URL } from '$lib/constants/backend';
	import { token } from '$lib/stores/token.svelte';
	import { createRefCountedCache } from '$lib/cache/createRefCountedCache';
	import { cn } from '$lib/utils';

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
	}

	let queue = $state<QueueItem[]>([]);
	let groupedQueue = $state<Record<string, QueueItem[]>>({});
	let loading = $state(false);
	let error = $state<string | null>(null);
	let merging = $state<Record<string, boolean>>({});
	let mergingFiles = $state<Record<string, boolean>>({});
	let printing = $state<Record<number, boolean>>({});
	let charging = $state<Record<number, boolean>>({});
	let previewUrl = $state<string | null>(null);
	let previewLoading = $state(false);
	let selectedItems = $state<Record<string, Record<string, boolean>>>({});
	let mergingAllForUser = $state<Record<string, boolean>>({});
	let confirmingSelected = $state<Record<string, boolean>>({});
	let unprocessingItem = $state<Record<number, boolean>>({});
	let expandedMergedItems = $state<Record<string, boolean>>({});
	let itemPrintMode = $state<Record<number, 'duplex' | 'simplex'>>({});

	const mergedPdfCache = createRefCountedCache<string>();
	const fetchedPdfCache = createRefCountedCache<string>();

	function hashFiles(files: string[]): string {
		return files.slice().sort().join('|');
	}

	function groupByUser(items: QueueItem[]): Record<string, QueueItem[]> {
		return items.reduce(
			(acc, item) => {
				if (!acc[item.user]) acc[item.user] = [];
				acc[item.user].push(item);
				return acc;
			},
			{} as Record<string, QueueItem[]>
		);
	}

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

	async function chargeForPdf(item: QueueItem): Promise<boolean> {
		if (!item.pageCount) return false;
		const mode = itemPrintMode[item.id] || 'duplex';
		if (mode !== 'simplex') return true;

		const sheets = item.pageCount % 2 === 0 ? item.pageCount : item.pageCount + 1;
		if (sheets <= 0) return true;

		charging = { ...charging, [item.id]: true };
		try {
			const res = await fetch(CHARGE_ENDPOINT, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${token.value}`
				},
				body: JSON.stringify({
					user_id: item.user_id,
					amount: sheets,
					description: `Simplex printing: ${item.file.split('/').pop()} (${item.pageCount} pages → ${sheets} sheets)`
				})
			});
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.detail || 'Charge failed');
			}
			return true;
		} catch (err) {
			error =
				err instanceof Error ? `Charge failed for ${item.file}: ${err.message}` : 'Charge error';
			return false;
		} finally {
			charging = { ...charging, [item.id]: false };
		}
	}

	async function printPdf(item: QueueItem) {
		const { id, file } = item;
		printing = { ...printing, [id]: true };

		try {
			const charged = await chargeForPdf(item);
			if (!charged) return;

			const pdfBlobUrl = await fetchAndCachePdf(file);
			const iframe = document.createElement('iframe');
			iframe.style.position = 'absolute';
			iframe.style.left = '-9999px';
			iframe.style.top = '-9999px';
			iframe.style.width = '0';
			iframe.style.height = '0';
			iframe.setAttribute('aria-hidden', 'true');
			iframe.src = pdfBlobUrl;

			await new Promise<void>((resolve, reject) => {
				iframe.onload = () => resolve();
				iframe.onerror = () => reject(new Error('PDF load failed'));
				document.body.appendChild(iframe);
			});

			iframe.contentWindow?.print();

			setTimeout(() => {
				if (document.body.contains(iframe)) document.body.removeChild(iframe);
			}, 10000);
		} catch (err) {
			error = err instanceof Error ? `Print error: ${err.message}` : 'Print failed';
		} finally {
			printing = { ...printing, [id]: false };
		}
	}

	async function mergePdfsBackend(user: string) {
		const files = Object.entries(selectedItems[user] || {})
			.filter(([, checked]) => checked)
			.map(([file]) => file);
		if (files.length < 2) return; // Safety: should not happen due to UI guard

		const cacheKey = hashFiles(files);
		let blobUrl: string;

		if (mergedPdfCache.has(cacheKey)) {
			mergedPdfCache.incrementRef(cacheKey);
			blobUrl = mergedPdfCache.get(cacheKey)!;
		} else {
			const userItems = groupedQueue[user] || [];
			merging = { ...merging, [user]: true };
			mergingFiles = { ...mergingFiles };
			for (const f of files) mergingFiles[f] = true;

			try {
				const formData = new FormData();
				const blobUrlsToRelease: string[] = [];
				for (const url of files) {
					const bUrl = await fetchAndCachePdf(url);
					blobUrlsToRelease.push(bUrl);
					const res = await fetch(bUrl);
					const blob = await res.blob();
					formData.append('files', blob, url.split('/').pop() || 'file.pdf');
				}

				const mergeRes = await fetch(MERGE_ENDPOINT, {
					method: 'POST',
					body: formData,
					headers: { Authorization: `Bearer ${token.value}` }
				});

				if (!mergeRes.ok) {
					const text = await mergeRes.text();
					throw new Error(`Merge failed: ${text}`);
				}

				const mergedBlob = await mergeRes.blob();
				blobUrl = URL.createObjectURL(mergedBlob);
				mergedPdfCache.set(cacheKey, blobUrl);
				mergedPdfCache.incrementRef(cacheKey);
				blobUrlsToRelease.forEach(releasePdfBlob);
			} catch (err) {
				error = err instanceof Error ? `Merge error: ${err.message}` : 'Merge failed';
				return;
			} finally {
				merging = { ...merging, [user]: false };
				mergingFiles = { ...mergingFiles };
				for (const f of files) delete mergingFiles[f];
			}
		}

		insertMergedItem(user, files, blobUrl);
		selectedItems = { ...selectedItems, [user]: {} };
	}

	async function mergeAllForUserBackend(user: string) {
		const userItems = groupedQueue[user] || [];
		const filesToMerge = userItems
			.filter((item) => !item.hidden && !item.isMerged)
			.map((item) => item.file);
		if (filesToMerge.length < 2) return; // Cannot merge <2 files

		const cacheKey = hashFiles(filesToMerge);
		let blobUrl: string;

		if (mergedPdfCache.has(cacheKey)) {
			mergedPdfCache.incrementRef(cacheKey);
			blobUrl = mergedPdfCache.get(cacheKey)!;
		} else {
			mergingAllForUser = { ...mergingAllForUser, [user]: true };
			mergingFiles = { ...mergingFiles };
			for (const f of filesToMerge) mergingFiles[f] = true;

			try {
				const formData = new FormData();
				const blobUrlsToRelease: string[] = [];
				for (const url of filesToMerge) {
					const bUrl = await fetchAndCachePdf(url);
					blobUrlsToRelease.push(bUrl);
					const res = await fetch(bUrl);
					const blob = await res.blob();
					formData.append('files', blob, url.split('/').pop() || 'file.pdf');
				}

				const mergeRes = await fetch(MERGE_ENDPOINT, {
					method: 'POST',
					body: formData,
					headers: { Authorization: `Bearer ${token.value}` }
				});

				if (!mergeRes.ok) {
					const text = await mergeRes.text();
					throw new Error(`Merge failed: ${text}`);
				}

				const mergedBlob = await mergeRes.blob();
				blobUrl = URL.createObjectURL(mergedBlob);
				mergedPdfCache.set(cacheKey, blobUrl);
				mergedPdfCache.incrementRef(cacheKey);
				blobUrlsToRelease.forEach(releasePdfBlob);
			} catch (err) {
				error = err instanceof Error ? `Merge error: ${err.message}` : 'Merge failed';
				return;
			} finally {
				mergingAllForUser = { ...mergingAllForUser, [user]: false };
				mergingFiles = { ...mergingFiles };
				for (const f of filesToMerge) delete mergingFiles[f];
			}
		}

		insertMergedItem(user, filesToMerge, blobUrl);
		selectedItems = { ...selectedItems, [user]: {} };
	}

	function insertMergedItem(user: string, files: string[], url: string) {
		const userItems = groupedQueue[user] || [];
		const selectedIndices: number[] = [];
		for (const [idx, item] of userItems.entries()) {
			if (files.includes(item.file)) selectedIndices.push(idx);
		}
		const maxIndex =
			selectedIndices.length > 0 ? Math.max(...selectedIndices) : userItems.length - 1;
		const insertIndex = maxIndex + 1;

		const mergedId = `merged_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

		const mergedItem: QueueItem = {
			id: -1,
			file: url,
			processed: true,
			created_at: new Date().toISOString(),
			user,
			user_id: userItems[0]?.user_id ?? -1,
			isMerged: true,
			mergedFrom: files,
			hidden: false,
			mergedId,
			pageCount: undefined
		};

		const updatedItems = userItems.map((item) =>
			files.includes(item.file) ? { ...item, hidden: true } : item
		);
		const finalItems = [...updatedItems];
		finalItems.splice(insertIndex, 0, mergedItem);
		groupedQueue = { ...groupedQueue, [user]: finalItems };
	}

	$effect(() => {
		async function fetchQueue() {
			try {
				loading = true;
				error = null;
				const res = await fetch(QUEUE_URL, {
					headers: { Authorization: `Bearer ${token.value}` }
				});
				if (!res.ok) throw new Error('Failed to fetch queue');
				const data = await res.json();
				queue = (data.queue || []).map((item: any) => ({
					...item,
					pageCount: item.page_count ?? undefined
				}));
				groupedQueue = groupByUser(queue);
				selectedItems = {};
				itemPrintMode = {};
				for (const item of queue) {
					itemPrintMode[item.id] = 'duplex';
				}
				for (const user of Object.keys(groupedQueue)) {
					selectedItems[user] = {};
				}
			} catch (err) {
				error = err instanceof Error ? err.message : 'Unknown error';
			} finally {
				loading = false;
			}
		}
		fetchQueue();
	});

	$effect(() => {
		for (const [user, items] of Object.entries(groupedQueue)) {
			for (const item of items) {
				if (!item.isMerged || !item.mergedFrom || !item.mergedId) continue;

				let total = 0;
				let allResolved = true;

				for (const sourceFile of item.mergedFrom) {
					const sourceItem = items.find((i) => i.file === sourceFile && !i.isMerged);
					if (!sourceItem) {
						const fallback = queue.find((q) => q.file === sourceFile && q.user === user);
						if (fallback?.pageCount !== undefined) {
							total += fallback.pageCount;
						} else {
							allResolved = false;
							total += 1;
						}
					} else if (sourceItem.pageCount !== undefined) {
						total += sourceItem.pageCount;
					} else {
						allResolved = false;
						total += 1;
					}
				}

				if (allResolved && item.pageCount !== total) {
					const idx = items.findIndex((i) => i.mergedId === item.mergedId);
					if (idx !== -1) {
						const updated = { ...item, pageCount: total };
						const newItems = [...items];
						newItems[idx] = updated;
						groupedQueue = { ...groupedQueue, [user]: newItems };
					}
				} else if (!allResolved && item.pageCount === undefined) {
					const idx = items.findIndex((i) => i.mergedId === item.mergedId);
					if (idx !== -1) {
						const updated = { ...item, pageCount: total };
						const newItems = [...items];
						newItems[idx] = updated;
						groupedQueue = { ...groupedQueue, [user]: newItems };
					}
				}
			}
		}
	});

	let userPageTotals = $state<Record<string, number>>({});

	$effect(() => {
		const newTotals: Record<string, number> = {};
		for (const [user, items] of Object.entries(groupedQueue)) {
			let total = 0;
			for (const item of items) {
				if (item.hidden) continue;
				total += item.pageCount ?? 1;
			}
			newTotals[user] = total;
		}
		userPageTotals = newTotals;
	});

	function toggleSelect(user: string, file: string, checked: boolean) {
		if (mergingFiles[file]) return;
		selectedItems = {
			...selectedItems,
			[user]: { ...selectedItems[user], [file]: checked }
		};
	}

	function unmerge(user: string, fileUrl: string) {
		const userItems = groupedQueue[user] || [];
		const mergedIndex = userItems.findIndex((item) => item.file === fileUrl && item.isMerged);
		if (mergedIndex === -1) return;

		const mergedItem = userItems[mergedIndex];
		if (!mergedItem.mergedFrom || !mergedItem.mergedId) return;

		releasePdfBlob(fileUrl);

		const withoutMerged = [...userItems];
		withoutMerged.splice(mergedIndex, 1);

		const restoredOriginals = mergedItem.mergedFrom.map((file) => {
			const original = queue.find((q) => q.file === file && q.user === user);
			return original
				? { ...original, hidden: false }
				: {
						id: -1,
						file,
						processed: false,
						created_at: new Date().toISOString(),
						user,
						user_id: mergedItem.user_id,
						hidden: false
					};
		});

		const restored = [...withoutMerged];
		restored.splice(mergedIndex, 0, ...restoredOriginals);
		groupedQueue = { ...groupedQueue, [user]: restored };

		selectedItems = { ...selectedItems, [user]: {} };
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

	async function confirmSelectedItems(user: string) {
		const userItems = groupedQueue[user] || [];
		const selectedItemsForUser = selectedItems[user] || {};
		const itemsToConfirm = userItems.filter(
			(item) => !item.hidden && !item.processed && !item.isMerged && selectedItemsForUser[item.file]
		);
		if (itemsToConfirm.length === 0) return;

		confirmingSelected = { ...confirmingSelected, [user]: true };
		try {
			for (const item of itemsToConfirm) {
				const res = await fetch(`${QUEUE_URL}${item.id}/processed`, {
					method: 'POST',
					headers: { Authorization: `Bearer ${token.value}`, 'Content-Type': 'application/json' }
				});
				if (!res.ok) {
					const err = await res.json();
					throw new Error(err.detail || `Confirm failed for ${item.id}`);
				}
				const result = await res.json();
				if (result.processed) {
					const userQueue = groupedQueue[user] || [];
					const idx = userQueue.findIndex((i) => i.id === item.id);
					if (idx !== -1) userQueue[idx] = { ...userQueue[idx], processed: true };
					groupedQueue = { ...groupedQueue, [user]: userQueue };
				}
			}
			selectedItems = { ...selectedItems, [user]: {} };
		} catch (err) {
			error = err instanceof Error ? `Confirm error: ${err.message}` : 'Confirm failed';
		} finally {
			confirmingSelected = { ...confirmingSelected, [user]: false };
		}
	}

	async function unprocessItem(item: QueueItem) {
		if (!item.processed || item.isMerged || item.hidden) return;
		const { id, user } = item;
		unprocessingItem = { ...unprocessingItem, [id]: true };
		try {
			const res = await fetch(`${QUEUE_URL}${id}/processed`, {
				method: 'DELETE',
				headers: { Authorization: `Bearer ${token.value}`, 'Content-Type': 'application/json' }
			});
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.detail || `Unprocess failed for ${id}`);
			}
			const userQueue = groupedQueue[user] || [];
			const idx = userQueue.findIndex((i) => i.id === id);
			if (idx !== -1) userQueue[idx] = { ...userQueue[idx], processed: false };
			groupedQueue = { ...groupedQueue, [user]: userQueue };
		} catch (err) {
			error = err instanceof Error ? `Unprocess error: ${err.message}` : 'Unprocess failed';
		} finally {
			unprocessingItem = { ...unprocessingItem, [id]: false };
		}
	}

	async function confirmItem(item: QueueItem) {
		if (item.processed || item.isMerged || item.hidden) return;
		const { id, user } = item;
		unprocessingItem = { ...unprocessingItem, [id]: true };
		try {
			const res = await fetch(`${QUEUE_URL}${id}/processed`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${token.value}`,
					'Content-Type': 'application/json'
				}
			});
			if (!res.ok) {
				const err = await res.json();
				throw new Error(err.detail || `Confirm failed for ${id}`);
			}
			const result = await res.json();
			if (result.processed) {
				const userQueue = groupedQueue[user] || [];
				const idx = userQueue.findIndex((i) => i.id === id);
				if (idx !== -1) userQueue[idx] = { ...userQueue[idx], processed: true };
				groupedQueue = { ...groupedQueue, [user]: userQueue };
			}
		} catch (err) {
			error = err instanceof Error ? `Confirm error: ${err.message}` : 'Confirm failed';
		} finally {
			unprocessingItem = { ...unprocessingItem, [id]: false };
		}
	}

	function canClearQueue(user: string): boolean {
		const items = groupedQueue[user] || [];
		return items.every((item) => item.processed || item.hidden);
	}

	function clearUserQueue(user: string) {
		const { [user]: _, ...rest } = groupedQueue;
		groupedQueue = rest;
		const { [user]: __, ...restSel } = selectedItems;
		selectedItems = restSel;
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
		<h1 class="text-3xl font-bold tracking-tight">PDF Processing Queue</h1>

		{#if error}
			<Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>
		{/if}

		{#if loading}
			<div class="flex h-32 items-center justify-center">
				<LoaderCircle class="h-8 w-8 animate-spin text-primary" />
			</div>
		{:else if Object.keys(groupedQueue).length === 0}
			<div class="py-12 text-center">
				<FileText class="mx-auto h-12 w-12 text-muted-foreground" />
				<h3 class="mt-2 text-lg font-medium">No items in queue</h3>
			</div>
		{:else}
			<div class="space-y-8">
				{#each Object.entries(groupedQueue) as [user, items]}
					<div class="overflow-hidden rounded-lg border">
						<div class="flex flex-wrap items-center justify-between gap-4 bg-muted/50 px-6 py-4">
							<div>
								<h2 class="text-xl font-semibold">
									{user}
									<span class="ml-2 text-sm font-normal text-muted-foreground">
										({userPageTotals[user]}
										{userPageTotals[user] === 1 ? 'page' : 'pages'})
									</span>
								</h2>
							</div>
							<div class="flex flex-wrap gap-2">
								<!-- Unified Merge Button: only shown if ≥2 mergeable items exist -->
								{#if items.filter((i) => !i.hidden && !i.isMerged).length >= 2}
									{#if selectedItems[user]}
										{#if Object.values(selectedItems[user]).filter(Boolean).length >= 2}
											<Button
												variant="default"
												size="sm"
												disabled={merging[user] ||
													mergingAllForUser[user] ||
													Object.values(mergingFiles).some((v) => v)}
												onclick={() => mergePdfsBackend(user)}
											>
												{#if merging[user] || mergingAllForUser[user]}
													<LoaderCircle class="mr-2 h-4 w-4 animate-spin" /> Merging...
												{:else}
													<Merge class="mr-2 h-4 w-4" /> Merge Selected
												{/if}
											</Button>
										{:else}
											<Button
												variant="default"
												size="sm"
												disabled={merging[user] ||
													mergingAllForUser[user] ||
													Object.values(mergingFiles).some((v) => v)}
												onclick={() => mergeAllForUserBackend(user)}
											>
												{#if merging[user] || mergingAllForUser[user]}
													<LoaderCircle class="mr-2 h-4 w-4 animate-spin" /> Merging...
												{:else}
													<Merge class="mr-2 h-4 w-4" /> Merge All
												{/if}
											</Button>
										{/if}
									{:else}
										<Button
											variant="default"
											size="sm"
											disabled={merging[user] ||
												mergingAllForUser[user] ||
												Object.values(mergingFiles).some((v) => v)}
											onclick={() => mergeAllForUserBackend(user)}
										>
											{#if merging[user] || mergingAllForUser[user]}
												<LoaderCircle class="mr-2 h-4 w-4 animate-spin" /> Merging...
											{:else}
												<Merge class="mr-2 h-4 w-4" /> Merge All
											{/if}
										</Button>
									{/if}
								{/if}

								<!-- Confirm Selected -->
								<Button
									variant="outline"
									size="sm"
									disabled={confirmingSelected[user] ||
										!selectedItems[user] ||
										Object.values(selectedItems[user] || {}).filter(Boolean).length === 0}
									onclick={() => confirmSelectedItems(user)}
								>
									{#if confirmingSelected[user]}
										<LoaderCircle class="mr-2 h-4 w-4 animate-spin" /> Confirming...
									{:else}
										<CheckCircle class="mr-2 h-4 w-4" /> Confirm Selected
									{/if}
								</Button>

								{#if canClearQueue(user)}
									<Button variant="destructive" size="sm" onclick={() => clearUserQueue(user)}>
										Clear Queue
									</Button>
								{/if}
							</div>
						</div>

						<Table>
							<TableHeader>
								<TableRow>
									<TableHead class="w-12"></TableHead>
									<TableHead>File</TableHead>
									<TableHead>Status</TableHead>
									<TableHead>Created</TableHead>
									<TableHead>Print Mode</TableHead>
									<TableHead class="text-right">Actions</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{#each items as item}
									{#if !item.hidden}
										<TableRow
											class={cn(
												'transition-opacity duration-200 ease-in-out',
												mergingFiles[item.file] && 'pointer-events-none opacity-50'
											)}
										>
											<TableCell>
												{#if !item.isMerged}
													<Checkbox
														checked={!!selectedItems[item.user]?.[item.file]}
														onCheckedChange={(checked) =>
															toggleSelect(item.user, item.file, checked)}
														disabled={mergingFiles[item.file]}
													/>
												{:else if item.mergedId}
													<Button
														variant="ghost"
														size="sm"
														class="h-6 w-6 p-0"
														onclick={() => {
															expandedMergedItems[item.mergedId!] =
																!expandedMergedItems[item.mergedId!];
														}}
													>
														{#if expandedMergedItems[item.mergedId]}
															<ChevronDown class="h-3 w-3 text-muted-foreground" />
														{:else}
															<ChevronRight class="h-3 w-3 text-muted-foreground" />
														{/if}
													</Button>
												{/if}
											</TableCell>
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
													<span class="ml-2 text-xs text-muted-foreground"
														>({item.pageCount} pg)</span
													>
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
																	variant={itemPrintMode[item.id] === 'duplex'
																		? 'default'
																		: 'outline'}
																	size="sm"
																	class="h-8 w-8 p-0"
																	onclick={() =>
																		(itemPrintMode = { ...itemPrintMode, [item.id]: 'duplex' })}
																>
																	<Repeat class="h-4 w-4" />
																</Button>
															</TooltipTrigger>
															<TooltipContent>Duplex (free)</TooltipContent>
														</Tooltip>
														<Tooltip>
															<TooltipTrigger>
																<Button
																	variant={itemPrintMode[item.id] === 'simplex'
																		? 'default'
																		: 'outline'}
																	size="sm"
																	class="h-8 w-8 p-0"
																	onclick={() =>
																		(itemPrintMode = { ...itemPrintMode, [item.id]: 'simplex' })}
																>
																	<FileText class="h-4 w-4" />
																</Button>
															</TooltipTrigger>
															<TooltipContent>Simplex (1 taka per sheet)</TooltipContent>
														</Tooltip>
													</div>
												{:else}
													<span class="text-sm text-muted-foreground">
														{itemPrintMode[item.id] === 'simplex' ? 'Simplex' : 'Duplex'}
													</span>
												{/if}
											</TableCell>

											<!-- Responsive Actions Cell -->
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
																	disabled={mergingFiles[item.file]}
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
																	disabled={mergingFiles[item.file]}
																>
																	<ExternalLink class="h-4 w-4" />
																</Button>
															</TooltipTrigger>
															<TooltipContent>Open in new tab</TooltipContent>
														</Tooltip>
													</div>

													<Tooltip>
														<TooltipTrigger>
															<Button
																variant="default"
																size="sm"
																disabled={printing[item.id] ||
																	charging[item.id] ||
																	mergingFiles[item.file]}
																onclick={() => printPdf(item)}
															>
																{#if charging[item.id]}
																	<CreditCard class="mr-1 h-3 w-3 animate-pulse" />
																	Charging...
																{:else if printing[item.id]}
																	<LoaderCircle class="mr-1 h-3 w-3 animate-spin" />
																	Printing...
																{:else}
																	<Printer class="h-4 w-4" />
																	Print
																{/if}
															</Button>
														</TooltipTrigger>
														<TooltipContent>
															{itemPrintMode[item.id] === 'simplex'
																? 'Print Simplex (will charge)'
																: 'Print Duplex (free)'}
														</TooltipContent>
													</Tooltip>

													{#if item.processed && !item.isMerged}
														<Tooltip>
															<TooltipTrigger>
																<Button
																	variant="outline"
																	size="sm"
																	disabled={unprocessingItem[item.id]}
																	onclick={() => unprocessItem(item)}
																>
																	{#if unprocessingItem[item.id]}
																		<LoaderCircle class="h-4 w-4 animate-spin" />
																	{:else}
																		<X class="h-4 w-4" />
																	{/if}
																</Button>
															</TooltipTrigger>
															<TooltipContent>Unprocess</TooltipContent>
														</Tooltip>
													{:else if !item.processed && !item.isMerged}
														<Tooltip>
															<TooltipTrigger>
																<Button
																	variant="outline"
																	size="sm"
																	disabled={unprocessingItem[item.id]}
																	onclick={() => confirmItem(item)}
																>
																	{#if unprocessingItem[item.id]}
																		<LoaderCircle class="h-4 w-4 animate-spin" />
																	{:else}
																		<CheckCircle class="h-4 w-4" />
																	{/if}
																</Button>
															</TooltipTrigger>
															<TooltipContent>Confirm</TooltipContent>
														</Tooltip>
													{/if}

													{#if item.isMerged}
														<Tooltip>
															<TooltipTrigger>
																<Button
																	variant="destructive"
																	size="icon"
																	onclick={() => unmerge(item.user, item.file)}
																>
																	<X class="h-4 w-4" />
																</Button>
															</TooltipTrigger>
															<TooltipContent>Unmerge</TooltipContent>
														</Tooltip>
													{/if}
												</div>

												<!-- Mobile/Medium -->
												<div class="md:hidden">
													<DropdownMenu>
														<DropdownMenuTrigger>
															<Button variant="outline" size="icon">
																<ChevronDown class="h-4 w-4" />
															</Button>
														</DropdownMenuTrigger>
														<DropdownMenuContent align="end" class="w-56">
															<DropdownMenuItem
																onclick={() => openPreview(item.file)}
																disabled={mergingFiles[item.file]}
															>
																<Eye class="mr-2 h-4 w-4" />
																Preview
															</DropdownMenuItem>
															<DropdownMenuItem
																onclick={() => openInNewTab(item.file)}
																disabled={mergingFiles[item.file]}
															>
																<ExternalLink class="mr-2 h-4 w-4" />
																Open in new tab
															</DropdownMenuItem>

															<DropdownMenuSeparator />

															<DropdownMenuItem
																onclick={() => printPdf(item)}
																disabled={printing[item.id] ||
																	charging[item.id] ||
																	mergingFiles[item.file]}
																class={cn(
																	'flex items-center',
																	(printing[item.id] || charging[item.id]) && 'opacity-75'
																)}
															>
																{#if charging[item.id]}
																	<CreditCard class="mr-2 h-3 w-3 animate-pulse" />
																	Charging...
																{:else if printing[item.id]}
																	<LoaderCircle class="mr-2 h-3 w-3 animate-spin" />
																	Printing...
																{:else}
																	<Printer class="mr-2 h-4 w-4" />
																	Print ({itemPrintMode[item.id] === 'simplex'
																		? 'Simplex'
																		: 'Duplex'})
																{/if}
															</DropdownMenuItem>

															{#if item.processed && !item.isMerged}
																<DropdownMenuItem
																	onclick={() => unprocessItem(item)}
																	disabled={unprocessingItem[item.id]}
																>
																	{#if unprocessingItem[item.id]}
																		<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
																		Unprocessing...
																	{:else}
																		<X class="mr-2 h-4 w-4" />
																		Unprocess
																	{/if}
																</DropdownMenuItem>
															{:else if !item.processed && !item.isMerged}
																<DropdownMenuItem
																	onclick={() => confirmItem(item)}
																	disabled={unprocessingItem[item.id]}
																>
																	{#if unprocessingItem[item.id]}
																		<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
																		Confirming...
																	{:else}
																		<CheckCircle class="mr-2 h-4 w-4" />
																		Confirm
																	{/if}
																</DropdownMenuItem>
															{/if}

															{#if item.isMerged}
																<DropdownMenuItem
																	onclick={() => unmerge(item.user, item.file)}
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

										<!-- Expanded originals -->
										{#if item.isMerged && item.mergedFrom && item.mergedId && expandedMergedItems[item.mergedId]}
											{#each item.mergedFrom as originalFile}
												{#if queue.find((q) => q.file === originalFile && q.user === item.user)}
													{@const original = queue.find(
														(q) => q.file === originalFile && q.user === item.user
													)!}
													<TableRow class="bg-muted/30">
														<TableCell></TableCell>
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
				{/each}
			</div>
		{/if}
	</div>
</TooltipProvider>
