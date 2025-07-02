// Shared UI components for AnkiWandler
import { createElement, escapeHtml, formatDate } from "./utils.js";

/**
 * Word Card Component
 */
export class WordCard {
  constructor(wordData, options = {}) {
    this.wordData = wordData;
    this.options = {
      showCheckbox: false,
      showActions: true,
      compact: false,
      ...options,
    };
    this.element = this.render();
  }

  render() {
    const { wordData, options } = this;
    const isSelected = options.selected || false;

    const card = createElement("div", {
      className: `word-card ${options.compact ? "compact" : ""} ${
        isSelected ? "selected" : ""
      }`,
      "data-word-id": wordData.id,
    });

    // Header
    const header = createElement("div", { className: "word-header" });

    if (options.showCheckbox) {
      const checkbox = createElement("input", {
        type: "checkbox",
        className: "word-checkbox",
        checked: isSelected,
      });
      header.appendChild(checkbox);
    }

    const textElement = createElement("div", {
      className: "word-text",
      textContent: wordData.text,
    });
    header.appendChild(textElement);

    // Badges
    const badges = createElement("div", { className: "word-badges" });

    const typeBadge = createElement("span", {
      className: `word-badge ${wordData.type}`,
      textContent: wordData.type,
    });
    badges.appendChild(typeBadge);

    const syncBadge = createElement("span", {
      className: `word-badge ${wordData.synced ? "synced" : "pending"}`,
      textContent: wordData.synced ? "Synced" : "Pending",
    });
    badges.appendChild(syncBadge);

    header.appendChild(badges);
    card.appendChild(header);

    // Context (if exists)
    if (wordData.context && !options.compact) {
      const context = createElement("div", {
        className: "word-context",
        textContent: wordData.context,
      });
      card.appendChild(context);
    }

    // Meta information
    if (!options.compact) {
      const meta = createElement("div", { className: "word-meta" });

      const date = createElement("span", {
        className: "word-date",
        textContent: formatDate(wordData.createdAt),
      });
      meta.appendChild(date);

      if (options.showActions) {
        const actions = createElement("div", { className: "word-actions" });

        const editBtn = createElement("button", {
          className: "btn btn-small btn-secondary",
          textContent: "Edit",
          "data-action": "edit",
          "data-word-id": wordData.id,
        });
        actions.appendChild(editBtn);

        const deleteBtn = createElement("button", {
          className: "btn btn-small btn-danger",
          textContent: "Delete",
          "data-action": "delete",
          "data-word-id": wordData.id,
        });
        actions.appendChild(deleteBtn);

        meta.appendChild(actions);
      }

      card.appendChild(meta);
    }

    return card;
  }

  updateSelection(selected) {
    const checkbox = this.element.querySelector(".word-checkbox");
    if (checkbox) {
      checkbox.checked = selected;
    }
    this.element.classList.toggle("selected", selected);
  }

  updateSyncStatus(synced) {
    const syncBadge = this.element.querySelector(
      ".word-badge.synced, .word-badge.pending"
    );
    if (syncBadge) {
      syncBadge.className = `word-badge ${synced ? "synced" : "pending"}`;
      syncBadge.textContent = synced ? "Synced" : "Pending";
    }
  }

  remove() {
    if (this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
  }
}

/**
 * Stats Card Component
 */
export class StatsCard {
  constructor(title, stats, options = {}) {
    this.title = title;
    this.stats = stats;
    this.options = {
      showChart: false,
      chartType: "pie",
      ...options,
    };
    this.element = this.render();
  }

  render() {
    const card = createElement("div", { className: "stats-card" });

    // Title
    const title = createElement("h3", {
      className: "stats-title",
      textContent: this.title,
    });
    card.appendChild(title);

    if (this.options.showChart) {
      // Chart container
      const chartContainer = createElement("div", {
        className: "chart-container",
      });

      // Placeholder for chart (could integrate with Chart.js later)
      const chartPlaceholder = createElement("div", {
        className: "chart-placeholder",
        textContent: "Chart visualization coming soon",
      });
      chartContainer.appendChild(chartPlaceholder);
      card.appendChild(chartContainer);
    }

    // Stats list
    const statsList = createElement("div", { className: "stats-list" });

    Object.entries(this.stats).forEach(([key, value]) => {
      const statItem = createElement("div", { className: "stats-item" });

      const statKey = createElement("span", {
        className: "stats-key",
        textContent: this.formatKey(key),
      });
      statItem.appendChild(statKey);

      const statValue = createElement("span", {
        className: "stats-value",
        textContent: this.formatValue(key, value),
      });
      statItem.appendChild(statValue);

      statsList.appendChild(statItem);
    });

    card.appendChild(statsList);
    return card;
  }

  formatKey(key) {
    return (
      key
        .replace(/([A-Z])/g, " $1")
        .replace(/^./, (str) => str.toUpperCase())
        .replace(/([a-z])([A-Z])/g, "$1 $2") + ":"
    );
  }

