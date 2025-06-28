# AnkiWandler 📝

An integrated language learning tool that captures words from web browsing and automatically creates flashcards in Anki using AI-powered translations and contextual examples.

## ⚠️ Early Development Stage

**This project is currently in early development and requires specific configuration to work properly.** It is not yet ready for general use.

## 🎯 Project Overview

AnkiWandler is a comprehensive language learning workflow consisting of three main components:

1. **Browser Extension** - Captures words and text snippets while browsing
2. **FastAPI Server** - Processes collected words using local AI and external APIs
3. **Anki Add-on** - Automatically creates flashcards from processed word data

### How It Works

1. **Collect**: Highlight text on any webpage and save it via the browser extension
2. **Process**: Words are sent to a Python API that generates translations, example sentences, and additional language data using AI
3. **Learn**: The Anki extension automatically creates flashcards with the processed information

### Components

- **Web Extension**: Stores words locally until synced with server
- **FastAPI Python API**: Manages word processing with local AI and external API calls
- **Anki Add-on**: Retrieves processed data and creates flashcards automatically

## 🔧 Limitations

- No automated installation process
- Hard-coded configurations for specific use cases
- Limited error handling and user guidance
- Server and AI dependencies must be manually configured

## 🔮 Future Vision

The goal is to create a seamless language learning tool where:

- Users can effortlessly collect vocabulary while reading
- AI automatically provides rich context and translations
- Flashcards are created without manual intervention
- The system adapts to individual learning patterns
