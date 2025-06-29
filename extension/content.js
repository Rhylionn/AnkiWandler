// Enhanced content script for Text Collector extension
// Two collection modes: Direct word collection vs Context-based collection

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

      // Store basic selection info for context menu
      chrome.runtime.sendMessage({
        action: "selectionMade",
        text: selectedText,
      });
    }
  }

  /**
   * Extract context information for a text selection
   * @param {Selection} selection - The browser selection object
   * @returns {Object} Context information including sentence
   */
  function getSelectionContext(selection) {
    if (!selection || selection.rangeCount === 0) {
      return null;
    }

    try {
      const range = selection.getRangeAt(0);
      const selectedText = selection.toString().trim();

      // Get the containing element and its text content
      const container = range.commonAncestorContainer;
      const element =
        container.nodeType === Node.TEXT_NODE
          ? container.parentElement
          : container;

      // Extract full text content from the containing element
      const fullText = element.textContent || element.innerText || "";

      // Find the sentence containing the selected text
      const sentence = extractSentenceContainingText(fullText, selectedText);

      return {
        sentence: sentence,
        isSingleWord: selectedText.split(/\s+/).length === 1,
      };
    } catch (error) {
      console.warn("Error extracting context:", error);
      return null;
    }
  }

  /**
   * Extract the sentence containing the selected text
   * @param {string} fullText - The full text content
   * @param {string} selectedText - The selected text
   * @returns {string|null} The sentence containing the selected text
   */
  function extractSentenceContainingText(fullText, selectedText) {
    if (!fullText || !selectedText) {
      return null;
    }

    // Clean up the text (normalize whitespace)
    const cleanFullText = fullText.replace(/\s+/g, " ").trim();
    const cleanSelectedText = selectedText.replace(/\s+/g, " ").trim();

    // Find the position of selected text in full text
    const selectedIndex = cleanFullText
      .toLowerCase()
      .indexOf(cleanSelectedText.toLowerCase());

    if (selectedIndex === -1) {
      return null;
    }

    // Look for sentence boundaries around the selected text
    const beforeText = cleanFullText.substring(0, selectedIndex);
    const afterText = cleanFullText.substring(
      selectedIndex + cleanSelectedText.length
    );

    // Find sentence start (look backward for sentence enders or beginning)
    const sentenceStartMatch = beforeText.match(/[.!?…]+\s*([^.!?…]*)$/);
    const sentenceStart = sentenceStartMatch
      ? sentenceStartMatch[1]
      : beforeText;

    // Find sentence end (look forward for sentence enders or end)
    const sentenceEndMatch = afterText.match(/^([^.!?…]*)[.!?…]/);
    const sentenceEnd = sentenceEndMatch ? sentenceEndMatch[1] : afterText;

    const sentence = (sentenceStart + cleanSelectedText + sentenceEnd).trim();
    return sentence.length > 10 ? sentence : null;
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
      collectWithContext(selectedText, selection);
    }
  });

  // Direct word collection
  function collectWord(selectedText) {
    chrome.runtime.sendMessage({
      action: "collectWord",
      text: selectedText,
      needsArticle: false,
      context: null,
    });

    showCollectionFeedback(selectedText, "Direct Collection", "#4285f4");
  }

  // Context-based collection
  function collectWithContext(selectedText, selection) {
    const contextInfo = getSelectionContext(selection);

    chrome.runtime.sendMessage({
      action: "collectWithContext",
      text: selectedText,
      needsArticle: true,
      context: contextInfo,
    });

    showCollectionFeedback(
      selectedText,
      contextInfo?.sentence
        ? `Context: "${contextInfo.sentence.substring(0, 50)}..."`
        : "Context Collection",
      "#059669"
    );
  }

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

  // Double-click for quick word collection (defaults to direct collection)
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
      z-index: 10000;
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
    document.head.appendChild(style);

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
        if (style.parentNode) {
          style.parentNode.removeChild(style);
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

  console.log(
    "Text Collector content script with dual collection modes loaded"
  );
})();
