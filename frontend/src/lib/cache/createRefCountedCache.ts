import { SvelteMap as Map } from 'svelte/reactivity';

export interface RefCountedCache<T> {
	get(key: string): T | null;
	set(key: string, value: T): void;
	incrementRef(key: string): void;
	decrementRef(key: string): boolean;
	has(key: string): boolean;
	getRefCount(key: string): number;
	evictAll(): void;
}

export function createRefCountedCache<T>(): RefCountedCache<T> {
	const values = new Map<string, T>();
	const refCounts = new Map<string, number>();

	function get(key: string): T | null {
		return values.get(key) ?? null;
	}

	function set(key: string, value: T): void {
		values.set(key, value);
		refCounts.set(key, 0);
	}

	function incrementRef(key: string): void {
		if (!refCounts.has(key)) return;
		refCounts.set(key, (refCounts.get(key) || 0) + 1);
	}

	function decrementRef(key: string): boolean {
		const current = refCounts.get(key) || 0;
		if (current <= 0) return false;
		const newCount = current - 1;
		refCounts.set(key, newCount);
		if (newCount === 0) {
			return true;
		}
		return false;
	}

	function has(key: string): boolean {
		return values.has(key);
	}

	function getRefCount(key: string): number {
		return refCounts.get(key) || 0;
	}

	function evictAll(): void {
		values.clear();
		refCounts.clear();
	}

	return {
		get,
		set,
		incrementRef,
		decrementRef,
		has,
		getRefCount,
		evictAll
	};
}
