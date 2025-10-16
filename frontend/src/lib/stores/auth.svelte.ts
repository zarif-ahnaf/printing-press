let isLoggedInState = $state<boolean | null>(null);
let isAdminUser = $state<null | boolean>(null);

export const is_logged_in = {
	get value() {
		return Boolean(isLoggedInState);
	},
	set(value: typeof isLoggedInState) {
		isLoggedInState = value;
	}
};

export const is_admin_user = {
	get value() {
		return Boolean(isAdminUser);
	},
	set(value: typeof isAdminUser) {
		isAdminUser = value;
	}
};
