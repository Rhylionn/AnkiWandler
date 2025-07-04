// Simplified background service worker for Text Collector extension
// Universal popup window approach with simple word selection
// Notification system removed

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

      updateBadge();
    } else if (info.menuItemId === "collectWithContext") {
      // Context collection using popup window
      await openWordSelectionPopup(selectedText);
    }
  } catch (error) {
    console.error("Error handling context menu click:", error);
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
  console.log("🚀 Starting sync process...");

  try {
    // Step 1: Get settings
    console.log("📋 Getting settings...");
    const settings = await chrome.storage.local.get([
      "serverAddress",
      "serverPort",
      "apiToken",
    ]);

    console.log("⚙️ Settings retrieved:", {
      serverAddress: settings.serverAddress,
      serverPort: settings.serverPort,
      apiToken: settings.apiToken ? "***PROVIDED***" : "❌ MISSING",
    });

    if (!settings.serverAddress || !settings.apiToken) {
      throw new Error(
        "Server configuration missing. Please configure server settings."
      );
    }

    // Step 2: Get collection
    console.log("📦 Getting collection...");
    const collection = await chrome.storage.local.get(["collection"]);
    const items = collection.collection || [];
    const unsyncedItems = items.filter((item) => !item.synced);

    console.log("📊 Collection stats:", {
      totalItems: items.length,
      unsyncedItems: unsyncedItems.length,
    });

    if (unsyncedItems.length === 0) {
      console.log("✅ No items to sync");
      return {
        success: true,
        message: "No items to sync",
        count: 0,
      };
    }

    // Step 3: Prepare words
    console.log("🔄 Preparing words for API...");
    const words = unsyncedItems.map((item) => ({
      word: item.text,
      date: item.date.split("T")[0],
      context_sentence: item.context?.sentence || null,
      needs_article: item.needsArticle,
    }));

    console.log("📝 Prepared words:", words);

    // Step 4: Build URL
    console.log("🔗 Building server URL...");
    const serverUrl = buildServerUrl(
      settings.serverAddress,
      settings.serverPort
    );
    const apiEndpoint = `${serverUrl}/api/v1/words/add_list`;

    console.log("🌐 Final API endpoint:", apiEndpoint);

    // Step 5: Prepare request
    const requestBody = JSON.stringify({ words });
    const requestHeaders = {
      "Content-Type": "application/json",
      Authorization: `Bearer ${settings.apiToken}`,
      Accept: "application/json",
    };

    console.log("📨 Request details:", {
      method: "POST",
      url: apiEndpoint,
      headers: {
        ...requestHeaders,
        Authorization: "Bearer ***HIDDEN***",
      },
      bodyLength: requestBody.length,
    });

    // Step 6: Make request with timeout
    console.log("🚀 Making fetch request...");
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      console.log("⏰ Request timeout triggered");
      controller.abort();
    }, 30000);

    let response;
    try {
      response = await fetch(apiEndpoint, {
        method: "POST",
        headers: requestHeaders,
        body: requestBody,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      console.log("📡 Fetch completed, response received");
    } catch (fetchError) {
      clearTimeout(timeoutId);
      console.error("❌ Fetch failed:", fetchError);

      if (fetchError.name === "AbortError") {
        throw new Error("Request timeout - server took too long to respond");
      }

      if (fetchError.message.includes("Failed to fetch")) {
        console.error("💔 Network error details:", {
          message: fetchError.message,
          stack: fetchError.stack,
          name: fetchError.name,
        });
        throw new Error(
          "Network error - Cannot reach server. Check URL and internet connection."
        );
      }

      throw fetchError;
    }

    // Step 7: Check response
    console.log("📊 Response details:", {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
      url: response.url,
      type: response.type,
    });

    // Log response headers
    console.log("📋 Response headers:");
    for (const [key, value] of response.headers.entries()) {
      console.log(`  ${key}: ${value}`);
    }

    if (!response.ok) {
      let errorMessage = `Server error ${response.status}: ${response.statusText}`;

      try {
        const errorData = await response.text();
        console.log("❌ Error response body:", errorData);
        if (errorData) {
          errorMessage += ` - ${errorData}`;
        }
      } catch (e) {
        console.log("⚠️ Could not read error response body");
      }

      throw new Error(errorMessage);
    }

    // Step 8: Parse response
    console.log("📖 Parsing response...");
    let responseData;
    try {
      responseData = await response.json();
      console.log("✅ Response data:", responseData);
    } catch (parseError) {
      console.error("❌ Failed to parse response JSON:", parseError);
      throw new Error("Invalid JSON response from server");
    }

    // Step 9: Update local storage
    console.log("💾 Updating local storage...");
    const syncedIds = unsyncedItems.map((item) => item.id);
    const remainingItems = items.filter((item) => !syncedIds.includes(item.id));

    await chrome.storage.local.set({ collection: remainingItems });
    await updateBadge();

    console.log("✅ Local storage updated, badge updated");

    const contextCount = unsyncedItems.filter(
      (item) => item.needsArticle
    ).length;
    const directCount = unsyncedItems.length - contextCount;

    const successMessage = `Synced ${directCount} direct + ${contextCount} context words`;
    console.log("🎉 Sync completed successfully:", successMessage);

    return {
      success: true,
      message: successMessage,
      count: unsyncedItems.length,
    };
  } catch (error) {
    console.error("💥 Sync error:", error);
    console.error("📊 Error details:", {
      name: error.name,
      message: error.message,
      stack: error.stack,
    });

    return {
      success: false,
      message: error.message,
      count: 0,
    };
  }
}

// Enhanced URL building with validation
function buildServerUrl(serverAddress, serverPort) {
  console.log("🔧 Building URL from:", { serverAddress, serverPort });

  if (!serverAddress) {
    throw new Error("Server address is required");
  }

  // Remove any existing protocol and whitespace
  let cleanAddress = serverAddress.trim().replace(/^https?:\/\//, "");

  // Remove trailing slashes
  cleanAddress = cleanAddress.replace(/\/+$/, "");

  console.log("🧹 Cleaned address:", cleanAddress);

  if (!cleanAddress) {
    throw new Error("Invalid server address");
  }

  // Determine protocol
  let protocol = "https://";

  // Use HTTP only for localhost/127.0.0.1 or if explicitly specified
  if (
    serverAddress.startsWith("http://") ||
    cleanAddress.startsWith("localhost") ||
    cleanAddress.startsWith("127.0.0.1")
  ) {
    protocol = "http://";
  }

  console.log("🔒 Using protocol:", protocol);

  // Build the URL
  let url = protocol + cleanAddress;

  // Add port if specified and not standard
  if (
    serverPort &&
    !(
      (protocol === "http://" && serverPort === "80") ||
      (protocol === "https://" && serverPort === "443")
    )
  ) {
    url += ":" + serverPort;
    console.log("🔌 Added port:", serverPort);
  }

  console.log("🌐 Final URL:", url);
  return url;
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
