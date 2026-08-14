import { Injectable } from '@angular/core';

interface CacheEntry {
  value: any;
  expiresAt: number;
  uid: string | null;
}

const STORAGE_KEY = 'moscowle_data_cache_v1';

@Injectable({
  providedIn: 'root'
})
export class DataCacheService {
  private store = new Map<string, CacheEntry>();
  private loaded = false;

  get<T>(key: string): T | null {
    this.ensureLoaded();
    const uid = this.currentUserId();
    const entry = this.store.get(key);
    if (!entry || entry.uid !== uid) {
      return null;
    }
    if (Date.now() > entry.expiresAt) {
      this.store.delete(key);
      this.persist();
      return null;
    }
    return entry.value as T;
  }

  set(key: string, value: any, ttlMs: number): void {
    this.ensureLoaded();
    this.store.set(key, {
      value,
      expiresAt: Date.now() + ttlMs,
      uid: this.currentUserId()
    });
    this.persist();
  }

  delete(key: string): void {
    if (this.store.delete(key)) {
      this.persist();
    }
  }

  invalidateContaining(substring: string): void {
    let changed = false;
    for (const key of this.store.keys()) {
      if (key.includes(substring)) {
        this.store.delete(key);
        changed = true;
      }
    }
    if (changed) {
      this.persist();
    }
  }

  invalidateExcept(exceptions: string[]): void {
    let changed = false;
    for (const key of this.store.keys()) {
      if (!exceptions.some(e => key.includes(e))) {
        this.store.delete(key);
        changed = true;
      }
    }
    if (changed) {
      this.persist();
    }
  }

  clear(): void {
    if (this.store.size > 0) {
      this.store.clear();
      this.persist();
    }
  }

  clearForUser(): void {
    const uid = this.currentUserId();
    let changed = false;
    for (const [key, entry] of this.store.entries()) {
      if (entry.uid === uid || entry.uid === null) {
        this.store.delete(key);
        changed = true;
      }
    }
    if (changed) {
      this.persist();
    }
  }

  private currentUserId(): string | null {
    try {
      const raw = localStorage.getItem('user');
      if (!raw) {
        return null;
      }
      const user = JSON.parse(raw);
      return user?.id != null ? String(user.id) : null;
    } catch {
      return null;
    }
  }

  private ensureLoaded(): void {
    if (this.loaded) {
      return;
    }
    this.loaded = true;
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw);
      const now = Date.now();
      for (const [key, entry] of Object.entries<CacheEntry>(parsed)) {
        if (entry && entry.expiresAt > now) {
          this.store.set(key, entry);
        }
      }
    } catch {
      this.store.clear();
    }
  }

  private persist(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(Object.fromEntries(this.store)));
    } catch {
      try {
        localStorage.removeItem(STORAGE_KEY);
      } catch {
        // almacenamiento no disponible
      }
    }
  }
}
