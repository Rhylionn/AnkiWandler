// Updated content script for Text Collector extension
// Simplified since popup windows handle all collection
// Visual feedback removed (no notifications)

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

  // Helper function to get word at position
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

  console.log("Text Collector content script loaded");
})();
