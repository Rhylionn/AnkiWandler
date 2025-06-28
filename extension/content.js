// Content script for Text Collector extension
// This script runs on all web pages to enable text selection and collection

(function () {
  "use strict";

  // Prevent multiple injections
  if (window.textCollectorInjected) {
    return;
  }
  window.textCollectorInjected = true;

  // Enhanced selection handling
  let lastSelection = "";

  // Listen for text selection
  document.addEventListener("mouseup", handleSelection);
  document.addEventListener("keyup", handleSelection);

  function handleSelection() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (selectedText && selectedText !== lastSelection) {
      lastSelection = selectedText;

      // Store selection info for context menu
      chrome.runtime.sendMessage({
        action: "selectionMade",
        text: selectedText,
        url: window.location.href,
        title: document.title,
      });
    }
  }

  // Handle keyboard shortcuts for quick collection
  document.addEventListener("keydown", function (event) {
    // Ctrl+Shift+C (or Cmd+Shift+C on Mac) to collect selected text
    if (
      (event.ctrlKey || event.metaKey) &&
      event.shiftKey &&
      event.key === "C"
    ) {
      const selection = window.getSelection();
      const selectedText = selection.toString().trim();

      if (selectedText) {
        event.preventDefault();

        // Send message to background script to collect text
        chrome.runtime.sendMessage({
          action: "collectText",
          text: selectedText,
          url: window.location.href,
          title: document.title,
        });

        // Visual feedback
        showCollectionFeedback(selectedText);
      }
    }
  });

  // Show visual feedback when text is collected
  function showCollectionFeedback(text) {
    // Create a temporary tooltip
    const tooltip = document.createElement("div");
    tooltip.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: #4285f4;
      color: white;
      padding: 12px 16px;
      border-radius: 6px;
      font-family: Arial, sans-serif;
      font-size: 14px;
      font-weight: 500;
      z-index: 10000;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      animation: slideIn 0.3s ease;
      max-width: 300px;
      word-wrap: break-word;
    `;

    // Add animation styles
    const style = document.createElement("style");
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
    `;
    document.head.appendChild(style);

    const preview = text.length > 50 ? text.substring(0, 50) + "..." : text;
    tooltip.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px;">
        <span>📝</span>
        <span>Collected: "${preview}"</span>
      </div>
    `;

    document.body.appendChild(tooltip);

    // Remove tooltip after 3 seconds
    setTimeout(() => {
      tooltip.style.animation = "slideOut 0.3s ease";
      setTimeout(() => {
        if (tooltip.parentNode) {
          tooltip.parentNode.removeChild(tooltip);
        }
        if (style.parentNode) {
          style.parentNode.removeChild(style);
        }
      }, 300);
    }, 3000);
  }

  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "textCollected") {
      showCollectionFeedback(request.text);
    }
  });

  // Enhanced word selection for German language learning
  function getWordAtPosition(x, y) {
    const element = document.elementFromPoint(x, y);
    if (!element) return null;

    const range = document.caretRangeFromPoint(x, y);
    if (!range) return null;

    // Expand range to include whole word
    range.expand("word");
    return range.toString().trim();
  }

  // Double-click to collect single words
  document.addEventListener("dblclick", function (event) {
    if (event.ctrlKey || event.metaKey) {
      const word = getWordAtPosition(event.clientX, event.clientY);
      if (word && word.length > 1) {
        event.preventDefault();

        chrome.runtime.sendMessage({
          action: "collectText",
          text: word,
          url: window.location.href,
          title: document.title,
        });

        showCollectionFeedback(word);
      }
    }
  });

  console.log("Text Collector content script loaded");
})();
