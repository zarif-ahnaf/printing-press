<!-- src/routes/transaction/[username]/+page.svelte -->
<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import TransactionList from '$lib/components/TransactionList.svelte';
	import { BALANCE_URL, TRANSACTIONS_URL } from '$lib/constants/backend';
	import { token } from '$lib/stores/token.svelte';

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

	const BALANCE_BY_USER_URL = (user: string) => {
		if (!user) throw new Error('Username is required');
		return `${BALANCE_URL}${encodeURIComponent(user)}`;
	};

	const TRANSACTIONS_BY_USER_URL = (user: string) => {
		if (!user) throw new Error('Username is required');
		return `${TRANSACTIONS_URL}${encodeURIComponent(user)}`;
	};

	onMount(async () => {
		try {
			if (!username) {
				error = 'Username parameter is missing';
				return;
			}

			const [balanceRes, transactionsRes] = await Promise.all([
				fetch(BALANCE_BY_USER_URL(username), {
					headers: {
						Authorization: `Bearer ${token.value}`,
						'Content-Type': 'application/json'
					}
				}),
				fetch(TRANSACTIONS_BY_USER_URL(username), {
					headers: {
						Authorization: `Bearer ${token.value}`,
						'Content-Type': 'application/json'
					}
				})
			]);

			if (!balanceRes.ok) {
				if (balanceRes.status === 404) {
					error = 'User balance not found';
				} else {
					throw new Error(`Balance API: ${balanceRes.status}`);
				}
				return;
			}

			if (!transactionsRes.ok) {
				if (transactionsRes.status === 404) {
					error = 'User transactions not found';
				} else if (transactionsRes.status === 403) {
					error = 'You do not have permission to view this user’s data';
				} else {
					throw new Error(`Transactions API: ${transactionsRes.status}`);
				}
				return;
			}

			const balanceData = await balanceRes.json();
			const transactionsData: TransactionResponse[] = await transactionsRes.json();

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
