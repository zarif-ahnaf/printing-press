<script lang="ts">
	import { onDestroy } from 'svelte';

	// UI Components (unchanged)
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

	// Icons (unchanged)
	import { FileText, Printer, Merge, LoaderCircle, Eye, X } from 'lucide-svelte';
	import { QUEUE_URL } from '$lib/constants/backend';
	import { token } from '$lib/stores/token.svelte';
	import { PdfCache as PdfMergeCache } from './pdf_cache';

	// ✅ IMPORT WASM FUNCTION
	import { merge_pdfs_wasm } from '$lib/wasm/pdf_merge'; // Adjust path as needed

	interface QueueItem {
		id: number;
		file: string;
		processed: boolean;
		created_at: string;
		user: string;
		isMerged?: boolean;
		mergedFrom?: string[];
		hidden?: boolean;
		cacheKey?: string;
	}

	// ———————— State ————————
	let queue = $state<QueueItem[]>([]);
	let groupedQueue = $state<Record<string, QueueItem[]>>({});
	let loading = $state(false);
	let error = $state<string | null>(null);
	let merging = $state(new Set<string>());
	let mergingFiles = $state(new Set<string>());
	let printing = $state(new Set<string>());
	let previewUrl = $state<string | null>(null);
	let previewLoading = $state(false);
	let selectedItems = $state<Record<string, Set<string>>>({});

	const mergeCache = new PdfMergeCache();

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
				queue = data.queue || [];
				groupedQueue = groupByUser(queue);
				selectedItems = {};
				for (const user of Object.keys(groupedQueue)) {
					selectedItems[user] = new Set();
				}
			} catch (err) {
				error = err instanceof Error ? err.message : 'An unknown error occurred';
			} finally {
				loading = false;
			}
		}
		fetchQueue();
	});

	function toggleSelect(user: string, file: string, checked: boolean) {
		if (mergingFiles.has(file)) return;
		const currentSet = selectedItems[user] || new Set<string>();
		const newSet = new Set(currentSet);
		if (checked) newSet.add(file);
		else newSet.delete(file);
		selectedItems = { ...selectedItems, [user]: newSet };
	}

	// ✅ FETCH BLOB AS UINT8ARRAY
	async function fetchPdfAsUint8Array(url: string): Promise<Uint8Array> {
		const res = await fetch(url, {
			headers: { Authorization: `Bearer ${token.value}` }
		});
		if (!res.ok) throw new Error(`Failed to access: ${url}`);
		const arrayBuffer = await res.arrayBuffer();
		return new Uint8Array(arrayBuffer);
	}

	async function mergePdfs(user: string) {
		const files = Array.from(selectedItems[user] || []);
		if (files.length === 0) return;

		const cacheKey = mergeCache.generateKey(files);
		const userItems = groupedQueue[user] || [];

		mergingFiles = new Set([...mergingFiles, ...files]);

		// Check cache first
		if (mergeCache.has(cacheKey)) {
			const cached = mergeCache.get(cacheKey)!;
			const mergedItem: QueueItem = {
				id: -1,
				file: cached.url,
				processed: true,
				created_at: new Date().toISOString(),
				user,
				isMerged: true,
				mergedFrom: files,
				cacheKey
			};

			const updatedItems = userItems.map((item) =>
				files.includes(item.file) ? { ...item, hidden: true } : item
			);

			const insertIndex = updatedItems.findIndex((item) => !item.hidden) || 0;
			const finalItems = [...updatedItems];
			finalItems.splice(insertIndex, 0, mergedItem);

			groupedQueue = { ...groupedQueue, [user]: finalItems };
			selectedItems[user] = new Set();
			mergingFiles = new Set([...mergingFiles].filter((f) => !files.includes(f)));
			return;
		}

		// ✅ USE WASM INSTEAD OF HTTP ENDPOINT
		merging.add(user);
		try {
			// Fetch PDFs as Uint8Arrays
			const uint8Arrays: Uint8Array[] = [];
			for (const fileUrl of files) {
				const uint8 = await fetchPdfAsUint8Array(fileUrl);
				uint8Arrays.push(uint8);
			}

			// Create JS Array of Uint8Array for WASM
			const pdfArray = new Array(uint8Arrays.length);
			for (let i = 0; i < uint8Arrays.length; i++) {
				pdfArray[i] = uint8Arrays[i];
			}

			// Call WASM function
			const mergedBytes: Uint8Array = merge_pdfs_wasm(pdfArray);

			// Create blob and URL
			const mergedBlob = new Blob([mergedBytes], { type: 'application/pdf' });
			const url = URL.createObjectURL(mergedBlob);
			const filename = `${user}_merged.pdf`;
			mergeCache.set(cacheKey, url, filename);

			const mergedItem: QueueItem = {
				id: -1,
				file: url,
				processed: true,
				created_at: new Date().toISOString(),
				user,
				isMerged: true,
				mergedFrom: files,
				cacheKey
			};

			const updatedItems = userItems.map((item) =>
				files.includes(item.file) ? { ...item, hidden: true } : item
			);

			const firstVisibleIndex = updatedItems.findIndex((item) => !item.hidden);
			const insertIndex = firstVisibleIndex === -1 ? updatedItems.length : firstVisibleIndex;

			const finalItems = [...updatedItems];
			finalItems.splice(insertIndex, 0, mergedItem);

			groupedQueue = { ...groupedQueue, [user]: finalItems };
			selectedItems[user] = new Set();
		} catch (err) {
			error = err instanceof Error ? `Merge error: ${err.message}` : 'Merge failed';
		} finally {
			merging.delete(user);
			mergingFiles = new Set([...mergingFiles].filter((f) => !files.includes(f)));
		}
	}

	function unmerge(user: string, fileUrl: string) {
		const userItems = groupedQueue[user] || [];
		const mergedIndex = userItems.findIndex((item) => item.file === fileUrl && item.isMerged);
		if (mergedIndex === -1) return;

		const mergedItem = userItems[mergedIndex];
		if (!mergedItem.mergedFrom) {
			console.warn('Merged item missing mergedFrom:', mergedItem);
			return;
		}

		if (fileUrl.startsWith('blob:')) {
			URL.revokeObjectURL(fileUrl);
		}

		const withoutMerged = [...userItems];
		withoutMerged.splice(mergedIndex, 1);

		const originals = mergedItem.mergedFrom.map((file) => {
			const original = queue.find((q) => q.file === file && q.user === user);
			return original
				? { ...original, hidden: false }
				: {
						id: -1,
						file,
						processed: false,
						created_at: new Date().toISOString(),
						user,
						hidden: false
					};
		});

		const restored = [...withoutMerged];
		restored.splice(mergedIndex, 0, ...originals);
		groupedQueue = { ...groupedQueue, [user]: restored };
		selectedItems[user] = new Set();
	}

	// ———————— Print & Preview ———————— (unchanged)
	async function printPdf(url: string) {
		printing.add(url);
		try {
			const res = await fetch(url, { headers: { Authorization: `Bearer ${token.value}` } });
			if (!res.ok) throw new Error('Failed to fetch PDF');
			const blob = await res.blob();
			const pdfUrl = URL.createObjectURL(blob);
			const printWindow = window.open(pdfUrl, '_blank');
			if (!printWindow) {
				error = 'Popup blocked. Please allow popups to print.';
				return;
			}
			printWindow.addEventListener('load', () => {
				printWindow.print();
				URL.revokeObjectURL(pdfUrl);
			});
		} catch (err) {
			error = err instanceof Error ? `Print error: ${err.message}` : 'Print failed';
		} finally {
			printing.delete(url);
		}
	}

	async function openPreview(url: string) {
		previewLoading = true;
		previewUrl = null;
		try {
			const res = await fetch(url, { headers: { Authorization: `Bearer ${token.value}` } });
			if (!res.ok) throw new Error('PDF not accessible');
			const blob = await res.blob();
			previewUrl = URL.createObjectURL(blob);
		} catch (err) {
			error = err instanceof Error ? `Preview error: ${err.message}` : 'Failed to load PDF preview';
			previewUrl = null;
		} finally {
			previewLoading = false;
		}
	}

	function closePreview() {
		if (previewUrl) {
			URL.revokeObjectURL(previewUrl);
			previewUrl = null;
		}
	}

	onDestroy(() => {
		if (previewUrl) URL.revokeObjectURL(previewUrl);
		mergeCache.revokeAll();
	});
