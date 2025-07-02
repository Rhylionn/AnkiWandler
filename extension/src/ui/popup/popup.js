// Popup interface controller
import { MESSAGE_TYPES } from "../shared/constants.js";
import { formatDate } from "../shared/utils.js";

class PopupController {
  constructor() {
    this.elements = {};
    this.refreshInterval = null;
    this.init();
  }

  /**
   * Initialize popup
   */
  async init() {
    this.cacheElements();
    this.setupEventListeners();
    await this.loadData();
    this.startAutoRefresh();
  }

  /**
   * Cache DOM elements
   */
  cacheElements() {
    this.elements = {
      totalWords: document.getElementById("totalWords"),
      pendingSync: document.getElementById("pendingSync"),
      directWords: document.getElementById("directWords"),
      contextWords: document.getElementById("contextWords"),
      lastSync: document.getElementById("lastSync"),
      syncBtn: document.getElementById("syncBtn"),
      managerBtn: document.getElementById("managerBtn"),
      settingsBtn: document.getElementById("settingsBtn"),
      recentList: document.getElementById("recentList"),
      emptyState: document.getElementById("emptyState"),
      statusMessage: document.getElementById("statusMessage"),
      statusText: document.getElementById("statusText"),
      loadingOverlay: document.getElementById("loadingOverlay"),
    };
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    this.elements.syncBtn.addEventListener("click", () => this.handleSync());
    this.elements.managerBtn.addEventListener("click", () =>
      this.openManager()
    );
    this.elements.settingsBtn.addEventListener("click", () =>
      this.openSettings()
    );

    // Handle window focus for refresh
    window.addEventListener("focus", () => this.loadData());
  }

  /**
   * Load all data
   */
  async loadData() {
    try {
      await Promise.all([this.loadStats(), this.loadRecentWords()]);
    } catch (error) {
      console.error("Failed to load popup data:", error);
      this.showStatus("Failed to load data", "error");
    }
  }

  /**
   * Load statistics
   */
  async loadStats() {
    try {
      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.GET_STATS,
      });

      if (response.success) {
        const stats = response.data;
        this.updateStats(stats);
      } else {
        throw new Error(response.error);
      }
    } catch (error) {
      console.error("Failed to load stats:", error);
      // Set default values on error
      this.updateStats({
        totalWords: 0,
        directWords: 0,
        contextWords: 0,
        pendingWords: 0,
        lastSync: null,
      });
    }
  }

  /**
   * Update statistics display
   */
  updateStats(stats) {
    this.elements.totalWords.textContent = stats.totalWords || 0;
    this.elements.pendingSync.textContent = stats.pendingWords || 0;
    this.elements.directWords.textContent = stats.directWords || 0;
    this.elements.contextWords.textContent = stats.contextWords || 0;

    if (stats.lastSync) {
      this.elements.lastSync.textContent = formatDate(stats.lastSync);
    } else {
      this.elements.lastSync.textContent = "Never";
    }

    // Update sync button state
    if (stats.pendingWords > 0) {
      this.elements.syncBtn.classList.remove("disabled");
      this.elements.pendingSync.parentElement.style.backgroundColor = "#fef3c7";
    } else {
      this.elements.pendingSync.parentElement.style.backgroundColor = "#f0fdf4";
    }
  }

  /**
   * Load recent words
   */
  async loadRecentWords() {
    try {
      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.GET_WORDS,
        data: { limit: 5 },
      });

      if (response.success) {
        this.displayRecentWords(response.data);
      } else {
        throw new Error(response.error);
      }
    } catch (error) {
      console.error("Failed to load recent words:", error);
      this.displayRecentWords([]);
    }
  }

  /**
   * Display recent words
   */
  displayRecentWords(words) {
    if (!words || words.length === 0) {
      this.elements.recentList.style.display = "none";
      this.elements.emptyState.style.display = "block";
      return;
    }

    this.elements.recentList.style.display = "block";
    this.elements.emptyState.style.display = "none";

    this.elements.recentList.innerHTML = words
      .map((word) => this.createRecentWordElement(word))
      .join("");
  }

  /**
   * Create recent word element HTML
   */
  createRecentWordElement(word) {
    const truncatedText =
      word.text.length > 30 ? word.text.substring(0, 30) + "..." : word.text;

    const syncStatus = word.synced ? "" : "⏳";

    return `
      <div class="recent-item" data-word-id="${word.id}">
        <div class="recent-text">${this.escapeHtml(
          truncatedText
        )} ${syncStatus}</div>
        <div class="recent-meta">
          <span class="recent-type ${word.type}">${word.type}</span>
          <span class="recent-time">${formatDate(word.createdAt)}</span>
        </div>
      </div>
    `;
  }

  /**
   * Handle sync action
   */
  async handleSync() {
    if (this.elements.syncBtn.disabled) return;

    this.showLoading(true);
    this.elements.syncBtn.disabled = true;

    const originalText =
      this.elements.syncBtn.querySelector(".btn-text").textContent;
    this.elements.syncBtn.querySelector(".btn-text").textContent = "Syncing...";

    try {
      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.SYNC_TO_SERVER,
      });

      if (response.success) {
        this.showStatus(response.message, "success");
        await this.loadData(); // Refresh data after sync
      } else {
        this.showStatus(response.message || "Sync failed", "error");
      }
    } catch (error) {
      console.error("Sync failed:", error);
      this.showStatus("Sync failed: " + error.message, "error");
    } finally {
      this.showLoading(false);
      this.elements.syncBtn.disabled = false;
      this.elements.syncBtn.querySelector(".btn-text").textContent =
        originalText;
    }
  }

  /**
   * Open manager page
   */
  async openManager() {
    try {
      const url = chrome.runtime.getURL("src/ui/manager/manager.html");
      await chrome.tabs.create({ url });
      window.close();
    } catch (error) {
      console.error("Failed to open manager:", error);
      this.showStatus("Failed to open manager", "error");
    }
  }

  /**
   * Open settings page
   */
  async openSettings() {
    try {
      const url = chrome.runtime.getURL("src/ui/manager/manager.html#settings");
      await chrome.tabs.create({ url });
      window.close();
    } catch (error) {
      console.error("Failed to open settings:", error);
      this.showStatus("Failed to open settings", "error");
    }
  }

  /**
   * Show loading overlay
   */
  showLoading(show) {
    this.elements.loadingOverlay.style.display = show ? "flex" : "none";
  }

  /**
   * Show status message
   */
  showStatus(message, type = "info", duration = 3000) {
    this.elements.statusText.textContent = message;
    this.elements.statusMessage.className = `status-message ${type}`;
    this.elements.statusMessage.style.display = "block";

    // Auto-hide after duration
    setTimeout(() => {
      this.elements.statusMessage.style.display = "none";
    }, duration);
  }

  /**
   * Start auto-refresh
   */
  startAutoRefresh() {
    // Refresh every 30 seconds while popup is open
    this.refreshInterval = setInterval(() => {
      this.loadData();
    }, 30000);
  }

  /**
   * Stop auto-refresh
   */
  stopAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
      this.refreshInterval = null;
    }
  }

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Cleanup on window unload
   */
  cleanup() {
    this.stopAutoRefresh();
  }
}

// Initialize popup when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  const popup = new PopupController();

  // Cleanup on window unload
  window.addEventListener("beforeunload", () => {
    popup.cleanup();
  });
});

// Handle extension updates
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "dataUpdated") {
    // Refresh popup data when background notifies of changes
    const popup = window.popupController;
    if (popup) {
      popup.loadData();
    }
  }
});
