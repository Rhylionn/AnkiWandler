// Context menu management
import { MESSAGE_TYPES, COLLECTION_TYPES } from "../ui/shared/constants.js";
import { StorageManager } from "./storage-manager.js";
import { SyncService } from "./sync-service.js";

export class ContextMenus {
  /**
   * Initialize context menus
   */
  static async initialize() {
    try {
      // Remove all existing menus first
      await chrome.contextMenus.removeAll();

      // Create main context menus
      chrome.contextMenus.create({
        id: "ankiwandler-separator",
        type: "separator",
        contexts: ["selection"],
      });

      chrome.contextMenus.create({
        id: "collect-direct",
        title: "📝 Collect Word",
        contexts: ["selection"],
      });

      chrome.contextMenus.create({
        id: "collect-context",
        title: "📚 Collect with Context",
        contexts: ["selection"],
      });

      chrome.contextMenus.create({
        id: "ankiwandler-separator-2",
        type: "separator",
        contexts: ["selection"],
      });

      chrome.contextMenus.create({
        id: "open-manager",
        title: "⚙️ Open Manager",
        contexts: ["selection"],
      });

      console.log("Context menus initialized");
    } catch (error) {
      console.error("Failed to initialize context menus:", error);
    }
  }

  /**
   * Handle context menu clicks
   */
  static async handleClick(info, tab) {
    const selectedText = info.selectionText?.trim();

    if (!selectedText) {
      console.warn("No text selected");
      return;
    }

    try {
      switch (info.menuItemId) {
        case "collect-direct":
          await this.collectWord(selectedText, COLLECTION_TYPES.DIRECT, tab);
          break;

        case "collect-context":
          await this.openWordSelector(selectedText, tab);
          break;

        case "open-manager":
          await this.openManager();
          break;

        default:
          console.warn("Unknown menu item:", info.menuItemId);
      }
    } catch (error) {
      console.error("Context menu action failed:", error);
      this.showNotification("Action failed", "error");
    }
  }

  /**
   * Open word selector popup for context collection
   */
  static async openWordSelector(selectedText, tab) {
    try {
      console.log("Opening word selector for text:", selectedText);

      // Store selection data for popup access
      await chrome.storage.local.set({
        pendingWordSelection: {
          text: selectedText,
          timestamp: Date.now(),
          url: tab.url,
          title: tab.title,
        },
      });

      console.log("Stored pending selection, creating popup window...");

      // Get the word selector URL
      const popupUrl = chrome.runtime.getURL(
        "src/ui/word-selector/word-selector.html"
      );
      console.log("Popup URL:", popupUrl);

      // Create popup window without using screen object
      const popup = await chrome.windows.create({
        url: popupUrl,
        type: "popup",
        width: 650,
        height: 400,
        // Remove screen-dependent positioning - let Chrome position it
        focused: true,
      });

      console.log("Popup window created:", popup);

      // Store popup window ID for cleanup
      await chrome.storage.local.set({
        activeWordSelectorWindow: popup.id,
      });

      // Auto-cleanup after 60 seconds if no action taken
      setTimeout(async () => {
        try {
          await this.cleanupWordSelection();
        } catch (e) {
          console.warn("Auto-cleanup error:", e);
        }
      }, 60000);
    } catch (error) {
      console.error("Error opening word selector popup:", error);

      // Show error notification
      this.showNotification("Failed to open word selector", "error");

      // Fallback: direct context collection
      console.log("Falling back to direct context collection");
      await this.collectWord(selectedText, COLLECTION_TYPES.CONTEXT, tab);
    }
  }

  /**
   * Collect word directly without sending message to service worker
   */
  static async collectWord(text, type, tab) {
    try {
      // Save word directly using storage manager
      const word = await StorageManager.saveWord({
        text: text,
        type: type,
        context: type === COLLECTION_TYPES.CONTEXT ? text : null,
        url: tab.url,
        title: tab.title,
      });

      // Update badge count
      await this.updateBadge();

      // Notify content script for visual feedback
      if (tab.id) {
        chrome.tabs
          .sendMessage(tab.id, {
            type: "wordCollected",
            data: {
              text: text,
              type: type,
            },
          })
          .catch(() => {
            // Content script might not be available, ignore
          });
      }

      // Trigger auto-sync if enabled
      const settings = await StorageManager.getSettings();
      if (settings.autoSync) {
        SyncService.autoSync().catch(console.error);
      }

      this.showNotification(`Word collected: "${text}"`, "success");
    } catch (error) {
      console.error("Failed to collect word:", error);
      this.showNotification("Failed to collect word", "error");
    }
  }

  /**
   * Open manager page
   */
  static async openManager() {
    try {
      const url = chrome.runtime.getURL("src/ui/manager/manager.html");
      await chrome.tabs.create({ url });
    } catch (error) {
      console.error("Failed to open manager:", error);
    }
  }

  /**
   * Show notification
   */
  static showNotification(message, type = "info") {
    // For Manifest V3, we'll use the action badge instead of notifications
    // as notifications require additional permissions
    chrome.action.setBadgeText({ text: type === "success" ? "✓" : "✗" });
    chrome.action.setBadgeBackgroundColor({
      color: type === "success" ? "#10B981" : "#EF4444",
    });

    // Clear badge after 2 seconds
    setTimeout(() => {
      chrome.action.setBadgeText({ text: "" });
    }, 2000);
  }

  /**
   * Update context menu state based on selection
   */
  static async updateMenuState(hasSelection) {
    try {
      const menus = ["collect-direct", "collect-context"];

      for (const menuId of menus) {
        chrome.contextMenus.update(menuId, {
          enabled: hasSelection,
        });
      }
    } catch (error) {
      // Menu might not exist yet, ignore
    }
  }

  /**
   * Update extension badge with word count
   */
  static async updateBadge() {
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

  /**
   * Clean up word selection session
   */
  static async cleanupWordSelection() {
    try {
      const result = await chrome.storage.local.get([
        "activeWordSelectorWindow",
      ]);

      if (result.activeWordSelectorWindow) {
        try {
          await chrome.windows.remove(result.activeWordSelectorWindow);
        } catch (e) {
          // Window might already be closed
        }
      }

      await chrome.storage.local.remove([
        "pendingWordSelection",
        "activeWordSelectorWindow",
      ]);
    } catch (error) {
      console.error("Error during cleanup:", error);
    }
  }
}
