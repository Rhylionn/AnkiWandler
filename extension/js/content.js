// Updated content script for Text Collector extension
// Simplified since popup windows handle all collection

(function () {
  "use strict";

  // Prevent multiple injections
  if (window.textCollectorInjected) {
    return;
  }
  window.textCollectorInjected = true;

  // Track last selection for context menu
  let lastSelection = "";

  // Listen for text selection
  document.addEventListener("mouseup", handleSelection);
  document.addEventListener("keyup", handleSelection);

  function handleSelection() {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (selectedText && selectedText !== lastSelection) {
      lastSelection = selectedText;

      // Store selection info for context menu (though not strictly needed now)
      chrome.runtime
        .sendMessage({
          action: "selectionMade",
          text: selectedText,
        })
        .catch(() => {
          // Ignore errors if background script not available
        });
    }
  }

  // Handle keyboard shortcuts for quick collection
  document.addEventListener("keydown", function (event) {
    const selection = window.getSelection();
    const selectedText = selection.toString().trim();

    if (!selectedText) return;

    // Ctrl+Shift+C for direct word collection
    if (
      (event.ctrlKey || event.metaKey) &&
      event.shiftKey &&
      event.key === "C"
    ) {
      event.preventDefault();
      collectWord(selectedText);
    }

    // Ctrl+Shift+X for context collection
    if (
      (event.ctrlKey || event.metaKey) &&
      event.shiftKey &&
      event.key === "X"
    ) {
      event.preventDefault();
      collectWithContext(selectedText);
    }
  });

  // Direct word collection via keyboard shortcut
  function collectWord(selectedText) {
    chrome.runtime
      .sendMessage({
        action: "collectWord",
        text: selectedText,
        needsArticle: false,
        context: null,
      })
      .catch(() => {
        // Ignore errors
      });

    showCollectionFeedback(selectedText, "Direct Collection", "#4285f4");
  }

  // Context collection via keyboard shortcut
  function collectWithContext(selectedText) {
    chrome.runtime
      .sendMessage({
        action: "collectWithContext",
        text: selectedText,
        needsArticle: true,
        context: { sentence: selectedText },
      })
      .catch(() => {
        // Ignore errors
      });

    showCollectionFeedback(selectedText, "Context Collection", "#059669");
  }

  // Double-click for quick word collection
  document.addEventListener("dblclick", function (event) {
    if (event.ctrlKey || event.metaKey) {
      const word = getWordAtPosition(event.clientX, event.clientY);
      if (word && word.length > 1) {
        event.preventDefault();
        collectWord(word);
      }
    }
  });

  // Show visual feedback when text is collected
  function showCollectionFeedback(text, subtitle, color) {
    // Create a temporary tooltip
    const tooltip = document.createElement("div");
    tooltip.style.cssText = `
          position: fixed;
          top: 20px;
          right: 20px;
          background: ${color};
          color: white;
          padding: 12px 16px;
          border-radius: 6px;
          font-family: Arial, sans-serif;
          font-size: 14px;
          font-weight: 500;
          z-index: 2147483647;
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
          animation: slideIn 0.3s ease;
          max-width: 350px;
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

    if (!document.head.querySelector("style[data-text-collector]")) {
      style.setAttribute("data-text-collector", "true");
      document.head.appendChild(style);
    }

    const preview = text.length > 30 ? text.substring(0, 30) + "..." : text;

    tooltip.innerHTML = `
          <div style="display: flex; align-items: center; gap: 8px;">
              <span>📝</span>
              <div>
                  <div>Collected: "${preview}"</div>
                  <div style="font-size: 11px; opacity: 0.8; margin-top: 2px;">${subtitle}</div>
              </div>
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
      }, 300);
    }, 3000);
  }

  // Listen for messages from background script
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "textCollected") {
      showCollectionFeedback(
        request.text,
        request.needsArticle ? "Context Collection" : "Direct Collection",
        request.needsArticle ? "#059669" : "#4285f4"
      );
    }
  });

  console.log("Text Collector content script loaded");
})();
