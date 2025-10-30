import { client } from '$lib/client';
import { token } from './token.svelte';

let fetchState = $state<'not_fetched' | 'fetching' | 'fetched'>('not_fetched');

let isLoggedInState = $state<boolean | null>(null);
let isAdminUser = $state<null | boolean>(null);

let firstName = $state<string | null>(null);
let lastName = $state<string | null>(null);
let email = $state<string | null>(null);
let username = $state<string | null>(null);

$effect.root(() => {
	$effect(() => {
		if (token.value) {
			fetchState = 'fetching';
			client
				.GET('/api/user/')
				.then(async (_res) => {
					const res = _res.response;
					if (res.ok) {
						isLoggedInState = true;
						const data = await res.json();
						if (data) {
							isAdminUser = Boolean(data.is_superuser);
							firstName = data.first_name ?? null;
							lastName = data.last_name ?? null;
							email = data.email ?? null;
							username = data.username ?? null;
						}
						fetchState = 'fetched';
					} else {
						isLoggedInState = false;
						isAdminUser = null;
						firstName = lastName = email = username = null;
						token.set(null);
						fetchState = 'not_fetched';
					}
				})
				.catch(() => {
					isLoggedInState = false;
					isAdminUser = null;
					firstName = lastName = email = username = null;
					fetchState = 'not_fetched';
				});
		} else {
			// Reset state when token is cleared
			isLoggedInState = false;
			isAdminUser = null;
			firstName = lastName = email = username = null;
			fetchState = 'not_fetched';
		}
	});
});

export const is_logged_in = {
	get value() {
		return Boolean(isLoggedInState);
	}
};

export const is_admin_user = {
	get value() {
		return Boolean(isAdminUser);
	}
};

export const first_name = {
	get value() {
		return firstName;
	}
};
export const last_name = {
	get value() {
		return lastName;
	}
};
export const user_email = {
	get value() {
		return email;
	}
};
export const user_username = {
	get value() {
		return username;
	}
};
export const is_fetched = {
	get value() {
		return fetchState === 'fetched';
	}
};
