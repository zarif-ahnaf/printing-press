export interface Cache<T> {
	get(key: string): T | null;
	set(key: string, value: T, ttlMs?: number): void;
	has(key: string): boolean;
	delete(key: string): void;
	evict(): void;
}

export function createCache<T>(): Cache<T> {
	const store = new Map<string, { value: T; expiresAt?: number }>();

	function get(key: string): T | null {
		const entry = store.get(key);
		if (!entry) return null;
		if (entry.expiresAt !== undefined && Date.now() > entry.expiresAt) {
			store.delete(key);
			return null;
		}
		return entry.value;
	}

	function set(key: string, value: T, ttlMs?: number): void {
		const entry = { value, expiresAt: ttlMs ? Date.now() + ttlMs : undefined };
		store.set(key, entry);
	}

	function has(key: string): boolean {
		return get(key) !== null;
	}

	function deleteEntry(key: string): void {
		store.delete(key);
	}

	function evict(): void {
		store.clear();
	}

	return { get, set, has, delete: deleteEntry, evict };
}
