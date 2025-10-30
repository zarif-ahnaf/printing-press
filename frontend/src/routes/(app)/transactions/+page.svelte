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

	type TransactionResponse = {
		id: number;
		transaction_type: 'deposit' | 'charge';
		amount: string;
		description: string;
		created_at: string;
	};

	// --- Helper: Safely parse JSON without consuming original body ---
	async function safeJson(response: Response): Promise<any> {
		if (!response.bodyUsed && response.headers.get('content-type')?.includes('application/json')) {
			try {
				return await response.clone().json();
			} catch {
				toast.error('Failed to parse JSON response');
			}
		}
		return {};
	}

	onMount(async () => {
		try {
			const [balanceRes, transactionsRes] = await Promise.all([
				client.GET('/api/balance/', {
					headers: { Authorization: `Bearer ${token.value}` }
				}),
				client.GET('/api/transactions/', {
					headers: { Authorization: `Bearer ${token.value}` }
				})
			]);

			if (!balanceRes.response.ok) {
				const errData = await safeJson(balanceRes.response);
				throw new Error(errData.detail || `Balance API: ${balanceRes.response.status}`);
			}

			if (!transactionsRes.response.ok) {
				const errData = await safeJson(transactionsRes.response);
				throw new Error(errData.detail || `Transactions API: ${transactionsRes.response.status}`);
			}

			const balanceData = await safeJson(balanceRes.response);
			const transactionsData = (await safeJson(transactionsRes.response)) as TransactionResponse[];

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
