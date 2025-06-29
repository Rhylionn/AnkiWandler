// Updated manager script for Text Collector extension
// Enhanced for universal source tracking (web/pdf)
// Fixed storage size calculation and scroll to top on section switch

let currentCollection = [];
let filteredCollection = [];
let currentEditingId = null;

// Initialize the manager
document.addEventListener("DOMContentLoaded", async function () {
  await loadCollection();
  await loadSettings();
  setupEventListeners();

  // Check for hash navigation
  if (window.location.hash === "#settings") {
    switchSection("settings");
  }

  // Listen for storage changes
  chrome.storage.onChanged.addListener((changes, namespace) => {
    if (namespace === "local" && changes.collection) {
      loadCollection();
    }
  });
});

// Event listeners setup
function setupEventListeners() {
  // Navigation
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", (e) => {
      const section = e.target.dataset.section;
      switchSection(section);
    });
  });

  // Search
  document
    .getElementById("searchInput")
    .addEventListener("input", handleSearch);

  // Sync button
  document.getElementById("syncBtn").addEventListener("click", syncToServer);

  // Settings
  document.getElementById("testBtn").addEventListener("click", testConnection);
  document.getElementById("saveBtn").addEventListener("click", saveSettings);
  document.getElementById("clearBtn").addEventListener("click", clearAllData);
}

// Navigation with scroll to top fix
function switchSection(sectionName) {
  // Update nav items
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.classList.remove("active");
    if (item.dataset.section === sectionName) {
      item.classList.add("active");
    }
  });

  // Show/hide sections
  document.querySelectorAll(".section").forEach((section) => {
    section.classList.remove("active");
  });
  document.getElementById(sectionName).classList.add("active");

  // Update URL hash
  window.location.hash = sectionName === "collection" ? "" : "#" + sectionName;

  // Scroll to top when switching sections
  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}

// Collection management
async function loadCollection() {
  try {
    const result = await chrome.storage.local.get(["collection"]);
    currentCollection = result.collection || [];
    filteredCollection = [...currentCollection];

    updateStats();
    renderCollection();
  } catch (error) {
    console.error("Error loading collection:", error);
    showToast("Error loading collection", "error");
  }
}

function updateStats() {
  const total = currentCollection.length;
  document.getElementById("totalCount").textContent = total;

  // Count by collection type
  const directCount = currentCollection.filter(
    (item) => !item.needsArticle
  ).length;
  const contextCount = currentCollection.filter(
    (item) => item.needsArticle
  ).length;

  document.getElementById("directCount").textContent = directCount;
  document.getElementById("contextCount").textContent = contextCount;

  const storageSize = calculateStorageSize(currentCollection);
  document.getElementById("storageSize").textContent = formatBytes(storageSize);
}

function calculateStorageSize(collection) {
  // Fixed: Return 0 if collection is empty or has no items
  if (!collection || collection.length === 0) {
    return 0;
  }
  return new Blob([JSON.stringify(collection)]).size;
}

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function renderCollection() {
  const container = document.getElementById("collectionContainer");
  const emptyState = document.getElementById("emptyState");

  if (filteredCollection.length === 0) {
    container.innerHTML = "";
    emptyState.style.display = "block";
    return;
  }

  emptyState.style.display = "none";

  container.innerHTML = filteredCollection
    .map((item) => {
      const typeClass = item.needsArticle ? "context-badge" : "direct-badge";
      const typeLabel = item.needsArticle ? "Context" : "Direct";

      return `
                <div class="item" data-id="${item.id}">
                    <div class="item-header">
                        <div class="item-content" id="content-${
                          item.id
                        }">${escapeHtml(item.text)}</div>
                        <span class="${typeClass}">${typeLabel}</span>
                    </div>
                    ${
                      item.context?.sentence
                        ? `
                        <div class="item-context">
                            ${escapeHtml(item.context.sentence)}
                        </div>
                    `
                        : ""
                    }
                    <div class="item-meta">
                        <span class="item-date">${formatDate(item.date)}</span>
                    </div>
                    <div class="item-actions">
                        <button class="btn edit-btn" data-id="${
                          item.id
                        }">Edit</button>
                        <button class="btn btn-danger delete-btn" data-id="${
                          item.id
                        }">Delete</button>
                    </div>
                </div>
            `;
    })
    .join("");

  // Add event listeners to all edit and delete buttons
  container.querySelectorAll(".edit-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const id = e.target.getAttribute("data-id");
      editItem(id);
    });
  });

  container.querySelectorAll(".delete-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const id = e.target.getAttribute("data-id");
      deleteItem(id);
    });
  });
}

