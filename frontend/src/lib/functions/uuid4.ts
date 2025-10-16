export function uuidv4() {
	// Create a 16-byte (128-bit) buffer
	const bytes = crypto.getRandomValues(new Uint8Array(16));

	// Set version (4) in byte 6: xxxxxxxx-xxxx-Mxxx-Nxxx-xxxxxxxxxxxx
	bytes[6] = (bytes[6] & 0x0f) | 0x40; // M = 4

	// Set variant to 10 (RFC 4122) in byte 8
	bytes[8] = (bytes[8] & 0x3f) | 0x80; // N = 8, 9, a, or b

	// Format as hex with dashes
	const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');

	return `${hex.substring(0, 8)}-${hex.substring(8, 12)}-${hex.substring(12, 16)}-${hex.substring(16, 20)}-${hex.substring(20)}`;
}