  formatValue(key, value) {
    if (key.includes("Date") || key.includes("Time")) {
      return value ? formatDate(value) : "Never";
    }
    if (key.includes("Size") || key.includes("Storage")) {
      return this.formatBytes(value);
    }
    return String(value);
  }

  formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  updateStats(newStats) {
    this.stats = { ...this.stats, ...newStats };
    const statsList = this.element.querySelector(".stats-list");
    if (statsList) {
      statsList.innerHTML = "";
      Object.entries(this.stats).forEach(([key, value]) => {
        const statItem = createElement("div", { className: "stats-item" });

        const statKey = createElement("span", {
          className: "stats-key",
          textContent: this.formatKey(key),
        });
        statItem.appendChild(statKey);

        const statValue = createElement("span", {
          className: "stats-value",
          textContent: this.formatValue(key, value),
        });
        statItem.appendChild(statValue);

        statsList.appendChild(statItem);
      });
    }
  }
}

/**
 * Toast Notification Component
 */
export class Toast {
  constructor(message, type = "info", duration = 4000) {
    this.message = message;
    this.type = type;
    this.duration = duration;
    this.element = this.render();
    this.show();
  }

  render() {
    const toast = createElement("div", {
      className: `toast toast-${this.type}`,
      textContent: this.message,
    });

    // Add close button for longer messages
    if (this.message.length > 50) {
      const closeBtn = createElement("button", {
        className: "toast-close",
        textContent: "×",
      });
      closeBtn.addEventListener("click", () => this.hide());
      toast.appendChild(closeBtn);
    }

    return toast;
  }

  show() {
    // Find or create toast container
    let container = document.querySelector(".toast-container");
    if (!container) {
      container = createElement("div", { className: "toast-container" });
      document.body.appendChild(container);
    }

    container.appendChild(this.element);

    // Animate in
    requestAnimationFrame(() => {
      this.element.classList.add("toast-show");
    });

    // Auto-hide after duration
    if (this.duration > 0) {
      setTimeout(() => this.hide(), this.duration);
    }
  }

  hide() {
    this.element.classList.add("toast-hide");
    setTimeout(() => {
      if (this.element.parentNode) {
        this.element.parentNode.removeChild(this.element);
      }
    }, 300);
  }
}

/**
 * Modal Dialog Component
 */
export class Modal {
  constructor(title, content, options = {}) {
    this.title = title;
    this.content = content;
    this.options = {
      confirmText: "Confirm",
      cancelText: "Cancel",
      type: "confirm", // 'confirm', 'alert', 'custom'
      ...options,
    };
    this.element = this.render();
    this.promise = null;
    this.resolve = null;
  }

  render() {
    const overlay = createElement("div", { className: "modal-overlay" });

    const modal = createElement("div", { className: "modal" });

    // Header
    const header = createElement("div", { className: "modal-header" });
    const title = createElement("h3", {
      className: "modal-title",
      textContent: this.title,
    });
    header.appendChild(title);

    const closeBtn = createElement("button", {
      className: "modal-close",
      textContent: "×",
    });
    closeBtn.addEventListener("click", () => this.hide(false));
    header.appendChild(closeBtn);

    modal.appendChild(header);

    // Body
    const body = createElement("div", { className: "modal-body" });
    if (typeof this.content === "string") {
      body.textContent = this.content;
    } else {
      body.appendChild(this.content);
    }
    modal.appendChild(body);

    // Footer
    if (this.options.type !== "custom") {
      const footer = createElement("div", { className: "modal-footer" });

      if (this.options.type === "confirm") {
        const cancelBtn = createElement("button", {
          className: "btn btn-secondary",
          textContent: this.options.cancelText,
        });
        cancelBtn.addEventListener("click", () => this.hide(false));
        footer.appendChild(cancelBtn);
      }

      const confirmBtn = createElement("button", {
        className: "btn btn-primary",
        textContent: this.options.confirmText,
      });
      confirmBtn.addEventListener("click", () => this.hide(true));
      footer.appendChild(confirmBtn);

      modal.appendChild(footer);
    }

    overlay.appendChild(modal);

    // Close on overlay click
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        this.hide(false);
      }
    });

    // Close on escape key
    this.handleEscape = (e) => {
      if (e.key === "Escape") {
        this.hide(false);
      }
    };

    return overlay;
  }

  show() {
    return new Promise((resolve) => {
      this.resolve = resolve;
      document.body.appendChild(this.element);
      document.addEventListener("keydown", this.handleEscape);

      // Animate in
      requestAnimationFrame(() => {
        this.element.classList.add("modal-show");
      });
    });
  }

  hide(result = false) {
    document.removeEventListener("keydown", this.handleEscape);
    this.element.classList.add("modal-hide");

    setTimeout(() => {
      if (this.element.parentNode) {
        this.element.parentNode.removeChild(this.element);
      }
    }, 300);

    if (this.resolve) {
      this.resolve(result);
    }
  }
}

/**
 * Loading Spinner Component
 */
export class LoadingSpinner {
  constructor(text = "Loading...", size = "medium") {
    this.text = text;
    this.size = size;
    this.element = this.render();
  }

