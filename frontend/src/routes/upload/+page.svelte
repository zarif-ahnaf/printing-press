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
	import { NONBLANK_URL, QUEUE_URL, PDF_CONVERT_URL } from '$lib/constants/backend';
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
	let users = $state<APIUser[]>([]);
	let userSearch = $state('');
	let processingFiles = $state<string[]>([]);
	let isLoadingUsers = $state(false);

	interface APIUser {
		id: number;
		username: string;
		email: string;
		first_name: string;
		last_name: string;
	}

	interface PDFFile {
		id: string;
		file: File;
		optimizedFile: File | null;
		isOptimizing: boolean;
		nonBlankCount: number | null;
		enqueueStatus: 'idle' | 'processing' | 'success' | 'error';
		errorMessage: string | null;
		isConverting: boolean;
		isCurrentlyOptimized: boolean;
		previewUrl: string; // Track preview URL for reactivity
	}

	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	}

	function updatePreviewUrl(pdfFile: PDFFile) {
		// Revoke old URL if exists
		if (pdfFile.previewUrl) {
			URL.revokeObjectURL(pdfFile.previewUrl);
		}

		const fileToUse =
			pdfFile.optimizedFile && pdfFile.isCurrentlyOptimized ? pdfFile.optimizedFile : pdfFile.file;

		// Only create URL for PDFs
		if (fileToUse.type === 'application/pdf') {
			pdfFile.previewUrl = URL.createObjectURL(fileToUse);
		} else {
			pdfFile.previewUrl = '';
		}
	}

	function getDisplayName(user: APIUser): string {
		if (user.first_name || user.last_name) {
			return `${user.first_name} ${user.last_name}`.trim();
		}
		return user.username;
	}

	async function fetchUsers(searchTerm: string = '') {
		isLoadingUsers = true;
		try {
			const token = localStorage.getItem('token');
			const headers: Record<string, string> = {};
			if (token) {
				headers.Authorization = `Bearer ${token}`;
			}

			let url = 'http://127.0.0.1:8000/api/users/';
			if (searchTerm) {
				const params = new URLSearchParams({ name: searchTerm });
				url += `?${params.toString()}`;
			}

			const response = await fetch(url, {
				method: 'GET',
				headers
			});

			if (!response.ok) {
				throw new Error(`Failed to fetch users: ${response.status} ${response.statusText}`);
			}

			const userData: APIUser[] = await response.json();
			users = userData;
		} catch (error: any) {
			toast.error('Failed to load users', {
				description: error.message || 'An unknown error occurred',
				duration: 5000
			});
			console.error('Error fetching users:', error);
		} finally {
			isLoadingUsers = false;
		}
	}

	async function convertFileToPDF(file: File): Promise<File> {
		const formData = new FormData();
		formData.append('file', file);

		const token = localStorage.getItem('token');
		const headers: Record<string, string> = {};
		if (token) {
			headers.Authorization = `Bearer ${token}`;
		}

		const response = await fetch(PDF_CONVERT_URL, {
			method: 'POST',
			headers,
			body: formData
		});

		if (!response.ok) {
			throw new Error(`Failed to convert ${file.name} to PDF`);
		}

		const blob = await response.blob();
		return new File([blob], file.name.replace(/\.[^/.]+$/, '.pdf'), {
			type: 'application/pdf'
		});
	}

	async function handleFiles(fileList: FileList) {
		for (const file of Array.from(fileList)) {
			const newFileEntry: PDFFile = {
				id: crypto.randomUUID(),
				file,
				optimizedFile: null,
				isOptimizing: false,
				nonBlankCount: null,
				enqueueStatus: 'idle',
				errorMessage: null,
				isConverting: false,
				isCurrentlyOptimized: false,
				previewUrl: file.type === 'application/pdf' ? URL.createObjectURL(file) : ''
			};

			if (file.type !== 'application/pdf') {
				newFileEntry.isConverting = true;
				files.push(newFileEntry);

				try {
					const convertedPDF = await convertFileToPDF(file);

					const updatedFileEntry = {
						...newFileEntry,
						file: convertedPDF,
						isConverting: false
					};

					// Update preview URL (this mutates the object, but we’ll replace the whole item)
					updatePreviewUrl(updatedFileEntry);

					// Replace the old entry in files array with new one to trigger reactivity
					files = files.map((f) => (f.id === updatedFileEntry.id ? updatedFileEntry : f));

					toast.success('File converted to PDF', {
						description: file.name,
						duration: 2000
					});
				} catch (error: any) {
					newFileEntry.isConverting = false;
					newFileEntry.errorMessage = error.message;
					newFileEntry.enqueueStatus = 'error';
					toast.error('Conversion failed', {
						description: error.message,
						duration: 5000
					});
				}
			} else {
				files.push(newFileEntry);
			}
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

		// Clean up preview URL
		if (pdfFile.previewUrl) {
			URL.revokeObjectURL(pdfFile.previewUrl);
		}

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
			formData.append('files', fileToSubmit);

			if (isAdmin && selectedUserId !== null) {
				formData.append('user_id', selectedUserId.toString());
			}

			const token = localStorage.getItem('token');
			const headers: Record<string, string> = {};
			if (token) {
				headers.Authorization = `Bearer ${token}`;
			}

			processingFiles = [...processingFiles, pdfFile.id];
			pdfFile.enqueueStatus = 'processing';

			const res = await fetch(QUEUE_URL, {
				method: 'POST',
				headers,
				body: formData
			});

			if (!res.ok) {
				const errorText = await res.text();
				throw new Error(errorText || `Failed to enqueue ${pdfFile.file.name}`);
			}

			pdfFile.enqueueStatus = 'success';
			toast.success('File enqueued successfully', {
				description: pdfFile.file.name,
				duration: 3000
			});
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

		const formData = new FormData();
		filesToSubmit.forEach((pdfFile) => {
			const fileToSubmit =
				pdfFile.optimizedFile && pdfFile.isCurrentlyOptimized
					? pdfFile.optimizedFile
					: pdfFile.file;
			formData.append('files', fileToSubmit);
		});

		if (isAdmin && selectedUserId !== null) {
			formData.append('user_id', selectedUserId.toString());
		}

		const token = localStorage.getItem('token');
		const headers: Record<string, string> = {};
		if (token) {
			headers.Authorization = `Bearer ${token}`;
		}

		try {
			const res = await fetch(QUEUE_URL, {
				method: 'POST',
				headers,
				body: formData
			});

			if (res.ok) {
				filesToSubmit.forEach((pdfFile) => {
					pdfFile.enqueueStatus = 'success';
				});

				toast.success(`${filesToSubmit.length} file(s) enqueued successfully`, {
					duration: 4000
				});

				goto('/transactions');
			} else {
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

	async function optimizeFile(pdfFile: PDFFile) {
		try {
			pdfFile.isOptimizing = true;

			const formData = new FormData();
			formData.append('file', pdfFile.file);
			formData.append('return_pdf', 'true');

			const token = localStorage.getItem('token');
			const headers: Record<string, string> = {};
			if (token) {
				headers.Authorization = `Bearer ${token}`;
			}

			const response = await fetch(NONBLANK_URL, {
				method: 'POST',
				headers,
				body: formData
			});

			if (!response.ok) {
				throw new Error(`Failed to process ${pdfFile.file.name}`);
			}

			const blob = await response.blob();
			const optimizedFile = new File([blob], `cleaned_${pdfFile.file.name}`, {
				type: 'application/pdf'
			});

			pdfFile.optimizedFile = optimizedFile;
			updatePreviewUrl(pdfFile); // Update preview after optimization
			toast.success('File optimized successfully', {
				description: pdfFile.file.name,
				duration: 3000
			});
		} catch (error: any) {
			toast.error('Optimization failed', {
				description: error.message || 'An unknown error occurred',
				duration: 5000
			});
		} finally {
			pdfFile.isOptimizing = false;
		}
	}

	function toggleOptimizationView(pdfFile: PDFFile) {
		if (pdfFile.optimizedFile) {
			pdfFile.isCurrentlyOptimized = !pdfFile.isCurrentlyOptimized;
			updatePreviewUrl(pdfFile); // Update preview when toggling view
		} else {
			optimizeFile(pdfFile);
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

	// Handle user search input with debouncing
	let searchTimeout: any;
	function handleUserSearch() {
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			fetchUsers(userSearch);
		}, 300); // 300ms debounce
	}

	onMount(() => {
		// Fetch all users when component mounts
		fetchUsers();

		window.addEventListener('dragover', handleDragOver);
		window.addEventListener('dragleave', handleDragLeave);
		window.addEventListener('drop', handleDrop);
		return () => {
			clearTimeout(searchTimeout);
			// Clean up all blob URLs
			files.forEach((f) => {
				if (f.previewUrl) {
					URL.revokeObjectURL(f.previewUrl);
				}
			});
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
			<p class="mt-1 text-muted-foreground">Upload files and remove blank pages instantly</p>
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
							oninput={handleUserSearch}
							onblur={() => setTimeout(() => (isUserDropdownOpen = false), 150)}
							onkeydown={(e) => {
								if (e.key === 'Escape') {
									isUserDropdownOpen = false;
								}
							}}
							class="pr-8"
						/>
						{#if userSearch && (isUserDropdownOpen || isLoadingUsers)}
							<div
								class="absolute top-full z-50 mt-1 w-full animate-in rounded-md border bg-popover text-popover-foreground shadow-md fade-in-0 outline-none zoom-in-95"
							>
								{#if isLoadingUsers}
									<div class="px-3 py-2 text-sm text-muted-foreground">Loading...</div>
								{:else if users.length === 0}
									<div class="px-3 py-2 text-sm text-muted-foreground">No users found</div>
								{:else}
									{#each users as user}
										<button
											type="button"
											class="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left text-sm select-none hover:bg-accent hover:text-accent-foreground"
											onclick={() => {
												selectedUserId = user.id;
												userSearch = getDisplayName(user);
												isUserDropdownOpen = false;
											}}
										>
											<div
												class="mr-2 h-2 w-2 rounded-full {user.id === 1
													? 'bg-primary'
													: 'bg-muted-foreground'}"
											></div>
											<div class="flex flex-col">
												<span>{getDisplayName(user)}</span>
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
			<CardTitle>Upload Files</CardTitle>
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
				<p class="font-medium">Drag & drop files here</p>
				<p class="mt-1 text-sm text-muted-foreground">or click to browse files (PDF, DOCX, etc.)</p>
				<Input
					id="file-upload"
					type="file"
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
			<p class="text-muted-foreground">Upload files to get started</p>
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
					{#if pdfFile.isConverting}
						<div class="absolute top-2 left-2 z-10">
							<div class="h-3 w-3 animate-pulse rounded-full bg-blue-500"></div>
						</div>
					{:else if pdfFile.enqueueStatus === 'processing'}
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
						{#if pdfFile.previewUrl}
							<embed
								src={pdfFile.previewUrl}
								type="application/pdf"
								class="h-full w-full cursor-pointer object-cover transition-opacity
									{pdfFile.isOptimizing || pdfFile.isConverting ? 'opacity-50' : 'opacity-100'}"
								onclick={() => openPdfDialog(pdfFile)}
							/>
						{:else}
							<div
								class="flex h-full w-full items-center justify-center bg-muted text-muted-foreground"
							>
								{#if pdfFile.isConverting}
									<span class="text-sm">Converting...</span>
								{:else}
									<FileText class="h-12 w-12" />
								{/if}
							</div>
						{/if}

						{#if pdfFile.isOptimizing || pdfFile.isConverting}
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

					<!-- Hover action bar: Delete | Preview | Toggle Optimization -->
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
							disabled={pdfFile.isOptimizing ||
								pdfFile.isConverting ||
								pdfFile.enqueueStatus === 'processing'}
							onclick={async (e) => {
								e.stopPropagation();
								toggleOptimizationView(pdfFile);
							}}
						>
							{#if pdfFile.isOptimizing || pdfFile.isConverting}
								<Progress class="h-1 w-6" value={50} />
							{:else if pdfFile.optimizedFile && pdfFile.isCurrentlyOptimized}
								<Zap class="h-3.5 w-3.5 fill-primary text-primary" />
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
							<p class="text-xs text-muted-foreground">
								{formatFileSize(
									pdfFile.optimizedFile && pdfFile.isCurrentlyOptimized
										? pdfFile.optimizedFile.size
										: pdfFile.file.size
								)}
							</p>
							{#if pdfFile.optimizedFile}
								{#if pdfFile.isCurrentlyOptimized}
									<Badge variant="secondary" class="text-xs">Cleaned</Badge>
								{:else}
									<Badge variant="outline" class="text-xs">Original</Badge>
								{/if}
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
					Enqueue All Files
				{/if}
			</Button>
		</div>
	{/if}

	<!-- PDF Preview Dialog -->
	{#if selectedPdf}
		{#each [selectedPdf] as pdf (pdf.id)}
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
							<span class="max-w-xs truncate font-medium">{pdf.file.name}</span>
							{#if isAdmin && selectedUserId !== null}
								<Badge variant="outline" class="ml-2">
									{getDisplayName(users.find((u) => u.id === selectedUserId)!)}
								</Badge>
							{/if}
						</div>
						<div class="flex gap-2 p-5">
							{#if pdf.optimizedFile}
								<Button variant="outline" size="sm" onclick={() => downloadOptimized(pdf)}>
									<Download class="mr-1.5 h-4 w-4" />
									Download
								</Button>
								<Button
									variant="outline"
									size="sm"
									onclick={() => {
										pdf.isCurrentlyOptimized = !pdf.isCurrentlyOptimized;
										updatePreviewUrl(pdf);
									}}
								>
									{pdf.isCurrentlyOptimized ? 'Show Original' : 'Show Cleaned'}
								</Button>
							{/if}
							<Button
								variant="outline"
								size="sm"
								onclick={() => {
									const fileToOpen =
										pdf.optimizedFile && pdf.isCurrentlyOptimized ? pdf.optimizedFile : pdf.file;
									window.open(URL.createObjectURL(fileToOpen), '_blank');
								}}
							>
								Open in new tab
							</Button>
						</div>
					</div>

					<!-- PDF Viewer Area -->
					<div class="flex flex-1 overflow-hidden bg-muted/30">
						{#if pdf.previewUrl}
							<iframe
								title="pdf"
								src={pdf.previewUrl + '#toolbar=0&navpanes=0&scrollbar=0&zoom=55'}
								class="h-full w-full border-0"
								frameborder="0"
							></iframe>
						{:else}
							<div
								class="flex h-full w-full items-center justify-center bg-muted text-muted-foreground"
							>
								{#if pdf.isConverting}
									<span>Converting file to PDF...</span>
								{:else}
									<span>Preview not available</span>
								{/if}
							</div>
						{/if}
					</div>

					<!-- Status Bar -->
					{#if pdf.optimizedFile}
						<div
							class="flex justify-between border-t bg-background px-6 py-3 text-xs text-muted-foreground"
						>
							<span class="flex items-center gap-1">
								{#if pdf.isCurrentlyOptimized}
									<FileCheck class="text-success h-3 w-3" />
									Cleaned PDF • Blank pages removed
								{:else}
									<FileText class="h-3 w-3 text-muted-foreground" />
									Original PDF
								{/if}
							</span>
							<span>
								{formatFileSize(pdf.isCurrentlyOptimized ? pdf.optimizedFile!.size : pdf.file.size)}
							</span>
						</div>
					{/if}
				</DialogContent>
			</Dialog>
		{/each}
	{/if}
</div>
