// Word selector popup controller
import { MESSAGE_TYPES, COLLECTION_TYPES } from "../shared/constants.js";
import { extractWords, escapeHtml } from "../shared/utils.js";

class WordSelectorController {
  constructor() {
    this.selectedText = "";
    this.selectedWord = null;
    this.words = [];
    this.elements = {};

    this.init();
  }

  /**
   * Initialize word selector
   */
  async init() {
    this.cacheElements();
    this.setupEventListeners();
    await this.loadPendingSelection();

    // Focus window
    window.focus();
  }

  /**
   * Cache DOM elements
   */
  cacheElements() {
    this.elements = {
      loadingState: document.getElementById("loadingState"),
      errorState: document.getElementById("errorState"),
      successState: document.getElementById("successState"),
      mainContent: document.getElementById("mainContent"),
      selectedText: document.getElementById("selectedText"),
      wordsContainer: document.getElementById("wordsContainer"),
      cancelBtn: document.getElementById("cancelBtn"),
      acceptBtn: document.getElementById("acceptBtn"),
      acceptBtnText: document.querySelector(".btn-text"),
      errorMessage: document.getElementById("errorMessage"),
      successMessage: document.getElementById("successMessage"),
      countdown: document.getElementById("countdown"),
    };
  }

  /**
   * Setup event listeners
   */
  setupEventListeners() {
    this.elements.cancelBtn.addEventListener("click", () => this.closeWindow());
    this.elements.acceptBtn.addEventListener("click", () =>
      this.acceptSelectedWord()
    );

    // Close on Escape key
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.closeWindow();
      }
    });

    // Handle window beforeunload
    window.addEventListener("beforeunload", () => this.cleanup());
  }

  /**
   * Load pending selection from storage
   */
  async loadPendingSelection() {
    try {
      const result = await chrome.storage.local.get(["pendingWordSelection"]);
      const pending = result.pendingWordSelection;

      if (!pending) {
        this.showError("No text selection found");
        return;
      }

      // Check if data is not too old (60 seconds)
      if (Date.now() - pending.timestamp > 60000) {
        this.showError("Selection expired, please try again");
        return;
      }

      this.selectedText = pending.text;
      this.setupWordSelection(pending.text);
    } catch (error) {
      console.error("Error loading pending selection:", error);
      this.showError("Failed to load text selection");
    }
  }

  /**
   * Setup word selection interface
   */
  setupWordSelection(text) {
    try {
      // Extract words from the text
      this.words = extractWords(text);

      if (this.words.length === 0) {
        this.showError("No valid words found in selection");
        return;
      }

      // Display selected text
      this.elements.selectedText.textContent = text;

      // Create word buttons
      this.renderWords();

      // Show main content
      this.showMainContent();
    } catch (error) {
      console.error("Error setting up word selection:", error);
      this.showError("Failed to process text selection");
    }
  }

  /**
   * Render word selection buttons
   */
  renderWords() {
    this.elements.wordsContainer.innerHTML = "";

    this.words.forEach((word, index) => {
      const wordElement = document.createElement("div");
      wordElement.className = "word-item";
      wordElement.textContent = word;
      wordElement.dataset.word = word;
      wordElement.dataset.index = index;

      // Add click handler
      wordElement.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        this.selectWord(word, wordElement);
      });

      // Add keyboard navigation
      wordElement.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          this.selectWord(word, wordElement);
        }
      });

      // Make focusable
      wordElement.tabIndex = 0;

      this.elements.wordsContainer.appendChild(wordElement);
    });
  }

  /**
   * Select a word
   */
  selectWord(word, element) {
    // Remove selection from all words
    document.querySelectorAll(".word-item").forEach((item) => {
      item.classList.remove("selected");
    });

    // Select current word
    element.classList.add("selected");
    this.selectedWord = word;

    // Enable accept button
    this.elements.acceptBtn.disabled = false;
    this.elements.acceptBtnText.textContent = `Collect "${word}"`;
  }

  /**
   * Accept selected word
   */
  async acceptSelectedWord() {
    if (!this.selectedWord) {
      console.warn("No word selected");
      return;
    }

    try {
      // Disable buttons to prevent multiple clicks
      this.elements.acceptBtn.disabled = true;
      this.elements.cancelBtn.disabled = true;

      await this.collectWord(this.selectedWord);
    } catch (error) {
      console.error("Error accepting word:", error);
      this.showError(`Failed to collect word: ${error.message}`);

      // Re-enable buttons on error
      this.elements.acceptBtn.disabled = false;
      this.elements.cancelBtn.disabled = false;
      this.resetSelection();
    }
  }

  /**
   * Collect the selected word
   */
  async collectWord(word) {
    try {
      const response = await chrome.runtime.sendMessage({
        type: MESSAGE_TYPES.COLLECT_WITH_CONTEXT,
        data: {
          text: word,
          type: COLLECTION_TYPES.CONTEXT,
          context: this.selectedText,
          url: await this.getCurrentUrl(),
          title: await this.getCurrentTitle(),
        },
      });

      if (response?.success) {
        this.showSuccess(word);
      } else {
        throw new Error(response?.error || "Failed to collect word");
      }
    } catch (error) {
      console.error("Error collecting word:", error);
      throw error;
    }
  }

  /**
   * Get current tab URL
   */
  async getCurrentUrl() {
    try {
      const result = await chrome.storage.local.get(["pendingWordSelection"]);
      return result.pendingWordSelection?.url || "";
    } catch (error) {
      return "";
    }
  }

  /**
   * Get current tab title
   */
  async getCurrentTitle() {
    try {
      const result = await chrome.storage.local.get(["pendingWordSelection"]);
      return result.pendingWordSelection?.title || "";
    } catch (error) {
      return "";
    }
  }

  /**
   * Show main content
   */
  showMainContent() {
    this.hideAllSections();
    this.elements.mainContent.style.display = "flex";
    this.elements.mainContent.classList.add("active");
  }

  /**
   * Show success state
   */
  showSuccess(word) {
    this.hideAllSections();
    this.elements.successState.style.display = "flex";
    this.elements.successState.classList.add("active");

    this.elements.successMessage.textContent = `"${word}" has been added to your collection with context`;

    // Auto-close countdown
    this.startCountdown();
  }

  /**
   * Show error state
   */
  showError(message) {
    this.hideAllSections();
    this.elements.errorState.style.display = "flex";
    this.elements.errorState.classList.add("active");

    this.elements.errorMessage.textContent = message;

    // Auto-close after 3 seconds
    setTimeout(() => this.closeWindow(), 3000);
  }

  /**
   * Hide all sections
   */
  hideAllSections() {
    const sections = [
      this.elements.loadingState,
      this.elements.errorState,
      this.elements.successState,
      this.elements.mainContent,
    ];

    sections.forEach((section) => {
      section.style.display = "none";
      section.classList.remove("active");
    });
  }

  /**
   * Start countdown for auto-close
   */
  startCountdown() {
    let countdown = 3;
    this.elements.countdown.textContent = countdown;

    const timer = setInterval(() => {
      countdown--;
      this.elements.countdown.textContent = countdown;

      if (countdown <= 0) {
        clearInterval(timer);
        this.closeWindow();
      }
    }, 1000);
  }

  /**
   * Reset word selection
   */
  resetSelection() {
    document.querySelectorAll(".word-item").forEach((item) => {
      item.classList.remove("selected");
    });

    this.selectedWord = null;
    this.elements.acceptBtn.disabled = true;
    this.elements.acceptBtnText.textContent = "Select a word";
  }

  /**
   * Cleanup function
   */
  async cleanup() {
    try {
      // Clean up pending selection from storage
      await chrome.storage.local.remove(["pendingWordSelection"]);

      // Notify background script
      await chrome.runtime.sendMessage({
        type: "cleanupWordSelector",
      });
    } catch (error) {
      // Ignore cleanup errors
      console.warn("Cleanup error:", error);
    }
  }

  /**
   * Close window
   */
  async closeWindow() {
    await this.cleanup();
    window.close();
  }
}

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
  new WordSelectorController();
});
