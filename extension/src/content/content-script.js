// Content script for text selection and visual feedback
(function () {
  "use strict";

  // Prevent multiple injections
  if (window.ankiWandlerInjected) {
    return;
  }
  window.ankiWandlerInjected = true;

  // Configuration
  const CONFIG = {
    SELECTION_DEBOUNCE: 300,
    FEEDBACK_DURATION: 2000,
    MIN_WORD_LENGTH: 2,
    MAX_WORD_LENGTH: 500,
  };

  // State
  let lastSelection = "";
  let selectionTimeout = null;
  let feedbackElement = null;

  /**
   * Initialize content script
   */
  function initialize() {
    setupEventListeners();
    createFeedbackElement();
    console.log("AnkiWandler content script loaded");
  }

  /**
   * Setup event listeners
   */
  function setupEventListeners() {
    // Text selection events
    document.addEventListener("mouseup", handleSelection, { passive: true });
    document.addEventListener("keyup", handleSelection, { passive: true });

    // Keyboard shortcuts
    document.addEventListener("keydown", handleKeyboardShortcuts);

    // Listen for messages from background script
    chrome.runtime.onMessage.addListener(handleMessage);

    // Double-click for quick collection
    document.addEventListener("dblclick", handleDoubleClick);
  }

  /**
   * Handle text selection
   */
  function handleSelection(event) {
    // Debounce selection handling
    if (selectionTimeout) {
      clearTimeout(selectionTimeout);
    }

    selectionTimeout = setTimeout(() => {
      processSelection();
    }, CONFIG.SELECTION_DEBOUNCE);
  }

  /**
   * Process the current text selection
   */
  function processSelection() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    // Validate selection
    if (!selectedText || selectedText === lastSelection) {
      return;
    }

    if (
      selectedText.length < CONFIG.MIN_WORD_LENGTH ||
      selectedText.length > CONFIG.MAX_WORD_LENGTH
    ) {
      return;
    }

    lastSelection = selectedText;

    // Notify background script about selection
    chrome.runtime
      .sendMessage({
        type: "selectionMade",
        data: {
          text: selectedText,
          url: window.location.href,
          title: document.title,
        },
      })
      .catch(() => {
        // Background script might not be available
      });
  }

  /**
   * Handle keyboard shortcuts
   */
  function handleKeyboardShortcuts(event) {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (!selectedText || selectedText.length < CONFIG.MIN_WORD_LENGTH) {
      return;
    }

    // Ctrl/Cmd + Shift + C for direct collection
    if (
      (event.ctrlKey || event.metaKey) &&
      event.shiftKey &&
      event.key === "C"
    ) {
      event.preventDefault();
      collectWord(selectedText, "direct");
    }

    // Ctrl/Cmd + Shift + X for context collection
    if (
      (event.ctrlKey || event.metaKey) &&
      event.shiftKey &&
      event.key === "X"
    ) {
      event.preventDefault();
      collectWord(selectedText, "context");
    }
  }

  /**
   * Handle double-click for quick collection
   */
  function handleDoubleClick(event) {
    // Only if modifier key is held
    if (!(event.ctrlKey || event.metaKey)) {
      return;
    }

    const word = getWordAtPosition(event.clientX, event.clientY);
    if (word && word.length >= CONFIG.MIN_WORD_LENGTH) {
      event.preventDefault();
      collectWord(word, "direct");
    }
  }

  /**
   * Get word at specific position
   */
  function getWordAtPosition(x, y) {
    const range = document.caretRangeFromPoint(x, y);
    if (!range) return null;

    const textNode = range.startContainer;
    if (textNode.nodeType !== Node.TEXT_NODE) return null;

    const text = textNode.textContent;
    let start = range.startOffset;
    let end = range.startOffset;

    // Find word boundaries
    while (start > 0 && /\w/.test(text[start - 1])) {
      start--;
    }
    while (end < text.length && /\w/.test(text[end])) {
      end++;
    }

    return text.substring(start, end);
  }

  /**
   * Collect word via background script
   */
  function collectWord(text, type) {
    const messageType =
      type === "direct" ? "collectWord" : "collectWithContext";

    // Send message directly to service worker
    chrome.runtime
      .sendMessage({
        type: messageType,
        data: {
          text: text,
          type: type,
          context: type === "context" ? text : null,
          url: window.location.href,
          title: document.title,
        },
      })
      .then((response) => {
        if (response?.success) {
          showFeedback(`✓ Collected: "${text}"`, "success");
        } else {
          console.error("Collection failed:", response?.error);
          showFeedback(`✗ Failed to collect word`, "error");
        }
      })
      .catch((error) => {
        console.error("Collection failed:", error);
        showFeedback(`✗ Collection failed`, "error");
      });
  }

  /**
   * Handle messages from background script
   */
  function handleMessage(message, sender, sendResponse) {
    switch (message.type) {
      case "wordCollected":
        const { text, type } = message.data;
        const typeLabel = type === "direct" ? "word" : "word with context";
        showFeedback(`✓ Collected ${typeLabel}: "${text}"`, "success");
        break;

      case "collectionFailed":
        showFeedback(`✗ Failed to collect word`, "error");
        break;

      default:
        // Unknown message type
        break;
    }
  }

  /**
   * Create feedback element for visual notifications
   */
  function createFeedbackElement() {
    feedbackElement = document.createElement("div");
    feedbackElement.id = "ankiwandler-feedback";
    feedbackElement.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      padding: 12px 16px;
      border-radius: 8px;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      font-size: 14px;
      font-weight: 500;
      color: white;
      z-index: 999999;
      opacity: 0;
      transform: translateY(-10px);
      transition: all 0.3s ease;
      pointer-events: none;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      max-width: 300px;
      word-break: break-word;
    `;

    document.body.appendChild(feedbackElement);
  }

  /**
   * Show visual feedback
   */
  function showFeedback(message, type = "info") {
    if (!feedbackElement) {
      createFeedbackElement();
    }

    // Set colors based on type
    const colors = {
      success: "#10B981",
      error: "#EF4444",
      info: "#3B82F6",
      warning: "#F59E0B",
    };

    feedbackElement.style.backgroundColor = colors[type] || colors.info;
    feedbackElement.textContent = message;

    // Show feedback
    feedbackElement.style.opacity = "1";
    feedbackElement.style.transform = "translateY(0)";

    // Hide after duration
    setTimeout(() => {
      feedbackElement.style.opacity = "0";
      feedbackElement.style.transform = "translateY(-10px)";
    }, CONFIG.FEEDBACK_DURATION);
  }

  /**
   * Cleanup function
   */
  function cleanup() {
    if (selectionTimeout) {
      clearTimeout(selectionTimeout);
    }

    if (feedbackElement && feedbackElement.parentNode) {
      feedbackElement.parentNode.removeChild(feedbackElement);
    }
  }

  // Handle page unload
  window.addEventListener("beforeunload", cleanup);

  // Initialize when DOM is ready
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initialize);
  } else {
    initialize();
  }
})();
