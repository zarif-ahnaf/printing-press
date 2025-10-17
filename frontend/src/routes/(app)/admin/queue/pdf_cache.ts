export class PdfCache {
	private cache: Record<string, { url: string; filename: string; refCount: number }>;
	private readonly maxSize: number;

	constructor(maxSize = 10) {
		this.cache = {};
		this.maxSize = maxSize;
	}

	private enforceSizeLimit() {
		const keys = Object.keys(this.cache);
		if (keys.length <= this.maxSize) return;

		// Remove oldest entries with zero refCount
		for (const key of keys) {
			if (this.cache[key].refCount <= 0) {
				URL.revokeObjectURL(this.cache[key].url);
				delete this.cache[key];
				if (Object.keys(this.cache).length <= this.maxSize) break;
			}
		}

		// If still over limit, remove oldest (even if in use — rare)
		if (Object.keys(this.cache).length > this.maxSize) {
			const oldestKey = keys[0];
			URL.revokeObjectURL(this.cache[oldestKey].url);
			delete this.cache[oldestKey];
		}
	}

	generateKey(fileUrls: string[]): string {
		const sorted = [...fileUrls].sort();
		return btoa(encodeURIComponent(sorted.join('|')));
	}

	has(key: string): boolean {
		return key in this.cache;
	}

	get(key: string) {
		return this.cache[key];
	}

	set(key: string, url: string, filename: string): void {
		this.enforceSizeLimit();
		this.cache[key] = { url, filename, refCount: 0 };
	}

	incrementRef(key: string): boolean {
		if (!this.cache[key]) return false;
		this.cache[key].refCount += 1;
		return true;
	}

	decrementRef(key: string): boolean {
		if (!this.cache[key]) return false;
		this.cache[key].refCount -= 1;

		// Clean up immediately if unused
		if (this.cache[key].refCount <= 0) {
			URL.revokeObjectURL(this.cache[key].url);
			delete this.cache[key];
		}
		return true;
	}

	revokeAll(): void {
		for (const key in this.cache) {
			URL.revokeObjectURL(this.cache[key].url);
		}
		this.cache = {};
	}
}
