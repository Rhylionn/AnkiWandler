// Rewritten background service worker for Text Collector extension
// Clean separation of concerns with word selection popup for context collection

// Create context menus on extension startup
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "collectWord",
    title: "Collect Word",
    contexts: ["selection"],
  });

  chrome.contextMenus.create({
    id: "collectWithContext",
    title: "Collect with Context",
    contexts: ["selection"],
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const selectedText = info.selectionText?.trim();
  if (!selectedText) return;

  if (info.menuItemId === "collectWord") {
    // Direct word collection
    await saveCollectionItem({
      text: selectedText,
      needsArticle: false,
      context: null,
    });

    showNotification(selectedText, "Word Collected");
    updateBadge();
  } else if (info.menuItemId === "collectWithContext") {
    // Context collection with word selection popup
    try {
      await chrome.scripting.executeScript({
        target: { tabId: tab.id },
        function: showWordSelectionPopup,
        args: [selectedText],
      });
    } catch (error) {
      console.error("Error showing word selection popup:", error);
      showNotification("Failed to show word selection", "Error");
    }
  }
});

// Function to inject into page to show word selection popup
function showWordSelectionPopup(selectedSentence) {
  // Remove any existing popup
  const existingPopup = document.getElementById("text-collector-popup");
  if (existingPopup) {
    existingPopup.remove();
  }

  // Create popup overlay
  const overlay = document.createElement("div");
  overlay.id = "text-collector-popup";
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    z-index: 2147483647;
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  `;

  // Create popup content
  const popup = document.createElement("div");
  popup.style.cssText = `
    background: white;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
    max-width: 600px;
    width: 90%;
    max-height: 400px;
    overflow-y: auto;
  `;

  // Create header
  const header = document.createElement("div");
  header.style.cssText = `
    margin-bottom: 20px;
    text-align: center;
  `;
  header.innerHTML = `
    <h3 style="margin: 0 0 8px 0; color: #111827; font-size: 18px; font-weight: 600;">
      Select Word to Learn
    </h3>
    <p style="margin: 0; color: #6b7280; font-size: 14px;">
      Click on the word you want to add to your collection
    </p>
  `;

  // Create word container
  const wordContainer = document.createElement("div");
  wordContainer.style.cssText = `
    line-height: 1.8;
    font-size: 16px;
    margin-bottom: 20px;
    padding: 16px;
    background: #f9fafb;
    border-radius: 8px;
    border: 1px solid #e5e7eb;
  `;

  // Split sentence into words and punctuation
  const words = selectedSentence.match(/\S+/g) || [];

  words.forEach((token, index) => {
    // Separate word from punctuation
    const wordMatch = token.match(/^([a-zA-ZäöüÄÖÜß]+)(.*)/);

    if (wordMatch) {
      const [, word, punctuation] = wordMatch;

      // Create clickable word span
      const wordSpan = document.createElement("span");
      wordSpan.textContent = word;
      wordSpan.style.cssText = `
        cursor: pointer;
        padding: 4px 6px;
        margin: 2px;
        border-radius: 4px;
        transition: all 0.2s ease;
        background: #dbeafe;
        color: #1e40af;
        font-weight: 500;
      `;

      // Add hover effects
      wordSpan.addEventListener("mouseenter", () => {
        wordSpan.style.background = "#1e40af";
        wordSpan.style.color = "white";
        wordSpan.style.transform = "translateY(-1px)";
      });

      wordSpan.addEventListener("mouseleave", () => {
        wordSpan.style.background = "#dbeafe";
        wordSpan.style.color = "#1e40af";
        wordSpan.style.transform = "translateY(0)";
      });

      // Handle word selection
      wordSpan.addEventListener("click", () => {
        // Send message to background script to save the word
        chrome.runtime.sendMessage({
          action: "saveWordWithContext",
          word: word,
          context: selectedSentence,
        });

        // Remove popup
        overlay.remove();
      });

      wordContainer.appendChild(wordSpan);

      // Add punctuation as non-clickable text
      if (punctuation) {
        const punctSpan = document.createElement("span");
        punctSpan.textContent = punctuation;
        punctSpan.style.cssText = `
          color: #6b7280;
          margin-right: 4px;
        `;
        wordContainer.appendChild(punctSpan);
      }
    } else {
      // Token is just punctuation or special characters
      const punctSpan = document.createElement("span");
      punctSpan.textContent = token;
      punctSpan.style.cssText = `
        color: #6b7280;
        margin-right: 4px;
      `;
      wordContainer.appendChild(punctSpan);
    }

    // Add space between tokens (except for last one)
    if (index < words.length - 1) {
      wordContainer.appendChild(document.createTextNode(" "));
    }
  });

  // Create cancel button
  const cancelButton = document.createElement("button");
  cancelButton.textContent = "Cancel";
  cancelButton.style.cssText = `
    background: #f3f4f6;
    color: #374151;
    border: 1px solid #d1d5db;
    padding: 8px 16px;
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    font-weight: 500;
    transition: all 0.2s ease;
    width: 100%;
  `;

  cancelButton.addEventListener("mouseenter", () => {
    cancelButton.style.background = "#e5e7eb";
  });

  cancelButton.addEventListener("mouseleave", () => {
    cancelButton.style.background = "#f3f4f6";
  });

  cancelButton.addEventListener("click", () => {
    overlay.remove();
  });

  // Assemble popup
  popup.appendChild(header);
  popup.appendChild(wordContainer);
  popup.appendChild(cancelButton);
  overlay.appendChild(popup);

  // Add to page
  document.body.appendChild(overlay);

  // Close on overlay click
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) {
      overlay.remove();
    }
  });

  // Close on Escape key
  const handleEscape = (e) => {
    if (e.key === "Escape") {
      overlay.remove();
      document.removeEventListener("keydown", handleEscape);
    }
  };
  document.addEventListener("keydown", handleEscape);
}

// Helper function to save collection item
async function saveCollectionItem(itemData) {
  try {
    const result = await chrome.storage.local.get(["collection"]);
    const collection = result.collection || [];

    // Create clean item structure
    const item = {
      id: Date.now().toString(),
      text: itemData.text,
      needsArticle: itemData.needsArticle,
      context: itemData.context,
      date: new Date().toISOString(),
      synced: false,
    };

    collection.unshift(item); // Add to beginning
    await chrome.storage.local.set({ collection });
  } catch (error) {
    console.error("Error saving text:", error);
    throw error;
  }
}

// Show notification
function showNotification(text, type) {
  const preview = text.length > 40 ? text.substring(0, 40) + "..." : text;

  chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon48.png",
    title: type,
    message: `"${preview}" has been collected.`,
  });
}

// Update extension badge with collection count
async function updateBadge() {
  try {
    const result = await chrome.storage.local.get(["collection"]);
    const collection = result.collection || [];
    const count = collection.length;

    if (count > 0) {
      chrome.action.setBadgeText({ text: count.toString() });
      chrome.action.setBadgeBackgroundColor({ color: "#4285f4" });
    } else {
      chrome.action.setBadgeText({ text: "" });
    }
  } catch (error) {
    console.error("Error updating badge:", error);
  }
}

// Initialize badge on startup
chrome.runtime.onStartup.addListener(updateBadge);
chrome.runtime.onInstalled.addListener(updateBadge);

// Listen for messages from popup/manager/content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "updateBadge") {
    updateBadge();
    return;
  }

  if (request.action === "openManager") {
    chrome.tabs.create({
      url: chrome.runtime.getURL("manager.html"),
    });
    return;
  }

  // Handle word with context saving from popup
  if (request.action === "saveWordWithContext") {
    saveCollectionItem({
      text: request.word,
      needsArticle: true,
      context: { sentence: request.context },
    }).then(() => {
      updateBadge();
      showNotification(request.word, "Word with Context Collected");
    });
    return;
  }

  // Handle keyboard shortcuts from content script
  if (
    request.action === "collectWord" ||
    request.action === "collectWithContext"
  ) {
    saveCollectionItem({
      text: request.text,
      needsArticle: request.needsArticle,
      context: request.context,
    }).then(() => {
      updateBadge();
      // Send confirmation back to content script
      if (sender.tab) {
        chrome.tabs.sendMessage(sender.tab.id, {
          action: "textCollected",
          text: request.text,
          needsArticle: request.needsArticle,
        });
      }
    });
    return;
  }
});

// Enhanced sync functionality with clean data structure
async function syncToServer() {
  try {
    const settings = await chrome.storage.local.get([
      "serverAddress",
      "serverPort",
      "apiToken",
    ]);
    const collection = await chrome.storage.local.get(["collection"]);

    if (!settings.serverAddress || !settings.apiToken) {
      throw new Error("Server configuration missing");
    }

    const items = collection.collection || [];
    const unsyncedItems = items.filter((item) => !item.synced);

    if (unsyncedItems.length === 0) {
      return { success: true, message: "No items to sync", count: 0 };
    }

    // Prepare words for API with clean structure
    const words = unsyncedItems.map((item) => ({
      word: item.text,
      date: item.date.split("T")[0], // Extract date part
      context_sentence: item.context?.sentence || null,
      needs_article: item.needsArticle,
    }));

    const serverUrl = `http://${settings.serverAddress}:${
      settings.serverPort || 8000
    }`;

    const response = await fetch(`${serverUrl}/api/v1/words/add_list`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${settings.apiToken}`,
      },
      body: JSON.stringify({ words }),
    });

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    // Mark items as synced and remove them from collection
    const syncedIds = unsyncedItems.map((item) => item.id);
    const remainingItems = items.filter((item) => !syncedIds.includes(item.id));

    await chrome.storage.local.set({ collection: remainingItems });
    updateBadge();

    const contextCount = unsyncedItems.filter(
      (item) => item.needsArticle
    ).length;
    const directCount = unsyncedItems.length - contextCount;

    return {
      success: true,
      message: `Synced ${directCount} direct + ${contextCount} context words`,
      count: unsyncedItems.length,
    };
  } catch (error) {
    console.error("Sync error:", error);
    return {
      success: false,
      message: error.message,
      count: 0,
    };
  }
}

// Expose sync function to other parts of the extension
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "sync") {
    syncToServer().then(sendResponse);
    return true; // Keep message channel open for async response
  }
});

// Test server connection
async function testConnection(serverAddress, serverPort, apiToken) {
  try {
    const serverUrl = `http://${serverAddress}:${serverPort || 8000}`;

    const response = await fetch(serverUrl, {
      method: "GET",
      headers: {
        Authorization: `Bearer ${apiToken}`,
      },
    });

    return {
      success: response.ok,
      message: response.ok
        ? "Connection successful"
        : `Server error: ${response.status}`,
    };
  } catch (error) {
    return {
      success: false,
      message: `Connection failed: ${error.message}`,
    };
  }
}

// Expose test connection function
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "testConnection") {
    testConnection(
      request.serverAddress,
      request.serverPort,
      request.apiToken
    ).then(sendResponse);
    return true;
  }
});
