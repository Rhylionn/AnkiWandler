// Main service worker for Manifest V3
import { StorageManager } from "./storage-manager.js";
import { SyncService } from "./sync-service.js";
import { ContextMenus } from "./context-menus.js";
import { MESSAGE_TYPES, COLLECTION_TYPES } from "../ui/shared/constants.js";

// Service worker installation and initialization
chrome.runtime.onInstalled.addListener(async (details) => {
  console.log("AnkiWandler service worker installed:", details.reason);

  try {
    // Initialize storage
    await StorageManager.initialize();

    // Initialize context menus
    await ContextMenus.initialize();

    // Update badge
    await updateBadge();

    console.log("Service worker initialization completed");
  } catch (error) {
    console.error("Service worker initialization failed:", error);
  }
});

// Service worker startup
chrome.runtime.onStartup.addListener(async () => {
  console.log("AnkiWandler service worker started");

  try {
    await updateBadge();
    SyncService.startPeriodicSync();
  } catch (error) {
    console.error("Service worker startup failed:", error);
  }
});

// Context menu click handler
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  await ContextMenus.handleClick(info, tab);
});

// Message handler for communication between components
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender, sendResponse);
  return true; // Keep message channel open for async responses
});

/**
 * Handle messages from content scripts and UI components
 */
