<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import {
		Upload,
		FileText,
		Download,
		Zap,
		FileCheck,
		Trash2,
		Eye,
		Users,
		ArrowLeft,
		TriangleAlert
	} from 'lucide-svelte';

	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Progress } from '$lib/components/ui/progress';
	import { Dialog, DialogContent } from '$lib/components/ui/dialog';
	import { Badge } from '$lib/components/ui/badge';
	import { ADMIN_QUEUE_URL, NONBLANK_URL, QUEUE_URL } from '$lib/constants/backend';
	import { goto } from '$app/navigation';

	// Svelte 5 runes
	let files = $state<PDFFile[]>([]);
	let isDragging = $state(false);
	let isSubmitting = $state(false);
	let selectedPdf = $state<PDFFile | null>(null);
	let isDialogOpen = $state(false);
	let isAdmin = $state(true);
	let isUserDropdownOpen = $state(false);
	let selectedUserId: number | null = $state<number | null>(null);
	let users = $state([
		{ id: 1, name: 'John Doe', email: 'john@example.com', role: 'user' },
		{ id: 2, name: 'Jane Smith', email: 'jane@example.com', role: 'user' },
		{ id: 3, name: 'Robert Chen', email: 'robert@example.com', role: 'user' },
		{ id: 4, name: 'Alex Morgan', email: 'alex@example.com', role: 'user' },
		{ id: 5, name: 'System Admin', email: 'admin@example.com', role: 'admin' }
	]);
	let userSearch = $state('');
	let processingFiles = $state<string[]>([]);

	interface PDFFile {
		id: string;
		file: File;
		optimizedFile: File | null;
		isOptimizing: boolean;
		nonBlankCount: number | null;
		enqueueStatus: 'idle' | 'processing' | 'success' | 'error';
		errorMessage: string | null;
	}

	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	}

	function getFilteredUsers() {
		if (!userSearch) return users;
		return users.filter(
			(user) =>
				user.name.toLowerCase().includes(userSearch.toLowerCase()) ||
				user.email.toLowerCase().includes(userSearch.toLowerCase())
		);
	}

	async function handleFiles(fileList: FileList) {
		for (const file of Array.from(fileList)) {
			if (file.type !== 'application/pdf') {
				toast.error('Only PDF files are supported');
				continue;
			}

			// Allow multiple uploads of the same file - no duplicate check
			files.push({
				id: crypto.randomUUID(),
				file,
				optimizedFile: null,
				isOptimizing: false,
				nonBlankCount: null,
				enqueueStatus: 'idle',
				errorMessage: null
			});
		}
	}

	async function optimizePDF(pdfFile: PDFFile) {
		pdfFile.isOptimizing = true;
		pdfFile.enqueueStatus = 'processing';

		try {
			const formData = new FormData();
			formData.append('file', pdfFile.file);
			formData.append('return_pdf', 'true');

			const res = await fetch(NONBLANK_URL, {
				method: 'POST',
				body: formData
			});

			if (!res.ok) {
				const errorText = await res.text();
				throw new Error(errorText || 'Failed to process PDF');
			}

			const blob = await res.blob();
			pdfFile.optimizedFile = new File([blob], `cleaned_${pdfFile.file.name}`, {
				type: 'application/pdf'
			});
			pdfFile.enqueueStatus = 'success';
			toast.success('Blank pages removed successfully!', {
				description: `${pdfFile.file.name} processed`,
				duration: 3000
			});
		} catch (error: any) {
			pdfFile.enqueueStatus = 'error';
			pdfFile.errorMessage = error.message;
			toast.error('Failed to remove blank pages', {
				description: error.message,
				duration: 5000
			});
		} finally {
			pdfFile.isOptimizing = false;
		}
	}

	function downloadOptimized(pdfFile: PDFFile | null) {
		if (!pdfFile?.optimizedFile) return;
		const url = URL.createObjectURL(pdfFile.optimizedFile);
		const a = document.createElement('a');
		a.href = url;
		a.download = pdfFile.optimizedFile.name;
		a.click();
		URL.revokeObjectURL(url);
	}

	function deleteFile(pdfFile: PDFFile) {
		if (!confirm(`Delete "${pdfFile.file.name}"? This cannot be undone.`)) return;
		files = files.filter((f) => f.id !== pdfFile.id);
		if (selectedPdf?.id === pdfFile.id) {
			selectedPdf = null;
			isDialogOpen = false;
		}
		toast.success('File deleted', {
			description: pdfFile.file.name,
			duration: 2000
		});
	}

	async function enqueuePDF(pdfFile: PDFFile, fileToSubmit: File) {
		try {
			const formData = new FormData();
			formData.append('files', fileToSubmit); // Use the passed file instead of optimizedFile
			let endpoint = QUEUE_URL;
			let params = {};

			if (isAdmin && selectedUserId !== null) {
				formData.append('user_id', selectedUserId.toString());
				endpoint = ADMIN_QUEUE_URL;
				params = { user_id: selectedUserId };
			}

			const token = localStorage.getItem('token');
			const headers: Record<string, string> = {};
			if (token) {
				headers.Authorization = `Bearer ${token}`;
			}

			processingFiles = [...processingFiles, pdfFile.id];
			pdfFile.enqueueStatus = 'processing';

			const res = await fetch(endpoint, {
				method: 'POST',
				headers,
				body: formData
			});

			if (!res.ok) {
				const errorText = await res.text();
				throw new Error(errorText || `Failed to enqueue ${pdfFile.file.name}`);
			}

			pdfFile.enqueueStatus = 'success';
		} catch (error: any) {
			pdfFile.enqueueStatus = 'error';
			pdfFile.errorMessage = error.message;
			toast.error('Enqueue failed', {
				description: error.message,
				duration: 5000
			});
		} finally {
			processingFiles = processingFiles.filter((id) => id !== pdfFile.id);
		}
	}

	async function submitAll() {
		const filesToSubmit = files.filter((f) => f.enqueueStatus !== 'success');
		if (filesToSubmit.length === 0) {
			toast.info('No files to enqueue');
			return;
		}

		isSubmitting = true;
		const token = localStorage.getItem('token');
		const headers: Record<string, string> = {};
		if (token) {
			headers.Authorization = `Bearer ${token}`;
		}

		const formData = new FormData();
		filesToSubmit.forEach((pdfFile) => {
			const fileToSubmit = pdfFile.optimizedFile ?? pdfFile.file;
			formData.append('files', fileToSubmit);
		});

		if (isAdmin && selectedUserId !== null) {
			formData.append('user_id', selectedUserId.toString());
		}

		const endpoint = isAdmin && selectedUserId !== null ? ADMIN_QUEUE_URL : QUEUE_URL;

		try {
			const res = await fetch(endpoint, {
				method: 'POST',
				headers, // Note: Don't set Content-Type with FormData — browser sets boundary
				body: formData
			});

			if (res.ok) {
				filesToSubmit.forEach((pdfFile) => {
					pdfFile.enqueueStatus = 'success';
				});

				toast.success(`${filesToSubmit.length} file(s) enqueued successfully`, {
					duration: 4000
				});

				goto('/dashboard');
			} else {
				// Handle non-2xx response
				const errorText = await res.text();
				throw new Error(errorText || `Enqueue failed with status ${res.status}`);
			}
		} catch (error: any) {
			toast.error('Enqueue failed', {
				description: error.message || 'An unknown error occurred',
				duration: 5000
			});
		} finally {
			isSubmitting = false;
		}
	}

	function openPdfDialog(pdf: PDFFile) {
		selectedPdf = pdf;
		isDialogOpen = true;
	}

	// Drag & drop
	async function handleDragOver(e: DragEvent) {
		e.preventDefault();
		isDragging = true;
	}

	async function handleDragLeave(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
	}

	async function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
		if (e.dataTransfer?.files) await handleFiles(e.dataTransfer.files);
	}

	onMount(() => {
		window.addEventListener('dragover', handleDragOver);
		window.addEventListener('dragleave', handleDragLeave);
		window.addEventListener('drop', handleDrop);
		return () => {
			window.removeEventListener('dragover', handleDragOver);
			window.removeEventListener('dragleave', handleDragLeave);
			window.removeEventListener('drop', handleDrop);
		};
	});
