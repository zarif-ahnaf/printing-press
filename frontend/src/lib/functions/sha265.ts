import { sha256 } from 'hash-wasm';

export async function sha256Email(message: string): Promise<string> {
	const normalized = message.trim().toLowerCase();

	return await sha256(normalized);
}
