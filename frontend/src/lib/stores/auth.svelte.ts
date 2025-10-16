import { USER_ENDPOINT } from '$lib/constants/backend';
import { token } from './token.svelte';

let isLoggedInState = $state<boolean | null>(null);
let isAdminUser = $state<null | boolean>(null);

$effect.root(() => {
	if (token.value) {
		fetch(USER_ENDPOINT, {
			headers: {
				Authorization: `Bearer ${token.value}`
			}
		})
			.then(async (res) => {
				if (res.ok) {
					isLoggedInState = true;
					const data = await res.json();
					if (data && data.is_superuser) {
						isAdminUser = true;
					}
				} else {
					isLoggedInState = false;
					token.set(null);
				}
			})
			.catch(() => {
				isLoggedInState = false;
			});
	}
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
