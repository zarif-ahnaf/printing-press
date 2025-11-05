<script lang="ts">
	import { onMount } from 'svelte';
	import { Label } from '$lib/components/ui/label';
	import { Input } from '$lib/components/ui/input';
	import * as Select from '$lib/components/ui/select';
	import * as Card from '$lib/components/ui/card';
	import { Button } from '$lib/components/ui/button';
	import * as Alert from '$lib/components/ui/alert';
	import * as Dialog from '$lib/components/ui/dialog';
	import {
		Upload,
		FileText,
		Printer,
		CreditCard,
		LoaderCircle,
		TriangleAlert,
		CircleCheck,
		X,
		ArrowRight,
		Settings2
	} from 'lucide-svelte';
	import { client } from '$lib/client';
	import { token } from '$lib/stores/token.svelte';

	// Define TypeScript interfaces matching API responses
	interface User {
		id: number;
		username: string;
		first_name: string | null;
		last_name: string | null;
		balance?: number;
	}

	function getDisplayName(user: User): string {
		return user.first_name && user.last_name
			? `${user.first_name} ${user.last_name}`
			: user.username;
	}

	interface Printer {
		id: number;
		name: string;
		is_color: boolean;
		simplex_charge: number;
		duplex_charge: number;
		decomissioned: boolean;
		image: string | null; // Added image field
	}

	// Updated interface to include printer objects
	interface PrinterArrangement {
		id: number;
		color_printer: number | null;
		bw_printer: number | null;
		decomissioned: boolean;
		// Optional printer object properties
		color_printer_object?: Printer | null;
		bw_printer_object?: Printer | null;
	}

	// File entry interface
	interface FileEntry {
		id: string;
		file: File;
		pageCount: number | null;
		loading: boolean;
		error: string | null;
	}

	// State variables
	let files: FileEntry[] = $state([]);
	let users: User[] = $state([]);
	let printers: Printer[] = $state([]);
	let arrangements: PrinterArrangement[] = $state([]);
	let selectedUser: User | null = $state(null);
	let selectedArrangement: PrinterArrangement | null = $state(null);
	let copies: number = $state(1);
	let isColorPrint: boolean = $state(false);
	let isProcessing: boolean = $state(false);
	let error: string | null = $state(null);
	let success: string | null = $state(null);
	let isDragging: boolean = $state(false);
	let printMode: 'single-sided' | 'double-sided' = $state('single-sided');
	let isArrangementModalOpen: boolean = $state(false); // Modal state

	// Helper function to get auth headers
	function getAuthHeaders(): Record<string, string> {
		const token = localStorage.getItem('token');
		if (token) {
			return {
				Authorization: `Bearer ${token}`
			};
		}
		return {};
	}

	// Get the printer to use based on arrangement and color selection
	function getActivePrinter(): Printer | null {
		if (!selectedArrangement || !printers.length) return null;

		const printerId = isColorPrint
			? selectedArrangement.color_printer
			: selectedArrangement.bw_printer;

		if (!printerId) return null;

		return printers.find((p) => p.id === printerId) || null;
	}

	// Calculate total pages across all files
	let totalDocumentPages = $derived(
		files.reduce((sum, file) => {
			if (file.pageCount && !file.error) return sum + file.pageCount;
			return sum;
		}, 0)
	);

	// Calculate total price based on document pages * copies
	function calculateTotalPrice(): string {
		const activePrinter = getActivePrinter();
		if (!activePrinter || totalDocumentPages === 0 || copies === 0) return '0.00';

		const chargePerPage =
			printMode === 'double-sided' ? activePrinter.duplex_charge : activePrinter.simplex_charge;

		return (totalDocumentPages * copies * chargePerPage).toFixed(2);
	}

	let totalPrice = $derived(calculateTotalPrice());
	let activePrinter = $derived(getActivePrinter());
	let isCountingPages = $derived(files.some((file) => file.loading));
	let hasFileErrors = $derived(files.some((file) => file.error));

	// Fetch users, printers, and arrangements
	$effect(() => {
		async function loadData() {
			isProcessing = true;
			try {
				// Fetch users
				const usersResponse = await client.GET('/api/users/', {
					headers: {
						Authorization: `Bearer ${token.value}`
					}
				});
				if (usersResponse.error) throw new Error('Failed to fetch users');
				const usersData = usersResponse.data as User[];

				// Fetch balances for each user
				const usersWithBalances = await Promise.all(
					usersData.map(async (user) => {
						const balanceResponse = await client.GET('/api/admin/balance/{username}', {
							headers: {
								Authorization: `Bearer ${token.value}`
							},
							params: {
								path: {
									username: user.username
								}
							}
						});
						if (balanceResponse.error) {
							throw new Error('Failed to fetch user balance');
						}
						if (balanceResponse.data) {
							return {
								...user,
								balance: balanceResponse.data?.balance
									? parseFloat(balanceResponse.data.balance)
									: 0
							};
						}
						return { ...user, balance: 0 };
					})
				);
				users = usersWithBalances;

				// Fetch active printers
				const printersResponse = await client.GET('/api/printers/', {
					headers: {
						Authorization: `Bearer ${token.value}`
					}
				});

				if (printersResponse.error) throw new Error('Failed to fetch printers');
				const printersData = printersResponse.data as Printer[];
				printers = printersData.filter((p) => !p.decomissioned);

				// Fetch active arrangements
				const arrangementsResponse = await client.GET('/api/printers/arrangement/', {
					headers: {
						Authorization: `Bearer ${token.value}`
					}
				});

				if (arrangementsResponse.error) throw new Error('Failed to fetch printer arrangements');
				const arrangementsData = arrangementsResponse.data as PrinterArrangement[];

				// Map printers to arrangements for easier access
				arrangements = arrangementsData
					.filter((a) => !a.decomissioned)
					.map((arr) => {
						const colorPrinter = arr.color_printer
							? printers.find((p) => p.id === arr.color_printer)
							: null;
						const bwPrinter = arr.bw_printer ? printers.find((p) => p.id === arr.bw_printer) : null;

						return {
							...arr,
							color_printer_object: colorPrinter,
							bw_printer_object: bwPrinter
						};
					});
			} catch (err) {
				error = err instanceof Error ? err.message : 'Failed to load users and printers';
				console.error(err);
			} finally {
				isProcessing = false;
			}
		}

		loadData();
	});

	// Set up drag and drop event listeners
	onMount(() => {
		const handleDragOver = (e: DragEvent) => {
			e.preventDefault();
			isDragging = true;
		};

		const handleDragLeave = (e: DragEvent) => {
			e.preventDefault();
			const target = e.relatedTarget as Node | null;
			if (e.currentTarget && (!target || !(e.currentTarget as Node).contains(target))) {
				isDragging = false;
			}
		};

		const handleDrop = (e: DragEvent) => {
			e.preventDefault();
			isDragging = false;

			const files = e.dataTransfer?.files;
			if (files && files.length > 0) {
				handleFiles(Array.from(files));
			}
		};

		window.addEventListener('dragover', handleDragOver as unknown as EventListener);
		window.addEventListener('dragleave', handleDragLeave as unknown as EventListener);
		window.addEventListener('drop', handleDrop as unknown as EventListener);

		return () => {
			window.removeEventListener('dragover', handleDragOver as unknown as EventListener);
			window.removeEventListener('dragleave', handleDragLeave as unknown as EventListener);
			window.removeEventListener('drop', handleDrop as unknown as EventListener);
		};
	});

	// Handle multiple files selection
	function handleFiles(fileList: File[]) {
		const pdfFiles = fileList.filter((file) => file.type === 'application/pdf');
		const nonPdfFiles = fileList.filter((file) => file.type !== 'application/pdf');

		if (nonPdfFiles.length > 0) {
			error = `Skipped ${nonPdfFiles.length} non-PDF file${nonPdfFiles.length > 1 ? 's' : ''}. Please select only PDF files.`;
		}

		if (pdfFiles.length === 0) return;

		error = null;
		success = null;

		// Add each PDF file
		pdfFiles.forEach((file) => addFile(file));
	}

	// Add a new file and start counting pages
	async function addFile(file: File) {
		const id = crypto.randomUUID();
		const newFile: FileEntry = {
			id,
			file,
			pageCount: null,
			loading: true,
			error: null
		};

		files = [...files, newFile];

		try {
			const pageCount = await countPagesForFile(file);
			files = files.map((f) => (f.id === id ? { ...f, pageCount, loading: false } : f));
		} catch (err) {
			files = files.map((f) =>
				f.id === id
					? {
							...f,
							loading: false,
							error: err instanceof Error ? err.message : 'Failed to count pages'
						}
					: f
			);
		}
	}

	// Count pages in a single PDF file
	async function countPagesForFile(file: File): Promise<number> {
		const formData = new FormData();
		formData.append('file', file);

		const { data, error } = await client.POST('/api/count/pdf/pages/count-pages', {
			headers: {
				Authorization: `Bearer ${token.value}`
			},
			body: formData as any
		});

		if (error) {
			throw new Error(error || 'Failed to count pages in PDF');
		}

		if (data?.page_count) {
			return data.page_count;
		}

		throw new Error('Invalid response from page count API');
	}

	// Handle file input change
	function handleFileChange(event: Event) {
		const input = event.target as HTMLInputElement;
		const files = input.files;
		if (files && files.length > 0) {
			handleFiles(Array.from(files));
			// Reset input value to allow re-uploading same file
			input.value = '';
		}
	}

	// Remove a specific file
	function removeFile(id: string) {
		files = files.filter((file) => file.id !== id);
	}

	// Handle copies input
	function handleCopiesInput(event: Event) {
		const input = event.target as HTMLInputElement;
		const value = parseInt(input.value);
		copies = isNaN(value) || value < 1 ? 1 : value;
	}

	// Handle form submission (charge only)
	async function handleSubmit() {
		if (
			files.length === 0 ||
			isCountingPages ||
			hasFileErrors ||
			!selectedUser ||
			!selectedArrangement ||
			copies === 0 ||
			!activePrinter ||
			totalDocumentPages === 0
		) {
			error = 'Please fill in all required fields and ensure all files are processed successfully';
			return;
		}

		isProcessing = true;
		error = null;
		success = null;

		try {
			// Calculate charge amount based on total document pages * copies
			const chargePerPage =
				printMode === 'double-sided' ? activePrinter.duplex_charge : activePrinter.simplex_charge;
			const totalAmount = totalDocumentPages * copies * chargePerPage;

			const chargeResponse = await client.POST(`/api/charge/{username}`, {
				headers: {
					Authorization: `Bearer ${token.value}`
				},
				params: {
					path: {
						username: selectedUser.username
					}
				},
				body: {
					amount: totalAmount,
					description: `${isColorPrint ? 'Color' : 'B/W'} ${printMode} print for ${files.length} file${files.length > 1 ? 's' : ''} (${totalDocumentPages} pages × ${copies} copies)`
				}
			});

			if (chargeResponse.error) {
				throw new Error('Failed to charge wallet');
			}

			const chargeData = chargeResponse.data;
			success =
				`Successfully charged ৳${chargeData.charged_amount.toFixed(2)}. ` +
				`Remaining balance: ৳${chargeData.remaining_balance.toFixed(2)}`;

			// Reset form
			files = [];
			selectedUser = null;
			selectedArrangement = null;
			copies = 1;
			isColorPrint = false;
		} catch (err) {
			error = err instanceof Error ? err.message : 'An error occurred while charging the wallet';
			console.error(err);
		} finally {
			isProcessing = false;
		}
	}

	// Handle print mode change
	function changePrintMode(mode: 'single-sided' | 'double-sided') {
		printMode = mode;
	}

	// Handle color mode toggle
	function toggleColorMode() {
		isColorPrint = !isColorPrint;
	}

	// Handle arrangement selection in modal
	function selectArrangement(arrangement: PrinterArrangement) {
		selectedArrangement = arrangement;
	}
