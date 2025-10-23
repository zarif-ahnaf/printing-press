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
	import {
		Tooltip,
		TooltipContent,
		TooltipProvider,
		TooltipTrigger
	} from '$lib/components/ui/tooltip';

	// ✅ Lucide Icons (all from lucide-svelte)
	import {
		FileText,
		Printer,
		Merge,
		LoaderCircle,
		Eye,
		X,
		ExternalLink,
		ChevronRight
	} from 'lucide-svelte';

	import { QUEUE_URL } from '$lib/constants/backend';
	import { token } from '$lib/stores/token.svelte';

	// ✅ pdf-lib for client-side merging
	import { PDFDocument } from 'pdf-lib';

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
	let mergingAllForUser = $state<Record<string, boolean>>({});

	const activeMergedBlobs = new Set<string>();

	// ✅ Merge using pdf-lib
	async function mergePdfsUsingPdfLib(pdfUrls: string[]): Promise<Uint8Array> {
		if (pdfUrls.length === 0) throw new Error('No PDFs to merge');
		if (pdfUrls.length === 1) {
			const uint8 = await fetchPdfAsUint8Array(pdfUrls[0]);
			return uint8;
		}

		const mergedPdf = await PDFDocument.create();
		for (const url of pdfUrls) {
			const uint8 = await fetchPdfAsUint8Array(url);
			const sourcePdf = await PDFDocument.load(uint8, { ignoreEncryption: true });
			const copiedPages = await mergedPdf.copyPages(sourcePdf, sourcePdf.getPageIndices());
			copiedPages.forEach((page) => mergedPdf.addPage(page));
			await new Promise((resolve) => setTimeout(resolve, 0)); // yield to UI
		}
		return await mergedPdf.save();
	}

	async function fetchPdfAsUint8Array(url: string): Promise<Uint8Array> {
		const res = await fetch(url, {
			headers: { Authorization: `Bearer ${token.value}` }
		});
		if (!res.ok) throw new Error(`Failed to access: ${url}`);
		const arrayBuffer = await res.arrayBuffer();
		return new Uint8Array(arrayBuffer);
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

	// No WASM init needed
	onMount(() => {
		// pdf-lib is pure JS
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
			const mergedBytes = await mergePdfsUsingPdfLib(files);

			const mergedBlob = new Blob([mergedBytes.slice()], { type: 'application/pdf' });
			const url = URL.createObjectURL(mergedBlob);
			activeMergedBlobs.add(url);

			const selectedIndices: number[] = [];
			for (const [idx, item] of userItems.entries()) {
				if (files.includes(item.file)) {
					selectedIndices.push(idx);
				}
			}
			const maxIndex =
				selectedIndices.length > 0 ? Math.max(...selectedIndices) : userItems.length - 1;
			const insertIndex = maxIndex + 1;

			const mergedItem: QueueItem = {
				id: -1,
				file: url,
				processed: true,
				created_at: new Date().toISOString(),
				user,
				isMerged: true,
				mergedFrom: files,
				hidden: false
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

	async function mergeAllForUser(user: string) {
		const userItems = groupedQueue[user] || [];
		const filesToMerge = userItems
			.filter((item) => !item.hidden && !item.isMerged)
			.map((item) => item.file);

		if (filesToMerge.length === 0) return;

		mergingAllForUser = { ...mergingAllForUser, [user]: true };
		mergingFiles = { ...mergingFiles };
		for (const f of filesToMerge) mergingFiles[f] = true;

		try {
			const mergedBytes = await mergePdfsUsingPdfLib(filesToMerge);

			const mergedBlob = new Blob([mergedBytes.slice()], { type: 'application/pdf' });
			const url = URL.createObjectURL(mergedBlob);
			activeMergedBlobs.add(url);

			const selectedIndices: number[] = [];
			for (const [idx, item] of userItems.entries()) {
				if (filesToMerge.includes(item.file)) {
					selectedIndices.push(idx);
				}
			}
			const maxIndex =
				selectedIndices.length > 0 ? Math.max(...selectedIndices) : userItems.length - 1;
			const insertIndex = maxIndex + 1;

			const mergedItem: QueueItem = {
				id: -1,
				file: url,
				processed: true,
				created_at: new Date().toISOString(),
				user,
				isMerged: true,
				mergedFrom: filesToMerge,
				hidden: false
			};

			const updatedItems = userItems.map((item) =>
				filesToMerge.includes(item.file) ? { ...item, hidden: true } : item
			);
			const finalItems = [...updatedItems];
			finalItems.splice(insertIndex, 0, mergedItem);

			groupedQueue = { ...groupedQueue, [user]: finalItems };
			selectedItems = { ...selectedItems, [user]: {} };
		} catch (err) {
			error = err instanceof Error ? `Merge error: ${err.message}` : 'Merge failed';
		} finally {
			mergingAllForUser = { ...mergingAllForUser, [user]: false };
			mergingFiles = { ...mergingFiles };
			for (const f of filesToMerge) delete mergingFiles[f];
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

	async function printPdf(url: string) {
		printing = { ...printing, [url]: true };
		let iframe: HTMLIFrameElement | null = null;
		let blobToRevoke: string | null = null;

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
				blobToRevoke = pdfUrl;
				shouldRevoke = true;
			}

			iframe = document.createElement('iframe');
			iframe.style.position = 'absolute';
			iframe.style.left = '-9999px';
			iframe.style.top = '-9999px';
			iframe.style.width = '0';
			iframe.style.height = '0';
			iframe.setAttribute('aria-hidden', 'true');

			await new Promise<void>((resolve, reject) => {
				iframe!.onload = () => resolve();
				iframe!.onerror = () => reject(new Error('Failed to load PDF in iframe'));
				iframe!.src = pdfUrl;
				document.body.appendChild(iframe!);
			});

			iframe.contentWindow?.print();

			setTimeout(() => {
				if (iframe && document.body.contains(iframe)) {
					document.body.removeChild(iframe);
					iframe = null;
				}
				if (shouldRevoke && blobToRevoke) {
					URL.revokeObjectURL(blobToRevoke);
				}
			}, 10000);
		} catch (err) {
			error = err instanceof Error ? `Print error: ${err.message}` : 'Print failed';
			if (iframe && document.body.contains(iframe)) {
				document.body.removeChild(iframe);
			}
			if (blobToRevoke) {
				URL.revokeObjectURL(blobToRevoke);
			}
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

	function openInNewTab(url: string) {
		if (url.startsWith('blob:')) {
			error = 'Cannot open merged PDFs in a new tab. Use preview instead.';
			return;
		}

		let blobUrl: string | null = null;
		(async () => {
			try {
				const res = await fetch(url, { headers: { Authorization: `Bearer ${token.value}` } });
				if (!res.ok) throw new Error('Failed to fetch PDF for new tab');
				const blob = await res.blob();
				blobUrl = URL.createObjectURL(blob);
				const win = window.open(blobUrl, '_blank');
				if (!win) {
					error = 'Popup blocked. Please allow popups to open PDF in new tab.';
					URL.revokeObjectURL(blobUrl);
					blobUrl = null;
				} else {
					setTimeout(() => {
						if (blobUrl) {
							URL.revokeObjectURL(blobUrl);
							blobUrl = null;
						}
					}, 60_000);
				}
			} catch (err) {
				error =
					err instanceof Error ? `New tab error: ${err.message}` : 'Failed to open in new tab';
				if (blobUrl) {
					URL.revokeObjectURL(blobUrl);
					blobUrl = null;
				}
			}
		})();
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

<!-- Dialog for PDF Preview -->
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

<!-- Main Content with TooltipProvider -->
<TooltipProvider>
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
							<div class="flex flex-wrap gap-2">
								<Button
									variant="outline"
									size="sm"
									disabled={mergingAllForUser[user] ||
										items.filter((i) => !i.hidden && !i.isMerged).length === 0}
									onclick={() => mergeAllForUser(user)}
								>
									{#if mergingAllForUser[user]}
										<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
										Merging All...
									{:else}
										<Merge class="mr-2 h-4 w-4" />
										Merge All
									{/if}
								</Button>

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
													<Tooltip>
														<TooltipTrigger>
															<Checkbox
																checked={!!selectedItems[user]?.[item.file]}
																onCheckedChange={(checked) =>
																	toggleSelect(user, item.file, checked)}
																disabled={mergingFiles[item.file]}
															/>
														</TooltipTrigger>
														<TooltipContent>Select PDF to merge</TooltipContent>
													</Tooltip>
												{:else}
													<div
														class="flex h-4 w-4 items-center justify-center text-muted-foreground"
													>
														<ChevronRight class="h-3 w-3" />
													</div>
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
											</TableCell>
											<TableCell>
												{#if item.isMerged}
													<Tooltip>
														<TooltipTrigger>
															<span><Badge variant="default">Merged</Badge></span>
														</TooltipTrigger>
														<TooltipContent
															>This PDF was created by merging multiple files</TooltipContent
														>
													</Tooltip>
												{:else if item.processed}
													<Tooltip>
														<TooltipTrigger>
															<span><Badge variant="secondary">Processed</Badge></span>
														</TooltipTrigger>
														<TooltipContent>PDF has been processed and is ready</TooltipContent>
													</Tooltip>
												{:else}
													<Tooltip>
														<TooltipTrigger>
															<span><Badge variant="destructive">Pending</Badge></span>
														</TooltipTrigger>
														<TooltipContent>PDF is waiting to be processed</TooltipContent>
													</Tooltip>
												{/if}
											</TableCell>
											<TableCell>
												{new Date(item.created_at).toLocaleString()}
											</TableCell>
											<TableCell class="text-right">
												<div class="flex justify-end gap-2">
													<div class="flex rounded-md border border-input shadow-sm">
														<Tooltip>
															<TooltipTrigger>
																<Button
																	variant="outline"
																	size="sm"
																	class="rounded-r-none border-r"
																	onclick={() => openPreview(item.file)}
																	disabled={mergingFiles[item.file]}
																	aria-label="Preview PDF"
																>
																	<Eye class="h-4 w-4" />
																</Button>
															</TooltipTrigger>
															<TooltipContent>Preview PDF</TooltipContent>
														</Tooltip>
														<Tooltip>
															<TooltipTrigger>
																<Button
																	variant="outline"
																	size="sm"
																	class="rounded-l-none"
																	onclick={() => openInNewTab(item.file)}
																	disabled={mergingFiles[item.file] ||
																		item.file.startsWith('blob:')}
																	aria-label="Open in new tab"
																>
																	<ExternalLink class="h-4 w-4" />
																</Button>
															</TooltipTrigger>
															<TooltipContent>
																{item.file.startsWith('blob:')
																	? 'Merged PDFs cannot be opened in a new tab — use Preview instead'
																	: 'Open in new browser tab'}
															</TooltipContent>
														</Tooltip>
													</div>

													<Tooltip>
														<TooltipTrigger>
															<Button
																variant="outline"
																size="sm"
																disabled={printing[item.file] || mergingFiles[item.file]}
																onclick={() => printPdf(item.file)}
																aria-label="Print PDF"
															>
																{#if printing[item.file]}
																	<LoaderCircle class="h-4 w-4 animate-spin" />
																{:else}
																	<Printer class="h-4 w-4" />
																{/if}
															</Button>
														</TooltipTrigger>
														<TooltipContent>Print PDF</TooltipContent>
													</Tooltip>

													{#if item.isMerged}
														<Tooltip>
															<TooltipTrigger>
																<Button
																	variant="destructive"
																	size="icon"
																	onclick={() => unmerge(user, item.file)}
																	aria-label="Unmerge PDF"
																>
																	<X class="h-4 w-4" />
																</Button>
															</TooltipTrigger>
															<TooltipContent>Unmerge: restore original PDFs</TooltipContent>
														</Tooltip>
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
</TooltipProvider>
