// Storage manager for secure and efficient data handling
import { STORAGE_KEYS, DEFAULT_SETTINGS } from "../ui/shared/constants.js";

export class StorageManager {
  /**
   * Initialize storage with default values
   */
  static async initialize() {
    try {
      const result = await chrome.storage.local.get(
        Object.values(STORAGE_KEYS)
      );

      // Initialize missing keys with defaults
      const updates = {};

      if (!result[STORAGE_KEYS.WORDS]) {
        updates[STORAGE_KEYS.WORDS] = [];
      }

      if (!result[STORAGE_KEYS.SETTINGS]) {
        updates[STORAGE_KEYS.SETTINGS] = DEFAULT_SETTINGS;
      }

      if (!result[STORAGE_KEYS.SYNC_QUEUE]) {
        updates[STORAGE_KEYS.SYNC_QUEUE] = [];
      }

      if (!result[STORAGE_KEYS.STATS]) {
        updates[STORAGE_KEYS.STATS] = {
          totalWords: 0,
          directWords: 0,
          contextWords: 0,
          lastSync: null,
          syncCount: 0,
        };
      }

      if (Object.keys(updates).length > 0) {
        await chrome.storage.local.set(updates);
      }

      console.log("Storage initialized successfully");
    } catch (error) {
      console.error("Failed to initialize storage:", error);
      throw new Error("Storage initialization failed");
    }
  }

  /**
   * Save a word to storage
   */
  static async saveWord(wordData) {
    try {
      console.log("Saving word:", wordData);

      const result = await chrome.storage.local.get([
        STORAGE_KEYS.WORDS,
        STORAGE_KEYS.STATS,
      ]);

      const word = {
        id: Date.now().toString(36) + Math.random().toString(36).substr(2),
        text: wordData.text,
        type: wordData.type,
        context: wordData.context || null,
        createdAt: new Date().toISOString(),
        synced: false,
        url: wordData.url || null,
        title: wordData.title || null,
      };

      const currentWords = result[STORAGE_KEYS.WORDS] || [];
      const updatedWords = [word, ...currentWords];

      // Keep only the latest 1000 words
      if (updatedWords.length > 1000) {
        updatedWords.splice(1000);
      }

      // Update stats
      const currentStats = result[STORAGE_KEYS.STATS] || {
        totalWords: 0,
        directWords: 0,
        contextWords: 0,
        lastSync: null,
        syncCount: 0,
      };

      const updatedStats = { ...currentStats };
      updatedStats.totalWords = updatedWords.length;
      updatedStats.directWords = updatedWords.filter(
        (w) => w.type === "direct"
      ).length;
      updatedStats.contextWords = updatedWords.filter(
        (w) => w.type === "context"
      ).length;

      await chrome.storage.local.set({
        [STORAGE_KEYS.WORDS]: updatedWords,
        [STORAGE_KEYS.STATS]: updatedStats,
      });

      console.log("Word saved successfully:", word);
      return word;
    } catch (error) {
      console.error("Failed to save word:", error);
      throw new Error("Failed to save word to storage");
    }
  }

  /**
   * Get all words
   */
  static async getWords(limit = null) {
    try {
      const result = await chrome.storage.local.get(STORAGE_KEYS.WORDS);
      const words = result[STORAGE_KEYS.WORDS] || [];

      return limit ? words.slice(0, limit) : words;
    } catch (error) {
      console.error("Failed to get words:", error);
      return [];
    }
  }

  /**
   * Delete a word
   */
  static async deleteWord(wordId) {
    try {
      const result = await chrome.storage.local.get([
        STORAGE_KEYS.WORDS,
        STORAGE_KEYS.STATS,
      ]);

      const currentWords = result[STORAGE_KEYS.WORDS] || [];
      const updatedWords = currentWords.filter((word) => word.id !== wordId);

      // Update stats
      const currentStats = result[STORAGE_KEYS.STATS] || {};
      const updatedStats = { ...currentStats };
      updatedStats.totalWords = updatedWords.length;
      updatedStats.directWords = updatedWords.filter(
        (w) => w.type === "direct"
      ).length;
      updatedStats.contextWords = updatedWords.filter(
        (w) => w.type === "context"
      ).length;

      await chrome.storage.local.set({
        [STORAGE_KEYS.WORDS]: updatedWords,
        [STORAGE_KEYS.STATS]: updatedStats,
      });

      return true;
    } catch (error) {
      console.error("Failed to delete word:", error);
      return false;
    }
  }

  /**
   * Clear all words
   */
  static async clearAllWords() {
    try {
      const stats = await this.getStats();
      const updatedStats = { ...stats };
      updatedStats.totalWords = 0;
      updatedStats.directWords = 0;
      updatedStats.contextWords = 0;

      await chrome.storage.local.set({
        [STORAGE_KEYS.WORDS]: [],
        [STORAGE_KEYS.STATS]: updatedStats,
      });

      return true;
    } catch (error) {
      console.error("Failed to clear words:", error);
      return false;
    }
  }

