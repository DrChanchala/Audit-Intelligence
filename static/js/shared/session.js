/**
 * Session utilities: hardens the client session by purging legacy token-bearing
 * localStorage keys (siteiq_*, token, etc.) and enforcing pure cookie-based sessions.
 */

export function purgeLegacyStorage() {
  try {
    const toRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && (key.startsWith('siteiq_') || key.toLowerCase().includes('token') || key.toLowerCase().includes('auth'))) {
        toRemove.push(key);
      }
    }
    toRemove.forEach(k => {
      try { localStorage.removeItem(k); } catch (_) {}
    });
  } catch (_) {
    // LocalStorage may be blocked by user privacy settings
  }
}

// Purge on module load
purgeLegacyStorage();
