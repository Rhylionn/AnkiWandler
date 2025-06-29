// Fixed word selector popup script

let selectedSentence = null;

// Initialize on DOM load
document.addEventListener("DOMContentLoaded", async function () {
  await loadPendingSelection();
  setupEventListeners();
  window.focus();
});

function setupEventListeners() {
  document.getElementById("cancelBtn").addEventListener("click", closeWindow);

  // Close on Escape key
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      closeWindow();
    }
  });
}

async function loadPendingSelection() {
  try {
    const result = await chrome.storage.local.get(["pendingWordSelection"]);
    const pending = result.pendingWordSelection;

    if (!pending) {
      showError("No text selection found");
      return;
    }

    // Check if data is not too old (60 seconds)
    if (Date.now() - pending.timestamp > 60000) {
      showError("Selection expired, please try again");
      return;
    }

    selectedSentence = pending.text;
    setupWordGrid(pending.text);
  } catch (error) {
    console.error("Error loading pending selection:", error);
    showError("Failed to load text selection");
  }
}

function setupWordGrid(sentence) {
  // Hide loading, show main content
  document.getElementById("loadingState").classList.remove("active");
  document.getElementById("loadingState").style.display = "none";
  document.getElementById("mainContent").style.display = "flex";

  // Create word grid (no need to show selected text anymore)
  const wordsContainer = document.getElementById("wordsContainer");
  wordsContainer.innerHTML = "";

  // Extract unique words
  const words = extractWords(sentence);

  if (words.length === 0) {
    showError("No valid words found in selection");
    return;
  }

  words.forEach((word) => {
    const wordElement = document.createElement("div");
    wordElement.className = "word-item";
    wordElement.textContent = word;

    // Add click handler to select word (not add immediately)
    wordElement.addEventListener("click", function (e) {
      e.stopPropagation();
      e.preventDefault();

      selectWord(word, wordElement);
    });

    wordsContainer.appendChild(wordElement);
  });
}

function selectWord(word, element) {
  // Remove selection from all words
  document.querySelectorAll(".word-item").forEach((item) => {
    item.classList.remove("selected");
  });

  // Select current word
  element.classList.add("selected");
  selectedWord = word;

  // Enable accept button
  const acceptBtn = document.getElementById("acceptBtn");
  acceptBtn.disabled = false;
  acceptBtn.textContent = `Accept "${word}"`;
}

async function acceptSelectedWord() {
  if (!selectedWord) return;

  try {
    // Disable buttons to prevent multiple clicks
    document.getElementById("acceptBtn").disabled = true;
    document.getElementById("cancelBtn").disabled = true;

    await addWord(selectedWord);
  } catch (error) {
    // Re-enable buttons on error
    document.getElementById("acceptBtn").disabled = false;
    document.getElementById("cancelBtn").disabled = false;
    throw error;
  }
}

function extractWords(sentence) {
  try {
    // Enhanced word extraction that handles various languages and punctuation
    const tokens =
      sentence.match(/[\w\u00C0-\u017F\u0100-\u024F\u1E00-\u1EFF]+/g) || [];

    // Remove duplicates and filter out very short words
    const uniqueWords = [...new Set(tokens)]
      .filter((word) => word && word.length > 1)
      .sort((a, b) => {
        // Maintain original order in sentence
        const indexA = sentence.toLowerCase().indexOf(a.toLowerCase());
        const indexB = sentence.toLowerCase().indexOf(b.toLowerCase());
        return indexA - indexB;
      });

    return uniqueWords;
  } catch (error) {
    console.error("Error extracting words:", error);
    return [];
  }
}

async function addWord(word) {
  try {
    // Validate inputs
    if (!word || !selectedSentence) {
      throw new Error("Missing word or sentence data");
    }

    // Send message to background script to save the word
    const response = await chrome.runtime.sendMessage({
      action: "saveWordWithContext",
      word: word.trim(),
      context: selectedSentence.trim(),
    });

    if (response && response.success) {
      showSuccess(word);
    } else {
      const errorMsg =
        response && response.error ? response.error : "Failed to save word";
      throw new Error(errorMsg);
    }
  } catch (error) {
    console.error("Error adding word:", error);

    // Re-enable buttons on error
    document.getElementById("acceptBtn").disabled = false;
    document.getElementById("cancelBtn").disabled = false;

    // Reset word selection
    document.querySelectorAll(".word-item").forEach((item) => {
      item.classList.remove("selected");
    });
    selectedWord = null;
    document.getElementById("acceptBtn").disabled = true;
    document.getElementById("acceptBtn").textContent = "Accept";

    showError(`Failed to add word: ${error.message}`);
  }
}

function showSuccess(word) {
  // Hide main content, show success state
  document.getElementById("mainContent").style.display = "none";
  document.getElementById("successState").style.display = "flex";

  const messageElement = document.getElementById("successMessage");
  if (messageElement) {
    messageElement.textContent = `"${word}" added to your collection with context`;
  }

  // Auto-close countdown
  startCountdown();
}

function startCountdown() {
  let countdown = 2;
  const countdownElement = document.getElementById("countdown");

  if (!countdownElement) {
    // Fallback: close immediately if countdown element not found
    setTimeout(closeWindow, 1000);
    return;
  }

  const timer = setInterval(() => {
    countdown--;
    countdownElement.textContent = countdown;

    if (countdown <= 0) {
      clearInterval(timer);
      closeWindow();
    }
  }, 1000);
}

function showError(message) {
  // Hide loading and main content, show error state
  document.getElementById("loadingState").style.display = "none";
  document.getElementById("mainContent").style.display = "none";
  document.getElementById("errorState").style.display = "flex";

  const errorMessageElement = document.getElementById("errorMessage");
  if (errorMessageElement) {
    errorMessageElement.textContent = message;
  }

  // Auto-close after 3 seconds
  setTimeout(closeWindow, 3000);
}

async function closeWindow() {
  try {
    // Notify background script to clean up
    await chrome.runtime.sendMessage({
      action: "closeWordSelector",
    });
  } catch (error) {
    console.error("Error notifying background script:", error);
  }

  // Close window
  window.close();
}

// Handle page unload
window.addEventListener("beforeunload", async function () {
  try {
    await chrome.runtime.sendMessage({
      action: "closeWordSelector",
    });
  } catch (error) {
    // Ignore errors during cleanup
  }
});
