// Sync service for server communication
import { StorageManager } from "./storage-manager.js";
import { API_ENDPOINTS, SYNC_STATUS } from "../ui/shared/constants.js";

export class SyncService {
  static currentSyncPromise = null;

  /**
   * Sync words to server
   */
  static async syncToServer() {
    // Prevent multiple simultaneous syncs
    if (this.currentSyncPromise) {
      return this.currentSyncPromise;
    }

    this.currentSyncPromise = this._performSync();

    try {
      const result = await this.currentSyncPromise;
      return result;
    } finally {
      this.currentSyncPromise = null;
    }
  }

  /**
   * Perform the actual sync operation
   */
  static async _performSync() {
    try {
      const settings = await StorageManager.getSettings();

      if (!settings.serverUrl || !settings.apiKey) {
        throw new Error("Server configuration missing");
      }

      // Get unsynced words
      const unsyncedWords = await StorageManager.getUnsyncedWords();

      if (unsyncedWords.length === 0) {
        return {
          success: true,
          message: "No words to sync",
          syncedCount: 0,
        };
      }

      // Prepare words for API
      const words = unsyncedWords.map((word) => ({
        word: word.text,
        date: word.createdAt.split("T")[0],
        context_sentence: word.context || null,
        needs_article: word.type === "context",
      }));

      // Send to server
      const result = await this._sendWordsToServer(settings, words);

      if (result.success) {
        // Mark words as synced
        const wordIds = unsyncedWords.map((word) => word.id);
        await StorageManager.markWordsSynced(wordIds);

        // Update sync statistics
        await StorageManager.updateSyncStats(unsyncedWords.length);

        return {
          success: true,
          message: `Synced ${unsyncedWords.length} words`,
          syncedCount: unsyncedWords.length,
        };
      } else {
        throw new Error(result.message || "Server returned error");
      }
    } catch (error) {
      console.error("Sync failed:", error);
      return {
        success: false,
        message: error.message,
        syncedCount: 0,
      };
    }
  }

  /**
   * Send words to server
   */
  static async _sendWordsToServer(settings, words) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout

    try {
      const response = await fetch(
        `${settings.serverUrl}${API_ENDPOINTS.ADD_WORD_LIST}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${settings.apiKey}`,
          },
          body: JSON.stringify({ words }),
          signal: controller.signal,
        }
      );

      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server error: ${response.status} - ${errorText}`);
      }

      const result = await response.json();
      return { success: true, data: result };
    } catch (error) {
      clearTimeout(timeoutId);

      if (error.name === "AbortError") {
        throw new Error("Request timeout");
      }

      throw error;
    }
  }

  /**
   * Test server connection
   */
  static async testConnection(serverUrl, apiKey) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout

    try {
      const response = await fetch(`${serverUrl}${API_ENDPOINTS.HEALTH}`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${apiKey}`,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      return {
        success: response.ok,
        message: response.ok
          ? "Connection successful"
          : `Server error: ${response.status}`,
        status: response.status,
      };
    } catch (error) {
      clearTimeout(timeoutId);

      if (error.name === "AbortError") {
        return {
          success: false,
          message: "Connection timeout",
          status: 0,
        };
      }

      return {
        success: false,
        message: `Connection failed: ${error.message}`,
        status: 0,
      };
    }
  }

  /**
   * Auto-sync based on settings
   */
  static async autoSync() {
    try {
      const settings = await StorageManager.getSettings();

      if (!settings.autoSync || !settings.serverUrl || !settings.apiKey) {
        return;
      }

      const unsyncedWords = await StorageManager.getUnsyncedWords();

      if (unsyncedWords.length === 0) {
        return;
      }

      console.log(`Auto-syncing ${unsyncedWords.length} words...`);
      const result = await this.syncToServer();

      if (result.success) {
        console.log(`Auto-sync completed: ${result.message}`);
      } else {
        console.error(`Auto-sync failed: ${result.message}`);
      }
    } catch (error) {
      console.error("Auto-sync error:", error);
    }
  }

  /**
   * Schedule periodic sync
   */
  static startPeriodicSync() {
    // Clear any existing interval
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
    }

    // Set up new interval
    this.syncInterval = setInterval(async () => {
      const settings = await StorageManager.getSettings();
      if (settings.autoSync) {
        await this.autoSync();
      }
    }, 300000); // 5 minutes
  }

  /**
   * Stop periodic sync
   */
  static stopPeriodicSync() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  /**
   * Get sync status
   */
  static async getSyncStatus() {
    try {
      const unsyncedWords = await StorageManager.getUnsyncedWords();
      const stats = await StorageManager.getStats();

      return {
        pendingWords: unsyncedWords.length,
        lastSync: stats.lastSync,
        syncCount: stats.syncCount,
        isOnline: navigator.onLine,
      };
    } catch (error) {
      console.error("Failed to get sync status:", error);
      return {
        pendingWords: 0,
        lastSync: null,
        syncCount: 0,
        isOnline: false,
      };
    }
  }

  /**
   * Retry failed syncs with exponential backoff
   */
  static async retrySync(maxRetries = 3) {
    let lastError;

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        const result = await this.syncToServer();
        if (result.success) {
          return result;
        }
        lastError = new Error(result.message);
      } catch (error) {
        lastError = error;
      }

      if (attempt < maxRetries) {
        const delay = Math.pow(2, attempt) * 1000; // Exponential backoff
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }

    throw lastError;
  }
}
