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
				.GET('/api/user/', {
					headers: {
						Authorization: `Bearer ${token.value}`
					}
				})
				.then((res) => {
					if (res.data) {
						// Success: OpenAPI defined 200 response → use res.data
						isLoggedInState = true;
						isAdminUser = Boolean(res.data.is_superuser);
						firstName = res.data.first_name ?? null;
						lastName = res.data.last_name ?? null;
						email = res.data.email ?? null;
						username = res.data.username ?? null;
						fetchState = 'fetched';
					} else {
						// Either 4xx/5xx or 2xx not defined in OpenAPI
						// Treat as unauthenticated
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
