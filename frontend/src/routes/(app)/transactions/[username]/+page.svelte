<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import TransactionList from '$lib/components/TransactionList.svelte';
	import { token } from '$lib/stores/token.svelte';
	import { client } from '$lib/client';

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

	onMount(async () => {
		try {
			if (!username) {
				error = 'Username parameter is missing';
				return;
			}

			const [balanceRes, transactionsRes] = await Promise.all([
				client.GET('/api/balance/{username}', {
					params: {
						path: {
							username
						}
					},
					headers: {
						Authorization: `Bearer ${token.value}`,
						'Content-Type': 'application/json'
					}
				}),
				client.GET('/api/transactions/{username}', {
					params: {
						path: {
							username
						}
					},
					headers: {
						Authorization: `Bearer ${token.value}`,
						'Content-Type': 'application/json'
					}
				})
			]);

			if (!balanceRes.response.ok) {
				if (balanceRes.response.status === 404) {
					error = 'User balance not found';
				} else {
					throw new Error(`Balance API: ${balanceRes.response.status}`);
				}
				return;
			}

			if (!transactionsRes.response.ok) {
				if (transactionsRes.response.status === 404) {
					error = 'User transactions not found';
				} else if (transactionsRes.response.status === 403) {
					error = 'You do not have permission to view this user’s data';
				} else {
					throw new Error(`Transactions API: ${transactionsRes.response.status}`);
				}
				return;
			}

			const balanceData = await balanceRes.response.json();
			const transactionsData: TransactionResponse[] = await transactionsRes.response.json();

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
