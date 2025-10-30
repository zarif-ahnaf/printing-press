<script lang="ts">
	import { onMount } from 'svelte';
	import TransactionList from '$lib/components/TransactionList.svelte';
	import { token } from '$lib/stores/token.svelte';
	import { client } from '$lib/client';

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
				client.GET('/api/balance/', {
					headers: { Authorization: `Bearer ${token.value}`, 'Content-Type': 'application/json' }
				}),
				client.GET('/api/transactions/', {
					headers: { Authorization: `Bearer ${token.value}`, 'Content-Type': 'application/json' }
				})
			]);

			if (!balanceRes.response.ok) throw new Error(`Balance API: ${balanceRes.response.status}`);
			if (!transactionsRes.response.ok)
				throw new Error(`Transactions API: ${transactionsRes.response.status}`);

			const balanceData = await balanceRes.response.json();
			const transactionsData: TransactionResponse[] = await transactionsRes.response.json();

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
