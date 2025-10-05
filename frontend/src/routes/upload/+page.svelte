<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { Upload, FileText, Download, Zap, FileCheck, Trash2, X, Eye } from 'lucide-svelte';

	// shadcn-svelte components
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Progress } from '$lib/components/ui/progress';
	import { Dialog, DialogContent, DialogHeader, DialogTitle } from '$lib/components/ui/dialog';

	// Svelte 5 runes
	let files = $state<PDFFile[]>([]);
	let isDragging = $state(false);
	let isSubmitting = $state(false);
	let selectedPdf = $state<PDFFile | null>(null);
	let isDialogOpen = $state(false);

	interface PDFFile {
		id: string;
		file: File;
		optimizedFile: File | null;
		isOptimizing: boolean;
		nonBlankCount: number | null;
	}

	function formatFileSize(bytes: number): string {
		if (bytes === 0) return '0 Bytes';
		const k = 1024;
		const sizes = ['Bytes', 'KB', 'MB', 'GB'];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
	}

	function handleFiles(fileList: FileList) {
		for (const file of Array.from(fileList)) {
			if (file.type !== 'application/pdf') {
				toast.error('Only PDF files are supported');
				continue;
			}
			files.push({
				id: crypto.randomUUID(),
				file,
				optimizedFile: null,
				isOptimizing: false,
				nonBlankCount: null
			});
		}
	}

	async function optimizePDF(pdfFile: PDFFile) {
		pdfFile.isOptimizing = true;
		try {
			const formData = new FormData();
			formData.append('file', pdfFile.file);
			formData.append('return_pdf', 'true');

			const res = await fetch('/api/count/nonblank', {
				method: 'POST',
				body: formData
			});

			if (!res.ok) throw new Error((await res.text()) || 'Failed to process PDF');

			const blob = await res.blob();
			pdfFile.optimizedFile = new File([blob], `cleaned_${pdfFile.file.name}`, {
				type: 'application/pdf'
			});
			toast.success('Blank pages removed successfully!');
		} catch (error: any) {
			toast.error(error.message || 'Failed to remove blank pages');
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
		toast.success('File deleted');
	}

	async function submitAll() {
		const optimized = files.filter((f) => f.optimizedFile);
		if (optimized.length === 0) {
			toast.error('No cleaned PDFs to submit');
			return;
		}

		isSubmitting = true;
		const formData = new FormData();
		optimized.forEach((f) =>
			formData.append('optimized_pdfs', f.optimizedFile!, f.optimizedFile!.name)
		);

		try {
			const token = localStorage.getItem('token');
			const res = await fetch('/api/submit-optimized/', {
				method: 'POST',
				headers: token ? { Authorization: `Bearer ${token}` } : {},
				body: formData
			});

			if (res.ok) {
				toast.success('All cleaned PDFs submitted!');
			} else {
				toast.error(`Submission failed: ${await res.text()}`);
			}
		} catch (error) {
			toast.error('Failed to submit PDFs');
		} finally {
			isSubmitting = false;
		}
	}

	function openPdfDialog(pdf: PDFFile) {
		selectedPdf = pdf;
		isDialogOpen = true;
	}

	// Drag & drop
	function handleDragOver(e: DragEvent) {
		e.preventDefault();
		isDragging = true;
	}
	function handleDragLeave(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
	}
	function handleDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
		if (e.dataTransfer?.files) handleFiles(e.dataTransfer.files);
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
	<header class="mb-8">
		<h1 class="text-3xl font-bold">PDF Cleaner</h1>
		<p class="mt-1 text-muted-foreground">Upload PDFs and remove blank pages instantly</p>
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
					onchange={(e) => {
						const input = e.currentTarget;
						if (input?.files) handleFiles(input.files);
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
				<div class="group relative overflow-hidden rounded-xl border bg-card">
					<!-- Thumbnail -->
					<div class="relative aspect-[3/4] w-full bg-muted">
						<embed
							src={URL.createObjectURL(pdfFile.optimizedFile ?? pdfFile.file)}
							type="application/pdf"
							class="h-full w-full cursor-pointer object-cover"
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
							disabled={pdfFile.isOptimizing}
							onclick={(e) => {
								e.stopPropagation();
								optimizePDF(pdfFile);
							}}
						>
							{#if pdfFile.isOptimizing}
								<Progress class="h-1 w-6" value={50} />
							{:else}
								<Zap class="h-3.5 w-3.5 text-primary" />
							{/if}
						</Button>
					</div>

					<!-- Filename -->
					<div class="p-3">
						<p class="truncate text-sm font-medium">{pdfFile.file.name}</p>
						<p class="mt-1 text-xs text-muted-foreground">{formatFileSize(pdfFile.file.size)}</p>
					</div>
				</div>
			{/each}
		</div>

		<!-- Submit Button -->
		<div class="mt-8 flex justify-end">
			<Button
				size="lg"
				disabled={isSubmitting || files.every((f) => !f.optimizedFile)}
				onclick={submitAll}
			>
				{#if isSubmitting}
					<span class="flex items-center gap-2">
						<Progress class="h-2 w-16" value={50} />
						Submitting...
					</span>
				{:else}
					<Zap class="mr-2 h-4 w-4" />
					Submit All Cleaned PDFs
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
			<DialogContent class="flex h-[65vh] w-[90vw] flex-col overflow-hidden p-0">
				<!-- Top Bar -->
				<div class="flex items-center justify-between border-b bg-background px-4 py-3">
					<div class="flex items-center gap-2">
						<FileText class="h-5 w-5 text-muted-foreground" />
						<span class="max-w-xs truncate font-medium">{selectedPdf.file.name}</span>
					</div>
					{#if selectedPdf.optimizedFile}
						<Button variant="outline" size="sm" onclick={() => downloadOptimized(selectedPdf)}>
							<Download class="mr-1.5 h-4 w-4" />
							Download
						</Button>
					{/if}
				</div>

				<!-- PDF Viewer Area -->
				<div class="flex flex-1 items-center justify-center overflow-auto bg-muted/30 p-4">
					<!-- A4 aspect ratio container — no overflow-x, uses more height naturally -->
					<div
						class="aspect-[210/297] w-full max-w-4xl overflow-hidden rounded border bg-white shadow-sm"
					>
						<iframe
							title="pdf"
							src={URL.createObjectURL(selectedPdf.optimizedFile ?? selectedPdf.file) +
								'#toolbar=0&navpanes=0&scrollbar=0&zoom=100'}
							class="h-full w-full border-0"
							frameborder="0"
						></iframe>
					</div>
				</div>

				<!-- Bottom Bar -->
				{#if selectedPdf.optimizedFile}
					<div
						class="flex justify-between border-t bg-background px-4 py-2 text-xs text-muted-foreground"
					>
						<span>Cleaned PDF • Blank pages removed</span>
						<span>{formatFileSize(selectedPdf.optimizedFile.size)}</span>
					</div>
				{/if}
			</DialogContent>
		</Dialog>
	{/if}
</div>
