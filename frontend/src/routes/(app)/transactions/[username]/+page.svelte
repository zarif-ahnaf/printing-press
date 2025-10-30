<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import TransactionList from '$lib/components/TransactionList.svelte';
	import { token } from '$lib/stores/token.svelte';
	import { client } from '$lib/client';
	import { page } from '$app/state';
	let transactions = $state<TransactionResponse[]>([]);
	let balance = $state<number | undefined>(undefined);
	let isLoading = $state(true);

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

		const { data: balanceData, error: balanceError } = await client.GET('/api/balance/{username}', {
			params: {
				path: {
					username: page.params.username ?? ''
				}
			},
			headers
		});
		if (balanceError) {
			toast.error(`Failed to load balance: ${balanceError ?? 'Unknown error'}`);
			isLoading = false;
			return;
		}

		const { data: transactionData, error: transactionError } = await client.GET(
			'/api/transactions/{username}',
			{
				headers,
				params: {
					path: {
						username: page.params.username ?? ''
					}
				}
			}
		);
		if (transactionError) {
			toast.error(`Failed to load transactions: ${transactionError ?? 'Unknown error'}`);
			isLoading = false;
			return;
		}

		// Success: update state
		balance = parseFloat(balanceData.balance);

		const validated: TransactionResponse[] = [];
		for (const tx of transactionData) {
			if (isValidTransactionType(tx.transaction_type)) {
				validated.push({
					id: tx.id,
					transaction_type: tx.transaction_type,
					amount: tx.amount,
					description: tx.description,
					created_at: tx.created_at
				});
			}
		}

		transactions = validated.sort(
			(a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
		);

		isLoading = false;
	});
</script>

<TransactionList {transactions} {balance} {isLoading} title="My Transaction History" />
