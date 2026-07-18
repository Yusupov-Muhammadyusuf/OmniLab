export function readStorageValue(key) {
    try {
        return window.localStorage.getItem(key);
    }
    catch {
        return null;
    }
}
export function writeStorageValue(key, value) {
    try {
        window.localStorage.setItem(key, value);
    }
    catch {
        // Persistence is optional. Keep the in-memory lab session usable.
    }
}
export function removeStorageValue(key) {
    try {
        window.localStorage.removeItem(key);
    }
    catch {
        // Persistence is optional. Keep the in-memory lab session usable.
    }
}
//# sourceMappingURL=storage.js.map
