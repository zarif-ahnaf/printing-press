<script lang="ts">
	import { format, parseISO } from 'date-fns';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import {
		Table,
		TableBody,
		TableCell,
		TableHead,
		TableHeader,
		TableRow
	} from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { Alert, AlertDescription } from '$lib/components/ui/alert';
	import { Button } from '$lib/components/ui/button';
	import { is_admin_user, user_username } from '$lib/stores/auth.svelte';
	import { Checkbox } from '$lib/components/ui/checkbox';
	import {
		DropdownMenu,
		DropdownMenuContent,
		DropdownMenuItem,
		DropdownMenuTrigger
	} from '$lib/components/ui/dropdown-menu';
	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogFooter,
		DialogClose
	} from '$lib/components/ui/dialog';
	import { toast } from 'svelte-sonner';
	import { CheckCircle, Printer, Trash2, Merge, Eye } from 'lucide-svelte';
	import { onMount, onDestroy } from 'svelte';
	import { QUEUE_URL } from '$lib/constants/backend';
	import { token } from '$lib/stores/token.svelte';

	type QueueFile = {
		id: number;
		file: string; // full URL to PDF
		processed: boolean;
		created_at: string;
	};

	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let queue = $state<QueueFile[]>([]);
	let selectedFiles = $state<Set<number>>(new Set());
	let isMerging = $state(false);
	let isMergingAll = $state(false);
	let previewUrl = $state<string | null>(null);
	let isPreviewOpen = $state(false);
	let currentPreviewFile = $state<string | null>(null);

	const getUnprocessedFiles = () => queue.filter((f) => !f.processed);

	const fetchQueue = async () => {
		try {
			isLoading = true;
			error = null;
			let url = QUEUE_URL;
			const response = await fetch(url, {
				headers: { Authorization: `Bearer ${token.value}` }
			});
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			const data = await response.json();
			queue = Array.isArray(data) ? data : data.queue || [];
		} catch (err) {
			const msg = err instanceof Error ? err.message : 'Unknown error';
			error = msg;
			toast.error('Failed to load queue', { description: msg });
		} finally {
			isLoading = false;
		}
	};

	const markAsProcessed = async (id: number) => {
		try {
			const res = await fetch(`/api/queue/${id}/processed`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${token.value}`,
					'Content-Type': 'application/json'
				}
			});
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			const { message } = await res.json();
			queue = queue.map((f) => (f.id === id ? { ...f, processed: true } : f));
			toast.success(message);
		} catch (err) {
			toast.error('Failed to mark as processed', {
				description: (err as Error).message || 'Unknown error'
			});
		}
	};

	const removeFromQueue = async (id: number) => {
		try {
			const res = await fetch(`/api/queue/${id}/processed`, {
				method: 'DELETE',
				headers: { Authorization: `Bearer ${token.value}` }
			});
			if (!res.ok) throw new Error(`HTTP ${res.status}`);
			const { message } = await res.json();
			queue = queue.filter((f) => f.id !== id);
			toast.success(message);
		} catch (err) {
			toast.error('Failed to remove from queue', {
				description: (err as Error).message || 'Unknown error'
			});
		}
	};

	// 🔒 SAFE PDF FETCH — includes auth token
	const fetchPDFAsBlob = async (pdfUrl: string): Promise<Blob> => {
		const response = await fetch(pdfUrl, {
			headers: {
				Authorization: `Bearer ${token.value}`
			}
		});
		if (!response.ok) {
			throw new Error(
				`Failed to fetch PDF from ${pdfUrl}: ${response.status} ${response.statusText}`
			);
		}
		return await response.blob();
	};

	const previewPDF = async (fileUrl: string) => {
		try {
			const blob = await fetchPDFAsBlob(fileUrl);
			previewUrl = URL.createObjectURL(blob);
			currentPreviewFile = fileUrl.split('/').pop() || 'document.pdf';
			isPreviewOpen = true;
		} catch (err) {
			toast.error('Preview failed', {
				description: (err as Error).message || 'Could not load PDF'
			});
		}
	};

	const printPDF = async (fileUrl: string) => {
		try {
			const blob = await fetchPDFAsBlob(fileUrl);
			const url = URL.createObjectURL(blob);
			const printWindow = window.open(url, '_blank');
			if (!printWindow) throw new Error('Popup blocked');
			printWindow.addEventListener('load', () => {
				printWindow.focus();
				printWindow.print();
				setTimeout(() => {
					printWindow.close();
					URL.revokeObjectURL(url);
				}, 1000);
			});
			toast.success('Print dialog opened');
		} catch (err) {
			toast.error('Print failed', {
				description: (err as Error).message || 'Could not print PDF'
			});
		}
	};

	// ✅ CORE: MERGE SELECTED — downloads real PDFs
	const mergeSelectedPDFs = async () => {
		if (selectedFiles.size < 2) {
			toast.error('Please select at least 2 files to merge');
			return;
		}

		const selectedQueueFiles = queue.filter((f) => selectedFiles.has(f.id));
		if (selectedQueueFiles.length < 2) {
			toast.error('Invalid selection');
			return;
		}

		try {
			isMerging = true;
			const formData = new FormData();

			// 🔽 Download each PDF and append as File
			for (const qf of selectedQueueFiles) {
				const blob = await fetchPDFAsBlob(qf.file);
				const filename = qf.file.split('/').pop() || `file-${qf.id}.pdf`;
				const file = new File([blob], filename, { type: 'application/pdf' });
				formData.append('files', file);
			}

			// 🔽 Send to merge endpoint
			const response = await fetch('/api/merge/pdf/', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${token.value}`
					// ⚠️ DO NOT set Content-Type — let browser set multipart/form-data with boundary
				},
				body: formData
			});

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(`Merge failed: ${response.status} ${errorText}`);
			}

			// 🔽 Trigger download of merged PDF
			const mergedBlob = await response.blob();
			const downloadUrl = URL.createObjectURL(mergedBlob);
			const a = document.createElement('a');
			a.href = downloadUrl;
			a.download = 'merged.pdf';
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(downloadUrl);

			toast.success('PDFs merged successfully');
			selectedFiles = new Set();
			await fetchQueue(); // refresh to reflect any backend changes
		} catch (err) {
			console.error('Merge error:', err);
			toast.error('Merge failed', {
				description: (err as Error).message || 'An unknown error occurred during merge'
			});
		} finally {
			isMerging = false;
		}
	};

	// ✅ CORE: MERGE ALL UNPROCESSED — same logic, different source
	const mergeAllPDFs = async () => {
		const unprocessedFiles = getUnprocessedFiles();
		if (unprocessedFiles.length < 2) {
			toast.error('Need at least 2 unprocessed files to merge');
			return;
		}

		try {
			isMergingAll = true;
			const formData = new FormData();

			for (const qf of unprocessedFiles) {
				const blob = await fetchPDFAsBlob(qf.file);
				const filename = qf.file.split('/').pop() || `file-${qf.id}.pdf`;
				const file = new File([blob], filename, { type: 'application/pdf' });
				formData.append('files', file);
			}

			const response = await fetch('/api/merge/pdf/', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${token.value}`
				},
				body: formData
			});

			if (!response.ok) {
				const errorText = await response.text();
				throw new Error(`Merge all failed: ${response.status} ${errorText}`);
			}

			const mergedBlob = await response.blob();
			const downloadUrl = URL.createObjectURL(mergedBlob);
			const a = document.createElement('a');
			a.href = downloadUrl;
			a.download = 'merged_all.pdf';
			a.click();
			URL.revokeObjectURL(downloadUrl);

			toast.success('All unprocessed PDFs merged');
			await fetchQueue();
		} catch (err) {
			console.error('Merge all error:', err);
			toast.error('Merge all failed', {
				description: (err as Error).message || 'An unknown error occurred'
			});
		} finally {
			isMergingAll = false;
		}
	};

	const closePreview = () => {
		if (previewUrl) {
			URL.revokeObjectURL(previewUrl);
			previewUrl = null;
		}
		isPreviewOpen = false;
		currentPreviewFile = null;
	};

	const formatTime = (dateString: string) => format(parseISO(dateString), 'h:mm a');
	const formatDate = (dateString: string) => format(parseISO(dateString), 'MMM d, yyyy');

	onMount(() => {
		fetchQueue();
	});

	onDestroy(() => {
		closePreview();
	});
</script>

<!-- Preview Dialog -->
<Dialog open={isPreviewOpen} onOpenChange={closePreview}>
	<DialogContent class="flex max-h-[90vh] max-w-4xl flex-col p-0">
		<DialogHeader class="border-b px-6 py-4">
			<DialogTitle class="text-lg">Preview: {currentPreviewFile}</DialogTitle>
		</DialogHeader>
		{#if previewUrl}
			<div class="flex-1 overflow-hidden bg-muted/30">
				<embed
					src={previewUrl}
					type="application/pdf"
					class="h-full max-h-[70vh] min-h-[60vh] w-full"
				/>
			</div>
		{/if}
		<DialogFooter class="border-t bg-background px-6 py-4">
			<DialogClose>
				<Button variant="outline">Close</Button>
			</DialogClose>
		</DialogFooter>
	</DialogContent>
</Dialog>

<!-- Rest of UI unchanged from previous version -->
<div class="container mx-auto space-y-8 py-6">
	{#if error}
		<Alert variant="destructive">
			<AlertDescription>{error}</AlertDescription>
		</Alert>
	{/if}

	<Card class="border-none shadow-none">
		<CardHeader>
			<div class="flex items-center justify-between">
				<CardTitle>Print Queue</CardTitle>
				<div class="flex gap-2">
					{#if selectedFiles.size > 0 && is_admin_user.value}
						<Button onclick={mergeSelectedPDFs} disabled={isMerging}>
							{isMerging ? 'Merging...' : 'Merge Selected'}
							<Merge class="ml-2 h-4 w-4" />
						</Button>
					{/if}

					{#if is_admin_user.value && getUnprocessedFiles().length >= 2}
						<Button onclick={mergeAllPDFs} disabled={isMergingAll} variant="default">
							{isMergingAll ? 'Merging All...' : 'Merge All'}
							<Merge class="ml-2 h-4 w-4" />
						</Button>
					{/if}
				</div>
			</div>
			<p class="text-sm text-muted-foreground">
				{#if is_admin_user.value}
					Manage all queued print jobs.
				{:else}
					View your queued print jobs.
				{/if}
			</p>
		</CardHeader>

		<CardContent>
			{#if isLoading}
				<div class="space-y-4">
					{#each { length: 3 } as _, i}
						<div class="h-12 animate-pulse rounded bg-muted"></div>
					{/each}
				</div>
			{:else if queue.length === 0}
				<div class="py-8 text-center text-muted-foreground">
					{#if is_admin_user.value}
						No files in the queue.
					{:else}
						You have no files in the queue.
					{/if}
				</div>
			{:else}
				<div class="space-y-6">
					{#if is_admin_user.value}
						<div class="mb-4 flex items-center gap-2">
							<span class="text-sm font-medium">Selected: {selectedFiles.size} files</span>
							{#if selectedFiles.size > 0}
								<Button variant="ghost" size="sm" onclick={() => (selectedFiles = new Set())}>
									Clear Selection
								</Button>
							{/if}
						</div>
					{/if}

					<div class="overflow-hidden rounded-md border">
						<Table>
							<TableHeader>
								<TableRow class="bg-muted/40">
									{#if is_admin_user.value}
										<TableHead class="w-[50px]">
											<div class="flex items-center justify-center">
												<Checkbox
													checked={getUnprocessedFiles().length > 0 &&
														getUnprocessedFiles().every((f) => selectedFiles.has(f.id))}
													indeterminate={selectedFiles.size > 0 &&
														selectedFiles.size < getUnprocessedFiles().length}
													onclick={(e) => {
														e.stopPropagation();
														const unproc = getUnprocessedFiles();
														if (unproc.length === 0) return;
														const allSelected = unproc.every((f) => selectedFiles.has(f.id));
														selectedFiles = allSelected
															? new Set()
															: new Set(unproc.map((f) => f.id));
													}}
												/>
											</div>
										</TableHead>
									{/if}
									<TableHead class="w-[70px] font-medium">ID</TableHead>
									<TableHead class="font-medium">Filename</TableHead>
									<TableHead class="font-medium">Status</TableHead>
									<TableHead class="font-medium">Date Added</TableHead>
									<TableHead class="font-medium">Time Added</TableHead>
									<TableHead class="text-right font-medium">Actions</TableHead>
								</TableRow>
							</TableHeader>

							<TableBody>
								{#each queue as file (file.id)}
									<TableRow class={file.processed ? 'bg-muted/20' : ''}>
										{#if is_admin_user.value}
											<TableCell>
												{#if !file.processed}
													<div class="flex items-center justify-center">
														<Checkbox
															checked={selectedFiles.has(file.id)}
															onclick={(e) => {
																e.stopPropagation();
																const newSet = new Set(selectedFiles);
																newSet.has(file.id) ? newSet.delete(file.id) : newSet.add(file.id);
																selectedFiles = newSet;
															}}
														/>
													</div>
												{:else}
													<span class="text-xs text-muted-foreground">Processed</span>
												{/if}
											</TableCell>
										{/if}

										<TableCell class="font-mono">#{file.id}</TableCell>
										<TableCell class="max-w-[220px] truncate sm:max-w-none">
											{file.file.split('/').pop() || 'document.pdf'}
										</TableCell>
										<TableCell>
											<Badge variant={file.processed ? 'default' : 'secondary'}>
												{file.processed ? 'Processed' : 'Pending'}
											</Badge>
										</TableCell>
										<TableCell>{formatDate(file.created_at)}</TableCell>
										<TableCell class="text-sm text-muted-foreground">
											{formatTime(file.created_at)}
										</TableCell>
										<TableCell class="text-right">
											<DropdownMenu>
												<DropdownMenuTrigger>
													<Button variant="ghost" size="icon">
														<svg
															xmlns="http://www.w3.org/2000/svg"
															width="24"
															height="24"
															viewBox="0 0 24 24"
															fill="none"
															stroke="currentColor"
															stroke-width="2"
															stroke-linecap="round"
															stroke-linejoin="round"
															class="h-4 w-4"
														>
															<circle cx="12" cy="12" r="1" />
															<circle cx="19" cy="12" r="1" />
															<circle cx="5" cy="12" r="1" />
														</svg>
														<span class="sr-only">Actions</span>
													</Button>
												</DropdownMenuTrigger>
												<DropdownMenuContent align="end">
													<DropdownMenuItem onclick={() => previewPDF(file.file)}>
														<Eye class="mr-2 h-4 w-4" />
														Preview
													</DropdownMenuItem>

													{#if is_admin_user.value}
														<DropdownMenuItem onclick={() => markAsProcessed(file.id)}>
															<CheckCircle class="mr-2 h-4 w-4" />
															Mark as Processed
														</DropdownMenuItem>
													{/if}

													<DropdownMenuItem onclick={() => removeFromQueue(file.id)}>
														<Trash2 class="mr-2 h-4 w-4" />
														Remove from Queue
													</DropdownMenuItem>

													{#if is_admin_user.value}
														<DropdownMenuItem onclick={() => printPDF(file.file)}>
															<Printer class="mr-2 h-4 w-4" />
															Print
														</DropdownMenuItem>

														{#if !file.processed}
															<DropdownMenuItem
																onclick={() => {
																	selectedFiles = new Set([file.id]);
																	mergeSelectedPDFs();
																}}
															>
																<Merge class="mr-2 h-4 w-4" />
																Merge with Selection
															</DropdownMenuItem>
														{/if}
													{/if}
												</DropdownMenuContent>
											</DropdownMenu>
										</TableCell>
									</TableRow>
								{/each}
							</TableBody>
						</Table>
					</div>
				</div>
			{/if}
		</CardContent>
	</Card>
</div>
