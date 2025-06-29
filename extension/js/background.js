// Simplified background service worker for Text Collector extension
// Universal popup window approach with simple word selection

// Initialize extension
chrome.runtime.onInstalled.addListener(() => {
  createContextMenus();
  updateBadge();
});

chrome.runtime.onStartup.addListener(() => {
  updateBadge();
});

// Create context menus
function createContextMenus() {
  chrome.contextMenus.removeAll(() => {
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
}

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  const selectedText = info.selectionText?.trim();
  if (!selectedText) return;

  try {
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
      // Context collection using popup window
      await openWordSelectionPopup(selectedText);
    }
  } catch (error) {
    console.error("Error handling context menu click:", error);
    showNotification("Error collecting text", "Error");
  }
});

// Open word selection popup
async function openWordSelectionPopup(selectedText) {
  try {
    // Store selection data for popup access
    await chrome.storage.local.set({
      pendingWordSelection: {
        text: selectedText,
        timestamp: Date.now(),
      },
    });

    // Create popup window
    const popup = await chrome.windows.create({
      url: chrome.runtime.getURL("html/word-selector.html"),
      type: "popup",
      width: 650,
      height: 350,
      left: 50,
      top: 50,
      focused: true,
    });

    // Store popup window ID for cleanup
    await chrome.storage.local.set({
      activeWordSelectorWindow: popup.id,
    });

    // Auto-cleanup after 60 seconds if no action taken
    setTimeout(async () => {
      try {
        await cleanupWordSelection();
      } catch (e) {
        // Ignore cleanup errors
      }
    }, 60000);
  } catch (error) {
    console.error("Error opening word selection popup:", error);

    // Fallback: direct context collection
    await saveCollectionItem({
      text: selectedText,
      needsArticle: true,
      context: { sentence: selectedText },
    });

    showNotification(selectedText, "Context Collected (Fallback)");
    updateBadge();
  }
}

// Save collection item
async function saveCollectionItem(itemData) {
  try {
    const result = await chrome.storage.local.get(["collection"]);
    const collection = result.collection || [];

    const item = {
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      text: itemData.text.trim(),
      needsArticle: itemData.needsArticle,
      context: itemData.context,
      date: new Date().toISOString(),
      synced: false,
      createdAt: Date.now(),
    };

    // Add to beginning of collection
    collection.unshift(item);

    // Limit collection size (keep last 1000 items)
    if (collection.length > 1000) {
      collection.splice(1000);
    }

    await chrome.storage.local.set({ collection });

    return item;
  } catch (error) {
    console.error("Error saving collection item:", error);
    throw error;
  }
}

// Update extension badge
async function updateBadge() {
  try {
    const result = await chrome.storage.local.get(["collection"]);
    const collection = result.collection || [];
    const count = collection.length;

    if (count > 0) {
      await chrome.action.setBadgeText({ text: count.toString() });
      await chrome.action.setBadgeBackgroundColor({ color: "#059669" });
    } else {
      await chrome.action.setBadgeText({ text: "" });
    }
  } catch (error) {
    console.error("Error updating badge:", error);
  }
}

// Show notification
function showNotification(text, title) {
  try {
    const preview = text.length > 50 ? text.substring(0, 50) + "..." : text;

    chrome.notifications
      .create({
        type: "basic",
        iconUrl: chrome.runtime.getURL("icons/icon.png"),
        title: title,
        message: `"${preview}"`,
      })
      .catch((error) => {
        console.warn("Notification failed:", error);
        // Notification failure shouldn't break the flow
      });
  } catch (error) {
    console.warn("Notification error:", error);
    // Continue without notification if it fails
  }
}

// Clean up word selection session
async function cleanupWordSelection() {
  try {
    const result = await chrome.storage.local.get(["activeWordSelectorWindow"]);

    if (result.activeWordSelectorWindow) {
      try {
        await chrome.windows.remove(result.activeWordSelectorWindow);
      } catch (e) {
        // Window might already be closed
      }
    }

    await chrome.storage.local.remove([
      "pendingWordSelection",
      "activeWordSelectorWindow",
    ]);
  } catch (error) {
    console.error("Error during cleanup:", error);
  }
}

