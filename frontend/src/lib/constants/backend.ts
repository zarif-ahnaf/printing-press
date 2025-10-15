const BACKEND_URL = 'http://localhost:8000';
const API_URL = `${BACKEND_URL}/api`;

export var LOGIN_URL = `${API_URL}/user/login/`;
export var TRANSACTIONS_URL = `${API_URL}/transactions/`;
export var BALANCE_URL = `${API_URL}/balance/`;
export var NONBLANK_URL = `${API_URL}/count/nonblank/`;
export var QUEUE_URL = `${API_URL}/queue/`;

export var ADMIN_QUEUE_URL = `${API_URL}/admin/queue/`;
