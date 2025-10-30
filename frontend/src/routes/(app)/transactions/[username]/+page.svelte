<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import TransactionList from '$lib/components/TransactionList.svelte';
	import { token } from '$lib/stores/token.svelte';
	import { client } from '$lib/client';
	import { toast } from 'svelte-sonner';
	const username = $derived(page.params?.username ?? '');

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
				toast.error('Failed to parse server response');
			}
		}
		return {};
	}

	onMount(async () => {
		try {
			if (!username) {
				error = 'Username parameter is missing';
				return;
			}

			const [balanceRes, transactionsRes] = await Promise.all([
				client.GET('/api/balance/{username}', {
					params: {
						path: { username }
					},
					headers: {
						Authorization: `Bearer ${token.value}`
					}
				}),
				client.GET('/api/transactions/{username}', {
					params: {
						path: { username }
					},
					headers: {
						Authorization: `Bearer ${token.value}`
					}
				})
			]);

			if (!balanceRes.response.ok) {
				if (balanceRes.response.status === 404) {
					error = 'User balance not found';
				} else {
					const errData = await safeJson(balanceRes.response);
					throw new Error(errData.detail || `Balance API: ${balanceRes.response.status}`);
				}
				return;
			}

			if (!transactionsRes.response.ok) {
				if (transactionsRes.response.status === 404) {
					error = 'User transactions not found';
				} else if (transactionsRes.response.status === 403) {
					error = 'You do not have permission to view this user’s data';
				} else {
					const errData = await safeJson(transactionsRes.response);
					throw new Error(errData.detail || `Transactions API: ${transactionsRes.response.status}`);
				}
				return;
			}

			const balanceData = await safeJson(balanceRes.response);
			const transactionsData = (await safeJson(transactionsRes.response)) as TransactionResponse[];

			balance = parseFloat(balanceData.balance);
			transactions = transactionsData.sort(
				(a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
			);
		} catch (err) {
			console.error('Failed to fetch user data:', err);
			error = err instanceof Error ? err.message : 'Failed to load user data';
		} finally {
			isLoading = false;
		}
	});
</script>

<TransactionList
	{transactions}
	{balance}
	{isLoading}
	{error}
	title={`Transactions for @${username || 'Unknown'}`}
/>