// Handle window closed event
chrome.windows.onRemoved.addListener(async (windowId) => {
  try {
    const result = await chrome.storage.local.get(["activeWordSelectorWindow"]);

    if (result.activeWordSelectorWindow === windowId) {
      // Word selector window was closed, clean up
      await chrome.storage.local.remove([
        "pendingWordSelection",
        "activeWordSelectorWindow",
      ]);
    }
  } catch (error) {
    // Ignore errors during cleanup
  }
});

// Message handling
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  handleMessage(request, sender, sendResponse);
  return true; // Keep message channel open for async responses
});

async function handleMessage(request, sender, sendResponse) {
  try {
    switch (request.action) {
      case "updateBadge":
        await updateBadge();
        sendResponse({ success: true });
        break;

      case "openManager":
        await chrome.tabs.create({
          url: chrome.runtime.getURL("html/manager.html"),
        });
        sendResponse({ success: true });
        break;

      case "saveWordWithContext":
        try {
          // Validate inputs
          if (!request.word || !request.context) {
            throw new Error("Missing word or context data");
          }

          const item = await saveCollectionItem({
            text: request.word,
            needsArticle: true,
            context: { sentence: request.context },
          });

          await updateBadge();

          // Show notification (non-blocking)
          try {
            showNotification(request.word, "Word Added");
          } catch (notifError) {
            console.warn("Notification failed:", notifError);
          }

          // Close word selector window
          await cleanupWordSelection();

          sendResponse({ success: true, item });
        } catch (error) {
          console.error("Error saving word with context:", error);
          sendResponse({ success: false, error: error.message });
        }
        break;

      case "closeWordSelector":
        await cleanupWordSelection();
        sendResponse({ success: true });
        break;

      case "collectWord":
      case "collectWithContext":
        const savedItem = await saveCollectionItem({
          text: request.text,
          needsArticle: request.needsArticle,
          context: request.context,
        });

        await updateBadge();

        // Send confirmation back to content script
        if (sender.tab) {
          chrome.tabs
            .sendMessage(sender.tab.id, {
              action: "textCollected",
              text: request.text,
              needsArticle: request.needsArticle,
            })
            .catch(() => {
              // Ignore if content script not available
            });
        }

        sendResponse({ success: true, item: savedItem });
        break;

      case "sync":
        const syncResult = await syncToServer();
        sendResponse(syncResult);
        break;

      case "testConnection":
        const testResult = await testConnection(
          request.serverAddress,
          request.serverPort,
          request.apiToken
        );
        sendResponse(testResult);
        break;

      default:
        sendResponse({ success: false, error: "Unknown action" });
    }
  } catch (error) {
    console.error("Error handling message:", error);
    sendResponse({ success: false, error: error.message });
  }
}

// Sync functionality
async function syncToServer() {
  try {
    const settings = await chrome.storage.local.get([
      "serverAddress",
      "serverPort",
      "apiToken",
    ]);

    if (!settings.serverAddress || !settings.apiToken) {
      throw new Error("Server configuration missing");
    }

    const collection = await chrome.storage.local.get(["collection"]);
    const items = collection.collection || [];
    const unsyncedItems = items.filter((item) => !item.synced);

    if (unsyncedItems.length === 0) {
      return {
        success: true,
        message: "No items to sync",
        count: 0,
      };
    }

    // Prepare words for API
    const words = unsyncedItems.map((item) => ({
      word: item.text,
      date: item.date.split("T")[0],
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

    // Remove synced items from collection
    const syncedIds = unsyncedItems.map((item) => item.id);
    const remainingItems = items.filter((item) => !syncedIds.includes(item.id));

    await chrome.storage.local.set({ collection: remainingItems });
    await updateBadge();

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
