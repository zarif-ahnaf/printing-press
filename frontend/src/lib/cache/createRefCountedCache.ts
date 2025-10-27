export function createRefCountedCache<T>() {
	const store = new Map<string, T>();
	const refCounts = new Map<string, number>();

	return {
		has(key: string): boolean {
			return store.has(key);
		},
		get(key: string): T | undefined {
			return store.get(key);
		},
		set(key: string, value: T): void {
			store.set(key, value);
			refCounts.set(key, 0);
		},
		incrementRef(key: string): void {
			if (refCounts.has(key)) {
				refCounts.set(key, (refCounts.get(key) || 0) + 1);
			}
		},
		decrementRef(key: string): boolean {
			const count = refCounts.get(key) || 0;
			if (count <= 1) {
				refCounts.delete(key);
				store.delete(key);
				return true; // safe to revoke
			} else {
				refCounts.set(key, count - 1);
				return false;
			}
		},
		evictAll(): void {
			store.clear();
			refCounts.clear();
		},
		// ✅ Allow safe iteration
		entries(): IterableIterator<[string, T]> {
			return store.entries();
		}
	};
}
