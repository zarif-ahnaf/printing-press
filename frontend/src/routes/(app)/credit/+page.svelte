<script lang="ts">
	import { CreditCard, Plus, Minus, List, Search, User, AlertCircle, X } from 'lucide-svelte';
	import { token } from '$lib/stores/token.svelte';
	import { toast } from 'svelte-sonner';

	import { Button } from '$lib/components/ui/button';
	import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '$lib/components/ui/card';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { Alert, AlertDescription, AlertTitle } from '$lib/components/ui/alert';
	import {
		Table,
		TableHeader,
		TableRow,
		TableHead,
		TableBody,
		TableCell
	} from '$lib/components/ui/table';
	import { Badge } from '$lib/components/ui/badge';
	import { client } from '$lib/client';

	// --- Types ---
	interface BalanceResponse {
		balance: string;
	}

	interface Transaction {
		id: number;
		transaction_type: 'deposit' | 'charge';
		amount: string;
		description: string;
		created_at: string;
	}

	interface UserItem {
		id: number;
		username: string;
		email: string;
		first_name: string;
		last_name: string;
	}

	// --- State ---
	let balance = $state<string>('0.00');
	let transactions = $state<Transaction[]>([]);
	let selectedUser = $state<UserItem | null>(null);
	let userSearch = $state<string>('');
	let isUserDropdownOpen = $state<boolean>(false);
	let users = $state<UserItem[]>([]);
	let isLoadingUsers = $state<boolean>(false);
	let amount = $state<string>('');
	let description = $state<string>('');
	let operationType = $state<'deposit' | 'charge'>('deposit');
	let isLoading = $state<boolean>(false);
	let error = $state<string | null>(null);

	const API_BASE = 'http://localhost:8000/api';

	const operationOptions = [
		{ value: 'deposit', label: 'Add Funds (Deposit)' },
		{ value: 'charge', label: 'Deduct Funds (Charge)' }
	];

	function getDisplayName(user: UserItem): string {
		if (user.first_name || user.last_name) {
			return `${user.first_name} ${user.last_name}`.trim();
		}
		return user.username;
	}

	async function fetchUsers(searchTerm: string = '') {
		isLoadingUsers = true;
		try {
			const res = await client.GET('/api/users/', {
				params: searchTerm ? { query: { name: searchTerm } } : {},
				headers: {
					Authorization: `Bearer ${token.value}`,
					'Content-Type': 'application/json'
				}
			});

			if (!res.response.ok) throw new Error('Failed to fetch users');
			users = (await res.response.json()) as UserItem[];
		} catch (err) {
			const message = (err as Error).message;
			error = message;
			toast.error(message);
			users = [];
		} finally {
			isLoadingUsers = false;
		}
	}

	async function fetchBalance() {
		if (!selectedUser) return;
		try {
			const res = await client.GET('/api/balance/{username}', {
				params: {
					path: {
						username: selectedUser.username
					}
				},
				headers: {
					Authorization: `Bearer ${token.value}`,
					'Content-Type': 'application/json'
				}
			});

			if (!res.response.ok) {
				const errData = await res.response.json().catch(() => ({}));
				throw new Error(errData.detail || 'Failed to fetch balance');
			}
			const data = (await res.response.json()) as BalanceResponse;
			balance = data.balance;
		} catch (err) {
			const message = (err as Error).message;
			error = message;
			toast.error(message);
		}
	}

	async function fetchTransactions() {
		if (!selectedUser) return;
		try {
			const res = await client.GET('/api/transactions/{username}', {
				params: {
					path: {
						username: selectedUser.username
					}
				},
				headers: {
					Authorization: `Bearer ${token.value}`,
					'Content-Type': 'application/json'
				}
			});

			if (!res.response.ok) {
				const errData = await res.response.json().catch(() => ({}));
				throw new Error(errData.detail || 'Failed to fetch transactions');
			}
			transactions = (await res.response.json()) as Transaction[];
		} catch (err) {
			const message = (err as Error).message;
			error = message;
			toast.error(message);
			transactions = [];
		}
	}

	async function handleOperation() {
		const numAmount = parseFloat(amount);
		if (!amount || isNaN(numAmount) || numAmount <= 0) {
			const msg = 'Please enter a valid positive amount.';
			error = msg;
			toast.error(msg);
			return;
		}

		if (!selectedUser) {
			const msg = 'Please select a user to perform this operation.';
			error = msg;
			toast.error(msg);
			return;
		}

		isLoading = true;
		error = null;

		try {
			const endpoint = operationType === 'deposit' ? '/api/admin/deposit/' : '/api/charge/';
			const payload = {
				amount: amount.toString(),
				description:
					description || (operationType === 'deposit' ? 'Admin deposit' : 'Manual charge'),
				username: selectedUser.username
			};

			const res = await client.POST(endpoint, {
				headers: {
					Authorization: `Bearer ${token.value}`,
					'Content-Type': 'application/json'
				},
				body: payload
			});

			if (!res.response.ok) {
				const errData = await res.response.json().catch(() => ({}));
				throw new Error(errData.detail || 'Operation failed');
			}

			toast.success(
				`${operationType === 'deposit' ? 'Funds added' : 'Funds deducted'} successfully!`
			);

			await fetchBalance();
			await fetchTransactions();

			amount = '';
			description = '';
		} catch (err) {
			const message = (err as Error).message;
			error = message;
			toast.error(message);
		} finally {
			isLoading = false;
		}
	}

	// Debounced search
	let searchTimeout: number;
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

	// Initial load: fetch all users
	$effect(() => {
		fetchUsers();
	});

	// When user is selected, load their data
	$effect(() => {
		if (selectedUser) {
			fetchBalance();
			fetchTransactions();
		} else {
			balance = '0.00';
			transactions = [];
		}
	});
