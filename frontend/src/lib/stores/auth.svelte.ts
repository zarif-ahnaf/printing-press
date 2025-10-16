import { USER_ENDPOINT } from '$lib/constants/backend';
import { token } from './token.svelte';

let isLoggedInState = $state<boolean | null>(null);
let isAdminUser = $state<null | boolean>(null);

let firstName = $state<string | null>(null);
let lastName = $state<string | null>(null);
let email = $state<string | null>(null);
let username = $state<string | null>(null);

$effect.root(() => {
	$effect(() => {
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
						if (data) {
							if (data.is_superuser) {
								isAdminUser = true;
							}
							if (data.first_name) {
								firstName = data.first_name;
							}
							if (data.last_name) {
								lastName = data.last_name;
							}
							if (data.email) {
								email = data.email;
							}
							if (data.username) {
								username = data.username;
							}
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
