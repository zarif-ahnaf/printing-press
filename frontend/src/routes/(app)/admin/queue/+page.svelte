<script lang="ts">
	import { onMount } from 'svelte';

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

	// Icons
	import { FileText, Printer, Merge, Loader2, Eye } from 'lucide-svelte';
	import { QUEUE_URL } from '$lib/constants/backend';
	import { token } from '$lib/stores/token.svelte';

	interface QueueItem {
		id: number;
		file: string;
		processed: boolean;
		created_at: string;
		user: string;
	}

	let queue: QueueItem[] = [];
	let groupedQueue: Record<string, QueueItem[]> = {};
	let loading = false;
	let error: string | null = null;
	let merging = new Set<string>();
	let printing = new Set<string>();
	let previewUrl: string | null = null;
	let previewLoading = false;

	async function fetchQueue() {
		try {
			loading = true;
			error = null;
			const res = await fetch(QUEUE_URL, {
				headers: {
					Authorization: `Bearer ${token.value}`
				}
			});
			if (!res.ok) throw new Error('Failed to fetch queue');
			const data = await res.json();
			queue = data.queue || [];
			groupedQueue = groupByUser(queue);
		} catch (err) {
			if (err instanceof Error) {
				error = err.message;
			} else {
				error = 'An unknown error occurred';
			}
		} finally {
			loading = false;
		}
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

	async function mergePdfs(user: string) {
		const userItems = groupedQueue[user];
		if (!userItems?.length) return;

		const fileUrls = userItems.map((item) => item.file);
		merging.add(user);

		try {
			const res = await fetch('/api/merge/pdf', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ files: fileUrls })
			});

			if (!res.ok) throw new Error('Merge failed');

			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${user}_merged.pdf`;
			document.body.appendChild(a);
			a.click();
			URL.revokeObjectURL(url);
			document.body.removeChild(a);
		} catch (err) {
			if (err instanceof Error) {
				error = `Merge error: ${err.message}`;
			} else {
				error = 'Merge failed: unknown error';
			}
		} finally {
			merging.delete(user);
		}
	}

	async function printPdf(url: string) {
		printing.add(url);
		try {
			const res = await fetch(url);
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
			if (err instanceof Error) {
				error = `Print error: ${err.message}`;
			} else {
				error = 'Print failed: unknown error';
			}
		} finally {
			printing.delete(url);
		}
	}

	async function openPreview(url: string) {
		previewLoading = true;
		previewUrl = null;

		try {
			// Verify PDF is accessible before showing preview
			const res = await fetch(url);
			if (!res.ok) throw new Error('PDF not accessible');

			// Create blob URL for secure embedding
			const blob = await res.blob();
			previewUrl = URL.createObjectURL(blob);
		} catch (err) {
			if (err instanceof Error) {
				error = `Preview error: ${err.message}`;
			} else {
				error = 'Failed to load PDF preview';
			}
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

	onMount(fetchQueue);
</script>

<Dialog open={!!previewUrl} onOpenChange={(open) => !open && closePreview()}>
	<DialogContent class="flex max-h-[90vh] max-w-4xl flex-col p-0">
		<DialogHeader class="border-b px-6 py-4">
			<DialogTitle>PDF Preview</DialogTitle>
		</DialogHeader>

		<div class="flex-1 overflow-hidden bg-muted/30">
			{#if previewLoading}
				<div class="flex h-full items-center justify-center">
					<Loader2 class="h-8 w-8 animate-spin text-primary" />
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
			<Loader2 class="h-8 w-8 animate-spin text-primary" />
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
					<div class="flex items-center justify-between bg-muted/50 px-6 py-4">
						<div>
							<h2 class="text-xl font-semibold">{user}</h2>
							<p class="text-sm text-muted-foreground">
								{items.length} pending PDF{items.length !== 1 ? 's' : ''}
							</p>
						</div>
						<Button
							variant="default"
							size="sm"
							disabled={merging.has(user)}
							onclick={() => mergePdfs(user)}
						>
							{#if merging.has(user)}
								<Loader2 class="mr-2 h-4 w-4 animate-spin" />
								Merging...
							{:else}
								<Merge class="mr-2 h-4 w-4" />
								Merge PDFs
							{/if}
						</Button>
					</div>

					<Table>
						<TableHeader>
							<TableRow>
								<TableHead>File</TableHead>
								<TableHead>Status</TableHead>
								<TableHead>Created</TableHead>
								<TableHead class="text-right">Actions</TableHead>
							</TableRow>
						</TableHeader>
						<TableBody>
							{#each items as item}
								<TableRow>
									<TableCell class="font-medium">
										{item.file.split('/').pop() || 'merged.pdf'}
									</TableCell>
									<TableCell>
										{#if item.processed}
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
											<Button variant="outline" size="sm" onclick={() => openPreview(item.file)}>
												<Eye class="h-4 w-4" />
											</Button>
											<Button
												variant="outline"
												size="sm"
												disabled={printing.has(item.file)}
												onclick={() => printPdf(item.file)}
											>
												{#if printing.has(item.file)}
													<Loader2 class="h-4 w-4 animate-spin" />
												{:else}
													<Printer class="h-4 w-4" />
												{/if}
											</Button>
										</div>
									</TableCell>
								</TableRow>
							{/each}
						</TableBody>
					</Table>
				</div>
			{/each}
		</div>
	{/if}
</div>
