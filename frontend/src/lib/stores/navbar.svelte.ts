let navbarState = $state<'hidden' | 'visible' | null>(null);

export const navbar_state = {
	hide() {
		navbarState = 'hidden';
	},
	show() {
		navbarState = 'visible';
	},
	get hidden() {
		return navbarState === 'hidden';
	},
	get visible() {
		return navbarState === 'visible';
	},
	get state() {
		return navbarState;
	}
};
