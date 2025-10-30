<script lang="ts">
	import { onMount } from 'svelte';
	import TransactionList from '$lib/components/TransactionList.svelte';
	import { token } from '$lib/stores/token.svelte';
	import { client } from '$lib/client';
	import { toast } from 'svelte-sonner';

	let transactions = $state<TransactionResponse[]>([]);
	let balance = $state<number | undefined>(undefined);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	type TransactionType = 'deposit' | 'charge';

	interface TransactionResponse {
		id: number;
		transaction_type: TransactionType;
		amount: string;
		description: string;
		created_at: string;
	}

	function isValidTransactionType(type: string): type is TransactionType {
		return type === 'deposit' || type === 'charge';
	}

	onMount(async () => {
		isLoading = true;
		const headers = { Authorization: `Bearer ${token.value}` };

		const balanceReq = client.GET('/api/balance/', { headers });
		const transactionsReq = client.GET('/api/transactions/', { headers });

		const [balanceResult, transactionsResult] = await Promise.all([balanceReq, transactionsReq]);

		if (balanceResult.error) {
			const detail = (balanceResult.error as any)?.body?.detail;
			error = `Balance API: ${detail || balanceResult.error.status}`;
		} else if (transactionsResult.error) {
			const detail = (transactionsResult.error as any)?.body?.detail;
			error = `Transactions API: ${detail || transactionsResult.error.status}`;
		} else {
			// Both succeeded
			balance = parseFloat(balanceResult.data.balance);

			// Validate and cast transaction types
			const validatedTransactions: TransactionResponse[] = [];
			for (const tx of transactionsResult.data) {
				if (!isValidTransactionType(tx.transaction_type)) {
					console.warn('Unknown transaction_type:', tx.transaction_type);
					continue; // or handle as error
				}
				validatedTransactions.push({
					id: tx.id,
					transaction_type: tx.transaction_type,
					amount: tx.amount,
					description: tx.description,
					created_at: tx.created_at
				});
			}

			transactions = validatedTransactions.sort(
				(a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
			);
		}

		isLoading = false;
	});
</script>

<TransactionList {transactions} {balance} {isLoading} {error} title="My Transaction History" />
