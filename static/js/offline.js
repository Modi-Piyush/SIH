/**
 * Offline Sync & IndexedDB Storage Engine (FR15, FR16, FR17)
 * Ensures 100% operational resilience during rural network outages.
 * Guarantees zero lost/duplicate transactions with idempotent UUID synchronization.
 */

const DB_NAME = 'FarmerProcureOfflineDB';
const DB_VERSION = 1;

class OfflineStorageManager {
  constructor() {
    this.db = null;
    this.isOnline = navigator.onLine;
    this.simulatedOffline = false;
    this.listeners = [];
  }

  async init() {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // 1. Offline Manifest Store (cached center bookings for gate verification)
        if (!db.objectStoreNames.contains('manifest')) {
          const manifestStore = db.createObjectStore('manifest', { keyPath: 'token_code' });
          manifestStore.createIndex('center_id', 'center_id', { unique: false });
        }

        // 2. Pending Offline Transactions Store
        if (!db.objectStoreNames.contains('pending_transactions')) {
          const pendingStore = db.createObjectStore('pending_transactions', { keyPath: 'client_tx_id' });
          pendingStore.createIndex('token_code', 'token_code', { unique: false });
          pendingStore.createIndex('status', 'status', { unique: false });
        }

        // 3. Synced Transactions Audit Store
        if (!db.objectStoreNames.contains('synced_audit')) {
          db.createObjectStore('synced_audit', { keyPath: 'client_tx_id' });
        }
      };

      request.onsuccess = (event) => {
        this.db = event.target.result;
        this.setupNetworkListeners();
        resolve(this.db);
      };

      request.onerror = (event) => {
        console.error('IndexedDB init error:', event.target.error);
        reject(event.target.error);
      };
    });
  }

  setupNetworkListeners() {
    window.addEventListener('online', () => {
      this.isOnline = true;
      this.notifyNetworkChange();
      if (!this.simulatedOffline) {
        this.syncPendingTransactions();
      }
    });

    window.addEventListener('offline', () => {
      this.isOnline = false;
      this.notifyNetworkChange();
    });
  }

  onNetworkChange(callback) {
    this.listeners.push(callback);
  }

  notifyNetworkChange() {
    const effectiveOnline = this.getEffectiveOnlineStatus();
    this.listeners.forEach((cb) => cb(effectiveOnline));
  }

  setSimulatedOffline(isSimulated) {
    this.simulatedOffline = isSimulated;
    this.notifyNetworkChange();
    if (!this.simulatedOffline && navigator.onLine) {
      this.syncPendingTransactions();
    }
  }

  getEffectiveOnlineStatus() {
    return navigator.onLine && !this.simulatedOffline;
  }

  // Cache manifest from server for offline verification
  async cacheManifest(bookings) {
    if (!this.db || !bookings || !bookings.length) return;
    const tx = this.db.transaction(['manifest'], 'readwrite');
    const store = tx.objectStore('manifest');

    for (const b of bookings) {
      store.put(b);
    }

    return new Promise((resolve) => {
      tx.oncomplete = () => resolve(true);
      tx.onerror = () => resolve(false);
    });
  }

  // Lookup booking in offline IndexedDB
  async lookupOfflineBooking(tokenCode) {
    if (!this.db) return null;
    return new Promise((resolve) => {
      const tx = this.db.transaction(['manifest'], 'readonly');
      const store = tx.objectStore('manifest');
      const req = store.get(tokenCode.trim());

      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => resolve(null);
    });
  }

  // Queue a check-in transaction offline
  async queueOfflineCheckIn(tokenCode, tractorNumber, farmerName = '') {
    if (!this.db) return null;

    const clientTxId = `TX-${Date.now()}-${Math.random().toString(36).substring(2, 9).toUpperCase()}`;
    const txItem = {
      client_tx_id: clientTxId,
      sync_type: 'CHECK_IN',
      token_code: tokenCode.trim(),
      payload: {
        tractor_number: tractorNumber || 'UP-65-OFFLINE',
        farmer_name: farmerName,
        checkin_mode: 'OFFLINE_GATE_ENTRY'
      },
      client_timestamp: new Date().toISOString(),
      device_id: 'GATE-TAB-01',
      status: 'PENDING_SYNC'
    };

    return new Promise((resolve, reject) => {
      const tx = this.db.transaction(['pending_transactions'], 'readwrite');
      const store = tx.objectStore('pending_transactions');
      const req = store.put(txItem);

      tx.oncomplete = () => {
        // Also update local manifest so gate guard immediately sees updated state locally
        this.updateLocalManifestStatus(tokenCode, 'CHECKED_IN');
        resolve(txItem);
      };

      tx.onerror = (e) => reject(e.target.error);
    });
  }

  async updateLocalManifestStatus(tokenCode, newStatus) {
    if (!this.db) return;
    const tx = this.db.transaction(['manifest'], 'readwrite');
    const store = tx.objectStore('manifest');
    const getReq = store.get(tokenCode);

    getReq.onsuccess = () => {
      if (getReq.result) {
        const updated = { ...getReq.result, status: newStatus };
        store.put(updated);
      }
    };
  }

  // Get list of pending offline transactions
  async getPendingTransactions() {
    if (!this.db) return [];
    return new Promise((resolve) => {
      const tx = this.db.transaction(['pending_transactions'], 'readonly');
      const store = tx.objectStore('pending_transactions');
      const req = store.getAll();

      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => resolve([]);
    });
  }

  // Sync all pending transactions to backend
  async syncPendingTransactions() {
    if (!this.getEffectiveOnlineStatus()) {
      return { status: 'offline', message: 'Currently offline. Transactions are queued locally.' };
    }

    const pending = await this.getPendingTransactions();
    if (!pending.length) {
      return { status: 'synced', message: 'Offline queue is clear. All transactions synced.', count: 0 };
    }

    try {
      const response = await fetch('/api/sync-offline-transactions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          device_id: 'GATE-TAB-01',
          transactions: pending
        })
      });

      if (!response.ok) {
        throw new Error(`Sync failed with server status ${response.status}`);
      }

      const syncResult = await response.json();

      // Clear pending and move to audit
      const tx = this.db.transaction(['pending_transactions', 'synced_audit'], 'readwrite');
      const pendingStore = tx.objectStore('pending_transactions');
      const auditStore = tx.objectStore('synced_audit');

      for (const item of pending) {
        pendingStore.delete(item.client_tx_id);
        auditStore.put({ ...item, synced_at: new Date().toISOString(), sync_status: 'SYNCED_OK' });
      }

      return new Promise((resolve) => {
        tx.oncomplete = () => {
          resolve({
            status: 'success',
            synced_count: syncResult.synced_count,
            duplicate_count: syncResult.duplicate_count,
            message: `Synchronized ${syncResult.synced_count} offline transactions seamlessly!`
          });
        };
        tx.onerror = () => resolve({ status: 'error', message: 'Failed to clear local queue after sync.' });
      });

    } catch (err) {
      console.error('Offline sync error:', err);
      return { status: 'error', message: `Sync error: ${err.message}` };
    }
  }
}

// Global instance
window.offlineStorage = new OfflineStorageManager();
window.addEventListener('DOMContentLoaded', () => {
  window.offlineStorage.init().then(() => {
    console.log('Farmer Procurement Offline DB initialized.');
  });
});
