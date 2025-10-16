<!-- src/routes/transaction/+page.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import TransactionList from '$lib/components/TransactionList.svelte';
	import { BALANCE_URL, TRANSACTIONS_URL } from '$lib/constants/backend';
	import { token } from '$lib/stores/token.svelte';

	let transactions = $state<TransactionResponse[]>([]);
	let balance = $state<number | undefined>(undefined);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	type TransactionResponse = {
		id: number;
		transaction_type: 'deposit' | 'charge';
		amount: string;
		description: string;
		created_at: string;
	};

	onMount(async () => {
		try {
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

			const balanceData = await balanceRes.json();
			const transactionsData: TransactionResponse[] = await transactionsRes.json();

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
</script>

<TransactionList {transactions} {balance} {isLoading} {error} title="My Transaction History" />
