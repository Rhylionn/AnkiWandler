// Manager interface controller
import { MESSAGE_TYPES, DEFAULT_SETTINGS } from "../shared/constants.js";
import {
  formatDate,
  formatBytes,
  debounce,
  escapeHtml,
} from "../shared/utils.js";

class ManagerController {
  constructor() {
    this.elements = {};
    this.currentWords = [];
    this.filteredWords = [];
    this.selectedWords = new Set();
    this.currentPage = 1;
    this.itemsPerPage = 20;
    this.searchQuery = "";
    this.filters = { type: "", sync: "" };

    this.init();
  }

  /**
   * Initialize manager
   */
  async init() {
    this.cacheElements();
    this.setupEventListeners();
    this.handleHashNavigation();
    await this.loadInitialData();
  }

  /**
   * Cache DOM elements
   */
  cacheElements() {
    this.elements = {
      // Navigation
      navItems: document.querySelectorAll(".nav-item"),
      sections: document.querySelectorAll(".section"),

      // Header
      syncBtn: document.getElementById("syncBtn"),

      // Words section
      searchInput: document.getElementById("searchInput"),
      typeFilter: document.getElementById("typeFilter"),
      syncFilter: document.getElementById("syncFilter"),
      selectAllBtn: document.getElementById("selectAllBtn"),
      deleteSelectedBtn: document.getElementById("deleteSelectedBtn"),
      wordsList: document.getElementById("wordsList"),
      emptyState: document.getElementById("emptyState"),
      pagination: document.getElementById("pagination"),
      prevBtn: document.getElementById("prevBtn"),
      nextBtn: document.getElementById("nextBtn"),
      pageInfo: document.getElementById("pageInfo"),

      // Stats
      totalCount: document.getElementById("totalCount"),
      directCount: document.getElementById("directCount"),
      contextCount: document.getElementById("contextCount"),
      pendingCount: document.getElementById("pendingCount"),
      lastSyncTime: document.getElementById("lastSyncTime"),
      syncCount: document.getElementById("syncCount"),
      pendingSyncCount: document.getElementById("pendingSyncCount"),
      totalStorage: document.getElementById("totalStorage"),
      wordsStorage: document.getElementById("wordsStorage"),
      settingsStorage: document.getElementById("settingsStorage"),

      // Settings
      serverUrl: document.getElementById("serverUrl"),
      apiKey: document.getElementById("apiKey"),
      showApiKey: document.getElementById("showApiKey"),
      testConnectionBtn: document.getElementById("testConnectionBtn"),
      connectionStatus: document.getElementById("connectionStatus"),
      autoSync: document.getElementById("autoSync"),
      syncInterval: document.getElementById("syncInterval"),
      maxWords: document.getElementById("maxWords"),
      saveSettingsBtn: document.getElementById("saveSettingsBtn"),
      clearAllBtn: document.getElementById("clearAllBtn"),
      resetSettingsBtn: document.getElementById("resetSettingsBtn"),
      exportDataBtn: document.getElementById("exportDataBtn"),
      importDataBtn: document.getElementById("importDataBtn"),
      importFileInput: document.getElementById("importFileInput"),

      // UI elements
      toastContainer: document.getElementById("toastContainer"),
      loadingOverlay: document.getElementById("loadingOverlay"),
      modalOverlay: document.getElementById("modalOverlay"),
      modalTitle: document.getElementById("modalTitle"),
      modalMessage: document.getElementById("modalMessage"),
      modalClose: document.getElementById("modalClose"),
      modalCancel: document.getElementById("modalCancel"),
      modalConfirm: document.getElementById("modalConfirm"),
    };
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    // Navigation
    this.elements.navItems.forEach((item) => {
      item.addEventListener("click", (e) => {
        const section = e.target.dataset.section;
        this.switchSection(section);
      });
    });

    // Header actions
    this.elements.syncBtn.addEventListener("click", () => this.handleSync());

    // Search and filters
    this.elements.searchInput.addEventListener(
      "input",
      debounce((e) => this.handleSearch(e.target.value), 300)
    );
    this.elements.typeFilter.addEventListener("change", (e) =>
      this.handleFilter("type", e.target.value)
    );
    this.elements.syncFilter.addEventListener("change", (e) =>
      this.handleFilter("sync", e.target.value)
    );

    // Bulk actions
    this.elements.selectAllBtn.addEventListener("click", () =>
      this.toggleSelectAll()
    );
    this.elements.deleteSelectedBtn.addEventListener("click", () =>
      this.deleteSelected()
    );

    // Pagination
    this.elements.prevBtn.addEventListener("click", () => this.changePage(-1));
    this.elements.nextBtn.addEventListener("click", () => this.changePage(1));

    // Settings
    this.elements.showApiKey.addEventListener("click", () =>
      this.toggleApiKeyVisibility()
    );
    this.elements.testConnectionBtn.addEventListener("click", () =>
      this.testConnection()
    );
    this.elements.saveSettingsBtn.addEventListener("click", () =>
      this.saveSettings()
    );
    this.elements.clearAllBtn.addEventListener("click", () =>
      this.clearAllWords()
    );
    this.elements.resetSettingsBtn.addEventListener("click", () =>
      this.resetSettings()
    );
    this.elements.exportDataBtn.addEventListener("click", () =>
      this.exportData()
    );
    this.elements.importDataBtn.addEventListener("click", () =>
      this.elements.importFileInput.click()
    );
    this.elements.importFileInput.addEventListener("change", (e) =>
      this.importData(e)
    );

    // Modal
    this.elements.modalClose.addEventListener("click", () => this.hideModal());
    this.elements.modalCancel.addEventListener("click", () => this.hideModal());
    this.elements.modalOverlay.addEventListener("click", (e) => {
      if (e.target === this.elements.modalOverlay) this.hideModal();
    });

    // Hash change for navigation
    window.addEventListener("hashchange", () => this.handleHashNavigation());
  }

