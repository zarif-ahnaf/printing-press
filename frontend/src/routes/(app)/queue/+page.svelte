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
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { is_admin_user, user_username } from '$lib/stores/auth.svelte';
	import { Checkbox } from '$lib/components/ui/checkbox';

	import {
		Dialog,
		DialogContent,
		DialogHeader,
		DialogTitle,
		DialogTrigger
	} from '$lib/components/ui/dialog';
	import {
		DropdownMenu,
		DropdownMenuContent,
		DropdownMenuItem,
		DropdownMenuTrigger
	} from '$lib/components/ui/dropdown-menu';
	import { toast } from 'svelte-sonner';
	import { CheckCircle, Printer, Trash2, Download, Merge, Split } from 'lucide-svelte';
	import { onMount } from 'svelte';
	import { QUEUE_URL } from '$lib/constants/backend';

	type QueueFile = {
		id: number;
		filename: string;
		processed: boolean;
		created_at: string;
		is_merged: boolean;
		merged_id?: number | null;
		selected?: boolean;
	};

	let isLoading = $state(false);
	let error = $state<string | null>(null);
	let queue = $state<QueueFile[]>([]);
	let isMerging = $state(false);
	let isMergingAll = $state(false);
	let mergeError = $state('');
	let showMerged = $state(false);

	// Derived properties for UI display only
	let allSelected = $derived(
		queue.filter((f) => !f.is_merged).length > 0 &&
			queue.filter((f) => !f.is_merged).every((f) => f.selected)
	);
	let someSelected = $derived(
		queue.filter((f) => !f.is_merged).length > 0 &&
			queue.filter((f) => !f.is_merged).some((f) => f.selected)
	);
	let selectedCount = $derived(queue.filter((f) => !f.is_merged && f.selected).length);

	const fetchQueue = async () => {
		try {
			isLoading = true;
			error = null;

			let url = QUEUE_URL;
			if (user_username.value && !is_admin_user.value) {
				url = `${QUEUE_URL}${user_username.value}/`;
			}

			if (showMerged) {
				url += (url.includes('?') ? '&' : '?') + 'merged=true';
			}

			const response = await fetch(url, {
				method: 'GET',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (!response.ok) {
				throw new Error(`Failed to fetch queue: ${response.status}`);
			}

			const data = await response.json();
			queue = data.queue.map((file: any) => ({ ...file, selected: false }));
		} catch (err) {
			const errorMsg = err instanceof Error ? err.message : 'An unknown error occurred';
			error = errorMsg;
			toast.error(errorMsg, {
				description: 'Failed to load print queue'
			});
		} finally {
			isLoading = false;
		}
	};

	const markAsProcessed = async (queueId: number) => {
		try {
			const response = await fetch(`/api/queue/${queueId}/processed`, {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`,
					'Content-Type': 'application/json'
				}
			});

			if (!response.ok) {
				throw new Error(`Failed to mark as processed: ${response.status}`);
			}

			const data = await response.json();

			const fileIndex = queue.findIndex((f) => f.id === queueId);
			if (fileIndex !== -1) {
				queue = [
					...queue.slice(0, fileIndex),
					{ ...queue[fileIndex], processed: data.processed },
					...queue.slice(fileIndex + 1)
				];
			}

			toast.success(data.message);
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
			toast.error(errorMessage, {
				description: 'Failed to mark file as processed'
			});
		}
	};

	const removeFromQueue = async (queueId: number) => {
		try {
			const response = await fetch(`/api/queue/${queueId}/processed`, {
				method: 'DELETE',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`,
					'Content-Type': 'application/json'
				}
			});

			if (!response.ok) {
				throw new Error(`Failed to remove from queue: ${response.status}`);
			}

			const data = await response.json();
			queue = queue.filter((f) => f.id !== queueId);
			toast.success(data.message);
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
			toast.error(errorMessage, {
				description: 'Failed to remove file from queue'
			});
		}
	};

	const mergeSelectedPDFs = async () => {
		const selectedFiles = queue.filter((f) => !f.is_merged && f.selected);

		if (selectedFiles.length < 2) {
			mergeError = 'Please select at least 2 files to merge';
			toast.error(mergeError);
			return;
		}

		try {
			isMerging = true;
			mergeError = '';

			const formData = new FormData();
			selectedFiles.forEach((file) => {
				const dummyFile = new File([new Blob([''], { type: 'application/pdf' })], file.filename, {
					type: 'application/pdf'
				});
				formData.append('files', dummyFile);
			});

			const response = await fetch('/api/merge/pdf/', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: formData
			});

			if (!response.ok) {
				throw new Error(`Failed to merge PDFs: ${response.status}`);
			}

			const blob = await response.blob();
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'merged.pdf';
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);

			toast.success('Merge Successful', {
				description: 'PDFs have been merged successfully'
			});

			queue = queue.map((file) => ({ ...file, selected: false }));
			await fetchQueue();
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
			mergeError = errorMessage;
			toast.error('Merge Failed', {
				description: errorMessage
			});
		} finally {
			isMerging = false;
		}
	};

	const mergeAllPDFs = async () => {
		try {
			isMergingAll = true;
			mergeError = '';

			const unmergedFiles = queue.filter((f) => !f.is_merged);
			if (unmergedFiles.length < 2) {
				toast.error('Merge Failed', {
					description: 'Need at least 2 unmerged PDFs to merge'
				});
				return;
			}

			const formData = new FormData();
			unmergedFiles.forEach((file) => {
				const dummyFile = new File([new Blob([''], { type: 'application/pdf' })], file.filename, {
					type: 'application/pdf'
				});
				formData.append('files', dummyFile);
			});

			const response = await fetch('/api/merge/pdf/', {
				method: 'POST',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				},
				body: formData
			});

			if (!response.ok) {
				throw new Error(`Failed to merge all PDFs: ${response.status}`);
			}

			const blob = await response.blob();
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = 'merged.pdf';
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);

			toast.success('Merge All Successful', {
				description: 'All PDFs have been merged successfully'
			});

			await fetchQueue();
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
			mergeError = errorMessage;
			toast.error('Merge Failed', {
				description: errorMessage
			});
		} finally {
			isMergingAll = false;
		}
	};

	const printPDF = async (queueId: number) => {
		try {
			const response = await fetch(`/api/queue/${queueId}/processed`, {
				method: 'GET',
				headers: {
					Authorization: `Bearer ${localStorage.getItem('token')}`
				}
			});

			if (!response.ok) {
				throw new Error(`Failed to get PDF: ${response.status}`);
			}

			const blob = await response.blob();
			const url = window.URL.createObjectURL(blob);
			const printWindow = window.open(url, '_blank');

			printWindow?.addEventListener('load', () => {
				printWindow?.focus();
				printWindow?.print();
				setTimeout(() => {
					printWindow?.close();
					window.URL.revokeObjectURL(url);
				}, 1000);
			});

			toast.success('Print Job Sent', {
				description: 'Opening print dialog...'
			});
		} catch (err) {
			const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
			toast.error('Print Failed', {
				description: errorMessage
			});
		}
	};

	const toggleSelectAll = () => {
		// Always compute current state from actual queue
		const unmergedFiles = queue.filter((f) => !f.is_merged);
		if (unmergedFiles.length === 0) return;

		const currentlyAllSelected = unmergedFiles.every((f) => f.selected);
		const newSelectedState = !currentlyAllSelected;

		// Update only unmerged files
		queue = queue.map((file) => {
			if (!file.is_merged) {
				return { ...file, selected: newSelectedState };
			}
			return file;
		});
	};

	const toggleFileSelection = (id: number) => {
		const fileIndex = queue.findIndex((f) => f.id === id);
		if (fileIndex !== -1 && !queue[fileIndex].is_merged) {
			queue = [
				...queue.slice(0, fileIndex),
				{ ...queue[fileIndex], selected: !queue[fileIndex].selected },
				...queue.slice(fileIndex + 1)
			];
		}
	};

	const toggleMergedView = () => {
		showMerged = !showMerged;
		fetchQueue();
	};

	const formatTime = (dateString: string) => {
		return format(parseISO(dateString), 'h:mm a');
	};

	const formatDate = (dateString: string) => {
		return format(parseISO(dateString), 'MMMM d, yyyy');
	};

	onMount(() => {
		fetchQueue();
	});
