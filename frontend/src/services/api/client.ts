import { toCamelCaseObject } from '../../utils/case';
import { BASE_URL } from './env';

export async function apiFetch<T>(
    url: string,
    options: RequestInit = {},
): Promise<T> {
    const res = await fetch(`${BASE_URL}${url}`, {
        ...options,
        headers: {
            accept: 'application/json',
            ...options.headers,
        },
    });

    if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
    }

    if (res.status === 204) {
        return undefined as T;
    }

    const data = await res.json();
    return toCamelCaseObject(data) as T;
}
