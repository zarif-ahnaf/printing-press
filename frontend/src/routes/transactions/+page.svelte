<script lang="ts">
	import { onMount } from 'svelte';
	import { format, parseISO, isSameDay } from 'date-fns';
	import {
		Card,
		CardContent,
		CardHeader,
		CardTitle,
		CardDescription
	} from '$lib/components/ui/card';
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
	import { BALANCE_URL, TRANSACTIONS_URL } from '$lib/constants/backend';
	import { token } from '$lib/stores/token.svelte';

	type TransactionResponse = {
		id: number;
		transaction_type: 'deposit' | 'charge';
		amount: string;
		description: string;
		created_at: string;
	};

	type BalanceResponse = {
		balance: string;
	};

	type TransactionGroup = {
		date: Date;
		label: string;
		transactions: TransactionResponse[];
	};

	// Reactive state
	let transactions: TransactionResponse[] = $state([]);
	let balance: number = $state(0);
	let isLoading: boolean = $state(true);
	let error: string | null = $state(null);

	// Format helpers
	const formatCurrency = (value: number) => {
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD'
		}).format(value);
	};

	const formatTime = (dateString: string) => {
		return format(parseISO(dateString), 'h:mm a');
	};

	// Fetch data on mount
	onMount(async () => {
		try {
			// Fetch balance and transactions in parallel
			const [balanceRes, transactionsRes] = await Promise.all([
				fetch(BALANCE_URL, {
					headers: { Authorization: `Bearer ${token.value}`, 'Content-Type': 'application/json' }
				}),
				fetch(TRANSACTIONS_URL, {
					headers: { Authorization: `Bearer ${token.value}`, 'Content-Type': 'application/json' }
				})
			]);

			if (!balanceRes.ok) throw new Error(`Balance API: ${balanceRes.status}`);
			if (!transactionsRes.ok) throw new Error(`Transactions API: ${transactionsRes.status}`);

			const balanceData: BalanceResponse = await balanceRes.json();
			const transactionsData: TransactionResponse[] = await transactionsRes.json();

			// Update state
			balance = parseFloat(balanceData.balance);
			transactions = transactionsData.sort(
				(a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
			);
		} catch (err) {
			console.error('Failed to fetch data:', err);
			error = err instanceof Error ? err.message : 'Failed to load data';
		} finally {
			isLoading = false;
		}
	});

	const groupedTransactions = $derived.by(() => {
		const groups: TransactionGroup[] = [];
		for (const tx of transactions) {
			const txDate = parseISO(tx.created_at);
			const existing = groups.find((g) => isSameDay(g.date, txDate));
			if (existing) {
				existing.transactions.push(tx);
			} else {
				groups.push({
					date: txDate,
					label: format(txDate, 'MMMM d, yyyy'),
					transactions: [tx]
				});
			}
		}
		return groups;
	});
</script>

<div class="container mx-auto space-y-8 py-6">
	<!-- Error Alert -->
	{#if error}
		<Alert variant="destructive">
			<AlertDescription>{error}</AlertDescription>
		</Alert>
	{/if}

	<!-- Balance Summary Card -->
	<Card class="border-l-4 border-l-primary">
		<CardHeader>
			<CardTitle>Account Balance</CardTitle>
			<CardDescription>Current available funds</CardDescription>
		</CardHeader>
		<CardContent>
			{#if isLoading}
				<div class="h-8 w-32 animate-pulse rounded bg-muted"></div>
			{:else}
				<div class="text-3xl font-bold">
					{formatCurrency(balance)}
				</div>
				<div class="mt-1 text-sm text-muted-foreground">
					Based on {transactions.length} transactions
				</div>
			{/if}
		</CardContent>
	</Card>

	<!-- Transaction History -->
	<Card class="border-none shadow-none">
		<CardHeader>
			<CardTitle>Transaction History</CardTitle>
		</CardHeader>
		<CardContent>
			{#if isLoading}
				<div class="space-y-4">
					{#each { length: 3 } as _, i}
						<div class="h-12 animate-pulse rounded bg-muted"></div>
					{/each}
				</div>
			{:else if groupedTransactions.length === 0}
				<div class="py-8 text-center text-muted-foreground">No transactions found</div>
			{:else}
				<div class="space-y-6">
					{#each groupedTransactions as group}
						<div>
							<h3 class="border-muted-200 border-b py-2 text-lg font-semibold">{group.label}</h3>
							<div class="mt-2 overflow-hidden rounded-md border">
								<Table>
									<TableHeader>
										<TableRow class="bg-muted/40">
											<TableHead class="w-[70px] font-medium">ID</TableHead>
											<TableHead class="font-medium">Type</TableHead>
											<TableHead class="font-medium">Description</TableHead>
											<TableHead class="text-right font-medium">Amount</TableHead>
											<TableHead class="text-right font-medium">Time</TableHead>
										</TableRow>
									</TableHeader>
									<TableBody>
										{#each group.transactions as transaction (transaction.id)}
											<TableRow>
												<TableCell class="font-mono">#{transaction.id}</TableCell>
												<TableCell>
													<Badge
														variant={transaction.transaction_type === 'deposit'
															? 'default'
															: 'destructive'}
														class="capitalize"
													>
														{transaction.transaction_type}
													</Badge>
												</TableCell>
												<TableCell class="max-w-[220px] truncate sm:max-w-none">
													{transaction.description}
												</TableCell>
												<TableCell class="text-right font-medium">
													{transaction.transaction_type === 'deposit' ? '+' : '−'}
													{formatCurrency(parseFloat(transaction.amount))}
												</TableCell>
												<TableCell class="text-right text-sm text-muted-foreground">
													{formatTime(transaction.created_at)}
												</TableCell>
											</TableRow>
										{/each}
									</TableBody>
								</Table>
							</div>
						</div>
					{/each}
				</div>
			{/if}
		</CardContent>
	</Card>
</div>