async function handleMessage(message, sender, sendResponse) {
  try {
    const { type, data } = message;

    console.log("Received message:", type, data);

    switch (type) {
      case MESSAGE_TYPES.COLLECT_WORD:
        await handleCollectWord(data, sendResponse);
        break;

      case MESSAGE_TYPES.COLLECT_WITH_CONTEXT:
        await handleCollectWithContext(data, sendResponse);
        break;

      case MESSAGE_TYPES.SYNC_TO_SERVER:
        await handleSyncToServer(sendResponse);
        break;

      case MESSAGE_TYPES.GET_STATS:
        await handleGetStats(sendResponse);
        break;

      case MESSAGE_TYPES.GET_WORDS:
        await handleGetWords(data, sendResponse);
        break;

      case MESSAGE_TYPES.DELETE_WORD:
        await handleDeleteWord(data, sendResponse);
        break;

      case MESSAGE_TYPES.CLEAR_ALL:
        await handleClearAll(sendResponse);
        break;

      case MESSAGE_TYPES.UPDATE_SETTINGS:
        await handleUpdateSettings(data, sendResponse);
        break;

      case MESSAGE_TYPES.TEST_CONNECTION:
        await handleTestConnection(data, sendResponse);
        break;

      case "selectionMade":
        // Just acknowledge selection, no action needed
        sendResponse({ success: true });
        break;

      case "cleanupWordSelector":
        await ContextMenus.cleanupWordSelection();
        sendResponse({ success: true });
        break;

      default:
        console.warn("Unknown message type:", type);
        sendResponse({ success: false, error: "Unknown message type" });
    }
  } catch (error) {
    console.error("Message handling failed:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handle word collection
 */
async function handleCollectWord(data, sendResponse) {
  try {
    const word = await StorageManager.saveWord({
      text: data.text,
      type: COLLECTION_TYPES.DIRECT,
      context: null,
      url: data.url,
      title: data.title,
    });

    await updateBadge();

    // Auto-sync if enabled
    const settings = await StorageManager.getSettings();
    if (settings.autoSync) {
      SyncService.autoSync().catch(console.error);
    }

    sendResponse({
      success: true,
      word,
      message: "Word collected successfully",
    });
  } catch (error) {
    console.error("Failed to collect word:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handle word collection with context
 */
async function handleCollectWithContext(data, sendResponse) {
  try {
    const word = await StorageManager.saveWord({
      text: data.text,
      type: COLLECTION_TYPES.CONTEXT,
      context: data.context,
      url: data.url,
      title: data.title,
    });

    await updateBadge();

    // Auto-sync if enabled
    const settings = await StorageManager.getSettings();
    if (settings.autoSync) {
      SyncService.autoSync().catch(console.error);
    }

    sendResponse({
      success: true,
      word,
      message: "Word with context collected successfully",
    });
  } catch (error) {
    console.error("Failed to collect word with context:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handle sync to server
 */
async function handleSyncToServer(sendResponse) {
  try {
    const result = await SyncService.syncToServer();
    await updateBadge();
    sendResponse(result);
  } catch (error) {
    console.error("Sync failed:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handle get statistics
 */
async function handleGetStats(sendResponse) {
  try {
    const stats = await StorageManager.getStats();
    const syncStatus = await SyncService.getSyncStatus();
    const storageUsage = await StorageManager.getStorageUsage();

    sendResponse({
      success: true,
      data: {
        ...stats,
        ...syncStatus,
        storage: storageUsage,
      },
    });
  } catch (error) {
    console.error("Failed to get stats:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handle get words
 */
async function handleGetWords(data, sendResponse) {
  try {
    const { limit, search } = data || {};

    let words;
    if (search) {
      words = await StorageManager.searchWords(search);
    } else {
      words = await StorageManager.getWords(limit);
    }

    sendResponse({ success: true, data: words });
  } catch (error) {
    console.error("Failed to get words:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handle delete word
 */
async function handleDeleteWord(data, sendResponse) {
  try {
    const success = await StorageManager.deleteWord(data.wordId);
    await updateBadge();

    sendResponse({
      success,
      message: success ? "Word deleted successfully" : "Failed to delete word",
    });
  } catch (error) {
    console.error("Failed to delete word:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handle clear all words
 */
async function handleClearAll(sendResponse) {
  try {
    const success = await StorageManager.clearAllWords();
    await updateBadge();

    sendResponse({
      success,
      message: success
        ? "All words cleared successfully"
        : "Failed to clear words",
    });
  } catch (error) {
    console.error("Failed to clear words:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handle update settings
 */
async function handleUpdateSettings(data, sendResponse) {
  try {
    const settings = await StorageManager.saveSettings(data);

    // Restart periodic sync with new settings
    SyncService.stopPeriodicSync();
    SyncService.startPeriodicSync();

    sendResponse({
      success: true,
      data: settings,
      message: "Settings updated successfully",
    });
  } catch (error) {
    console.error("Failed to update settings:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Handle test connection
 */
async function handleTestConnection(data, sendResponse) {
  try {
    const result = await SyncService.testConnection(
      data.serverUrl,
      data.apiKey
    );
    sendResponse(result);
  } catch (error) {
    console.error("Connection test failed:", error);
    sendResponse({ success: false, error: error.message });
  }
}

/**
 * Update extension badge with word count
 */
async function updateBadge() {
  try {
    const words = await StorageManager.getWords();
    const unsyncedCount = words.filter((word) => !word.synced).length;

    if (unsyncedCount > 0) {
      await chrome.action.setBadgeText({ text: unsyncedCount.toString() });
      await chrome.action.setBadgeBackgroundColor({ color: "#3B82F6" });
    } else {
      await chrome.action.setBadgeText({ text: "" });
    }
  } catch (error) {
    console.error("Failed to update badge:", error);
  }
}

// Handle window closed event
chrome.windows.onRemoved.addListener(async (windowId) => {
  try {
    const result = await chrome.storage.local.get(["activeWordSelectorWindow"]);

    if (result.activeWordSelectorWindow === windowId) {
      // Word selector window was closed, clean up
      await chrome.storage.local.remove([
        "pendingWordSelection",
        "activeWordSelectorWindow",
      ]);
    }
  } catch (error) {
    // Ignore errors during cleanup
  }
});

// Handle network state changes
self.addEventListener("online", () => {
  console.log("Network back online, attempting auto-sync...");
  SyncService.autoSync().catch(console.error);
});

// Periodic cleanup (run every hour)
setInterval(async () => {
  try {
    await StorageManager.cleanup();
  } catch (error) {
    console.error("Cleanup failed:", error);
  }
}, 3600000);

console.log("AnkiWandler service worker loaded");