  /**
   * Get settings
   */
  static async getSettings() {
    try {
      const result = await chrome.storage.local.get(STORAGE_KEYS.SETTINGS);
      return { ...DEFAULT_SETTINGS, ...result[STORAGE_KEYS.SETTINGS] };
    } catch (error) {
      console.error("Failed to get settings:", error);
      return DEFAULT_SETTINGS;
    }
  }

  /**
   * Save settings
   */
  static async saveSettings(settings) {
    try {
      const currentSettings = await this.getSettings();
      const updatedSettings = { ...currentSettings, ...settings };

      // Validate critical settings
      if (settings.serverUrl && !this.isValidUrl(settings.serverUrl)) {
        throw new Error("Invalid server URL");
      }

      await chrome.storage.local.set({
        [STORAGE_KEYS.SETTINGS]: updatedSettings,
      });

      return updatedSettings;
    } catch (error) {
      console.error("Failed to save settings:", error);
      throw new Error("Failed to save settings");
    }
  }

  /**
   * Get statistics
   */
  static async getStats() {
    try {
      const result = await chrome.storage.local.get(STORAGE_KEYS.STATS);
      return (
        result[STORAGE_KEYS.STATS] || {
          totalWords: 0,
          directWords: 0,
          contextWords: 0,
          lastSync: null,
          syncCount: 0,
        }
      );
    } catch (error) {
      console.error("Failed to get stats:", error);
      return {
        totalWords: 0,
        directWords: 0,
        contextWords: 0,
        lastSync: null,
        syncCount: 0,
      };
    }
  }

  /**
   * Update sync statistics
   */
  static async updateSyncStats(syncedCount) {
    try {
      const stats = await this.getStats();
      const updatedStats = {
        ...stats,
        lastSync: new Date().toISOString(),
        syncCount: stats.syncCount + 1,
      };

      await chrome.storage.local.set({
        [STORAGE_KEYS.STATS]: updatedStats,
      });

      return updatedStats;
    } catch (error) {
      console.error("Failed to update sync stats:", error);
    }
  }

  /**
   * Mark words as synced
   */
  static async markWordsSynced(wordIds) {
    try {
      const result = await chrome.storage.local.get(STORAGE_KEYS.WORDS);
      const currentWords = result[STORAGE_KEYS.WORDS] || [];

      const updatedWords = currentWords.map((word) => {
        if (wordIds.includes(word.id)) {
          return { ...word, synced: true };
        }
        return word;
      });

      await chrome.storage.local.set({
        [STORAGE_KEYS.WORDS]: updatedWords,
      });

      return true;
    } catch (error) {
      console.error("Failed to mark words as synced:", error);
      return false;
    }
  }

  /**
   * Get unsynced words
   */
  static async getUnsyncedWords() {
    try {
      const words = await this.getWords();
      return words.filter((word) => !word.synced);
    } catch (error) {
      console.error("Failed to get unsynced words:", error);
      return [];
    }
  }

  /**
   * Get storage usage
   */
  static async getStorageUsage() {
    try {
      const result = await chrome.storage.local.get(null);
      const usage = {
        totalBytes: new Blob([JSON.stringify(result)]).size,
        words: new Blob([JSON.stringify(result[STORAGE_KEYS.WORDS] || [])])
          .size,
        settings: new Blob([
          JSON.stringify(result[STORAGE_KEYS.SETTINGS] || {}),
        ]).size,
      };

      return usage;
    } catch (error) {
      console.error("Failed to get storage usage:", error);
      return { totalBytes: 0, words: 0, settings: 0 };
    }
  }

  /**
   * Search words
   */
  static async searchWords(query) {
    try {
      const words = await this.getWords();
      const lowerQuery = query.toLowerCase();

      return words.filter(
        (word) =>
          word.text.toLowerCase().includes(lowerQuery) ||
          (word.context && word.context.toLowerCase().includes(lowerQuery))
      );
    } catch (error) {
      console.error("Failed to search words:", error);
      return [];
    }
  }

  /**
   * Validate URL
   */
  static isValidUrl(string) {
    try {
      const url = new URL(string);
      return url.protocol === "http:" || url.protocol === "https:";
    } catch (_) {
      return false;
    }
  }

  /**
   * Clean up old data
   */
  static async cleanup() {
    try {
      const words = await this.getWords();
      const oneMonthAgo = new Date();
      oneMonthAgo.setMonth(oneMonthAgo.getMonth() - 1);

      // Remove synced words older than 1 month
      const filteredWords = words.filter((word) => {
        if (!word.synced) return true;
        return new Date(word.createdAt) > oneMonthAgo;
      });

      if (filteredWords.length !== words.length) {
        await chrome.storage.local.set({
          [STORAGE_KEYS.WORDS]: filteredWords,
        });

        console.log(
          `Cleaned up ${words.length - filteredWords.length} old words`
        );
      }
    } catch (error) {
      console.error("Failed to cleanup storage:", error);
    }
  }
}
