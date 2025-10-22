<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

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

	// Icons
	import { FileText, Printer, Merge, LoaderCircle, Eye, X } from 'lucide-svelte';
	import { QUEUE_URL } from '$lib/constants/backend';
	import { token } from '$lib/stores/token.svelte';
	import init, { merge_pdfs_wasm } from '$lib/wasm/pdf_merge';

	interface QueueItem {
		id: number;
		file: string;
		processed: boolean;
		created_at: string;
		user: string;
		isMerged?: boolean;
		mergedFrom?: string[];
		hidden?: boolean;
	}

	let queue = $state<QueueItem[]>([]);
	let groupedQueue = $state<Record<string, QueueItem[]>>({});
	let loading = $state(false);
	let error = $state<string | null>(null);
	let merging = $state<Record<string, boolean>>({});
	let mergingFiles = $state<Record<string, boolean>>({});
	let printing = $state<Record<string, boolean>>({});
	let previewUrl = $state<string | null>(null);
	let previewLoading = $state(false);
	let selectedItems = $state<Record<string, Record<string, boolean>>>({});

	const activeMergedBlobs = new Set<string>();

	// 🔍 Estimate available memory (in bytes)
	function getEstimatedMemory(): number {
		// Chromium: use performance.memory
		if ('memory' in performance) {
			const mem = (performance as any).memory;
			if (mem && typeof mem.jsHeapSizeLimit === 'number') {
				// jsHeapSizeLimit is close to total JS heap, but we want total system estimate
				return Math.min(mem.jsHeapSizeLimit * 2, 4 * 1024 ** 3); // cap at 4GB for safety
			}
		}

		// navigator.deviceMemory (in GB, rounded)
		if ('deviceMemory' in navigator) {
			const deviceMemGB = (navigator as any).deviceMemory;
			if (typeof deviceMemGB === 'number') {
				return deviceMemGB * 1024 ** 3;
			}
		}

		// Conservative fallback: assume 4GB on low-end, 8GB on others
		if (
			'navigator' in window &&
			'hardwareConcurrency' in navigator &&
			(navigator as any).hardwareConcurrency <= 2
		) {
			return 4 * 1024 ** 3; // 4GB
		}
		return 8 * 1024 ** 3; // 8GB
	}

	// 🔍 Fetch size without loading full PDF
	async function getPDFSize(url: string): Promise<number> {
		const res = await fetch(url, {
			method: 'HEAD',
			headers: { Authorization: `Bearer ${token.value}` }
		});
		if (!res.ok) {
			// Fallback: GET with Range to avoid full download
			const rangeRes = await fetch(url, {
				headers: {
					Authorization: `Bearer ${token.value}`,
					Range: 'bytes=0-0'
				}
			});
			if (rangeRes.status === 206 || rangeRes.status === 200) {
				const contentRange = rangeRes.headers.get('Content-Range') || '';
				const total = contentRange.split('/').pop();
				if (total && !isNaN(Number(total))) {
					return Number(total);
				}
			}
			throw new Error(`Cannot determine size: ${url}`);
		}
		const length = res.headers.get('Content-Length');
		return length ? parseInt(length, 10) : 0;
	}

	async function fetchPdfAsUint8Array(url: string): Promise<Uint8Array> {
		const res = await fetch(url, {
			headers: { Authorization: `Bearer ${token.value}` }
		});
		if (!res.ok) throw new Error(`Failed to access: ${url}`);
		const arrayBuffer = await res.arrayBuffer();
		return new Uint8Array(arrayBuffer);
	}

	// 🔁 Sequential merge: merge A+B → AB, then AB+C → ABC, etc.
	async function mergeSequentially(pdfs: Uint8Array[]): Promise<Uint8Array> {
		let current = pdfs[0];
		for (let i = 1; i < pdfs.length; i++) {
			current = merge_pdfs_wasm([current, pdfs[i]]);
			// Optional: yield to keep UI responsive
			await new Promise((resolve) => setTimeout(resolve, 0));
		}
		return current;
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

	onMount(async () => {
		await init();
	});

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
					selectedItems[user] = {};
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
		if (mergingFiles[file]) return;
		selectedItems = {
			...selectedItems,
			[user]: {
				...selectedItems[user],
				[file]: checked
			}
		};
	}

	async function mergePdfs(user: string) {
		const files = Object.entries(selectedItems[user] || {})
			.filter(([, checked]) => checked)
			.map(([file]) => file);

		if (files.length === 0) return;

		const userItems = groupedQueue[user] || [];

		merging = { ...merging, [user]: true };
		mergingFiles = { ...mergingFiles };
		for (const f of files) mergingFiles[f] = true;

		try {
			// 🔍 Step 1: Estimate total size
			let totalSize = 0;
			try {
				const sizePromises = files.map((url) => getPDFSize(url));
				const sizes = await Promise.all(sizePromises);
				totalSize = sizes.reduce((sum, s) => sum + s, 0);
			} catch (sizeErr) {
				console.warn('Size estimation failed, assuming safe merge:', sizeErr);
				totalSize = 0; // skip memory check
			}

			// 🔍 Step 2: Decide merge strategy
			const useSequential =
				totalSize > 0 &&
				(() => {
					const mem = getEstimatedMemory();
					const threshold = mem * 0.8; // 80%
					return totalSize >= threshold;
				})();

			// Fetch all PDFs
			const uint8Arrays: Uint8Array[] = [];
			for (const fileUrl of files) {
				const uint8 = await fetchPdfAsUint8Array(fileUrl);
				uint8Arrays.push(uint8);
			}

			// 🔀 Merge
			let mergedBytes: Uint8Array;
			if (useSequential && uint8Arrays.length > 1) {
				mergedBytes = await mergeSequentially(uint8Arrays);
			} else {
				mergedBytes = merge_pdfs_wasm(uint8Arrays);
			}

			const mergedBlob = new Blob([mergedBytes.slice()], { type: 'application/pdf' });
			const url = URL.createObjectURL(mergedBlob);
			activeMergedBlobs.add(url);

			// Insert in order
			const fileToIndex = new Map<string, number>();
			for (const [idx, item] of userItems.entries()) {
				if (files.includes(item.file)) fileToIndex.set(item.file, idx);
			}
			const selectedIndices = files.map((f) => fileToIndex.get(f)!);
			const maxIndex = Math.max(...selectedIndices);
			const insertIndex = maxIndex + 1;

			const mergedItem: QueueItem = {
				id: -1,
				file: url,
				processed: true,
				created_at: new Date().toISOString(),
				user,
				isMerged: true,
				mergedFrom: files
			};

			const updatedItems = userItems.map((item) =>
				files.includes(item.file) ? { ...item, hidden: true } : item
			);
			const finalItems = [...updatedItems];
			finalItems.splice(insertIndex, 0, mergedItem);

			groupedQueue = { ...groupedQueue, [user]: finalItems };
			selectedItems = { ...selectedItems, [user]: {} };
		} catch (err) {
			error = err instanceof Error ? `Merge error: ${err.message}` : 'Merge failed';
		} finally {
			merging = { ...merging, [user]: false };
			mergingFiles = { ...mergingFiles };
			for (const f of files) delete mergingFiles[f];
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

		if (fileUrl.startsWith('blob:') && activeMergedBlobs.has(fileUrl)) {
			URL.revokeObjectURL(fileUrl);
			activeMergedBlobs.delete(fileUrl);
		}

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
						hidden: false
					};
		});

		const restored = [...withoutMerged];
		restored.splice(mergedIndex, 0, ...restoredOriginals);
		groupedQueue = { ...groupedQueue, [user]: restored };
		selectedItems = { ...selectedItems, [user]: {} };
	}

	// --- Print & Preview (unchanged from previous memory-safe version) ---
	async function printPdf(url: string) {
		printing = { ...printing, [url]: true };
		try {
			let pdfUrl: string;
			let shouldRevoke = false;

			if (url.startsWith('blob:')) {
				pdfUrl = url;
			} else {
				const res = await fetch(url, { headers: { Authorization: `Bearer ${token.value}` } });
				if (!res.ok) throw new Error('Failed to fetch PDF');
				const blob = await res.blob();
				pdfUrl = URL.createObjectURL(blob);
				shouldRevoke = true;
			}

			const printWindow = window.open(pdfUrl, '_blank');
			if (!printWindow) {
				error = 'Popup blocked. Please allow popups to print.';
				if (shouldRevoke) URL.revokeObjectURL(pdfUrl);
				return;
			}

			const cleanup = () => {
				if (shouldRevoke) URL.revokeObjectURL(pdfUrl);
			};

			printWindow.addEventListener('load', () => printWindow.print());
			printWindow.addEventListener('beforeunload', cleanup);

			const interval = setInterval(() => {
				if (printWindow.closed) {
					cleanup();
					clearInterval(interval);
				}
			}, 500);
		} catch (err) {
			error = err instanceof Error ? `Print error: ${err.message}` : 'Print failed';
		} finally {
			printing = { ...printing, [url]: false };
		}
	}

	async function openPreview(url: string) {
		previewLoading = true;
		previewUrl = null;
		try {
			if (url.startsWith('blob:')) {
				previewUrl = url;
			} else {
				const res = await fetch(url, { headers: { Authorization: `Bearer ${token.value}` } });
				if (!res.ok) throw new Error('PDF not accessible');
				const blob = await res.blob();
				previewUrl = URL.createObjectURL(blob);
			}
		} catch (err) {
			error = err instanceof Error ? `Preview error: ${err.message}` : 'Failed to load PDF preview';
			previewUrl = null;
		} finally {
			previewLoading = false;
		}
	}

	function closePreview() {
		if (previewUrl && !previewUrl.startsWith('http')) {
			URL.revokeObjectURL(previewUrl);
		}
		previewUrl = null;
	}

	onDestroy(() => {
		for (const url of activeMergedBlobs) {
			if (url.startsWith('blob:')) URL.revokeObjectURL(url);
		}
		activeMergedBlobs.clear();
		if (previewUrl && !previewUrl.startsWith('http')) {
			URL.revokeObjectURL(previewUrl);
		}
	});
</script>

<!-- Rest of the template (Dialog + Main Content) remains identical -->
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
							disabled={merging[user] ||
								Object.values(selectedItems[user] || {}).filter(Boolean).length === 0}
							onclick={() => mergePdfs(user)}
						>
							{#if merging[user]}
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
										class="transition-opacity duration-200 ease-in-out {mergingFiles[item.file]
											? 'pointer-events-none opacity-50'
											: ''}"
									>
										<TableCell>
											{#if !item.isMerged}
												<Checkbox
													checked={!!selectedItems[user]?.[item.file]}
													onCheckedChange={(checked) => toggleSelect(user, item.file, checked)}
													disabled={mergingFiles[item.file]}
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
													disabled={mergingFiles[item.file]}
												>
													<Eye class="h-4 w-4" />
												</Button>
												<Button
													variant="outline"
													size="sm"
													disabled={printing[item.file] || mergingFiles[item.file]}
													onclick={() => printPdf(item.file)}
												>
													{#if printing[item.file]}
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
