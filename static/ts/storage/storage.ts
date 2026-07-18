export function readStorageValue(key: string): string | null {
    try {
        return window.localStorage.getItem(key);
    } catch {
        return null;
    }
}

export function writeStorageValue(key: string, value: string): void {
    try {
        window.localStorage.setItem(key, value);
    } catch {
        // Persistence is optional. Keep the in-memory lab session usable.
    }
}

export function removeStorageValue(key: string): void {
    try {
        window.localStorage.removeItem(key);
    } catch {
        // Persistence is optional. Keep the in-memory lab session usable.
    }
}
