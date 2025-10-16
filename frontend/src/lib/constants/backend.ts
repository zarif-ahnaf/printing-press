import * as publicEnv from '$env/static/public';

// @ts-expect-error: I know what I'm doing
const BACKEND_URL = publicEnv.PUBLIC_API_URL ?? 'http://localhost:8000';
const API_URL = `${BACKEND_URL}/api`;

export var LOGIN_URL = `${API_URL}/user/login/`;
export var TRANSACTIONS_URL = `${API_URL}/transactions/`;
export var BALANCE_URL = `${API_URL}/balance/`;
export var NONBLANK_URL = `${API_URL}/convert/nonblank/`;
export var QUEUE_URL = `${API_URL}/queue/`;
export var PDF_CONVERT_URL = `${API_URL}/convert/pdf/`;
export var ALL_USER_ENDPOINT = `${API_URL}/users/`;
export var USER_ENDPOINT = `${API_URL}/user/`;