  render() {
    const container = createElement("div", {
      className: `loading-spinner loading-${this.size}`,
    });

    const spinner = createElement("div", { className: "spinner" });
    container.appendChild(spinner);

    if (this.text) {
      const textElement = createElement("span", {
        className: "loading-text",
        textContent: this.text,
      });
      container.appendChild(textElement);
    }

    return container;
  }

  updateText(newText) {
    const textElement = this.element.querySelector(".loading-text");
    if (textElement) {
      textElement.textContent = newText;
    }
  }

  show(parent = document.body) {
    parent.appendChild(this.element);
  }

  hide() {
    if (this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
  }
}

/**
 * Search Box Component
 */
export class SearchBox {
  constructor(placeholder = "Search...", onSearch = null, debounceMs = 300) {
    this.placeholder = placeholder;
    this.onSearch = onSearch;
    this.debounceMs = debounceMs;
    this.debounceTimer = null;
    this.element = this.render();
  }

  render() {
    const container = createElement("div", { className: "search-container" });

    const input = createElement("input", {
      type: "text",
      className: "search-input",
      placeholder: this.placeholder,
    });

    const icon = createElement("span", {
      className: "search-icon",
      textContent: "🔍",
    });

    input.addEventListener("input", (e) => this.handleInput(e.target.value));
    input.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.clear();
      }
    });

    container.appendChild(input);
    container.appendChild(icon);

    return container;
  }

  handleInput(value) {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(() => {
      if (this.onSearch) {
        this.onSearch(value);
      }
    }, this.debounceMs);
  }

  clear() {
    const input = this.element.querySelector(".search-input");
    input.value = "";
    if (this.onSearch) {
      this.onSearch("");
    }
  }

  getValue() {
    const input = this.element.querySelector(".search-input");
    return input.value;
  }

  setValue(value) {
    const input = this.element.querySelector(".search-input");
    input.value = value;
  }

  focus() {
    const input = this.element.querySelector(".search-input");
    input.focus();
  }
}

/**
 * Pagination Component
 */
export class Pagination {
  constructor(totalItems, itemsPerPage, onPageChange) {
    this.totalItems = totalItems;
    this.itemsPerPage = itemsPerPage;
    this.currentPage = 1;
    this.onPageChange = onPageChange;
    this.element = this.render();
  }

  render() {
    const container = createElement("div", { className: "pagination" });

    this.prevBtn = createElement("button", {
      className: "btn btn-secondary",
      textContent: "Previous",
    });
    this.prevBtn.addEventListener("click", () =>
      this.goToPage(this.currentPage - 1)
    );

    this.pageInfo = createElement("span", { className: "page-info" });

    this.nextBtn = createElement("button", {
      className: "btn btn-secondary",
      textContent: "Next",
    });
    this.nextBtn.addEventListener("click", () =>
      this.goToPage(this.currentPage + 1)
    );

    container.appendChild(this.prevBtn);
    container.appendChild(this.pageInfo);
    container.appendChild(this.nextBtn);

    this.updateDisplay();
    return container;
  }

  updateDisplay() {
    const totalPages = Math.ceil(this.totalItems / this.itemsPerPage);

    this.prevBtn.disabled = this.currentPage === 1;
    this.nextBtn.disabled = this.currentPage === totalPages || totalPages === 0;

    if (totalPages === 0) {
      this.pageInfo.textContent = "No items";
    } else {
      this.pageInfo.textContent = `Page ${this.currentPage} of ${totalPages}`;
    }

    // Hide pagination if only one page
    this.element.style.display = totalPages <= 1 ? "none" : "flex";
  }

  goToPage(page) {
    const totalPages = Math.ceil(this.totalItems / this.itemsPerPage);

    if (page >= 1 && page <= totalPages && page !== this.currentPage) {
      this.currentPage = page;
      this.updateDisplay();

      if (this.onPageChange) {
        this.onPageChange(page);
      }
    }
  }

  updateTotalItems(totalItems) {
    this.totalItems = totalItems;

    // Reset to page 1 if current page is out of bounds
    const totalPages = Math.ceil(totalItems / this.itemsPerPage);
    if (this.currentPage > totalPages) {
      this.currentPage = 1;
    }

    this.updateDisplay();
  }

  getCurrentPage() {
    return this.currentPage;
  }

  getTotalPages() {
    return Math.ceil(this.totalItems / this.itemsPerPage);
  }
}

/**
 * Utility function to show toast notifications
 */
export function showToast(message, type = "info", duration = 4000) {
  return new Toast(message, type, duration);
}

/**
 * Utility function to show modal dialogs
 */
export function showModal(title, content, options = {}) {
  const modal = new Modal(title, content, options);
  return modal.show();
}

/**
 * Utility function to show confirm dialogs
 */
export function showConfirm(title, message, options = {}) {
  return showModal(title, message, {
    type: "confirm",
    ...options,
  });
}

/**
 * Utility function to show alert dialogs
 */
export function showAlert(title, message, options = {}) {
  return showModal(title, message, {
    type: "alert",
    confirmText: "OK",
    ...options,
  });
}
