function camelToSnake(key: string): string {
    return key.replace(/[A-Z]/g, (m) => `_${m.toLowerCase()}`);
}

function snakeToCamel(key: string): string {
    return key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

export function toSnakeCaseObject<T>(obj: T): T {
    if (Array.isArray(obj)) {
        return obj.map(toSnakeCaseObject) as T;
    }
    if (obj !== null && typeof obj === 'object') {
        return Object.fromEntries(
            Object.entries(obj).map(([key, value]) => [
                camelToSnake(key),
                toSnakeCaseObject(value),
            ]),
        ) as T;
    }
    return obj;
}

export function toCamelCaseObject<T>(obj: T): T {
    if (Array.isArray(obj)) {
        return obj.map(toCamelCaseObject) as T;
    }
    if (obj !== null && typeof obj === 'object') {
        return Object.fromEntries(
            Object.entries(obj).map(([key, value]) => [
                snakeToCamel(key),
                toCamelCaseObject(value),
            ]),
        ) as T;
    }
    return obj;
}