  /**
   * Handle hash navigation
   */
  handleHashNavigation() {
    const hash = window.location.hash.slice(1);
    const section = hash || "words";
    this.switchSection(section);
  }

  /**
   * Switch between sections
   */
  switchSection(sectionName) {
    // Update navigation
    this.elements.navItems.forEach((item) => {
      item.classList.toggle("active", item.dataset.section === sectionName);
    });

    // Update sections
    this.elements.sections.forEach((section) => {
      section.classList.toggle(
        "active",
        section.id === `${sectionName}Section`
      );
    });

    // Update URL
    window.location.hash = sectionName === "words" ? "" : sectionName;

    // Load section-specific data
    this.loadSectionData(sectionName);
  }

  /**
   * Load initial data
   */
  async loadInitialData() {
    await Promise.all([
      this.loadWords(),
      this.loadStats(),
      this.loadSettings(),
    ]);
  }

  /**
   * Load section-specific data
   */
  async loadSectionData(section) {
    switch (section) {
      case "words":
        await this.loadWords();
        break;
      case "stats":
        await this.loadStats();
        break;
      case "settings":
        await this.loadSettings();
        break;
    }
  }

  /**
   * Load words data
   */
  async loadWords() {
    try {
      this.showLoading(true);

      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.GET_WORDS,
      });

