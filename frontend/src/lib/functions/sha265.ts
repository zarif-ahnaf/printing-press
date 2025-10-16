export async function sha256(message: string) {
	// 1. Normalize the email by converting to lowercase and removing whitespace.
	const normalizedEmail = message.trim().toLowerCase();

	// 2. Encode the string into a byte array.
	const encoder = new TextEncoder();
	const data = encoder.encode(normalizedEmail);

	// 3. Hash the data using SHA-256.
	const hashBuffer = await crypto.subtle.digest('SHA-256', data);

	// 4. Convert the ArrayBuffer to a hex string.
	const hashArray = Array.from(new Uint8Array(hashBuffer));
	const hashHex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('');

	return hashHex;
}
