let wasm;

let cachedUint8ArrayMemory0 = null;

function getUint8ArrayMemory0() {
	if (cachedUint8ArrayMemory0 === null || cachedUint8ArrayMemory0.byteLength === 0) {
		cachedUint8ArrayMemory0 = new Uint8Array(wasm.memory.buffer);
	}
	return cachedUint8ArrayMemory0;
}

function getArrayU8FromWasm0(ptr, len) {
	ptr = ptr >>> 0;
	return getUint8ArrayMemory0().subarray(ptr / 1, ptr / 1 + len);
}

let cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });

cachedTextDecoder.decode();

const MAX_SAFARI_DECODE_BYTES = 2146435072;
let numBytesDecoded = 0;
function decodeText(ptr, len) {
	numBytesDecoded += len;
	if (numBytesDecoded >= MAX_SAFARI_DECODE_BYTES) {
		cachedTextDecoder = new TextDecoder('utf-8', { ignoreBOM: true, fatal: true });
		cachedTextDecoder.decode();
		numBytesDecoded = len;
	}
	return cachedTextDecoder.decode(getUint8ArrayMemory0().subarray(ptr, ptr + len));
}

function getStringFromWasm0(ptr, len) {
	ptr = ptr >>> 0;
	return decodeText(ptr, len);
}

function takeFromExternrefTable0(idx) {
	const value = wasm.__wbindgen_export_0.get(idx);
	wasm.__externref_table_dealloc(idx);
	return value;
}
/**
 * @param {Array<any>} pdf_array
 * @returns {Uint8Array}
 */
export function merge_pdfs_wasm(pdf_array) {
	const ret = wasm.merge_pdfs_wasm(pdf_array);
	if (ret[3]) {
		throw takeFromExternrefTable0(ret[2]);
	}
	var v1 = getArrayU8FromWasm0(ret[0], ret[1]).slice();
	wasm.__wbindgen_free(ret[0], ret[1] * 1, 1);
	return v1;
}

const EXPECTED_RESPONSE_TYPES = new Set(['basic', 'cors', 'default']);

async function __wbg_load(module, imports) {
	if (typeof Response === 'function' && module instanceof Response) {
		if (typeof WebAssembly.instantiateStreaming === 'function') {
			try {
				return await WebAssembly.instantiateStreaming(module, imports);
			} catch (e) {
				const validResponse = module.ok && EXPECTED_RESPONSE_TYPES.has(module.type);

				if (validResponse && module.headers.get('Content-Type') !== 'application/wasm') {
					console.warn(
						'`WebAssembly.instantiateStreaming` failed because your server does not serve Wasm with `application/wasm` MIME type. Falling back to `WebAssembly.instantiate` which is slower. Original error:\n',
						e
					);
				} else {
					throw e;
				}
			}
		}

		const bytes = await module.arrayBuffer();
		return await WebAssembly.instantiate(bytes, imports);
	} else {
		const instance = await WebAssembly.instantiate(module, imports);

		if (instance instanceof WebAssembly.Instance) {
			return { instance, module };
		} else {
			return instance;
		}
	}
}

function __wbg_get_imports() {
	const imports = {};
	imports.wbg = {};
	imports.wbg.__wbg_get_0da715ceaecea5c8 = function (arg0, arg1) {
		const ret = arg0[arg1 >>> 0];
		return ret;
	};
	imports.wbg.__wbg_instanceof_Uint8Array_9a8378d955933db7 = function (arg0) {
		let result;
		try {
			result = arg0 instanceof Uint8Array;
		} catch (_) {
			result = false;
		}
		const ret = result;
		return ret;
	};
	imports.wbg.__wbg_length_186546c51cd61acd = function (arg0) {
		const ret = arg0.length;
		return ret;
	};
	imports.wbg.__wbg_length_6bb7e81f9d7713e4 = function (arg0) {
		const ret = arg0.length;
		return ret;
	};
	imports.wbg.__wbg_prototypesetcall_3d4a26c1ed734349 = function (arg0, arg1, arg2) {
		Uint8Array.prototype.set.call(getArrayU8FromWasm0(arg0, arg1), arg2);
	};
	imports.wbg.__wbg_wbindgenthrow_451ec1a8469d7eb6 = function (arg0, arg1) {
		throw new Error(getStringFromWasm0(arg0, arg1));
	};
	imports.wbg.__wbindgen_cast_2241b6af4c4b2941 = function (arg0, arg1) {
		// Cast intrinsic for `Ref(String) -> Externref`.
		const ret = getStringFromWasm0(arg0, arg1);
		return ret;
	};
	imports.wbg.__wbindgen_init_externref_table = function () {
		const table = wasm.__wbindgen_export_0;
		const offset = table.grow(4);
		table.set(0, undefined);
		table.set(offset + 0, undefined);
		table.set(offset + 1, null);
		table.set(offset + 2, true);
		table.set(offset + 3, false);
	};

	return imports;
}

function __wbg_init_memory(imports, memory) {}

function __wbg_finalize_init(instance, module) {
	wasm = instance.exports;
	__wbg_init.__wbindgen_wasm_module = module;
	cachedUint8ArrayMemory0 = null;

	wasm.__wbindgen_start();
	return wasm;
}

function initSync(module) {
	if (wasm !== undefined) return wasm;

	if (typeof module !== 'undefined') {
		if (Object.getPrototypeOf(module) === Object.prototype) {
			({ module } = module);
		} else {
			console.warn('using deprecated parameters for `initSync()`; pass a single object instead');
		}
	}

	const imports = __wbg_get_imports();

	__wbg_init_memory(imports);

	if (!(module instanceof WebAssembly.Module)) {
		module = new WebAssembly.Module(module);
	}

	const instance = new WebAssembly.Instance(module, imports);

	return __wbg_finalize_init(instance, module);
}

async function __wbg_init(module_or_path) {
	if (wasm !== undefined) return wasm;

	if (typeof module_or_path !== 'undefined') {
		if (Object.getPrototypeOf(module_or_path) === Object.prototype) {
			({ module_or_path } = module_or_path);
		} else {
			console.warn(
				'using deprecated parameters for the initialization function; pass a single object instead'
			);
		}
	}

	if (typeof module_or_path === 'undefined') {
		module_or_path = new URL('document_factory_bg.wasm', import.meta.url);
	}
	const imports = __wbg_get_imports();

	if (
		typeof module_or_path === 'string' ||
		(typeof Request === 'function' && module_or_path instanceof Request) ||
		(typeof URL === 'function' && module_or_path instanceof URL)
	) {
		module_or_path = fetch(module_or_path);
	}

	__wbg_init_memory(imports);

	const { instance, module } = await __wbg_load(await module_or_path, imports);

	return __wbg_finalize_init(instance, module);
}

export { initSync };
export default __wbg_init;