</script>

<div class="min-h-screen bg-black p-6 text-white">
	<div class="mx-auto max-w-6xl">
		<!-- Header -->
		<div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
			<div class="flex items-center gap-2">
				<CreditCard class="h-6 w-6" />
				<h1 class="text-2xl font-bold">Admin Credit Management</h1>
			</div>
			<div class="flex items-center gap-4">
				<span>Target Balance:</span>
				<Badge variant="secondary" class="px-4 py-2 text-lg">
					{selectedUser ? balance : '—'}
				</Badge>
			</div>
		</div>

		<!-- User Search (inspired by your reference) -->
		<Card class="mb-6">
			<CardHeader>
				<CardTitle class="flex items-center gap-2">
					<User class="h-4 w-4" />
					Select User <span class="text-red-500">*</span>
				</CardTitle>
			</CardHeader>
			<CardContent>
				<Label for="user-search">User</Label>
				<div class="relative mt-1">
					<div
						class="flex items-center rounded-md border border-gray-700 bg-black px-3 py-2 focus-within:ring-1 focus-within:ring-gray-500"
					>
						<Search class="mr-2 h-4 w-4 text-gray-400" />
						<Input
							id="user-search"
							type="text"
							placeholder="Search users..."
							bind:value={userSearch}
							oninput={handleUserSearch}
							onfocus={() => {
								if (!selectedUser) {
									isUserDropdownOpen = true;
								}
							}}
							onblur={closeDropdown}
							onkeydown={(e) => {
								if (e.key === 'Escape') {
									isUserDropdownOpen = false;
								}
							}}
							disabled={!!selectedUser}
							class="flex-1 border-0 bg-transparent pr-8 focus-visible:ring-0 focus-visible:ring-offset-0"
						/>
						{#if selectedUser}
							<Button
								type="button"
								variant="ghost"
								size="icon"
								class="ml-1 h-5 w-5 text-gray-400 hover:text-white"
								onclick={(e) => {
									e.stopPropagation();
									selectedUser = null;
									userSearch = '';
									isUserDropdownOpen = false;
								}}
								aria-label="Clear selected user"
							>
								<X class="h-3.5 w-3.5" />
							</Button>
						{/if}
					</div>

					<!-- Dropdown -->
					{#if (userSearch || isLoadingUsers) && isUserDropdownOpen && !selectedUser}
						<div
							class="absolute top-full z-50 mt-1 w-full animate-in rounded-md border border-gray-700 bg-black text-white shadow-lg fade-in-0 outline-none zoom-in-95"
						>
							{#if isLoadingUsers}
								<div class="px-3 py-2 text-sm text-gray-400">Loading...</div>
							{:else if users.length === 0}
								<div class="px-3 py-2 text-sm text-gray-400">No users found</div>
							{:else}
								{#each users as user}
									<button
										type="button"
										class="flex w-full cursor-pointer items-center gap-3 px-3 py-2 text-left text-sm hover:bg-gray-800"
										onclick={() => {
											selectedUser = user;
											userSearch = getDisplayName(user);
											isUserDropdownOpen = false;
										}}
									>
										<User class="h-4 w-4 text-gray-400" />
										<div class="flex flex-col">
											<span>{getDisplayName(user)}</span>
											<span class="text-xs text-gray-500">{user.email}</span>
										</div>
									</button>
								{/each}
							{/if}
						</div>
					{/if}
				</div>
			</CardContent>
		</Card>

		<!-- Deposit / Charge Form -->
		<Card class="mb-6">
			<CardHeader>
				<CardTitle class="flex items-center gap-2">
					{#if operationType === 'deposit'}
						<Plus class="h-4 w-4" />
						Add Funds
					{:else}
						<Minus class="h-4 w-4" />
						Deduct Funds
					{/if}
				</CardTitle>
			</CardHeader>
			<CardContent>
				<div class="grid gap-4">
					<div>
						<Label for="operationType">Operation Type</Label>
						<select
							id="operationType"
							bind:value={operationType}
							class="w-full rounded-md border border-gray-700 bg-gray-900 p-2 text-white"
						>
							{#each operationOptions as op}
								<option value={op.value}>{op.label}</option>
							{/each}
						</select>
					</div>

					<div>
						<Label for="amount">Amount</Label>
						<Input
							id="amount"
							bind:value={amount}
							type="number"
							step="0.01"
							min="0.01"
							placeholder="e.g., 10.50"
						/>
					</div>

					<div>
						<Label for="description">Description (optional)</Label>
						<Input
							id="description"
							bind:value={description}
							placeholder="e.g., Refund, Service fee"
						/>
					</div>
				</div>
			</CardContent>
			<CardFooter>
				<Button onclick={handleOperation} disabled={isLoading || !selectedUser} class="w-full">
					{#if !selectedUser}
						Select a user first
					{:else if isLoading}
						Processing...
					{:else}
						Confirm {operationType === 'deposit' ? 'Deposit' : 'Charge'}
					{/if}
				</Button>
			</CardFooter>
		</Card>

		<!-- Error Alert -->
		{#if error}
			<Alert variant="destructive" class="mb-4">
				<AlertCircle class="h-4 w-4" />
				<AlertTitle>Error</AlertTitle>
				<AlertDescription>{error}</AlertDescription>
			</Alert>
		{/if}

		<!-- Transaction History -->
		<Card>
			<CardHeader>
				<CardTitle class="flex items-center gap-2">
					<List class="h-4 w-4" />
					Transaction History
					{#if selectedUser}
						<span class="text-sm text-gray-400">(for {selectedUser.username})</span>
					{/if}
				</CardTitle>
			</CardHeader>
			<CardContent>
				{#if !selectedUser}
					<p class="text-gray-400">Select a user to view their transaction history.</p>
				{:else if transactions.length === 0}
					<p class="text-gray-400">No transactions found.</p>
				{:else}
					<div class="overflow-hidden rounded-md border border-gray-800">
						<Table>
							<TableHeader>
								<TableRow class="border-b border-gray-800">
									<TableHead>Date</TableHead>
									<TableHead>Type</TableHead>
									<TableHead>Amount</TableHead>
									<TableHead>Description</TableHead>
								</TableRow>
							</TableHeader>
							<TableBody>
								{#each transactions as tx}
									<TableRow class="border-b border-gray-800 hover:bg-gray-900">
										<TableCell>{new Date(tx.created_at).toLocaleString()}</TableCell>
										<TableCell>
											<Badge
												variant={tx.transaction_type === 'deposit' ? 'default' : 'destructive'}
												class="capitalize"
											>
												{tx.transaction_type}
											</Badge>
										</TableCell>
										<TableCell>{tx.amount}</TableCell>
										<TableCell class="max-w-xs truncate">{tx.description}</TableCell>
									</TableRow>
								{/each}
							</TableBody>
						</Table>
					</div>
				{/if}
			</CardContent>
		</Card>
	</div>
</div>
