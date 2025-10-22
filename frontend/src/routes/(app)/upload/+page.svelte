<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		Upload as UploadIcon,
		FileText as FileTextIcon,
		Download as DownloadIcon,
		Zap as ZapIcon,
		FileCheck as FileCheckIcon,
		Trash2 as Trash2Icon,
		Eye as EyeIcon,
		Users as UsersIcon,
		ArrowLeft as ArrowLeftIcon,
		TriangleAlert as TriangleAlertIcon,
		X as XIcon,
		Plus as PlusIcon,
		Ellipsis
	} from 'lucide-svelte';
	import { token } from '$lib/stores/token.svelte';
	import { is_admin_user } from '$lib/stores/auth.svelte';

	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Progress } from '$lib/components/ui/progress';
	import { Dialog, DialogContent } from '$lib/components/ui/dialog';
	import { Badge } from '$lib/components/ui/badge';
	import {
		DropdownMenu,
		DropdownMenuContent,
		DropdownMenuItem,
		DropdownMenuTrigger
	} from '$lib/components/ui/dropdown-menu';
	import {
		NONBLANK_URL,
		QUEUE_URL,
		PDF_CONVERT_URL,
		ALL_USER_ENDPOINT
	} from '$lib/constants/backend';
	import { goto } from '$app/navigation';
	import { uuidv4 } from '$lib/functions/uuid4';

	// Svelte 5 runes
	let files = $state<PDFFile[]>([]);
	let isDragging = $state(false);
	let isSubmitting = $state(false);
	let selectedPdf = $state<PDFFile | null>(null);
	let isDialogOpen = $state(false);
	let isUserDropdownOpen = $state(false);
	let selectedUserId: number | null = $state<number | null>(null);
	let users = $state<APIUser[]>([]);
	let userSearch = $state('');
	let isLoadingUsers = $state(false);
	let isGlobalDragOver = $state(false);

	// Duplication dialog state
	let isDuplicateDialogOpen = $state(false);
	let duplicateCount = $state(2);
	let fileToDuplicate: PDFFile | null = $state(null);

	// Delete confirmation dialog state
	let isDeleteDialogOpen = $state(false);
	let fileToDelete: PDFFile | null = $state(null);

	interface APIUser {
		id: number;
		username: string;
		email: string;
		first_name: string;
		last_name: string;
	}
	interface QueueUploadResponse {
		message: string;
		total_pages: number;
		queue_ids: number[];
		total_charged_bdt: string;
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
		previewUrl: string;
	}

	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	}

	function updatePreviewUrl(pdfFile: PDFFile) {
		if (pdfFile.previewUrl) {
			URL.revokeObjectURL(pdfFile.previewUrl);
		}

		const fileToUse =
			pdfFile.optimizedFile && pdfFile.isCurrentlyOptimized ? pdfFile.optimizedFile : pdfFile.file;

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
			const headers: Record<string, string> = {};
			if (token.value) {
				headers.Authorization = `Bearer ${token.value}`;
			}

			let url = ALL_USER_ENDPOINT;
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

		const headers: Record<string, string> = {};
		if (token.value) {
			headers.Authorization = `Bearer ${token.value}`;
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
				id: uuidv4(),
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

					updatePreviewUrl(updatedFileEntry);

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

	function openDeleteDialog(pdfFile: PDFFile) {
		fileToDelete = pdfFile;
		isDeleteDialogOpen = true;
	}

	function confirmDelete() {
		if (!fileToDelete) return;

		if (fileToDelete.previewUrl) {
			URL.revokeObjectURL(fileToDelete.previewUrl);
		}

		files = files.filter((f) => f.id !== fileToDelete!.id);
		if (selectedPdf?.id === fileToDelete.id) {
			selectedPdf = null;
			isDialogOpen = false;
		}
		toast.success('File deleted', {
			description: fileToDelete.file.name,
			duration: 2000
		});

		closeDeleteDialog();
	}

	function closeDeleteDialog() {
		isDeleteDialogOpen = false;
		fileToDelete = null;
	}

	function duplicateFile(pdfFile: PDFFile) {
		const newFileEntry: PDFFile = {
			id: uuidv4(),
			file: pdfFile.file,
			optimizedFile: null,
			isOptimizing: false,
			nonBlankCount: null,
			enqueueStatus: 'idle',
			errorMessage: null,
			isConverting: false,
			isCurrentlyOptimized: false,
			previewUrl: pdfFile.file.type === 'application/pdf' ? URL.createObjectURL(pdfFile.file) : ''
		};

		files.push(newFileEntry);

		toast.info('File duplicated', {
			description: pdfFile.file.name,
			duration: 2000
		});
	}

	function openDuplicateDialog(pdf: PDFFile) {
		fileToDuplicate = pdf;
		duplicateCount = 2;
		isDuplicateDialogOpen = true;
	}

	function confirmDuplicate() {
		if (!fileToDuplicate) return;

		const count = Math.max(parseInt(duplicateCount.toString(), 10) || 0, 1);
		if (count < 1) return;

		for (let i = 0; i < count; i++) {
			const newFileEntry: PDFFile = {
				id: uuidv4(),
				file: fileToDuplicate.file,
				optimizedFile: null,
				isOptimizing: false,
				nonBlankCount: null,
				enqueueStatus: 'idle',
				errorMessage: null,
				isConverting: false,
				isCurrentlyOptimized: false,
				previewUrl:
					fileToDuplicate.file.type === 'application/pdf'
						? URL.createObjectURL(fileToDuplicate.file)
						: ''
			};
			files.push(newFileEntry);
		}

		toast.info(`${count} copy/copies added`, {
			description: fileToDuplicate.file.name,
			duration: 2500
		});

		closeDuplicateDialog();
	}

	function closeDuplicateDialog() {
		isDuplicateDialogOpen = false;
		fileToDuplicate = null;
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

		if (is_admin_user.value && selectedUserId !== null && Number.isInteger(selectedUserId)) {
			formData.append('user_id', String(selectedUserId));
		}

		const headers: Record<string, string> = {};
		if (token.value) {
			headers.Authorization = `Bearer ${token.value}`;
		}

		try {
			const res = await fetch(QUEUE_URL, {
				method: 'POST',
				headers, // Note: DO NOT set Content-Type — browser sets it with boundary
				body: formData
			});

			if (res.ok) {
				const data: QueueUploadResponse = await res.json(); // ✅ Parse JSON response
				filesToSubmit.forEach((pdfFile) => {
					pdfFile.enqueueStatus = 'success';
				});
				toast.success(data.message, { duration: 4000 });
				goto('/transactions');
			} else {
				const errorData = await res.json().catch(() => ({}));
				const errorMsg =
					errorData?.detail || errorData?.message || `Enqueue failed (${res.status})`;
				throw new Error(errorMsg);
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

			const headers: Record<string, string> = {};
			if (token.value) {
				headers.Authorization = `Bearer ${token.value}`;
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
			updatePreviewUrl(pdfFile);
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
			updatePreviewUrl(pdfFile);
		} else {
			optimizeFile(pdfFile);
		}
	}

	function openPdfDialog(pdf: PDFFile) {
		selectedPdf = pdf;
		isDialogOpen = true;
	}

	// Drag & drop handlers
	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		isDragging = true;
	}

	function handleDragLeave(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		isDragging = false;
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		isDragging = false;
		isGlobalDragOver = false;
		if (e.dataTransfer?.files) {
			handleFiles(e.dataTransfer.files);
		}
	}

	function handleGlobalDragOver(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		if (e.dataTransfer?.types.includes('Files')) {
			isGlobalDragOver = true;
		}
	}

	function handleGlobalDragLeave(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		if (e.relatedTarget === null) {
			isGlobalDragOver = false;
		}
	}

	function handleGlobalDrop(e: DragEvent) {
		e.preventDefault();
		e.stopPropagation();
		isGlobalDragOver = false;
		if (e.dataTransfer?.files) {
			handleFiles(e.dataTransfer.files);
		}
	}

	let searchTimeout: ReturnType<typeof setTimeout>;
	function handleUserSearch() {
		isUserDropdownOpen = true;
		clearTimeout(searchTimeout);
		searchTimeout = setTimeout(() => {
			fetchUsers(userSearch);
		}, 300);
	}

	function closeDropdown() {
		setTimeout(() => {
			isUserDropdownOpen = false;
		}, 150);
	}

	onMount(() => {
		fetchUsers();

		window.addEventListener('dragover', handleGlobalDragOver);
		window.addEventListener('dragleave', handleGlobalDragLeave);
		window.addEventListener('drop', handleGlobalDrop);

		return () => {
			clearTimeout(searchTimeout);
			files.forEach((f) => {
				if (f.previewUrl) {
					URL.revokeObjectURL(f.previewUrl);
				}
			});
			window.removeEventListener('dragover', handleGlobalDragOver);
			window.removeEventListener('dragleave', handleGlobalDragLeave);
			window.removeEventListener('drop', handleGlobalDrop);
		};
	});
</script>

<!-- Large Drag Overlay -->
{#if isGlobalDragOver}
	<div
		role="region"
		aria-label="File drop zone"
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
		ondragover={handleGlobalDragOver}
		ondragleave={handleGlobalDragLeave}
		ondrop={handleGlobalDrop}
	>
		<div
			class="flex flex-col items-center gap-4 rounded-2xl border-2 border-dashed border-white/30 bg-black/20 p-12 text-center"
		>
			<UploadIcon class="h-16 w-16 text-white" />
			<h2 class="text-2xl font-bold text-white">Drop files here</h2>
			<p class="text-white/70">Drop your files to upload and clean them</p>
		</div>
	</div>
{/if}

<div class="bg-background p-4 md:p-8">
	<!-- Header -->
	<header class="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between">
		{#if is_admin_user.value}
			<div class="mt-4 sm:mt-0">
				<div class="flex items-center gap-2">
					<UsersIcon class="h-4 w-4 text-muted-foreground" />
					<span class="text-sm font-medium">Upload for:</span>

					<div class="relative w-[240px]">
						<div
							class="flex items-center rounded-md border border-input bg-background px-3 py-2 focus-within:ring-1 focus-within:ring-ring"
						>
							<Input
								type="text"
								placeholder="Search users..."
								bind:value={userSearch}
								oninput={handleUserSearch}
								onfocus={() => {
									if (!selectedUserId) {
										isUserDropdownOpen = true;
									}
								}}
								onblur={closeDropdown}
								onkeydown={(e) => {
									if (e.key === 'Escape') {
										isUserDropdownOpen = false;
									}
								}}
								disabled={!!selectedUserId}
								class="flex-1 border-0 bg-transparent pr-8 focus-visible:ring-0 focus-visible:ring-offset-0"
							/>
							{#if selectedUserId}
								<Button
									type="button"
									variant="ghost"
									size="icon"
									class="ml-1 h-5 w-5 text-muted-foreground hover:text-foreground"
									onclick={(e) => {
										e.stopPropagation();
										selectedUserId = null;
										userSearch = '';
										isUserDropdownOpen = false;
									}}
									aria-label="Clear selected user"
								>
									<XIcon class="h-3.5 w-3.5" />
								</Button>
							{/if}
						</div>

						{#if (userSearch || isLoadingUsers) && isUserDropdownOpen && !selectedUserId}
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
				<UploadIcon class="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
				<p class="font-medium">Drag & drop files here</p>
				<p class="mt-1 text-sm text-muted-foreground">or click to browse files (PDF, DOCX, etc.)</p>
				<Input
					id="file-upload"
					type="file"
					multiple
					class="hidden"
					onchange={(e) => {
						const input = e.currentTarget;
						if (input?.files) {
							handleFiles(input.files);
							input.value = '';
						}
					}}
				/>
			</Label>
		</CardContent>
	</Card>

	<!-- PDF Thumbnails -->
	{#if files.length === 0}
		<div class="py-16 text-center">
			<FileTextIcon class="mx-auto mb-4 h-16 w-16 text-muted-foreground" />
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
									<FileTextIcon class="h-12 w-12" />
								{/if}
							</div>
						{/if}

						{#if pdfFile.isOptimizing || pdfFile.isConverting}
							<div class="absolute inset-0 flex items-center justify-center bg-black/20">
								<Progress class="h-1.5 w-12" value={50} />
							</div>
						{/if}
					</div>

					{#if pdfFile.optimizedFile}
						<div
							class="bg-success text-success-foreground absolute top-2 right-2 rounded-full p-1.5"
						>
							<FileCheckIcon class="h-3 w-3" />
						</div>
					{/if}

					<!-- Action bar -->
					<div
						class="absolute right-0 bottom-0 left-0 flex justify-between bg-background/90 p-2 opacity-0 backdrop-blur transition-opacity group-hover:opacity-100"
					>
						<DropdownMenu>
							<DropdownMenuTrigger>
								<Button variant="ghost" size="icon" class="h-7 w-7" title="Duplicate options">
									<Ellipsis class="h-3.5 w-3.5 text-muted-foreground" />
								</Button>
							</DropdownMenuTrigger>
							<DropdownMenuContent class="w-48">
								<DropdownMenuItem
									onclick={(e) => {
										e.preventDefault();
										duplicateFile(pdfFile);
									}}
								>
									<PlusIcon class="mr-2 h-3.5 w-3.5" />
									Duplicate once
								</DropdownMenuItem>
								<DropdownMenuItem
									onclick={(e) => {
										e.preventDefault();
										openDuplicateDialog(pdfFile);
									}}
								>
									<FileTextIcon class="mr-2 h-3.5 w-3.5" />
									Duplicate multiple…
								</DropdownMenuItem>
							</DropdownMenuContent>
						</DropdownMenu>

						<Button
							variant="ghost"
							size="icon"
							class="h-7 w-7"
							onclick={(e) => {
								e.stopPropagation();
								openDeleteDialog(pdfFile);
							}}
						>
							<Trash2Icon class="h-3.5 w-3.5 text-destructive" />
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
							<EyeIcon class="h-3.5 w-3.5 text-muted-foreground" />
						</Button>
						<Button
							variant="ghost"
							size="icon"
							class="h-7 w-7"
							disabled={pdfFile.isOptimizing ||
								pdfFile.isConverting ||
								pdfFile.enqueueStatus === 'processing'}
							onclick={(e) => {
								e.stopPropagation();
								toggleOptimizationView(pdfFile);
							}}
						>
							{#if pdfFile.isOptimizing || pdfFile.isConverting}
								<Progress class="h-1 w-6" value={50} />
							{:else if pdfFile.optimizedFile && pdfFile.isCurrentlyOptimized}
								<ZapIcon class="h-3.5 w-3.5 fill-primary text-primary" />
							{:else if pdfFile.optimizedFile}
								<ZapIcon class="h-3.5 w-3.5 text-primary" />
							{:else}
								<ZapIcon class="h-3.5 w-3.5 text-muted-foreground" />
							{/if}
						</Button>
					</div>

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
								<TriangleAlertIcon class="mr-1 inline h-3 w-3" />
								{pdfFile.errorMessage.substring(0, 50)}
								{pdfFile.errorMessage.length > 50 ? '...' : ''}
							</div>
						{/if}
					</div>
				</div>
			{/each}
		</div>

		<div class="mt-8 flex justify-end">
			<Button size="lg" disabled={isSubmitting || files.length === 0} onclick={() => submitAll()}>
				{#if isSubmitting}
					<span class="flex items-center gap-2">
						<Progress class="h-2 w-16" value={50} />
						Enqueuing...
					</span>
				{:else}
					<ZapIcon class="mr-2 h-4 w-4" />
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
								<ArrowLeftIcon class="h-4 w-4" />
							</Button>
							<FileTextIcon class="h-5 w-5 text-muted-foreground" />
							<span class="max-w-xs truncate font-medium">{pdf.file.name}</span>
							{#if is_admin_user.value && selectedUserId !== null}
								<Badge variant="outline" class="ml-2">
									{getDisplayName(users.find((u) => u.id === selectedUserId)!)}
								</Badge>
							{/if}
						</div>
						<div class="flex gap-2">
							{#if pdf.optimizedFile}
								<Button variant="outline" size="sm" onclick={() => downloadOptimized(pdf)}>
									<DownloadIcon class="mr-1.5 h-4 w-4" />
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

					{#if pdf.optimizedFile}
						<div
							class="flex justify-between border-t bg-background px-6 py-3 text-xs text-muted-foreground"
						>
							<span class="flex items-center gap-1">
								{#if pdf.isCurrentlyOptimized}
									<FileCheckIcon class="text-success h-3 w-3" />
									Cleaned PDF • Blank pages removed
								{:else}
									<FileTextIcon class="h-3 w-3 text-muted-foreground" />
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

	<!-- Duplicate by Number Dialog -->
	{#if isDuplicateDialogOpen}
		<Dialog open={isDuplicateDialogOpen} onOpenChange={closeDuplicateDialog}>
			<DialogContent class="sm:max-w-[425px]">
				<div class="grid gap-4 py-4">
					<div class="flex flex-col gap-2">
						<h3 class="text-lg font-semibold">Duplicate File</h3>
						<p class="text-sm text-muted-foreground">
							How many copies of <span class="font-medium">{fileToDuplicate?.file.name}</span> would
							you like to add?
						</p>
					</div>

					<div class="grid gap-2">
						<Label for="duplicate-count">Number of copies</Label>
						<Input
							id="duplicate-count"
							type="number"
							min="1"
							class="w-full"
							bind:value={duplicateCount}
							onkeydown={(e) => {
								if (e.key === 'Enter') {
									confirmDuplicate();
								}
							}}
						/>
					</div>

					<div class="flex justify-end gap-2 pt-2">
						<Button variant="outline" onclick={closeDuplicateDialog}>Cancel</Button>
						<Button onclick={confirmDuplicate}>Add Copies</Button>
					</div>
				</div>
			</DialogContent>
		</Dialog>
	{/if}

	<!-- Delete Confirmation Dialog -->
	{#if isDeleteDialogOpen}
		<Dialog open={isDeleteDialogOpen} onOpenChange={closeDeleteDialog}>
			<DialogContent class="sm:max-w-[400px]">
				<div class="grid gap-4 py-4">
					<div class="flex flex-col gap-2">
						<h3 class="text-lg font-semibold text-destructive">Delete File?</h3>
						<p class="text-sm text-muted-foreground">
							Are you sure you want to delete "<span class="font-medium"
								>{fileToDelete?.file.name}</span
							>"? This action cannot be undone.
						</p>
					</div>

					<div class="flex justify-end gap-2 pt-2">
						<Button variant="outline" onclick={closeDeleteDialog}>Cancel</Button>
						<Button variant="destructive" onclick={confirmDelete}>Delete</Button>
					</div>
				</div>
			</DialogContent>
		</Dialog>
	{/if}
</div>
