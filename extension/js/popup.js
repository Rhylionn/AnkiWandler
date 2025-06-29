// Updated popup script for Text Collector extension

document.addEventListener("DOMContentLoaded", async function () {
  await loadStats();
  setupEventListeners();

  // Update stats every few seconds while popup is open
  const statsInterval = setInterval(loadStats, 2000);

  // Clean up interval when popup closes
  window.addEventListener("beforeunload", () => {
    clearInterval(statsInterval);
  });
});

function setupEventListeners() {
  document.getElementById("openManager").addEventListener("click", openManager);
  document.getElementById("syncBtn").addEventListener("click", syncToServer);
  document
    .getElementById("settingsBtn")
    .addEventListener("click", openSettings);
}

async function loadStats() {
  try {
    const result = await chrome.storage.local.get(["collection"]);
    const collection = result.collection || [];

    // Update total items
    document.getElementById("totalItems").textContent = collection.length;

    // Count by collection type
    const directCount = collection.filter((item) => !item.needsArticle).length;
    const contextCount = collection.filter((item) => item.needsArticle).length;

    document.getElementById("directItems").textContent = directCount;
    document.getElementById("contextItems").textContent = contextCount;

    // Calculate storage size
    const storageSize = calculateStorageSize(collection);
    document.getElementById("storageUsed").textContent =
      formatBytes(storageSize);

    // Show last added item
    if (collection.length > 0) {
      const lastItem = collection[0]; // Most recent item
      const lastAdded = new Date(lastItem.date);
      const timeAgo = getTimeAgo(lastAdded);

      document.getElementById("lastAdded").textContent = timeAgo;
      showRecentItem(lastItem);
    } else {
      document.getElementById("lastAdded").textContent = "Never";
      hideRecentItem();
    }
  } catch (error) {
    console.error("Error loading stats:", error);
  }
}

function showRecentItem(item) {
  const recentDiv = document.getElementById("recentItem");
  const textDiv = document.getElementById("recentText");
  const metaDiv = document.getElementById("recentMeta");

  const preview =
    item.text.length > 50 ? item.text.substring(0, 50) + "..." : item.text;
  textDiv.textContent = `"${preview}"`;

  const contextLabel = item.needsArticle ? "with context" : "direct";
  metaDiv.textContent = `${contextLabel} collection`;

  recentDiv.style.display = "block";
}

function hideRecentItem() {
  document.getElementById("recentItem").style.display = "none";
}

function calculateStorageSize(collection) {
  return new Blob([JSON.stringify(collection)]).size;
}

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function getTimeAgo(date) {
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}

function openManager() {
  chrome.runtime.sendMessage({ action: "openManager" });
  window.close();
}

function openSettings() {
  chrome.tabs.create({
    url: chrome.runtime.getURL("html/manager.html#settings"),
  });
  window.close();
}

async function syncToServer() {
  const syncBtn = document.getElementById("syncBtn");
  const statusDiv = document.getElementById("statusMessage");
  const statusText = document.getElementById("statusText");

  // Disable button and show pending state
  syncBtn.disabled = true;
  syncBtn.textContent = "Syncing...";

  showStatus("Connecting to server...", "pending");

  try {
    const response = await chrome.runtime.sendMessage({ action: "sync" });

    if (response.success) {
      showStatus(response.message, "success");

      // Update stats after successful sync
      setTimeout(async () => {
        await loadStats();
        hideStatus();
      }, 2000);
    } else {
      showStatus(response.message, "error");
    }
  } catch (error) {
    showStatus("Sync failed: " + error.message, "error");
  } finally {
    // Re-enable button
    syncBtn.disabled = false;
    syncBtn.textContent = "Sync to Server";

    // Hide status after delay
    setTimeout(hideStatus, 3000);
  }
}

function showStatus(message, type) {
  const statusDiv = document.getElementById("statusMessage");
  const statusText = document.getElementById("statusText");

  statusText.textContent = message;
  statusDiv.className = `status status-${type}`;
  statusDiv.style.display = "block";
}

function hideStatus() {
  const statusDiv = document.getElementById("statusMessage");
  statusDiv.style.display = "none";
}

// Listen for storage changes to update stats in real-time
chrome.storage.onChanged.addListener((changes, namespace) => {
  if (namespace === "local" && changes.collection) {
    loadStats();
  }
});
