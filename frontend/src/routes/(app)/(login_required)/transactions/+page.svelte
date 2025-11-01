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
		transaction_type: string;
		amount: string;
		description: string;
		created_at: string;
	};

	onMount(async () => {
		try {
			const { data: balanceData, error: balanceError } = await client.GET('/api/user/balance/', {
				headers: { Authorization: `Bearer ${token.value}` }
			});
			if (balanceError) throw new Error(`Balance API: ${balanceError}`);

			const { data: transactionsData, error: transactionsError } = await client.GET(
				'/api/user/transactions/',
				{
					headers: { Authorization: `Bearer ${token.value}` }
				}
			);
			if (transactionsError) throw new Error(`Transactions API: ${transactionsError}`);

			balance = parseFloat(balanceData.balance || '0');
			transactions = transactionsData?.sort(
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