function handleSearch() {
  const query = document.getElementById("searchInput").value.toLowerCase();

  if (query.trim() === "") {
    filteredCollection = [...currentCollection];
  } else {
    filteredCollection = currentCollection.filter(
      (item) =>
        item.text.toLowerCase().includes(query) ||
        (item.context?.sentence &&
          item.context.sentence.toLowerCase().includes(query))
    );
  }

  renderCollection();
}

// Item actions (edit/delete remain the same as before)
function editItem(id) {
  if (currentEditingId && currentEditingId !== id) {
    saveEdit(currentEditingId);
  }

  currentEditingId = id;
  const contentElement = document.getElementById(`content-${id}`);

  if (!contentElement) {
    console.error("Content element not found for ID:", id);
    return;
  }

  const currentText =
    currentCollection.find((item) => item.id === id)?.text || "";

  contentElement.contentEditable = true;
  contentElement.textContent = currentText;
  contentElement.style.background = "#f3f4f6";
  contentElement.style.border = "1px solid #d1d5db";
  contentElement.style.padding = "8px";
  contentElement.focus();

  const range = document.createRange();
  range.selectNodeContents(contentElement);
  const selection = window.getSelection();
  selection.removeAllRanges();
  selection.addRange(range);

  const handleKeydown = function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      saveEdit(id);
    }
    if (e.key === "Escape") {
      e.preventDefault();
      cancelEdit(id);
    }
  };

  const handleBlur = function (e) {
    if (!e.relatedTarget || !e.relatedTarget.classList.contains("btn")) {
      setTimeout(() => {
        if (currentEditingId === id) {
          saveEdit(id);
        }
      }, 100);
    }
  };

  contentElement.addEventListener("keydown", handleKeydown);
  contentElement.addEventListener("blur", handleBlur);
  contentElement._handleKeydown = handleKeydown;
  contentElement._handleBlur = handleBlur;
}

async function saveEdit(id) {
  if (!currentEditingId || currentEditingId !== id) return;

  const contentElement = document.getElementById(`content-${id}`);
  if (!contentElement) return;

  const newText = contentElement.textContent.trim();

  if (newText && newText !== "") {
    const itemIndex = currentCollection.findIndex((item) => item.id === id);
    if (itemIndex !== -1) {
      currentCollection[itemIndex].text = newText;

      const filteredIndex = filteredCollection.findIndex(
        (item) => item.id === id
      );
      if (filteredIndex !== -1) {
        filteredCollection[filteredIndex].text = newText;
      }

      try {
        await chrome.storage.local.set({ collection: currentCollection });
        showToast("Item updated successfully", "success");
      } catch (error) {
        console.error("Error saving edit:", error);
        showToast("Error saving changes", "error");
      }
    }
  } else {
    showToast("Cannot save empty text", "error");
  }

  // Clean up
  if (contentElement._handleKeydown) {
    contentElement.removeEventListener(
      "keydown",
      contentElement._handleKeydown
    );
    delete contentElement._handleKeydown;
  }
  if (contentElement._handleBlur) {
    contentElement.removeEventListener("blur", contentElement._handleBlur);
    delete contentElement._handleBlur;
  }

  contentElement.contentEditable = false;
  contentElement.style.background = "";
  contentElement.style.border = "";
  contentElement.style.padding = "4px";
  currentEditingId = null;

  renderCollection();
}

function cancelEdit(id) {
  const contentElement = document.getElementById(`content-${id}`);
  if (!contentElement) return;

  if (contentElement._handleKeydown) {
    contentElement.removeEventListener(
      "keydown",
      contentElement._handleKeydown
    );
    delete contentElement._handleKeydown;
  }
  if (contentElement._handleBlur) {
    contentElement.removeEventListener("blur", contentElement._handleBlur);
    delete contentElement._handleBlur;
  }

  contentElement.contentEditable = false;
  contentElement.style.background = "";
  contentElement.style.border = "";
  contentElement.style.padding = "4px";
  currentEditingId = null;

  renderCollection();
}