</script>

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
					{#if is_admin_user.value}
						<div class="flex items-center gap-2">
							<Button variant="outline" size="sm" onclick={toggleMergedView}>
								{#if showMerged}
									<Split class="mr-2 h-4 w-4" />
								{:else}
									<Merge class="mr-2 h-4 w-4" />
								{/if}
								{showMerged ? 'Show Unmerged' : 'Show Merged'}
							</Button>
						</div>
					{/if}

					{#if selectedCount > 0 && is_admin_user.value}
						<Button onclick={mergeSelectedPDFs} disabled={isMerging}>
							{isMerging ? 'Merging...' : 'Merge Selected'}
							<Merge class="ml-2 h-4 w-4" />
						</Button>
					{/if}

					{#if is_admin_user.value && queue.some((f) => !f.is_merged)}
						<Button
							onclick={mergeAllPDFs}
							disabled={isMergingAll || queue.filter((f) => !f.is_merged).length < 2}
							variant="default"
						>
							{isMergingAll ? 'Merging All...' : 'Merge All PDFs'}
							<Merge class="ml-2 h-4 w-4" />
						</Button>
					{/if}
				</div>
			</div>
			<p class="text-sm text-muted-foreground">
				{#if is_admin_user.value}
					View and manage all queued print jobs{showMerged ? ' (merged view)' : ''}.
				{:else}
					View your queued print jobs.
				{/if}
			</p>
		</CardHeader>
		<CardContent>
			{#if isLoading}
				<div class="space-y-4">
					{#each Array(3) as _, i}
						<div class="h-12 animate-pulse rounded bg-muted"></div>
					{/each}
				</div>
			{:else if queue.length === 0}
				<div class="py-8 text-center text-muted-foreground">
					{#if is_admin_user.value}
						{showMerged ? 'No merged PDFs in the queue.' : 'No files in the queue.'}
					{:else}
						You have no files in the queue.
					{/if}
				</div>
			{:else}
				<div class="space-y-6">
					{#if is_admin_user.value}
						<div class="mb-4 flex items-center gap-2">
							<span class="text-sm font-medium">Selected: {selectedCount} files</span>
							{#if selectedCount > 0}
								<Button
									variant="ghost"
									size="sm"
									onclick={() => {
										queue = queue.map((file) => ({ ...file, selected: false }));
									}}
								>
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
													checked={allSelected}
													indeterminate={someSelected && !allSelected}
													onchange={toggleSelectAll}
												/>
											</div>
										</TableHead>
									{/if}
									<TableHead class="w-[70px] font-medium">ID</TableHead>
									<TableHead class="font-medium">Filename</TableHead>
									<TableHead class="font-medium">Status</TableHead>
									{#if is_admin_user.value}
										<TableHead class="font-medium">Merged</TableHead>
									{/if}
									<TableHead class="font-medium">Date Added</TableHead>
									<TableHead class="font-medium">Time Added</TableHead>
									<TableHead class="text-right font-medium">Actions</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{#each queue as file (file.id)}
									<TableRow class={file.is_merged ? 'bg-muted/20' : ''}>
										{#if is_admin_user.value}
											<TableCell>
												{#if !file.is_merged}
													<div class="flex items-center justify-center">
														<Checkbox
															checked={file.selected}
															onchange={() => toggleFileSelection(file.id)}
														/>
													</div>
												{:else}
													<span class="text-xs text-muted-foreground">Merged</span>
												{/if}
											</TableCell>
										{/if}
										<TableCell class="font-mono">#{file.id}</TableCell>
										<TableCell class="max-w-[220px] truncate sm:max-w-none">
											{file.filename}
										</TableCell>
										<TableCell>
											<Badge variant={file.processed ? 'default' : 'secondary'} class="capitalize">
												{file.processed ? 'Processed' : 'Pending'}
											</Badge>
										</TableCell>
										{#if is_admin_user.value}
											<TableCell>
												{#if file.is_merged}
													<Badge variant="outline">Merged (ID: {file.merged_id})</Badge>
												{:else}
													<span class="text-muted-foreground">-</span>
												{/if}
											</TableCell>
										{/if}
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
														<DropdownMenuItem onclick={() => printPDF(file.id)}>
															<Printer class="mr-2 h-4 w-4" />
															Print
														</DropdownMenuItem>
														{#if !file.is_merged}
															<DropdownMenuItem
																onclick={() => {
																	queue = queue.map((f) => ({ ...f, selected: false }));
																	const currentFileIndex = queue.findIndex((f) => f.id === file.id);
																	if (currentFileIndex !== -1) {
																		queue = [
																			...queue.slice(0, currentFileIndex),
																			{ ...queue[currentFileIndex], selected: true },
																			...queue.slice(currentFileIndex + 1)
																		];
																	}
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
