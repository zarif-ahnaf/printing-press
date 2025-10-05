<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { Upload, FileText, Download, Zap, FileCheck } from 'lucide-svelte';

	// ✅ Your exact imports
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Progress } from '$lib/components/ui/progress';

	// ✅ Svelte 5 runes — NO $ prefix on your variables
	let files = $state<PDFFile[]>([]);
	let isDragging = $state(false);
	let balance = $state<string | null>(null);
	let isLoadingBalance = $state(false);

	interface PDFFile {
		id: string;
		file: File;
		optimizedFile: File | null;
		isOptimizing: boolean;
		nonBlankCount: number | null;
	}

	async function fetchBalance() {
		isLoadingBalance = true;
		try {
			const token = localStorage.getItem('token');
			if (!token) {
				balance = '0.00';
				return;
			}

			const res = await fetch('/api/balance/', {
				headers: { Authorization: `Bearer ${token}` }
			});
			if (res.ok) {
				const data = await res.json();
				balance = data.balance;
			} else {
				balance = '0.00';
			}
		} catch (error) {
			console.error('Balance fetch error:', error);
			toast.error('Failed to fetch balance');
			balance = '0.00';
		} finally {
			isLoadingBalance = false;
		}
	}

	function handleFiles(fileList: FileList) {
		for (const file of Array.from(fileList)) {
			if (file.type !== 'application/pdf') {
				toast.error('Only PDF files are supported');
				continue;
			}

			const id = crypto.randomUUID();
			const newFile: PDFFile = {
				id,
				file,
				optimizedFile: null,
				isOptimizing: false,
				nonBlankCount: null
			};

			files.push(newFile);
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

			if (!res.ok) {
				const errText = await res.text();
				throw new Error(errText || 'Optimization failed');
			}

			const blob = await res.blob();
			const optimizedFile = new File([blob], `optimized_${pdfFile.file.name}`, {
				type: 'application/pdf'
			});

			pdfFile.optimizedFile = optimizedFile;
			toast.success('PDF optimized successfully!');
		} catch (error: any) {
			console.error('Optimize error:', error);
			toast.error(error.message || 'Optimization failed');
		} finally {
			pdfFile.isOptimizing = false;
		}
	}

	function downloadOptimized(pdfFile: PDFFile) {
		if (!pdfFile.optimizedFile) return;

		const url = URL.createObjectURL(pdfFile.optimizedFile);
		const a = document.createElement('a');
		a.href = url;
		a.download = pdfFile.optimizedFile.name;
		document.body.appendChild(a);
		a.click();
		document.body.removeChild(a);
		URL.revokeObjectURL(url);
	}

	// Drag and drop
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
		if (e.dataTransfer?.files) {
			handleFiles(e.dataTransfer.files);
		}
	}

	onMount(() => {
		fetchBalance();

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
	<header class="mb-8">
		<h1 class="text-3xl font-bold">PDF Optimizer</h1>
		<div class="mt-2 flex items-center gap-2">
			{#if isLoadingBalance}
				<div class="h-4 w-24 animate-pulse rounded bg-muted"></div>
			{:else}
				<span class="text-sm font-medium">Balance: {balance}</span>
			{/if}
			<Button variant="outline" size="sm" onclick={fetchBalance}>Refresh</Button>
		</div>
	</header>

	<!-- Upload Area -->
	<Card class="mb-8">
		<CardHeader>
			<CardTitle>Upload PDFs</CardTitle>
		</CardHeader>
		<CardContent>
			<label
				for="file-upload"
				role="button"
				tabindex="0"
				aria-label="Upload PDFs"
				class="cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors
		  {isDragging ? 'border-primary bg-primary/5' : 'border-muted'}"
				ondragover={handleDragOver}
				ondragleave={handleDragLeave}
				ondrop={handleDrop}
				onkeydown={(e: KeyboardEvent) => {
					if (e.key === 'Enter' || e.key === ' ') {
						e.preventDefault();
						const input = document.getElementById('file-upload') as HTMLInputElement | null;
						input?.click();
					}
				}}
			>
				<Upload class="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
				<p class="mb-2">Drag & drop PDF files here</p>
				<p class="text-sm text-muted-foreground">or click to browse</p>
				<Input
					id="file-upload"
					type="file"
					accept=".pdf"
					multiple
					class="hidden"
					onchange={(e) => {
						const input = e.currentTarget as HTMLInputElement | null;
						if (input?.files) handleFiles(input.files);
					}}
				/>
			</label>
		</CardContent>
	</Card>

	<!-- PDF List -->
	{#if files.length === 0}
		<div class="py-12 text-center">
			<FileText class="mx-auto mb-4 h-16 w-16 text-muted-foreground" />
			<p class="text-muted-foreground">No PDFs uploaded yet</p>
		</div>
	{:else}
		<div class="grid gap-6">
			{#each files as pdfFile (pdfFile.id)}
				<Card>
					<CardHeader class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
						<CardTitle class="flex items-center gap-2 truncate">
							<FileText class="h-5 w-5 flex-shrink-0" />
							<span class="truncate">{pdfFile.file.name}</span>
						</CardTitle>
						<div class="flex flex-wrap justify-end gap-2">
							{#if pdfFile.optimizedFile}
								<Button size="sm" variant="outline" onclick={() => downloadOptimized(pdfFile)}>
									<Download class="mr-2 h-4 w-4" />
									Download Optimized
								</Button>
							{/if}
							<Button
								size="sm"
								disabled={pdfFile.isOptimizing}
								onclick={() => optimizePDF(pdfFile)}
							>
								{#if pdfFile.isOptimizing}
									<span class="flex items-center gap-2">
										<Progress class="h-2 w-16" value={50} />
										Optimizing...
									</span>
								{:else}
									<Zap class="mr-2 h-4 w-4" />
									Optimize
								{/if}
							</Button>
						</div>
					</CardHeader>
					<CardContent>
						<div class="aspect-[9/12] w-full overflow-hidden rounded border bg-muted">
							<embed
								src={URL.createObjectURL(pdfFile.optimizedFile ?? pdfFile.file)}
								type="application/pdf"
								class="h-full min-h-[300px] w-full"
							/>
						</div>

						{#if pdfFile.optimizedFile}
							<div class="bg-success/10 text-success mt-3 flex items-center gap-2 rounded-md p-3">
								<FileCheck class="h-4 w-4 flex-shrink-0" />
								<span>Optimized version ready (blank pages removed)</span>
							</div>
						{/if}
					</CardContent>
				</Card>
			{/each}
		</div>
	{/if}
</div>
