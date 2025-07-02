// Utility functions for the extension

/**
 * Generate a unique ID
 */
export function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

/**
 * Sanitize text input
 */
export function sanitizeText(text) {
  if (typeof text !== "string") return "";
  return text.trim().replace(/[\u0000-\u001F\u007F-\u009F]/g, "");
}

/**
 * Validate URL format
 */
export function isValidUrl(string) {
  try {
    const url = new URL(string);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch (_) {
    return false;
  }
}

/**
 * Format date for display
 */
export function formatDate(date) {
  const now = new Date();
  const targetDate = new Date(date);
  const diffMs = now - targetDate;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;

  return targetDate.toLocaleDateString();
}

/**
 * Format file size
 */
export function formatBytes(bytes) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

/**
 * Debounce function
 */
export function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function
 */
export function throttle(func, limit) {
  let inThrottle;
  return function (...args) {
    if (!inThrottle) {
      func.apply(this, args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Extract words from text
 */
export function extractWords(text) {
  if (!text || typeof text !== "string") return [];

  // Enhanced word extraction for multiple languages
  const tokens =
    text.match(/[\w\u00C0-\u017F\u0100-\u024F\u1E00-\u1EFF]+/g) || [];

  // Remove duplicates and filter short words
  return [...new Set(tokens)]
    .filter((word) => word && word.length > 1)
    .sort((a, b) => {
      const indexA = text.toLowerCase().indexOf(a.toLowerCase());
      const indexB = text.toLowerCase().indexOf(b.toLowerCase());
      return indexA - indexB;
    });
}

/**
 * Escape HTML to prevent XSS
 */
export function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Create DOM element with attributes
 */
export function createElement(tag, attributes = {}, children = []) {
  const element = document.createElement(tag);

  Object.entries(attributes).forEach(([key, value]) => {
    if (key === "className") {
      element.className = value;
    } else if (key === "textContent") {
      element.textContent = value;
    } else if (key === "innerHTML") {
      element.innerHTML = value;
    } else {
      element.setAttribute(key, value);
    }
  });

  children.forEach((child) => {
    if (typeof child === "string") {
      element.appendChild(document.createTextNode(child));
    } else if (child instanceof Element) {
      element.appendChild(child);
    }
  });

  return element;
}

/**
 * Show toast notification
 */
export function showToast(message, type = "info", duration = 3000) {
  const toast = createElement("div", {
    className: `toast toast-${type}`,
    textContent: message,
  });

  document.body.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.add("toast-show");
  });

  setTimeout(() => {
    toast.classList.add("toast-hide");
    setTimeout(() => {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 300);
  }, duration);
}

/**
 * Copy text to clipboard
 */
export async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch (err) {
    // Fallback for older browsers
    const textArea = document.createElement("textarea");
    textArea.value = text;
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
      document.execCommand("copy");
      return true;
    } catch (err) {
      return false;
    } finally {
      document.body.removeChild(textArea);
    }
  }
}

/**
 * Validate word input
 */
export function validateWord(word) {
  if (!word || typeof word !== "string") {
    return { valid: false, error: "Word is required" };
  }

  const sanitized = sanitizeText(word);
  if (sanitized.length === 0) {
    return { valid: false, error: "Word cannot be empty" };
  }

  if (sanitized.length > 500) {
    return { valid: false, error: "Word is too long (max 500 characters)" };
  }

  return { valid: true, word: sanitized };
}

/**
 * Calculate storage size
 */
export function calculateStorageSize(data) {
  return new Blob([JSON.stringify(data)]).size;
}

/**
 * Retry function with exponential backoff
 */
export async function retry(fn, maxAttempts = 3, baseDelay = 1000) {
  let lastError;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt === maxAttempts) {
        throw lastError;
      }

      const delay = baseDelay * Math.pow(2, attempt - 1);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }
}
