import { sha256 as basesha256 } from 'hash-wasm';

export async function sha256(message: string): Promise<string> {
	const normalized = message.trim().toLowerCase();

	return await basesha256(normalized);
}