</script>

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
				<embed
					src={previewUrl}
					type="application/pdf"
					class="h-full min-h-[500px] w-full"
					aria-label="PDF preview"
				/>
			{:else}
				<div class="flex h-full items-center justify-center text-destructive">
					Failed to load PDF preview
				</div>
			{/if}
		</div>
		<DialogFooter class="border-t bg-background px-6 py-4">
			<DialogClose>
				<Button variant="outline">Close</Button>
			</DialogClose>
		</DialogFooter>
	</DialogContent>
</Dialog>

<!-- Main Content -->
<div class="container mx-auto space-y-6 py-6">
	<h1 class="text-3xl font-bold tracking-tight">PDF Processing Queue</h1>

	{#if error}
		<Alert variant="destructive">
			<AlertDescription>{error}</AlertDescription>
		</Alert>
	{/if}

	{#if loading}
		<div class="flex h-32 items-center justify-center">
			<LoaderCircle class="h-8 w-8 animate-spin text-primary" />
		</div>
	{:else if Object.keys(groupedQueue).length === 0}
		<div class="py-12 text-center">
			<FileText class="mx-auto h-12 w-12 text-muted-foreground" />
			<h3 class="mt-2 text-lg font-medium">No items in queue</h3>
			<p class="mt-1 text-muted-foreground">All PDFs have been processed</p>
		</div>
	{:else}
		<div class="space-y-8">
			{#each Object.entries(groupedQueue) as [user, items]}
				<div class="overflow-hidden rounded-lg border">
					<div class="flex flex-wrap items-center justify-between gap-4 bg-muted/50 px-6 py-4">
						<div>
							<h2 class="text-xl font-semibold">{user}</h2>
							<p class="text-sm text-muted-foreground">
								{items.filter((i) => !i.hidden).length} pending PDF{items.filter((i) => !i.hidden)
									.length !== 1
									? 's'
									: ''}
							</p>
						</div>
						<Button
							variant="default"
							size="sm"
							disabled={merging.has(user) || (selectedItems[user]?.size || 0) === 0}
							onclick={() => mergePdfs(user)}
						>
							{#if merging.has(user)}
								<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
								Merging...
							{:else}
								<Merge class="mr-2 h-4 w-4" />
								Merge Selected
							{/if}
						</Button>
					</div>

					<Table>
						<TableHeader>
							<TableRow>
								<TableHead class="w-12"></TableHead>
								<TableHead>File</TableHead>
								<TableHead>Status</TableHead>
								<TableHead>Created</TableHead>
								<TableHead class="text-right">Actions</TableHead>
							</TableRow>
						</TableHeader>
						<TableBody>
							{#each items as item}
								{#if !item.hidden}
									<TableRow
										class="transition-opacity duration-200 ease-in-out {mergingFiles.has(item.file)
											? 'pointer-events-none opacity-50'
											: ''}"
									>
										<TableCell>
											{#if !item.isMerged}
												<Checkbox
													checked={selectedItems[user]?.has(item.file) || false}
													onCheckedChange={(checked) => toggleSelect(user, item.file, checked)}
													disabled={mergingFiles.has(item.file)}
												/>
											{/if}
										</TableCell>
										<TableCell class="font-medium">
											{item.file.split('/').pop()}
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
										<TableCell>
											{new Date(item.created_at).toLocaleString()}
										</TableCell>
										<TableCell class="text-right">
											<div class="flex justify-end gap-2">
												<Button
													variant="outline"
													size="sm"
													onclick={() => openPreview(item.file)}
													disabled={mergingFiles.has(item.file)}
												>
													<Eye class="h-4 w-4" />
												</Button>
												<Button
													variant="outline"
													size="sm"
													disabled={printing.has(item.file) || mergingFiles.has(item.file)}
													onclick={() => printPdf(item.file)}
												>
													{#if printing.has(item.file)}
														<LoaderCircle class="h-4 w-4 animate-spin" />
													{:else}
														<Printer class="h-4 w-4" />
													{/if}
												</Button>
												{#if item.isMerged}
													<Button
														variant="destructive"
														size="icon"
														onclick={() => unmerge(user, item.file)}
													>
														<X class="h-4 w-4" />
													</Button>
												{/if}
											</div>
										</TableCell>
									</TableRow>
								{/if}
							{/each}
						</TableBody>
					</Table>
				</div>
			{/each}
		</div>
	{/if}
</div>