</script>

<!-- Global drag and drop overlay/modal -->
{#if isDragging}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
		<div class="rounded-xl border border-dashed border-primary bg-card p-8 shadow-lg">
			<div class="text-center">
				<Upload class="mx-auto mb-4 h-12 w-12 text-primary" />
				<h3 class="mb-1 text-lg font-semibold">Drop PDF files here</h3>
				<p class="text-sm text-muted-foreground">Release to upload</p>
			</div>
		</div>
	</div>
{/if}

<!-- Arrangement Selection Modal - FULL PAGE VERSION -->
<Dialog.Root open={isArrangementModalOpen} onOpenChange={(open) => (isArrangementModalOpen = open)}>
	<Dialog.Trigger class="hidden" />

	<Dialog.Portal>
		<Dialog.Overlay class="fixed inset-0 z-40 animate-in bg-black/50 backdrop-blur-sm fade-in" />

		<Dialog.Content
			class="fixed inset-0 z-50 animate-in bg-background sm:inset-auto sm:top-1/2 sm:left-1/2 sm:w-full sm:max-w-2xl sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-xl sm:border sm:shadow-lg"
		>
			<Card.Root class="m-2 flex h-full flex-col sm:h-auto sm:rounded-xl">
				<Card.Header
					class="sticky top-0 z-10 border-b bg-background/95 p-4 backdrop-blur supports-[backdrop-filter]:bg-background/60"
				>
					<div class="flex items-center justify-between">
						<Card.Title class="text-lg font-semibold">Select Printer Arrangement</Card.Title>
					</div>
					<p class="mt-1 text-sm text-muted-foreground">
						Select a printer arrangement to use for your print job.
					</p>
				</Card.Header>

				<Card.Content class="min-h-0 flex-1 overflow-y-auto p-4">
					{#if arrangements.length === 0}
						<div class="flex flex-col items-center justify-center py-16 text-center">
							<Settings2 class="mb-4 h-10 w-10 text-muted-foreground" />
							<h3 class="mb-1 text-lg font-medium">No Printer Arrangements Found</h3>
							<p class="text-muted-foreground">
								No active printer arrangements are available. Please contact your system
								administrator to set up printers.
							</p>
							<Button
								variant="outline"
								class="mt-6"
								onclick={() => (isArrangementModalOpen = false)}
							>
								Go Back
							</Button>
						</div>
					{:else}
						<div class="space-y-6">
							{#each arrangements as arrangement}
								<div
									class="rounded-lg border p-4 transition-all duration-200 hover:shadow-md {selectedArrangement?.id ===
									arrangement.id
										? 'border-primary bg-primary/10 shadow-md ring-2 ring-primary/20'
										: 'border-border'}"
									onclick={() => {
										if (selectedArrangement?.id === arrangement.id) {
											// Double-click to unselect
											selectedArrangement = null;
										} else {
											// Single-click to select
											selectedArrangement = arrangement;
										}
									}}
									ondblclick={() => {
										if (selectedArrangement?.id === arrangement.id) {
											selectedArrangement = null;
										}
									}}
								>
									<!-- Arrangement Header -->
									<div class="mb-4 flex items-center justify-between">
										<h3 class="font-semibold">Arrangement #{arrangement.id}</h3>
										{#if selectedArrangement?.id === arrangement.id}
											<div class="rounded-full bg-primary/10 px-2 py-0.5">
												<span class="text-xs font-medium text-primary">Selected</span>
											</div>
										{/if}
									</div>

									<!-- B/W Printer Section -->
									<div class="mb-5">
										<div class="mb-2 flex items-center">
											<!-- Actual Printer Image -->
											{#if arrangement.bw_printer_object?.image}
												<img
													src={arrangement.bw_printer_object.image}
													alt="B/W Printer"
													class="mr-3 h-10 w-10 rounded-md object-cover"
												/>
											{:else}
												<!-- Fallback icon if no image -->
												<div
													class="mr-3 flex h-10 w-10 items-center justify-center rounded-md bg-blue-500"
												>
													<Printer class="h-5 w-5 text-white" />
												</div>
											{/if}
											<div class="flex-1">
												<p class="font-medium">
													{arrangement.bw_printer_object?.name || 'Not assigned'}
													{#if arrangement.bw_printer_object?.decomissioned}
														<span class="ml-1 text-xs text-destructive">(Decommissioned)</span>
													{/if}
												</p>
											</div>
										</div>

										<!-- Pricing Lines -->
										<div class="ml-14 space-y-1">
											<div class="flex items-center justify-between">
												<span class="text-muted-foreground">Simplex Charge:</span>
												<span class="font-medium"
													>৳{arrangement.bw_printer_object?.simplex_charge.toFixed(2) ||
														'N/A'}</span
												>
											</div>
											<div class="flex items-center justify-between">
												<span class="text-muted-foreground">Duplex Charge:</span>
												<span class="font-medium"
													>৳{arrangement.bw_printer_object?.duplex_charge.toFixed(2) || 'N/A'}</span
												>
											</div>
										</div>
									</div>

									<!-- Color Printer Section -->
									<div>
										<div class="mb-2 flex items-center">
											<!-- Actual Printer Image -->
											{#if arrangement.color_printer_object?.image}
												<img
													src={arrangement.color_printer_object.image}
													alt="Color Printer"
													class="mr-3 h-10 w-10 rounded-md object-cover"
												/>
											{:else}
												<!-- Fallback icon if no image -->
												<div
													class="mr-3 flex h-10 w-10 items-center justify-center rounded-md bg-purple-500"
												>
													<Printer class="h-5 w-5 text-white" />
												</div>
											{/if}
											<div class="flex-1">
												<p class="font-medium">
													{arrangement.color_printer_object?.name || 'Not assigned'}
													{#if arrangement.color_printer_object?.decomissioned}
														<span class="ml-1 text-xs text-destructive">(Decommissioned)</span>
													{/if}
												</p>
											</div>
										</div>

										<!-- Pricing Lines -->
										<div class="ml-14 space-y-1">
											<div class="flex items-center justify-between">
												<span class="text-muted-foreground">Simplex Charge:</span>
												<span class="font-medium"
													>৳{arrangement.color_printer_object?.simplex_charge.toFixed(2) ||
														'N/A'}</span
												>
											</div>
											<div class="flex items-center justify-between">
												<span class="text-muted-foreground">Duplex Charge:</span>
												<span class="font-medium"
													>৳{arrangement.color_printer_object?.duplex_charge.toFixed(2) ||
														'N/A'}</span
												>
											</div>
										</div>
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</Card.Content>

				<Card.Footer
					class="sticky bottom-0 z-10 border-t bg-background/95 p-4 backdrop-blur supports-[backdrop-filter]:bg-background/60"
				>
					<Button
						class="w-full"
						onclick={() => {
							if (selectedArrangement) {
								isArrangementModalOpen = false;
							}
						}}
						disabled={!selectedArrangement}
					>
						{#if selectedArrangement}
							<span class="flex items-center">
								<ArrowRight class="mr-2 h-4 w-4" />
								Use Selected Arrangement
							</span>
						{:else}
							<span>Select an Arrangement First</span>
						{/if}
					</Button>
				</Card.Footer>
			</Card.Root>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
<div class="mx-auto max-w-md p-4">
	<Card.Root class="rounded-xl border shadow-sm">
		<Card.Content class="space-y-4 p-4">
			<!-- File Upload Section -->
			<div class="space-y-2">
				<Label>PDF Files</Label>
				<!-- Fixed accessibility: Using Button component instead of div with click handler -->
				<Button
					variant="outline"
					class="flex min-h-[120px] w-full flex-col items-center justify-center rounded-lg border-2 border-dashed p-4 text-center transition-colors hover:bg-accent/50 {isDragging
						? 'border-primary bg-accent'
						: ''}"
					onclick={() => document.getElementById('file-input')?.click()}
				>
					{#if files.length === 0}
						<div class="space-y-3">
							<Upload class="mx-auto h-8 w-8 text-muted-foreground" />
							<div>
								<p class="text-sm font-medium text-foreground">Drag & drop PDF files here</p>
								<p class="mt-1 text-xs text-muted-foreground">or click to browse</p>
							</div>
						</div>
					{:else}
						<div class="max-h-60 w-full overflow-y-auto">
							{#each files as file (file.id)}
								<div class="mb-2 flex items-center justify-between rounded-md border p-2 last:mb-0">
									<div class="flex items-center gap-2">
										<FileText class="h-5 w-5 shrink-0 text-muted-foreground" />
										<div class="min-w-0">
											<p class="truncate text-sm font-medium">{file.file.name}</p>
											{#if file.loading}
												<p class="text-xs text-muted-foreground">Counting pages...</p>
											{:else if file.error}
												<p class="text-xs text-destructive">{file.error}</p>
											{:else if file.pageCount !== null}
												<p class="text-xs text-muted-foreground">
													{file.pageCount} page{file.pageCount === 1 ? '' : 's'}
												</p>
											{/if}
										</div>
									</div>
									<Button
										variant="ghost"
										size="icon"
										class="h-8 w-8"
										onclick={(e) => {
											e.stopPropagation();
											removeFile(file.id);
										}}
									>
										<X class="h-4 w-4" />
									</Button>
								</div>
							{/each}
						</div>
						<Button
							variant="outline"
							size="sm"
							class="mt-3 w-full"
							onclick={(e) => {
								e.stopPropagation();
								document.getElementById('file-input')?.click();
							}}
						>
							Add More Files
						</Button>
					{/if}
				</Button>
				<input
					id="file-input"
					type="file"
					accept=".pdf"
					multiple
					onchange={handleFileChange}
					class="hidden"
				/>
			</div>

			<!-- Copies Input -->
			<div class="space-y-2">
				<Label for="copies">Number of Copies</Label>
				<Input
					id="copies"
					type="number"
					min="1"
					value={copies}
					oninput={handleCopiesInput}
					placeholder="Enter number of copies"
					class="w-full"
				/>
			</div>

			<!-- User Selection -->
			<div class="space-y-2">
				<Label for="user-select">User</Label>
				<Select.Root
					type="single"
					value={selectedUser?.id?.toString() || ''}
					onValueChange={(value: string) => {
						if (!value) {
							selectedUser = null;
							return;
						}
						const userId = parseInt(value);
						selectedUser = users.find((u) => u.id === userId) || null;
					}}
				>
					<Select.Trigger class="w-full">
						<span class="text-muted-foreground">
							{selectedUser
								? getDisplayName(selectedUser) +
									' (৳' +
									(selectedUser.balance || 0).toFixed(2) +
									')'
								: 'Select user'}
						</span>
					</Select.Trigger>
					<Select.Content>
						{#each users as user}
							<Select.Item value={user.id.toString()}>
								{getDisplayName(user)} (৳{(user.balance || 0).toFixed(2)})
							</Select.Item>
						{/each}
					</Select.Content>
				</Select.Root>
			</div>

			<!-- Printer Arrangement Selection - MODAL TRIGGER -->
			<div class="space-y-2">
				<Label>Printer Arrangement</Label>
				<Button
					variant="outline"
					class="w-full justify-between"
					onclick={() => (isArrangementModalOpen = true)}
				>
					<span class="text-muted-foreground">
						{selectedArrangement ? `Arrangement #${selectedArrangement.id}` : 'Select arrangement'}
					</span>
					<ArrowRight class="h-4 w-4 text-muted-foreground" />
				</Button>
			</div>

			<!-- Color Mode Toggle -->
			{#if selectedArrangement}
				<div class="space-y-2">
					<Label>Print Type</Label>
					<div class="inline-flex rounded-md border">
						<Button
							variant={isColorPrint ? 'outline' : 'default'}
							size="sm"
							onclick={toggleColorMode}
							class="rounded-r-none"
						>
							<FileText class="mr-2 h-4 w-4" />
							Black & White
						</Button>
						<Button
							variant={isColorPrint ? 'default' : 'outline'}
							size="sm"
							onclick={toggleColorMode}
							class="rounded-l-none"
						>
							<Printer class="mr-2 h-4 w-4" />
							Color
						</Button>
					</div>
				</div>
			{/if}

			<!-- Print Mode Toggle -->
			<div class="space-y-2">
				<Label>Print Mode</Label>
				<div class="inline-flex rounded-md border">
					<Button
						variant={printMode === 'single-sided' ? 'default' : 'outline'}
						size="sm"
						onclick={() => changePrintMode('single-sided')}
						class="rounded-r-none"
					>
						<FileText class="mr-2 h-4 w-4" />
						Single-sided
					</Button>
					<Button
						variant={printMode === 'double-sided' ? 'default' : 'outline'}
						size="sm"
						onclick={() => changePrintMode('double-sided')}
						class="rounded-l-none"
					>
						<FileText class="mr-2 h-4 w-4" />
						Double-sided
					</Button>
				</div>
			</div>

			<!-- Pricing Summary -->
			<div class="rounded-lg bg-muted/30 p-3">
				<h3 class="mb-2 block text-sm font-medium">Pricing Summary</h3>
				{#if isCountingPages}
					<div class="flex justify-center py-3">
						<LoaderCircle class="h-5 w-5 animate-spin text-primary" />
					</div>
				{:else if totalDocumentPages > 0 && selectedArrangement && activePrinter}
					<div class="space-y-2">
						<div class="flex justify-between">
							<span class="text-sm text-muted-foreground">Total Files:</span>
							<span class="font-medium">{files.length}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-sm text-muted-foreground">Total Pages:</span>
							<span class="font-medium">{totalDocumentPages}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-sm text-muted-foreground">Copies:</span>
							<span class="font-medium">{copies}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-sm text-muted-foreground">Print Type:</span>
							<span class="font-medium">{isColorPrint ? 'Color' : 'Black & White'}</span>
						</div>
						<div class="flex justify-between">
							<span class="text-sm text-muted-foreground">Print Mode:</span>
							<span class="font-medium"
								>{printMode === 'single-sided' ? 'Single-sided' : 'Double-sided'}</span
							>
						</div>
						<div class="flex justify-between">
							<span class="text-sm text-muted-foreground">Cost per page:</span>
							<span class="font-medium">
								৳{(printMode === 'double-sided'
									? activePrinter.duplex_charge
									: activePrinter.simplex_charge
								).toFixed(2)}
							</span>
						</div>
						<div class="flex justify-between">
							<span class="text-sm text-muted-foreground">Total Price:</span>
							<span class="font-medium text-primary">৳{totalPrice}</span>
						</div>
					</div>
				{:else}
					<p class="py-2 text-center text-sm text-muted-foreground">
						Upload PDF files to see pricing
					</p>
				{/if}
			</div>

			<!-- Error and Success Messages -->
			{#if error}
				<Alert.Root variant="destructive">
					<TriangleAlert class="h-4 w-4" />
					<Alert.Title>Error</Alert.Title>
					<Alert.Description>{error}</Alert.Description>
				</Alert.Root>
			{/if}

			{#if success}
				<Alert.Root variant="default" class="border-green-500 bg-green-50 text-green-800">
					<CircleCheck class="h-4 w-4 text-green-500" />
					<Alert.Title>Success</Alert.Title>
					<Alert.Description>{success}</Alert.Description>
				</Alert.Root>
			{/if}
		</Card.Content>

		<Card.Footer class="p-4">
			<Button
				class="w-full"
				disabled={isProcessing ||
					files.length === 0 ||
					isCountingPages ||
					hasFileErrors ||
					!selectedUser ||
					!selectedArrangement ||
					copies === 0 ||
					!activePrinter ||
					totalDocumentPages === 0}
				onclick={handleSubmit}
			>
				{#if isProcessing}
					<span class="flex items-center">
						<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
						Processing...
					</span>
				{:else}
					<span class="flex items-center">
						<CreditCard class="mr-2 h-4 w-4" />
						Charge User
					</span>
				{/if}
			</Button>
		</Card.Footer>
	</Card.Root>
</div>
