import createClient from 'openapi-fetch';
import type { paths } from './backend';
import { BACKEND_URL } from '$lib/constants/backend';

const client = createClient<paths>({ baseUrl: BACKEND_URL, headers: {} });

export { client };
