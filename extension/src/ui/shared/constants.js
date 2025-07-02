// Application constants
export const APP_NAME = "AnkiWandler";
export const VERSION = "2.0.0";

// Storage keys
export const STORAGE_KEYS = {
  WORDS: "words",
  SETTINGS: "settings",
  SYNC_QUEUE: "syncQueue",
  STATS: "stats",
};

// Default settings
export const DEFAULT_SETTINGS = {
  serverUrl: "http://localhost:8000",
  apiKey: "",
  autoSync: true,
  syncInterval: 300000, // 5 minutes
  maxWords: 1000,
  theme: "light",
};

// Word collection types
export const COLLECTION_TYPES = {
  DIRECT: "direct",
  CONTEXT: "context",
};

// Sync status
export const SYNC_STATUS = {
  PENDING: "pending",
  SYNCING: "syncing",
  COMPLETED: "completed",
  FAILED: "failed",
};

// Message types for communication
export const MESSAGE_TYPES = {
  COLLECT_WORD: "collectWord",
  COLLECT_WITH_CONTEXT: "collectWithContext",
  SYNC_TO_SERVER: "syncToServer",
  GET_STATS: "getStats",
  UPDATE_SETTINGS: "updateSettings",
  GET_WORDS: "getWords",
  DELETE_WORD: "deleteWord",
  CLEAR_ALL: "clearAll",
  TEST_CONNECTION: "testConnection",
};

// UI constants
export const UI = {
  POPUP_WIDTH: 380,
  POPUP_HEIGHT: 580,
  TOAST_DURATION: 3000,
  ANIMATION_DURATION: 200,
};

// API endpoints
export const API_ENDPOINTS = {
  HEALTH: "/",
  ADD_WORD: "/api/v1/words/add",
  ADD_WORD_LIST: "/api/v1/words/add_list",
  PROCESSED_WORDS: "/api/v1/words/processed",
  PENDING_WORDS: "/api/v1/words/pending",
};

// Error messages
export const ERROR_MESSAGES = {
  NO_SELECTION: "No text selected",
  SYNC_FAILED: "Failed to sync with server",
  CONNECTION_FAILED: "Unable to connect to server",
  STORAGE_ERROR: "Storage operation failed",
  INVALID_API_KEY: "Invalid API key",
  WORD_TOO_LONG: "Selected text is too long (max 500 characters)",
};

// Success messages
export const SUCCESS_MESSAGES = {
  WORD_COLLECTED: "Word collected successfully",
  SYNC_COMPLETED: "Sync completed",
  SETTINGS_SAVED: "Settings saved",
  CONNECTION_OK: "Connection successful",
};
