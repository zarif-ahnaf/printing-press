import * as publicEnv from '$env/static/public';

// @ts-expect-error: I know what I'm doing
const BACKEND_URL = publicEnv.PUBLIC_API_URL ?? 'http://localhost:8000';
const API_URL = `${BACKEND_URL}/api`;

// CANNOT BE CONVERTED
export var PDF_CONVERT_URL = `${API_URL}/convert/pdf/`;
export var MERGE_ENDPOINT = `${API_URL}/convert/merge/`;
export var NONBLANK_URL = `${API_URL}/convert/nonblank/`;
export { BACKEND_URL };