async function deleteItem(id) {
  const item = currentCollection.find((item) => item.id === id);
  if (!item) return;

  const confirmMessage = `Are you sure you want to delete this item?\n\n"${item.text.substring(
    0,
    100
  )}${item.text.length > 100 ? "..." : ""}"`;

  if (confirm(confirmMessage)) {
    try {
      // Remove from both collections
      currentCollection = currentCollection.filter((item) => item.id !== id);
      filteredCollection = filteredCollection.filter((item) => item.id !== id);

      await chrome.storage.local.set({ collection: currentCollection });

      updateStats();
      renderCollection();
      showToast("Item deleted successfully", "success");

      chrome.runtime.sendMessage({ action: "updateBadge" });
    } catch (error) {
      console.error("Error deleting item:", error);
      showToast("Error deleting item", "error");
    }
  }
}

// Sync functionality
async function syncToServer() {
  const syncBtn = document.getElementById("syncBtn");
  const originalText = syncBtn.textContent;

  syncBtn.disabled = true;
  syncBtn.textContent = "Syncing...";

  try {
    const response = await chrome.runtime.sendMessage({ action: "sync" });

    if (response.success) {
      showToast(response.message, "success");
    } else {
      showToast(response.message, "error");
    }
  } catch (error) {
    showToast("Sync failed: " + error.message, "error");
  } finally {
    syncBtn.disabled = false;
    syncBtn.textContent = originalText;
  }
}

// Settings management
async function loadSettings() {
  try {
    const result = await chrome.storage.local.get([
      "serverAddress",
      "serverPort",
      "apiToken",
    ]);

    document.getElementById("serverAddress").value = result.serverAddress || "";
    document.getElementById("serverPort").value = result.serverPort || "8000";
    document.getElementById("apiToken").value = result.apiToken || "";
  } catch (error) {
    console.error("Error loading settings:", error);
  }
}

async function saveSettings() {
  const serverAddress = document.getElementById("serverAddress").value.trim();
  const serverPort = document.getElementById("serverPort").value.trim();
  const apiToken = document.getElementById("apiToken").value.trim();

  try {
    await chrome.storage.local.set({
      serverAddress,
      serverPort: serverPort || "8000",
      apiToken,
    });

    showStatus("Settings saved successfully", "success");
    showToast("Settings saved", "success");
  } catch (error) {
    showStatus("Error saving settings", "error");
    showToast("Error saving settings", "error");
  }
}

async function testConnection() {
  const serverAddress = document.getElementById("serverAddress").value.trim();
  const serverPort = document.getElementById("serverPort").value.trim();
  const apiToken = document.getElementById("apiToken").value.trim();

  if (!serverAddress || !apiToken) {
    showStatus("Please enter server address and API token", "error");
    return;
  }

  const testBtn = document.getElementById("testBtn");
  testBtn.disabled = true;
  testBtn.textContent = "Testing...";

  showStatus("Testing connection...", "pending");

  try {
    const response = await chrome.runtime.sendMessage({
      action: "testConnection",
      serverAddress,
      serverPort: serverPort || "8000",
      apiToken,
    });

    if (response.success) {
      showStatus("Connection successful!", "success");
    } else {
      showStatus(response.message, "error");
    }
  } catch (error) {
    showStatus("Connection test failed", "error");
  } finally {
    testBtn.disabled = false;
    testBtn.textContent = "Test Connection";
  }
}

async function clearAllData() {
  if (
    confirm(
      "Are you sure you want to delete all collected text? This action cannot be undone."
    )
  ) {
    if (
      confirm(
        "This will permanently delete all your collected text. Are you absolutely sure?"
      )
    ) {
      try {
        await chrome.storage.local.set({ collection: [] });
        currentCollection = [];
        filteredCollection = [];

        updateStats();
        renderCollection();
        showToast("All data cleared", "success");

        chrome.runtime.sendMessage({ action: "updateBadge" });
      } catch (error) {
        showToast("Error clearing data", "error");
      }
    }
  }
}

// Utility functions
function showStatus(message, type) {
  const statusDiv = document.getElementById("connectionStatus");
  const statusText = document.getElementById("statusText");

  statusText.textContent = message;
  statusDiv.className = `status status-${type}`;
  statusDiv.style.display = "block";

  if (type === "success") {
    setTimeout(() => {
      statusDiv.style.display = "none";
    }, 3000);
  }
}

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;

  document.body.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "slideOut 0.3s ease";
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }, 3000);
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatDate(dateString) {
  const date = new Date(dateString);
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
