// Background service worker for Text Collector extension

// Create context menu on extension startup
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: "collectText",
    title: "Collect Text",
    contexts: ["selection"],
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === "collectText" && info.selectionText) {
    const selectedText = info.selectionText.trim();

    if (selectedText) {
      // Get the page URL and title
      const url = tab.url;
      const title = tab.title;

      // Create collection item
      const item = {
        id: Date.now().toString(),
        text: selectedText,
        url: url,
        title: title,
        date: new Date().toISOString(),
        synced: false,
      };

      // Save to storage
      try {
        const result = await chrome.storage.local.get(["collection"]);
        const collection = result.collection || [];
        collection.unshift(item); // Add to beginning

        await chrome.storage.local.set({ collection });

        // Show notification
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon48.png",
          title: "Text Collected",
          message: `"${selectedText.substring(0, 50)}${
            selectedText.length > 50 ? "..." : ""
          }" has been added to your collection.`,
        });

        // Update badge
        updateBadge();
      } catch (error) {
        console.error("Error saving text:", error);
        chrome.notifications.create({
          type: "basic",
          iconUrl: "icons/icon48.png",
          title: "Collection Error",
          message: "Failed to save text to collection.",
        });
      }
    }
  }
});

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

// Listen for messages from popup/manager
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "updateBadge") {
    updateBadge();
  }

  if (request.action === "openManager") {
    chrome.tabs.create({
      url: chrome.runtime.getURL("manager.html"),
    });
  }
});

// Sync functionality
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

    // Prepare words for API
    const words = unsyncedItems.map((item) => ({
      word: item.text,
      date: item.date.split("T")[0], // Extract date part
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

    return {
      success: true,
      message: `Successfully synced ${unsyncedItems.length} items`,
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