</script>

<div class="min-h-screen bg-background p-4 md:p-8">
	<!-- Header -->
	<header class="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between">
		<div>
			<h1 class="text-3xl font-bold">PDF Cleaner</h1>
			<p class="mt-1 text-muted-foreground">Upload PDFs and remove blank pages instantly</p>
		</div>

		{#if isAdmin}
			<div class="mt-4 sm:mt-0">
				<div class="flex items-center gap-2">
					<Users class="h-4 w-4 text-muted-foreground" />
					<span class="text-sm font-medium">Upload for:</span>

					<!-- Searchable user input using shadcn Input -->
					<div class="relative w-[240px]">
						<Input
							type="text"
							placeholder="Search users..."
							bind:value={userSearch}
							oninput={() => (isUserDropdownOpen = true)}
							onblur={() => setTimeout(() => (isUserDropdownOpen = false), 150)}
							onkeydown={(e) => {
								if (e.key === 'Escape') {
									isUserDropdownOpen = false;
								}
							}}
							class="pr-8"
						/>
						{#if isUserDropdownOpen && userSearch}
							<div
								class="absolute top-full z-50 mt-1 w-full animate-in rounded-md border bg-popover text-popover-foreground shadow-md fade-in-0 outline-none zoom-in-95"
							>
								{#if getFilteredUsers().length === 0}
									<div class="px-3 py-2 text-sm text-muted-foreground">No users found</div>
								{:else}
									{#each getFilteredUsers() as user}
										<button
											type="button"
											class="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left text-sm select-none hover:bg-accent hover:text-accent-foreground"
											onclick={() => {
												selectedUserId = user.id;
												userSearch = user.name;
												isUserDropdownOpen = false;
											}}
										>
											<div
												class="mr-2 h-2 w-2 rounded-full {user.role === 'admin'
													? 'bg-primary'
													: 'bg-muted-foreground'}"
											></div>
											<div class="flex flex-col">
												<span>{user.name}</span>
												<span class="text-xs text-muted-foreground">{user.email}</span>
											</div>
										</button>
									{/each}
								{/if}
							</div>
						{/if}
					</div>
				</div>
			</div>
		{/if}
	</header>

	<!-- Upload Area -->
	<Card class="mb-8">
		<CardHeader>
			<CardTitle>Upload PDFs</CardTitle>
		</CardHeader>
		<CardContent>
			<Label
				for="file-upload"
				class="block cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors
				{isDragging ? 'border-primary bg-primary/5' : 'border-muted'}"
				ondragover={handleDragOver}
				ondragleave={handleDragLeave}
				ondrop={handleDrop}
				onkeydown={(e) => {
					if (e.key === 'Enter' || e.key === ' ') {
						e.preventDefault();
						(document.getElementById('file-upload') as HTMLInputElement)?.click();
					}
				}}
			>
				<Upload class="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
				<p class="font-medium">Drag & drop PDFs here</p>
				<p class="mt-1 text-sm text-muted-foreground">or click to browse files</p>
				<Input
					id="file-upload"
					type="file"
					accept=".pdf"
					multiple
					class="hidden"
					onchange={async (e) => {
						const input = e.currentTarget;
						if (input?.files) await handleFiles(input.files);
					}}
				/>
			</Label>
		</CardContent>
	</Card>

	<!-- PDF Thumbnails -->
	{#if files.length === 0}
		<div class="py-16 text-center">
			<FileText class="mx-auto mb-4 h-16 w-16 text-muted-foreground" />
			<p class="text-muted-foreground">Upload PDFs to get started</p>
		</div>
	{:else}
		<div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
			{#each files as pdfFile (pdfFile.id)}
				<div
					class="group relative overflow-hidden rounded-xl border bg-card transition-all duration-300 hover:shadow-md
					{pdfFile.enqueueStatus === 'success' ? 'border-green-500/50' : ''}
					{pdfFile.enqueueStatus === 'error' ? 'border-destructive/50' : ''}"
				>
					<!-- Status Indicator -->
					{#if pdfFile.enqueueStatus === 'processing'}
						<div class="absolute top-2 left-2 z-10">
							<div class="h-3 w-3 animate-pulse rounded-full bg-primary"></div>
						</div>
					{:else if pdfFile.enqueueStatus === 'success'}
						<div class="absolute top-2 left-2 z-10">
							<div class="h-3 w-3 rounded-full bg-green-500"></div>
						</div>
					{:else if pdfFile.enqueueStatus === 'error'}
						<div class="absolute top-2 left-2 z-10">
							<div class="h-3 w-3 rounded-full bg-destructive"></div>
						</div>
					{/if}

					<!-- Thumbnail -->
					<div class="relative aspect-[3/4] w-full bg-muted">
						<embed
							src={URL.createObjectURL(pdfFile.optimizedFile ?? pdfFile.file)}
							type="application/pdf"
							class="h-full w-full cursor-pointer object-cover transition-opacity
								{pdfFile.isOptimizing ? 'opacity-50' : 'opacity-100'}"
							onclick={() => openPdfDialog(pdfFile)}
						/>
						{#if pdfFile.isOptimizing}
							<div class="absolute inset-0 flex items-center justify-center bg-black/20">
								<Progress class="h-1.5 w-12" value={50} />
							</div>
						{/if}
					</div>

					<!-- Optimized badge -->
					{#if pdfFile.optimizedFile}
						<div
							class="bg-success text-success-foreground absolute top-2 right-2 rounded-full p-1.5"
						>
							<FileCheck class="h-3 w-3" />
						</div>
					{/if}

					<!-- Hover action bar: Delete | Preview | Optimize -->
					<div
						class="absolute right-0 bottom-0 left-0 flex justify-between bg-background/90 p-2 opacity-0 backdrop-blur transition-opacity group-hover:opacity-100"
					>
						<Button
							variant="ghost"
							size="icon"
							class="h-7 w-7"
							onclick={(e) => {
								e.stopPropagation();
								deleteFile(pdfFile);
							}}
						>
							<Trash2 class="h-3.5 w-3.5 text-destructive" />
						</Button>
						<Button
							variant="ghost"
							size="icon"
							class="h-7 w-7"
							onclick={(e) => {
								e.stopPropagation();
								openPdfDialog(pdfFile);
							}}
						>
							<Eye class="h-3.5 w-3.5 text-muted-foreground" />
						</Button>
						<Button
							variant="ghost"
							size="icon"
							class="h-7 w-7"
							disabled={pdfFile.isOptimizing || pdfFile.enqueueStatus === 'processing'}
							onclick={async (e) => {
								e.stopPropagation();
								if (pdfFile.optimizedFile) {
									await enqueuePDF(pdfFile, pdfFile.optimizedFile);
								} else {
									await enqueuePDF(pdfFile, pdfFile.file);
								}
							}}
						>
							{#if pdfFile.isOptimizing || pdfFile.enqueueStatus === 'processing'}
								<Progress class="h-1 w-6" value={50} />
							{:else if pdfFile.optimizedFile}
								<Zap class="h-3.5 w-3.5 text-primary" />
							{:else}
								<Zap class="h-3.5 w-3.5 text-muted-foreground" />
							{/if}
						</Button>
					</div>

					<!-- Filename -->
					<div class="p-3">
						<p class="truncate text-sm font-medium">{pdfFile.file.name}</p>
						<div class="mt-1 flex items-center justify-between">
							<p class="text-xs text-muted-foreground">{formatFileSize(pdfFile.file.size)}</p>
							{#if pdfFile.optimizedFile}
								<Badge variant="secondary" class="text-xs">Cleaned</Badge>
							{/if}
						</div>

						{#if pdfFile.enqueueStatus === 'error' && pdfFile.errorMessage}
							<div
								class="mt-2 rounded border border-destructive/30 bg-destructive/10 p-2 text-xs text-destructive"
							>
								<TriangleAlert class="mr-1 inline h-3 w-3" />
								{pdfFile.errorMessage.substring(0, 50)}
								{pdfFile.errorMessage.length > 50 ? '...' : ''}
							</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>

		<!-- Submit Button -->
		<div class="mt-8 flex justify-end">
			<Button
				size="lg"
				disabled={isSubmitting || files.length === 0}
				onclick={async () => await submitAll()}
			>
				{#if isSubmitting}
					<span class="flex items-center gap-2">
						<Progress class="h-2 w-16" value={50} />
						Enqueuing...
					</span>
				{:else}
					<Zap class="mr-2 h-4 w-4" />
					Enqueue All PDFs
				{/if}
			</Button>
		</div>
	{/if}

	<!-- PDF Preview Dialog -->
	{#if selectedPdf}
		<Dialog
			open={isDialogOpen}
			onOpenChange={(open) => {
				isDialogOpen = open;
				if (!open) selectedPdf = null;
			}}
		>
			<DialogContent
				class="flex h-[90vh] w-[95vw] flex-col overflow-hidden rounded-xl border-0 p-0 shadow-2xl"
			>
				<!-- Top Bar -->
				<div class="flex items-center justify-between border-b bg-background px-6 py-4">
					<div class="flex items-center gap-2">
						<Button
							variant="ghost"
							size="icon"
							class="h-8 w-8"
							onclick={() => {
								isDialogOpen = false;
								selectedPdf = null;
							}}
						>
							<ArrowLeft class="h-4 w-4" />
						</Button>
						<FileText class="h-5 w-5 text-muted-foreground" />
						<span class="max-w-xs truncate font-medium">{selectedPdf.file.name}</span>
						{#if isAdmin && selectedUserId !== null}
							<Badge variant="outline" class="ml-2">
								{users.find((u) => u.id === selectedUserId)?.name}
							</Badge>
						{/if}
					</div>
					<div class="flex gap-2 p-5">
						{#if selectedPdf.optimizedFile}
							<Button variant="outline" size="sm" onclick={() => downloadOptimized(selectedPdf)}>
								<Download class="mr-1.5 h-4 w-4" />
								Download
							</Button>
						{/if}
						<Button
							variant="outline"
							size="sm"
							onclick={() => {
								window.open(
									URL.createObjectURL(selectedPdf!.optimizedFile ?? selectedPdf!.file),
									'_blank'
								);
							}}
						>
							Open in new tab
						</Button>
					</div>
				</div>

				<!-- PDF Viewer Area -->
				<div class="flex flex-1 overflow-hidden bg-muted/30">
					<iframe
						title="pdf"
						src={URL.createObjectURL(selectedPdf.optimizedFile ?? selectedPdf.file) +
							'#toolbar=0&navpanes=0&scrollbar=0&zoom=55'}
						class="h-full w-full border-0"
						frameborder="0"
					></iframe>
				</div>

				<!-- Status Bar -->
				{#if selectedPdf.optimizedFile}
					<div
						class="flex justify-between border-t bg-background px-6 py-3 text-xs text-muted-foreground"
					>
						<span class="flex items-center gap-1">
							<FileCheck class="text-success h-3 w-3" />
							Cleaned PDF • Blank pages removed
						</span>
						<span>{formatFileSize(selectedPdf.optimizedFile.size)}</span>
					</div>
				{/if}
			</DialogContent>
		</Dialog>
	{/if}
</div>
