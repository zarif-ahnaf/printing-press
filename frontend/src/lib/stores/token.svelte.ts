let _token: string | null = null;

if (typeof window !== 'undefined') {
	_token = localStorage.getItem('token');
}

let tokenState = $state(_token);

$effect.root(() => {
	if (typeof window === 'undefined') return;

	// Sync to localStorage
	$effect(() => {
		if (tokenState) {
			localStorage.setItem('token', tokenState);
		} else {
			localStorage.removeItem('token');
		}
	});

	// Listen for cross-tab changes
	const handleStorage = (event: StorageEvent) => {
		if (event.key === 'token') {
			tokenState = event.newValue;
		}
	};

	window.addEventListener('storage', handleStorage);

	return () => {
		window.removeEventListener('storage', handleStorage);
	};
});

export const token = {
	get value() {
		return tokenState;
	},
	set(value: string | null) {
		tokenState = value;
	}
};
