import { token } from './token.svelte';

let isLoggedInState = $state(!!token.value);

$effect.root(() => {
	isLoggedInState = !!token.value;
});

export const is_logged_in = {
	get value() {
		return isLoggedInState;
	}
};
