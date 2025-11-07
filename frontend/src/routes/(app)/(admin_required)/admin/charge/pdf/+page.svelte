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
		Settings2,
		User,
		Search,
		Info
	} from 'lucide-svelte';
	import { client } from '$lib/client';
	import { token } from '$lib/stores/token.svelte';
	import type { ComponentType } from 'svelte';
	// Define TypeScript interfaces matching API responses
	interface User {
		id: number;
		username: string;
		first_name: string | null;
		last_name: string | null;
		balance?: number;
		email: string;
		is_staff: boolean;
		is_superuser: boolean;
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
	// Updated QueueItem interface to make printer_id optional
	interface QueueItem {
		id: number;
		file: string;
		processed: boolean;
		created_at: string;
		user: string;
		user_id: number;
		page_count: number | null;
		print_mode: 'single-sided' | 'double-sided';
		printer_id?: number | null; // Made optional to match API response
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
	let allUsers: User[] = $state([]); // Store all users for resetting search
	let printers: Printer[] = $state([]);
	let arrangements: PrinterArrangement[] = $state([]);
	let queueData: QueueItem[] = $state([]);
	let currentUser: User | null = $state(null);
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
	let isUserModalOpen: boolean = $state(false); // User modal state
	let userSearchQuery: string = $state(''); // User search query state
	let userSearchLoading: boolean = $state(false); // Loading state for user search
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
	// Fetch users, printers, arrangements and queue data
	$effect(() => {
		async function loadData() {
			isProcessing = true;
			try {
				// Fetch current user info
				const currentUserResponse = await client.GET('/api/user/', {
					headers: {
						Authorization: `Bearer ${token.value}`
					}
				});
				if (currentUserResponse.error) throw new Error('Failed to fetch current user');
				currentUser = currentUserResponse.data as User;
				// Fetch all users and their balances
				await fetchUsers();
				// Store all users for resetting search later
				allUsers = [...users];
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
				// Fetch queue data to show printer status
				const queueResponse = await client.GET('/api/admin/queue/', {
					headers: {
						Authorization: `Bearer ${token.value}`
					},
					params: {
						query: {
							include_processed: false
						}
					}
				});
				if (queueResponse.error) throw new Error('Failed to fetch queue data');
				queueData = queueResponse.data?.queue || [];
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
	// Helper function to check if both printers in an arrangement are the same
	function isSamePrinter(arrangement: PrinterArrangement): boolean {
		return (
			arrangement.color_printer !== null &&
			arrangement.bw_printer !== null &&
			arrangement.color_printer === arrangement.bw_printer
		);
	}
	// Handle user selection in modal
	function selectUser(user: User) {
		selectedUser = user;
	}
	// Fetch users from backend with optional search query
	async function fetchUsers(searchQuery: string = '') {
		userSearchLoading = true;
		try {
			// Fetch users with search query if provided
			const usersResponse = await client.GET('/api/users/', {
				headers: {
					Authorization: `Bearer ${token.value}`
				},
				params: {
					query: {
						name: searchQuery || undefined // Pass search query to backend or undefined if empty
					}
				}
			});
			if (usersResponse.error) throw new Error('Failed to fetch users');
			const usersData = usersResponse.data as User[];
			// Fetch balances for each user
			const usersWithBalances = await Promise.all(
				usersData.map(async (user) => {
					try {
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
						if (balanceResponse.data) {
							return {
								...user,
								balance: balanceResponse.data?.balance
									? parseFloat(balanceResponse.data.balance)
									: 0
							};
						}
						return { ...user, balance: 0 };
					} catch (err) {
						console.warn(`Failed to fetch balance for user ${user.username}:`, err);
						return { ...user, balance: 0 };
					}
				})
			);
			users = usersWithBalances;
			return usersWithBalances;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to fetch users';
			console.error('Error fetching users:', err);
			return [];
		} finally {
			userSearchLoading = false;
		}
	}
	// Effect to handle user search when query changes
	$effect(() => {
		// Only fetch when the user modal is open and we have a search query
		if (isUserModalOpen && userSearchQuery.trim() !== '') {
			fetchUsers(userSearchQuery.trim());
		} else if (isUserModalOpen && userSearchQuery.trim() === '') {
			// Show all users when search query is cleared
			users = [...allUsers];
		}
	});
	// Effect to reset search when modal closes
	$effect(() => {
		if (!isUserModalOpen) {
			userSearchQuery = '';
		}
	});
	// Helper functions for the enhanced arrangement modal
	function getTotalPrinterCount(arrangement: PrinterArrangement): number {
		if (!arrangement) return 0;
		if (isSamePrinter(arrangement)) return 1;
		const hasBw = arrangement.bw_printer !== null && arrangement.bw_printer_object;
		const hasColor = arrangement.color_printer !== null && arrangement.color_printer_object;
		return (hasBw ? 1 : 0) + (hasColor ? 1 : 0);
	}
	// Get available features for an arrangement
	function getAvailableFeatures(arrangement: PrinterArrangement): string[] {
		const features: string[] = [];
		if (arrangement.bw_printer_object && !arrangement.bw_printer_object.decomissioned) {
			features.push('B/W printing');
		}
		if (arrangement.color_printer_object && !arrangement.color_printer_object.decomissioned) {
			features.push('Color printing');
		}
		// Add duplex capability if any printer supports it
		if (
			(arrangement.bw_printer_object?.duplex_charge || 0) > 0 ||
			(arrangement.color_printer_object?.duplex_charge || 0) > 0
		) {
			features.push('Double-sided');
		}
		return features;
	}
	// Get minimum price per page across all options
	function getMinPrice(arrangement: PrinterArrangement): number {
		const prices = [];
		if (arrangement.bw_printer_object) {
			prices.push(arrangement.bw_printer_object.simplex_charge);
			prices.push(arrangement.bw_printer_object.duplex_charge);
		}
		if (arrangement.color_printer_object) {
			prices.push(arrangement.color_printer_object.simplex_charge);
			prices.push(arrangement.color_printer_object.duplex_charge);
		}
		return Math.min(...prices.filter((p) => p > 0));
	}
	// Get printer status text
	function getPrinterStatus(printer: Printer | null | undefined): string {
		if (!printer) return 'Not assigned';
		if (printer.decomissioned) return 'Decommissioned';
		// Check if this printer has pending jobs
		const pendingJobs = queueData.filter((q) => q.printer_id === printer.id && !q.processed).length;
		if (pendingJobs > 10) return 'Heavy load';
		if (pendingJobs > 5) return 'Moderate load';
		if (pendingJobs > 0) return 'Light load';
		return 'Available';
	}
	// Get printer job count
	function getPrinterPendingJobCount(printerId: number | null): number {
		if (!printerId) return 0;
		return queueData.filter((q) => q.printer_id === printerId && !q.processed).length;
	}
	// Get printer reliability metrics (mock for now)
	function getPrinterReliability(printer: Printer | null | undefined): {
		completionRate: number;
		avgTime: string;
	} {
		if (!printer) return { completionRate: 0, avgTime: 'N/A' };
		// In a real app, this would be fetched from analytics endpoints
		return {
			completionRate: 98.5 - Math.random() * 5,
			avgTime: `${(1.5 + Math.random() * 3).toFixed(1)} min`
		};
	}
	// Estimate cost for current document
	function estimateCostForArrangement(arrangement: PrinterArrangement): {
		bwCost: number;
		colorCost: number;
	} {
		if (
			totalDocumentPages === 0 ||
			copies === 0 ||
			!arrangement.bw_printer_object ||
			!arrangement.color_printer_object
		) {
			return { bwCost: 0, colorCost: 0 };
		}
		const bwSimplexCost =
			totalDocumentPages * copies * arrangement.bw_printer_object.simplex_charge;
		const colorDuplexCost =
			totalDocumentPages * copies * arrangement.color_printer_object.duplex_charge;
		return {
			bwCost: parseFloat(bwSimplexCost.toFixed(2)),
			colorCost: parseFloat(colorDuplexCost.toFixed(2))
		};
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
<!-- Enhanced Arrangement Selection Modal -->
<Dialog.Root open={isArrangementModalOpen} onOpenChange={(open) => (isArrangementModalOpen = open)}>
	<Dialog.Trigger class="hidden" />
	<Dialog.Portal>
		<Dialog.Overlay
			class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity duration-300 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0"
		/>
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 max-h-[90vh] w-full max-w-3xl -translate-x-1/2 -translate-y-1/2 rounded-2xl border bg-card shadow-xl transition-all duration-300 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-100 sm:w-full"
		>
			<div class="flex h-full flex-col">
				<div class="flex items-center justify-between border-b p-6 pb-5">
					<div>
						<Dialog.Title class="text-2xl font-bold text-foreground">
							Select Printer Arrangement
						</Dialog.Title>
						<p class="mt-1 text-sm text-muted-foreground">
							Choose the perfect printing setup for your needs
						</p>
					</div>
				</div>
				<div class="flex-1 overflow-y-auto p-6 pt-2">
					<div class="mb-6 flex items-center space-x-3 rounded-xl bg-muted/30 p-3">
						<div class="rounded-lg bg-primary/10 p-2">
							<Info class="h-5 w-5 text-primary" />
						</div>
						<p class="text-sm text-muted-foreground">
							Each arrangement includes both black & white and color printers. Select the
							arrangement that best matches your printing needs and budget.
						</p>
					</div>
					{#if arrangements.length === 0}
						<div class="flex flex-col items-center justify-center py-16 text-center">
							<div class="mb-4 rounded-full bg-muted p-4">
								<Settings2 class="h-7 w-7 text-muted-foreground" />
							</div>
							<h3 class="mb-2 text-xl font-semibold">No Printer Arrangements Found</h3>
							<p class="max-w-md px-4 text-muted-foreground">
								No active printer arrangements are available. Please contact your system
								administrator to set up printers and create arrangements.
							</p>
							<Button
								variant="outline"
								class="mt-6 px-6"
								onclick={() => (isArrangementModalOpen = false)}
							>
								Go Back
							</Button>
						</div>
					{:else}
						<div class="space-y-4">
							{#each arrangements as arrangement (arrangement.id)}
								<div
									role="button"
									tabindex="0"
									class="group relative cursor-pointer overflow-hidden rounded-2xl border bg-card transition-all duration-200 hover:-translate-y-[2px] hover:shadow-lg {selectedArrangement?.id ===
									arrangement.id
										? 'border-primary shadow-xl ring-2 ring-primary/30'
										: 'border-border hover:border-primary/20'}"
									onclick={() => {
										if (selectedArrangement?.id === arrangement.id) {
											selectedArrangement = null;
										} else {
											selectedArrangement = arrangement;
										}
									}}
									onkeydown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.preventDefault();
											if (selectedArrangement?.id === arrangement.id) {
												selectedArrangement = null;
											} else {
												selectedArrangement = arrangement;
											}
										}
									}}
								>
									<!-- Selection indicator -->
									{#if selectedArrangement?.id === arrangement.id}
										<div
											class="absolute -top-2 -right-2 rounded-full border-2 border-background bg-primary p-2 shadow-lg"
										>
											<CircleCheck class="h-5 w-5 text-primary-foreground" />
										</div>
									{/if}
									<div class="p-5">
										<!-- Arrangement Header -->
										<div class="mb-5 flex flex-col sm:flex-row sm:items-center sm:justify-between">
											<div>
												<div class="mb-1 flex items-center space-x-2">
													<h3 class="text-lg font-bold">Arrangement #{arrangement.id}</h3>
													{#if arrangement.id <= 3}
														<span
															class="rounded-full bg-blue-500/10 px-2 py-0.5 text-xs font-medium text-blue-700"
														>
															Recommended
														</span>
													{/if}
												</div>
												<div class="mt-1 flex flex-wrap gap-2">
													<span class="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
														{isSamePrinter(arrangement)
															? 'Shared Printer Setup'
															: 'Dedicated Printers'}
													</span>
													<span
														class="rounded-full bg-green-500/10 px-2 py-0.5 text-xs text-green-700"
													>
														{getTotalPrinterCount(arrangement)} printer{getTotalPrinterCount(
															arrangement
														) > 1
															? 's'
															: ''}
													</span>
													<span
														class="rounded-full bg-amber-500/10 px-2 py-0.5 text-xs text-amber-700"
													>
														{getAvailableFeatures(arrangement).join(', ')}
													</span>
												</div>
											</div>
											<div class="mt-3 flex items-center justify-end sm:mt-0">
												<div class="text-right">
													<p class="text-lg font-bold text-primary">
														Starting at ৳{getMinPrice(arrangement).toFixed(2)}<span
															class="text-base font-normal text-muted-foreground">/page</span
														>
													</p>
													<p class="mt-0.5 text-xs text-muted-foreground">
														Based on cheapest print option
													</p>
												</div>
											</div>
										</div>
										<!-- Arrangement Diagram -->
										<div class="mb-5">
											<div class="flex flex-col sm:flex-row sm:items-center sm:space-x-6">
												<div class="min-w-[200px] flex-1">
													<div class="space-y-6">
														{#if isSamePrinter(arrangement)}
															<div class="flex flex-col items-center">
																<div class="relative">
																	{#if arrangement.bw_printer_object?.image}
																		<img
																			src={arrangement.bw_printer_object.image}
																			alt="Shared Printer"
																			class="h-24 w-24 rounded-xl border-2 border-border object-cover shadow-sm"
																		/>
																	{:else}
																		<div
																			class="flex h-24 w-24 items-center justify-center rounded-xl border-2 border-border bg-gradient-to-br from-blue-500/10 to-purple-500/10 shadow-sm"
																		>
																			<Printer class="h-8 w-8 text-primary" />
																		</div>
																	{/if}
																	<div
																		class="absolute -right-2 -bottom-2 rounded-full border bg-background p-1 shadow-sm"
																	>
																		<div
																			class={`h-3 w-3 rounded-full border-2 border-background ${getPrinterPendingJobCount(arrangement.bw_printer_object?.id || 0) > 0 ? 'animate-pulse bg-yellow-500' : 'bg-green-500'}`}
																		></div>
																	</div>
																</div>
																<p class="mt-3 text-center font-medium">
																	{arrangement.bw_printer_object?.name || 'Shared Printer'}
																</p>
																<p class="mt-1 text-xs text-muted-foreground">
																	{getPrinterStatus(arrangement.bw_printer_object)} • {getPrinterPendingJobCount(
																		arrangement.bw_printer_object?.id || 0
																	)} pending jobs
																</p>
															</div>
														{:else}
															<div class="grid grid-cols-2 gap-4">
																<div class="flex flex-col items-center">
																	<div class="relative">
																		{#if arrangement.bw_printer_object?.image}
																			<img
																				src={arrangement.bw_printer_object.image}
																				alt="B/W Printer"
																				class="h-20 w-20 rounded-xl border-2 border-border object-cover shadow-sm"
																			/>
																		{:else}
																			<div
																				class="flex h-20 w-20 items-center justify-center rounded-xl border-2 border-border bg-blue-500/10 shadow-sm"
																			>
																				<Printer class="h-7 w-7 text-blue-500" />
																			</div>
																		{/if}
																		<div
																			class="absolute -right-2 -bottom-2 rounded-full border bg-background p-1 shadow-sm"
																		>
																			<div
																				class={`h-3 w-3 rounded-full border-2 border-background ${getPrinterPendingJobCount(arrangement.bw_printer_object?.id || 0) > 0 ? 'animate-pulse bg-yellow-500' : 'bg-green-500'}`}
																			></div>
																		</div>
																	</div>
																	<p
																		class="mt-2 text-center text-xs font-medium text-muted-foreground"
																	>
																		B/W Printer
																	</p>
																	<p class="mt-0.5 text-center text-sm font-medium">
																		{arrangement.bw_printer_object?.name || 'Not assigned'}
																	</p>
																	<p class="mt-1 text-xs text-muted-foreground">
																		{getPrinterStatus(arrangement.bw_printer_object)}
																	</p>
																</div>
																<div class="flex flex-col items-center">
																	<div class="relative">
																		{#if arrangement.color_printer_object?.image}
																			<img
																				src={arrangement.color_printer_object.image}
																				alt="Color Printer"
																				class="h-20 w-20 rounded-xl border-2 border-border object-cover shadow-sm"
																			/>
																		{:else}
																			<div
																				class="flex h-20 w-20 items-center justify-center rounded-xl border-2 border-border bg-purple-500/10 shadow-sm"
																			>
																				<Printer class="h-7 w-7 text-purple-500" />
																			</div>
																		{/if}
																		<div
																			class="absolute -right-2 -bottom-2 rounded-full border bg-background p-1 shadow-sm"
																		>
																			<div
																				class={`h-3 w-3 rounded-full border-2 border-background ${getPrinterPendingJobCount(arrangement.color_printer_object?.id || 0) > 0 ? 'animate-pulse bg-yellow-500' : 'bg-green-500'}`}
																			></div>
																		</div>
																	</div>
																	<p
																		class="mt-2 text-center text-xs font-medium text-muted-foreground"
																	>
																		Color Printer
																	</p>
																	<p class="mt-0.5 text-center text-sm font-medium">
																		{arrangement.color_printer_object?.name || 'Not assigned'}
																	</p>
																	<p class="mt-1 text-xs text-muted-foreground">
																		{getPrinterStatus(arrangement.color_printer_object)}
																	</p>
																</div>
															</div>
														{/if}
													</div>
												</div>
												<div
													class="mt-6 flex-1 border-l border-border pt-6 pl-6 sm:mt-0 sm:border-t sm:border-l-0 sm:pt-4 sm:pl-0"
												>
													<div class="mb-3 flex items-center">
														<FileText class="mr-2 h-4 w-4 text-muted-foreground" />
														<span class="font-medium">Print Flow</span>
													</div>
													<div class="flex items-center space-x-1.5 text-sm">
														<div class="flex items-center">
															<div
																class="flex h-8 w-10 items-center justify-center rounded-l-lg bg-muted text-xs font-medium"
															>
																Files
															</div>
															<ArrowRight class="mx-1 h-4 w-4 text-muted-foreground" />
														</div>
														<div class="flex items-center">
															{#if isSamePrinter(arrangement)}
																<div
																	class="flex h-8 w-24 items-center justify-center rounded-lg border border-blue-500/30 bg-blue-500/10 text-xs font-medium text-blue-700"
																>
																	Shared Printer
																</div>
															{:else}
																<div class="flex flex-col items-center">
																	<div
																		class="flex h-6 w-16 items-center justify-center rounded-t-lg border border-blue-500/30 bg-blue-500/10 text-[10px] font-medium text-blue-700"
																	>
																		B/W Files
																	</div>
																	<div
																		class="flex h-6 w-16 items-center justify-center rounded-b-lg border border-purple-500/30 bg-purple-500/10 text-[10px] font-medium text-purple-700"
																	>
																		Color Files
																	</div>
																</div>
															{/if}
															<ArrowRight class="mx-1 h-4 w-4 text-muted-foreground" />
														</div>
														<div
															class="flex h-8 w-14 items-center justify-center rounded-r-lg bg-green-500/10 text-xs font-medium text-green-700"
														>
															Output
														</div>
													</div>
													<p class="mt-3 text-xs text-muted-foreground">
														Your documents will be automatically routed to the appropriate printer
														based on your color selection.
													</p>
												</div>
											</div>
										</div>
										<!-- Detailed Pricing and Specifications -->
										<div class="overflow-hidden rounded-xl border">
											<div class="grid grid-cols-2 divide-x divide-border">
												<div class="bg-muted/30 p-4">
													<div class="mb-3 flex items-center">
														<FileText class="mr-2 h-4 w-4 text-muted-foreground" />
														<span class="text-sm font-medium">Black & White Pricing</span>
													</div>
													<div class="space-y-2.5">
														<div class="flex items-center justify-between">
															<span class="flex items-center text-xs text-muted-foreground">
																<ArrowRight class="mr-1 h-3 w-3" /> Single-sided
															</span>
															<span class="font-medium"
																>৳{(arrangement.bw_printer_object?.simplex_charge || 0).toFixed(
																	2
																)}</span
															>
														</div>
														<div class="flex items-center justify-between">
															<span class="flex items-center text-xs text-muted-foreground">
																<ArrowRight class="mr-1 h-3 w-3" /> Double-sided
															</span>
															<span class="font-medium"
																>৳{(arrangement.bw_printer_object?.duplex_charge || 0).toFixed(
																	2
																)}</span
															>
														</div>
														{#if isSamePrinter(arrangement)}
															<div class="mt-2 border-t border-border pt-2">
																<p class="mb-1 text-xs text-muted-foreground">
																	Same printer used for both color and B/W jobs
																</p>
															</div>
														{/if}
													</div>
												</div>
												<div class="p-4">
													<div class="mb-3 flex items-center">
														<FileText class="mr-2 h-4 w-4 text-muted-foreground" />
														<span class="text-sm font-medium">Color Pricing</span>
													</div>
													<div class="space-y-2.5">
														<div class="flex items-center justify-between">
															<span class="flex items-center text-xs text-muted-foreground">
																<ArrowRight class="mr-1 h-3 w-3" /> Single-sided
															</span>
															<span class="font-medium text-foreground"
																>৳{(arrangement.color_printer_object?.simplex_charge || 0).toFixed(
																	2
																)}</span
															>
														</div>
														<div class="flex items-center justify-between">
															<span class="flex items-center text-xs text-muted-foreground">
																<ArrowRight class="mr-1 h-3 w-3" /> Double-sided
															</span>
															<span class="font-medium text-foreground"
																>৳{(arrangement.color_printer_object?.duplex_charge || 0).toFixed(
																	2
																)}</span
															>
														</div>
													</div>
												</div>
											</div>
											<div class="border-t bg-muted/20 p-4">
												<div class="flex flex-wrap items-center justify-between gap-3">
													<div class="flex items-center space-x-3">
														<div class="flex items-center">
															<div class="mr-1.5 h-2 w-2 rounded-full bg-blue-500"></div>
															<span class="text-xs text-muted-foreground"
																>B/W: {getPrinterStatus(arrangement.bw_printer_object)}</span
															>
														</div>
														<div class="flex items-center">
															<div class="mr-1.5 h-2 w-2 rounded-full bg-purple-500"></div>
															<span class="text-xs text-muted-foreground"
																>Color: {getPrinterStatus(arrangement.color_printer_object)}</span
															>
														</div>
													</div>
													<div class="flex items-center">
														<span class="mr-2 text-xs text-muted-foreground">Reliability:</span>
														<span
															class="rounded-full bg-green-500/10 px-2 py-0.5 text-xs font-medium text-green-700"
														>
															{getPrinterReliability(
																arrangement.bw_printer_object
															).completionRate.toFixed(1)}% success
														</span>
													</div>
												</div>
											</div>
										</div>
										<!-- Cost Estimate Section based on current files -->
										{#if totalDocumentPages > 0 && copies > 0}
											<div class="mt-5 border-t border-border pt-5">
												<div class="mb-3 flex items-center">
													<CreditCard class="mr-2 h-4 w-4 text-muted-foreground" />
													<span class="font-medium">Estimated Cost for Your Document</span>
												</div>
												<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
													<div class="rounded-lg bg-blue-50 p-3">
														<p class="mb-1 flex items-center text-xs text-blue-700">
															<FileText class="mr-1 h-3 w-3" /> B/W, Single-sided
														</p>
														<p class="text-lg font-bold">
															৳{estimateCostForArrangement(arrangement).bwCost.toFixed(2)}
														</p>
														<p class="mt-1 text-xs text-muted-foreground">
															{totalDocumentPages} pages × {copies} copies × ৳{(
																arrangement.bw_printer_object?.simplex_charge || 0
															).toFixed(2)}/page
														</p>
													</div>
													<div class="rounded-lg bg-purple-50 p-3">
														<p class="mb-1 flex items-center text-xs text-purple-700">
															<FileText class="mr-1 h-3 w-3" /> Color, Double-sided
														</p>
														<p class="text-lg font-bold">
															৳{estimateCostForArrangement(arrangement).colorCost.toFixed(2)}
														</p>
														<p class="mt-1 text-xs text-muted-foreground">
															{totalDocumentPages} pages × {copies} copies × ৳{(
																arrangement.color_printer_object?.duplex_charge || 0
															).toFixed(2)}/page
														</p>
													</div>
												</div>
											</div>
										{/if}
										<!-- Additional Details Section -->
										{#if !isSamePrinter(arrangement) && arrangement.bw_printer_object && arrangement.color_printer_object}
											<div class="mt-5 border-t border-border pt-5">
												<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
													<div class="space-y-3">
														<div class="flex items-start space-x-3">
															<div class="mt-0.5">
																<Info class="h-4 w-4 text-muted-foreground" />
															</div>
															<div>
																<p class="mb-1 text-sm font-medium">B/W Printer Specifications</p>
																<ul class="space-y-1 text-xs text-muted-foreground">
																	<li class="flex">
																		<span class="mr-1 font-medium">•</span> Speed: Up to 40 pages/minute
																	</li>
																	<li class="flex">
																		<span class="mr-1 font-medium">•</span> Paper capacity: 500 sheets
																	</li>
																	<li class="flex">
																		<span class="mr-1 font-medium">•</span> Resolution: 1200 x 1200 dpi
																	</li>
																	<li class="flex">
																		<span class="mr-1 font-medium">•</span> Avg. completion time: {getPrinterReliability(
																			arrangement.bw_printer_object
																		).avgTime}
																	</li>
																</ul>
															</div>
														</div>
													</div>
													<div class="space-y-3">
														<div class="flex items-start space-x-3">
															<div class="mt-0.5">
																<Info class="h-4 w-4 text-muted-foreground" />
															</div>
															<div>
																<p class="mb-1 text-sm font-medium">Color Printer Specifications</p>
																<ul class="space-y-1 text-xs text-muted-foreground">
																	<li class="flex">
																		<span class="mr-1 font-medium">•</span> Speed: Up to 25 pages/minute
																	</li>
																	<li class="flex">
																		<span class="mr-1 font-medium">•</span> Paper capacity: 350 sheets
																	</li>
																	<li class="flex">
																		<span class="mr-1 font-medium">•</span> Resolution: 2400 x 1200 dpi
																	</li>
																	<li class="flex">
																		<span class="mr-1 font-medium">•</span> Avg. completion time: {getPrinterReliability(
																			arrangement.color_printer_object
																		).avgTime}
																	</li>
																</ul>
															</div>
														</div>
													</div>
												</div>
											</div>
										{/if}
										<!-- Admin Controls -->
										{#if currentUser?.is_staff}
											<div class="mt-5 flex justify-end space-x-3 border-t pt-5">
												<Button variant="outline" size="sm">
													<Settings2 class="mr-1 h-4 w-4" /> Manage
												</Button>
												<Button variant="secondary" size="sm">
													<Upload class="mr-1 h-4 w-4" /> Add Files
												</Button>
											</div>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>
				<div class="border-t bg-card/80 p-6 backdrop-blur-sm">
					<div class="mb-4 rounded-lg bg-muted/40 p-3">
						<p class="flex items-center text-sm font-medium">
							<Info class="mr-2 h-4 w-4 text-muted-foreground" />
							{selectedArrangement
								? 'You can change the arrangement later if needed.'
								: 'Select an arrangement to see detailed pricing for your documents.'}
						</p>
					</div>
					<Button
						class="w-full py-6 text-base font-semibold shadow-sm transition-transform hover:scale-[1.015] active:scale-[0.98]"
						onclick={() => {
							if (selectedArrangement) {
								isArrangementModalOpen = false;
							}
						}}
						disabled={!selectedArrangement}
					>
						{#if selectedArrangement}
							<span class="mx-auto flex items-center justify-center">
								Use Arrangement #{selectedArrangement.id}
								<ArrowRight class="ml-2.5 h-5 w-5" />
							</span>
						{:else}
							<span>Select an arrangement to continue</span>
						{/if}
					</Button>
				</div>
			</div>
		</Dialog.Content>
	</Dialog.Portal>
</Dialog.Root>
<!-- User Selection Modal -->
<Dialog.Root open={isUserModalOpen} onOpenChange={(open) => (isUserModalOpen = open)}>
	<Dialog.Trigger class="hidden" />
	<Dialog.Portal>
		<Dialog.Overlay
			class="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm transition-opacity duration-300 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:animate-in data-[state=open]:fade-in-0"
		/>
		<Dialog.Content
			class="fixed top-1/2 left-1/2 z-50 max-h-[90vh] w-full max-w-md -translate-x-1/2 -translate-y-1/2 rounded-2xl border bg-card shadow-xl transition-all duration-300 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-100 sm:w-full"
		>
			<div class="flex h-full flex-col">
				<div class="flex items-center justify-between border-b p-5">
					<Dialog.Title class="text-xl font-bold text-foreground">Select User</Dialog.Title>
				</div>
				<div class="flex-1 overflow-y-auto p-5">
					<div class="mb-6">
						<div class="relative">
							<Input
								type="text"
								placeholder="Search users by name or username..."
								value={userSearchQuery}
								oninput={(e) => (userSearchQuery = (e.target as HTMLInputElement).value)}
								class="h-11 pl-10"
							/>
							<Search
								class="absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-muted-foreground"
							/>
							{#if userSearchLoading}
								<LoaderCircle
									class="absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2 animate-spin text-primary"
								/>
							{/if}
						</div>
					</div>
					{#if userSearchLoading}
						<div class="flex justify-center py-8">
							<LoaderCircle class="h-6 w-6 animate-spin text-primary" />
						</div>
					{:else if users.length === 0}
						<div class="flex flex-col items-center justify-center py-16 text-center">
							<div class="mb-4 rounded-full bg-muted p-3">
								<User class="h-6 w-6 text-muted-foreground" />
							</div>
							<h3 class="mb-1 text-lg font-semibold">No Users Found</h3>
							<p class="max-w-md text-muted-foreground">
								No users are available to select. Please contact your system administrator.
							</p>
						</div>
					{:else}
						<div class="divide-y divide-border">
							{#each users as user (user.id)}
								<div
									role="button"
									tabindex="0"
									class="group flex cursor-pointer items-center justify-between rounded-xl p-4 transition-all duration-200 hover:bg-accent/50 {selectedUser?.id ===
									user.id
										? 'border border-primary/20 bg-primary/5'
										: ''}"
									onclick={() => {
										if (selectedUser?.id === user.id) {
											selectedUser = null;
										} else {
											selectedUser = user;
										}
									}}
									onkeydown={(e) => {
										if (e.key === 'Enter' || e.key === ' ') {
											e.preventDefault();
											if (selectedUser?.id === user.id) {
												selectedUser = null;
											} else {
												selectedUser = user;
											}
										}
									}}
								>
									<div class="flex items-center space-x-4">
										<div class="relative">
											<div
												class="flex h-12 w-12 items-center justify-center rounded-xl border bg-primary/10"
											>
												<User class="h-6 w-6 text-primary" />
											</div>
											{#if selectedUser?.id === user.id}
												<div
													class="absolute -right-1 -bottom-1 rounded-full bg-primary p-1 shadow-md"
												>
													<CircleCheck class="h-3 w-3 text-primary-foreground" />
												</div>
											{/if}
										</div>
										<div>
											<p class="text-base font-medium">{getDisplayName(user)}</p>
											<p class="text-sm text-muted-foreground">@{user.username}</p>
											{#if user.is_staff || user.is_superuser}
												<span
													class="mt-0.5 inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800"
												>
													{user.is_superuser ? 'Admin' : 'Staff'}
												</span>
											{/if}
										</div>
									</div>
									<div class="text-right">
										<p class="text-lg font-bold">৳{(user.balance || 0).toFixed(2)}</p>
										{#if selectedUser?.id === user.id}
											<span class="mt-1 inline-flex items-center text-xs font-medium text-primary">
												<CircleCheck class="mr-1 h-3 w-3" />
												Selected
											</span>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					{/if}
				</div>
				<div class="border-t bg-card/80 p-5 backdrop-blur-sm">
					<Button
						class="w-full py-5 text-base font-medium transition-transform hover:scale-[1.02] active:scale-[0.98]"
						onclick={() => {
							if (selectedUser) {
								isUserModalOpen = false;
							}
						}}
						disabled={!selectedUser}
					>
						{#if selectedUser}
							<span class="mx-auto flex items-center justify-center">
								Select {getDisplayName(selectedUser)}
								<ArrowRight class="ml-2 h-5 w-5" />
							</span>
						{:else}
							<span>Select a user to continue</span>
						{/if}
					</Button>
				</div>
			</div>
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
			<!-- User Selection - MODAL TRIGGER -->
			<div class="space-y-2">
				<Label>User</Label>
				<Button
					variant="outline"
					class="w-full justify-between"
					onclick={() => (isUserModalOpen = true)}
				>
					<span class="text-muted-foreground">
						{selectedUser
							? getDisplayName(selectedUser) + ' (৳' + (selectedUser.balance || 0).toFixed(2) + ')'
							: 'Select user'}
					</span>
					<ArrowRight class="h-4 w-4 text-muted-foreground" />
				</Button>
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