      if (response.success) {
        this.currentWords = response.data;
        this.applyFilters();
        this.updateWordStats();
      } else {
        throw new Error(response.error);
      }
    } catch (error) {
      console.error("Failed to load words:", error);
      this.showToast("Failed to load words", "error");
      this.currentWords = [];
      this.filteredWords = [];
    } finally {
      this.showLoading(false);
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
        this.updateStatsDisplay(response.data);
      }
    } catch (error) {
      console.error("Failed to load stats:", error);
      this.showToast("Failed to load statistics", "error");
    }
  }

  /**
   * Load settings
   */
  async loadSettings() {
    try {
      const settings = await chrome.storage.local.get("settings");
      const currentSettings = { ...DEFAULT_SETTINGS, ...settings.settings };

      this.elements.serverUrl.value = currentSettings.serverUrl || "";
      this.elements.apiKey.value = currentSettings.apiKey || "";
      this.elements.autoSync.checked = currentSettings.autoSync;
      this.elements.syncInterval.value = currentSettings.syncInterval / 60000; // Convert to minutes
      this.elements.maxWords.value = currentSettings.maxWords;
    } catch (error) {
      console.error("Failed to load settings:", error);
      this.showToast("Failed to load settings", "error");
    }
  }

  /**
   * Apply search and filters
   */
  applyFilters() {
    let filtered = [...this.currentWords];

    // Apply search
    if (this.searchQuery) {
      const query = this.searchQuery.toLowerCase();
      filtered = filtered.filter(
        (word) =>
          word.text.toLowerCase().includes(query) ||
          (word.context && word.context.toLowerCase().includes(query))
      );
    }

    // Apply type filter
    if (this.filters.type) {
      filtered = filtered.filter((word) => word.type === this.filters.type);
    }

    // Apply sync filter
    if (this.filters.sync) {
      const isSynced = this.filters.sync === "synced";
      filtered = filtered.filter((word) => !!word.synced === isSynced);
    }

    this.filteredWords = filtered;
    this.currentPage = 1;
    this.selectedWords.clear();
    this.renderWords();
    this.updatePagination();
  }

  /**
   * Handle search
   */
  handleSearch(query) {
    this.searchQuery = query;
    this.applyFilters();
  }

  /**
   * Handle filter change
   */
  handleFilter(type, value) {
    this.filters[type] = value;
    this.applyFilters();
  }

  /**
   * Render words list
   */
  renderWords() {
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = startIndex + this.itemsPerPage;
    const pageWords = this.filteredWords.slice(startIndex, endIndex);

    if (pageWords.length === 0) {
      this.elements.wordsList.style.display = "none";
      this.elements.emptyState.style.display = "block";
      return;
    }

    this.elements.wordsList.style.display = "block";
    this.elements.emptyState.style.display = "none";

    this.elements.wordsList.innerHTML = pageWords
      .map((word) => this.createWordElement(word))
      .join("");

    // Add event listeners to word items
    this.attachWordEventListeners();
  }

  /**
   * Create word element HTML
   */
  createWordElement(word) {
    const isSelected = this.selectedWords.has(word.id);
    const syncBadge = word.synced ? "synced" : "pending";
    const syncText = word.synced ? "Synced" : "Pending";

    return `
      <div class="word-item ${isSelected ? "selected" : ""}" data-word-id="${
      word.id
    }">
        <div class="word-header">
          <input type="checkbox" class="word-checkbox" ${
            isSelected ? "checked" : ""
          }>
          <div class="word-text">${escapeHtml(word.text)}</div>
          <div class="word-badges">
            <span class="word-badge ${word.type}">${word.type}</span>
            <span class="word-badge ${syncBadge}">${syncText}</span>
          </div>
        </div>
        
        ${
          word.context
            ? `
          <div class="word-context">
            ${escapeHtml(word.context)}
          </div>
        `
            : ""
        }
        
        <div class="word-meta">
          <span>${formatDate(word.createdAt)}</span>
          <div class="word-actions">
            <button class="btn btn-small btn-secondary edit-word" data-word-id="${
              word.id
            }">
              Edit
            </button>
            <button class="btn btn-small btn-danger delete-word" data-word-id="${
              word.id
            }">
              Delete
            </button>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Attach event listeners to word items
   */
  attachWordEventListeners() {
    // Checkbox selection
    this.elements.wordsList
      .querySelectorAll(".word-checkbox")
      .forEach((checkbox) => {
        checkbox.addEventListener("change", (e) => {
          const wordId = e.target.closest(".word-item").dataset.wordId;
          this.toggleWordSelection(wordId, e.target.checked);
        });
      });

    // Edit buttons
    this.elements.wordsList.querySelectorAll(".edit-word").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const wordId = e.target.dataset.wordId;
        this.editWord(wordId);
      });
    });

    // Delete buttons
    this.elements.wordsList.querySelectorAll(".delete-word").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const wordId = e.target.dataset.wordId;
        this.deleteWord(wordId);
      });
    });
  }

  /**
   * Toggle word selection
   */
  toggleWordSelection(wordId, selected) {
    if (selected) {
      this.selectedWords.add(wordId);
    } else {
      this.selectedWords.delete(wordId);
    }

    // Update item visual state
    const wordItem = document.querySelector(`[data-word-id="${wordId}"]`);
    if (wordItem) {
      wordItem.classList.toggle("selected", selected);
    }

    // Update bulk action buttons
    this.updateBulkActionButtons();
  }

  /**
   * Toggle select all
   */
  toggleSelectAll() {
    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = startIndex + this.itemsPerPage;
    const pageWords = this.filteredWords.slice(startIndex, endIndex);

    const allSelected = pageWords.every((word) =>
      this.selectedWords.has(word.id)
    );

    if (allSelected) {
      // Deselect all on current page
      pageWords.forEach((word) => this.selectedWords.delete(word.id));
    } else {
      // Select all on current page
      pageWords.forEach((word) => this.selectedWords.add(word.id));
    }

    this.renderWords();
    this.updateBulkActionButtons();
  }

  /**
   * Update bulk action buttons
   */
  updateBulkActionButtons() {
    const hasSelection = this.selectedWords.size > 0;
    this.elements.deleteSelectedBtn.disabled = !hasSelection;

    const startIndex = (this.currentPage - 1) * this.itemsPerPage;
    const endIndex = startIndex + this.itemsPerPage;
    const pageWords = this.filteredWords.slice(startIndex, endIndex);
    const allPageSelected =
      pageWords.length > 0 &&
      pageWords.every((word) => this.selectedWords.has(word.id));

    this.elements.selectAllBtn.textContent = allPageSelected
      ? "Deselect All"
      : "Select All";
  }

  /**
   * Update pagination
   */
  updatePagination() {
    const totalPages = Math.ceil(this.filteredWords.length / this.itemsPerPage);

    if (totalPages <= 1) {
      this.elements.pagination.style.display = "none";
      return;
    }

    this.elements.pagination.style.display = "flex";
    this.elements.prevBtn.disabled = this.currentPage === 1;
    this.elements.nextBtn.disabled = this.currentPage === totalPages;
    this.elements.pageInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;
  }

  /**
   * Change page
   */
  changePage(direction) {
    const totalPages = Math.ceil(this.filteredWords.length / this.itemsPerPage);
    const newPage = this.currentPage + direction;

    if (newPage >= 1 && newPage <= totalPages) {
      this.currentPage = newPage;
      this.selectedWords.clear();
      this.renderWords();
      this.updatePagination();
    }
  }

  /**
   * Update word statistics
   */
  updateWordStats() {
    const total = this.currentWords.length;
    const direct = this.currentWords.filter((w) => w.type === "direct").length;
    const context = this.currentWords.filter(
      (w) => w.type === "context"
    ).length;
    const pending = this.currentWords.filter((w) => !w.synced).length;

    this.elements.totalCount.textContent = total;
    this.elements.directCount.textContent = direct;
    this.elements.contextCount.textContent = context;
    this.elements.pendingCount.textContent = pending;
  }

  /**
   * Update statistics display
   */
  updateStatsDisplay(stats) {
    if (this.elements.lastSyncTime) {
      this.elements.lastSyncTime.textContent = stats.lastSync
        ? formatDate(stats.lastSync)
        : "Never";
    }
    if (this.elements.syncCount) {
      this.elements.syncCount.textContent = stats.syncCount || 0;
    }
    if (this.elements.pendingSyncCount) {
      this.elements.pendingSyncCount.textContent = stats.pendingWords || 0;
    }
    if (this.elements.totalStorage && stats.storage) {
      this.elements.totalStorage.textContent = formatBytes(
        stats.storage.totalBytes
      );
      this.elements.wordsStorage.textContent = formatBytes(stats.storage.words);
      this.elements.settingsStorage.textContent = formatBytes(
        stats.storage.settings
      );
    }
  }

  /**
   * Handle sync
   */
  async handleSync() {
    try {
      this.showLoading(true, "Syncing to server...");

      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.SYNC_TO_SERVER,
      });

      if (response.success) {
        this.showToast(response.message, "success");
        await this.loadWords(); // Refresh words after sync
      } else {
        this.showToast(response.message || "Sync failed", "error");
      }
    } catch (error) {
      console.error("Sync failed:", error);
      this.showToast("Sync failed: " + error.message, "error");
    } finally {
      this.showLoading(false);
    }
  }

  /**
   * Edit word
   */
  editWord(wordId) {
    const word = this.currentWords.find((w) => w.id === wordId);
    if (!word) return;

    const newText = prompt("Edit word:", word.text);
    if (newText && newText !== word.text) {
      // TODO: Implement word editing
      this.showToast("Word editing will be implemented soon", "info");
    }
  }

  /**
   * Delete word
   */
  async deleteWord(wordId) {
    const word = this.currentWords.find((w) => w.id === wordId);
    if (!word) return;

    const confirmed = await this.showModal(
      "Delete Word",
      `Are you sure you want to delete "${word.text}"?`
    );

    if (confirmed) {
      try {
        const response = await chrome.runtime.sendMessage({
          type: MESSAGE_TYPES.DELETE_WORD,
          data: { wordId },
        });

        if (response.success) {
          this.showToast("Word deleted successfully", "success");
          await this.loadWords();
        } else {
          this.showToast("Failed to delete word", "error");
        }
      } catch (error) {
        console.error("Failed to delete word:", error);
        this.showToast("Failed to delete word", "error");
      }
    }
  }

  /**
   * Delete selected words
   */
  async deleteSelected() {
    if (this.selectedWords.size === 0) return;

    const confirmed = await this.showModal(
      "Delete Selected Words",
      `Are you sure you want to delete ${this.selectedWords.size} selected words?`
    );

    if (confirmed) {
      try {
        this.showLoading(true, "Deleting words...");

        // Delete words one by one (could be optimized with batch delete)
        for (const wordId of this.selectedWords) {
          await chrome.runtime.sendMessage({
            type: MESSAGE_TYPES.DELETE_WORD,
            data: { wordId },
          });
        }

        this.showToast(`Deleted ${this.selectedWords.size} words`, "success");
        this.selectedWords.clear();
        await this.loadWords();
      } catch (error) {
        console.error("Failed to delete words:", error);
        this.showToast("Failed to delete some words", "error");
      } finally {
        this.showLoading(false);
      }
    }
  }

  /**
   * Toggle API key visibility
   */
  toggleApiKeyVisibility() {
    const isPassword = this.elements.apiKey.type === "password";
    this.elements.apiKey.type = isPassword ? "text" : "password";
    this.elements.showApiKey.textContent = isPassword ? "Hide" : "Show";
  }

  /**
   * Test connection
   */
  async testConnection() {
    const serverUrl = this.elements.serverUrl.value.trim();
    const apiKey = this.elements.apiKey.value.trim();

    if (!serverUrl || !apiKey) {
      this.showConnectionStatus(
        "Please enter both server URL and API key",
        "error"
      );
      return;
    }

    try {
      this.elements.testConnectionBtn.disabled = true;
      this.elements.testConnectionBtn.textContent = "Testing...";

      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.TEST_CONNECTION,
        data: { serverUrl, apiKey },
      });

      this.showConnectionStatus(
        response.message,
        response.success ? "success" : "error"
      );
    } catch (error) {
      this.showConnectionStatus("Connection test failed", "error");
    } finally {
      this.elements.testConnectionBtn.disabled = false;
      this.elements.testConnectionBtn.textContent = "Test Connection";
    }
  }

  /**
   * Show connection status
   */
  showConnectionStatus(message, type) {
    this.elements.connectionStatus.textContent = message;
    this.elements.connectionStatus.className = `connection-status ${type}`;
    this.elements.connectionStatus.style.display = "block";

    setTimeout(() => {
      this.elements.connectionStatus.style.display = "none";
    }, 5000);
  }

  /**
   * Save settings
   */
  async saveSettings() {
    try {
      const settings = {
        serverUrl: this.elements.serverUrl.value.trim(),
        apiKey: this.elements.apiKey.value.trim(),
        autoSync: this.elements.autoSync.checked,
        syncInterval: parseInt(this.elements.syncInterval.value) * 60000, // Convert to ms
        maxWords: parseInt(this.elements.maxWords.value),
      };

      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.UPDATE_SETTINGS,
        data: settings,
      });

      if (response.success) {
        this.showToast("Settings saved successfully", "success");
      } else {
        this.showToast("Failed to save settings", "error");
      }
    } catch (error) {
      console.error("Failed to save settings:", error);
      this.showToast("Failed to save settings", "error");
    }
  }

  /**
   * Clear all words
   */
  async clearAllWords() {
    const confirmed = await this.showModal(
      "Clear All Words",
      "Are you sure you want to delete all words? This action cannot be undone."
    );

    if (confirmed) {
      try {
        const response = await chrome.runtime.sendMessage({
          type: MESSAGE_TYPES.CLEAR_ALL,
        });

        if (response.success) {
          this.showToast("All words cleared successfully", "success");
          await this.loadWords();
        } else {
          this.showToast("Failed to clear words", "error");
        }
      } catch (error) {
        console.error("Failed to clear words:", error);
        this.showToast("Failed to clear words", "error");
      }
    }
  }

  /**
   * Reset settings
   */
  async resetSettings() {
    const confirmed = await this.showModal(
      "Reset Settings",
      "Are you sure you want to reset all settings to default values?"
    );

    if (confirmed) {
      try {
        const response = await chrome.runtime.sendMessage({
          type: MESSAGE_TYPES.UPDATE_SETTINGS,
          data: DEFAULT_SETTINGS,
        });

        if (response.success) {
          this.showToast("Settings reset successfully", "success");
          await this.loadSettings();
        } else {
          this.showToast("Failed to reset settings", "error");
        }
      } catch (error) {
        console.error("Failed to reset settings:", error);
        this.showToast("Failed to reset settings", "error");
      }
    }
  }

  /**
   * Export data
   */
  async exportData() {
    try {
      const words = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.GET_WORDS,
      });

      if (words.success) {
        const data = {
          words: words.data,
          exportDate: new Date().toISOString(),
          version: "2.0.0",
        };

        const blob = new Blob([JSON.stringify(data, null, 2)], {
          type: "application/json",
        });

        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `ankiwandler-export-${
          new Date().toISOString().split("T")[0]
        }.json`;
        a.click();
        URL.revokeObjectURL(url);

        this.showToast("Data exported successfully", "success");
      }
    } catch (error) {
      console.error("Failed to export data:", error);
      this.showToast("Failed to export data", "error");
    }
  }

  /**
   * Import data
   */
  async importData(event) {
    const file = event.target.files[0];
    if (!file) return;

    try {
      const text = await file.text();
      const data = JSON.parse(text);

      if (!data.words || !Array.isArray(data.words)) {
        throw new Error("Invalid file format");
      }

      const confirmed = await this.showModal(
        "Import Data",
        `Import ${data.words.length} words? This will not overwrite existing words.`
      );

      if (confirmed) {
        // TODO: Implement data import
        this.showToast("Data import will be implemented soon", "info");
      }
    } catch (error) {
      console.error("Failed to import data:", error);
      this.showToast("Failed to import data: Invalid file format", "error");
    } finally {
      event.target.value = ""; // Reset file input
    }
  }

  /**
   * Show loading overlay
   */
  showLoading(show, text = "Processing...") {
    this.elements.loadingOverlay.style.display = show ? "flex" : "none";
    if (show && text) {
      const loadingText =
        this.elements.loadingOverlay.querySelector("#loadingText");
      if (loadingText) loadingText.textContent = text;
    }
  }

  /**
   * Show toast notification
   */
  showToast(message, type = "info", duration = 4000) {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;

    this.elements.toastContainer.appendChild(toast);

    // Auto-remove after duration
    setTimeout(() => {
      if (toast.parentNode) {
        toast.style.opacity = "0";
        setTimeout(() => {
          if (toast.parentNode) {
            toast.parentNode.removeChild(toast);
          }
        }, 300);
      }
    }, duration);
  }

  /**
   * Show modal dialog
   */
  showModal(title, message) {
    return new Promise((resolve) => {
      this.elements.modalTitle.textContent = title;
      this.elements.modalMessage.textContent = message;
      this.elements.modalOverlay.style.display = "flex";

      const handleConfirm = () => {
        this.hideModal();
        resolve(true);
      };

      const handleCancel = () => {
        this.hideModal();
        resolve(false);
      };

      // Remove existing listeners
      this.elements.modalConfirm.replaceWith(
        this.elements.modalConfirm.cloneNode(true)
      );
      this.elements.modalConfirm = document.getElementById("modalConfirm");

      // Add new listeners
      this.elements.modalConfirm.addEventListener("click", handleConfirm);

      // Also handle escape key
      const handleEscape = (e) => {
        if (e.key === "Escape") {
          document.removeEventListener("keydown", handleEscape);
          handleCancel();
        }
      };
      document.addEventListener("keydown", handleEscape);
    });
  }

  /**
   * Hide modal
   */
  hideModal() {
    this.elements.modalOverlay.style.display = "none";
  }
}

// Initialize manager when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  new ManagerController();
});
