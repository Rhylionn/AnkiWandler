A comprehensive FastAPI application for managing German words with automatic AI processing and English translation.

## Project Structure

```
word_management_api/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app creation
│   ├── config/
│   │   └── settings.py         # Configuration and environment variables
│   ├── database/
│   │   ├── connection.py       # Database connection and initialization
│   │   └── models.py          # Database models
│   ├── auth/
│   │   └── api_key.py         # API key authentication
│   ├── schemas/
│   │   ├── word.py            # Word-related Pydantic models
│   │   └── anki.py            # Anki-related Pydantic models
│   ├── api/
│   │   ├── endpoints/
│   │   │   ├── words.py       # Word management endpoints
│   │   │   ├── ai.py          # AI processing endpoints
│   │   │   └── anki.py        # Anki data endpoints
│   │   └── router.py          # Main API router
│   └── services/
│       ├── word_service.py    # Word business logic
│       ├── ai_service.py      # AI processing logic
│       ├── translation_service.py  # Translation logic
│       └── anki_service.py    # Anki data logic
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
└── run.py                     # Application entry point
```

## Processing Pipeline

### Complete Word Processing Flow:

1. **Word Addition**: German words are added to `pending_words` table
2. **AI Processing**: AI generates German sentence and plural form
3. **Translation**: Both the sentence and word are translated to English
4. **Final Storage**: Complete data moved to `processed_words` table
5. **Cleanup**: Successfully processed words removed from pending table

### Database Schema:

**pending_words**:

- `id`, `word`, `date`, `created_at`, `processing_status`

**processed_words**:

- `id`, `original_word`, `date`, `processed_at`
- `tl_word` (target language word - German)
- `nl_word` (native language word - English)
- `tl_sentence` (target language sentence - German)
- `nl_sentence` (native language sentence - English)
- `tl_plural` (plural form - German)

## Setup Instructions

### 1. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file with your settings:
API_KEY=your-secure-api-key-here
DATABASE_PATH=data/words.db
HOST=0.0.0.0
PORT=8000
DEBUG=True
AI_API_URL=http://localhost:5000/generate
AI_API_TIMEOUT=30
TRANSLATION_API_URL=http://localhost:5001/translate
TRANSLATION_API_TIMEOUT=15
```

### 4. External API Setup

#### AI API Configuration

Your AI API should accept POST requests at the configured endpoint:

**Request Format:**

```json
{
  "prompt": "Please analyze the German word \"Haus\" and provide:\n1. A natural German sentence using this word\n2. The plural form of this word...",
  "word": "Haus",
  "timestamp": "2025-06-08T10:30:00"
}
```

**Expected AI Response:**

```json
{
  "tl_sentence": "Das Haus ist sehr schön und groß.",
  "tl_plural": "Häuser"
}
```

#### Translation API Configuration

Your Translation API should accept POST requests:

**Request Format:**

```json
{
  "text": "Das Haus ist sehr schön und groß.",
  "target_language": "en"
}
```

**Expected Translation Response:**

```json
{
  "translated_text": "The house is very beautiful and big."
}
```

### 5. Run the Application

```bash
python run.py
```

## API Endpoints

### Authentication

All endpoints require Bearer token authentication:

```
Authorization: Bearer your-api-key-here
```

### Word Management

- `POST /api/v1/words/add` - Add single word (triggers full processing pipeline)
- `POST /api/v1/words/add_list` - Add multiple words (triggers batch processing)
- `GET /api/v1/words/pending` - Get words waiting for processing
- `GET /api/v1/words/processed` - Get fully processed words
- `DELETE /api/v1/words/pending/{id}` - Delete pending word
- `DELETE /api/v1/words/processed/{id}` - Delete processed word

### Legacy Endpoints

- `POST /api/v1/ai/create_word` - Legacy AI processing endpoint
- `POST /api/v1/anki/data` - Store Anki data

### Documentation

- API docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Usage Examples

### Add Single German Word

```bash
curl -X POST "http://localhost:8000/api/v1/words/add" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "word": "Serendipität",
    "date": "2025-06-08"
  }'
```

### Add Multiple German Words

```bash
curl -X POST "http://localhost:8000/api/v1/words/add_list" \
  -H "Authorization: Bearer your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "words": [
      {
        "word": "Wanderlust",
        "date": "2025-06-08"
      },
      {
        "word": "Gemütlichkeit",
        "date": "2025-06-07"
      }
    ]
  }'
```

### Get Processed Words

```bash
curl -X GET "http://localhost:8000/api/v1/words/processed" \
  -H "Authorization: Bearer your-api-key"
```

**Example Response:**

```json
[
  {
    "id": 1,
    "original_word": "Wanderlust",
    "date": "2025-06-08",
    "tl_word": "Wanderlust",
    "nl_word": "wanderlust",
    "tl_sentence": "Ich habe großes Wanderlust nach fernen Ländern.",
    "nl_sentence": "I have great wanderlust for distant countries.",
    "tl_plural": "Wanderluste",
    "processed_at": "2025-06-08T10:35:22"
  }
]
```

### Check Processing Status

```bash
curl -X GET "http://localhost:8000/api/v1/words/pending" \
  -H "Authorization: Bearer your-api-key"
```

## Features

- ✅ **Complete Processing Pipeline**: AI → Translation → Storage
- ✅ **Asynchronous Processing**: Non-blocking word addition
- ✅ **Concurrency Control**: Limits concurrent API calls (max 3)
- ✅ **Error Resilience**: Individual failures don't affect batch operations
- ✅ **Status Tracking**: Monitor processing status for each word
- ✅ **Request ID Tracking**: Track batch operations
- ✅ **Configurable Timeouts**: Separate timeouts for AI and translation APIs
- ✅ **Automatic Cleanup**: Successfully processed words auto-removed from pending
- ✅ **Comprehensive Logging**: Detailed processing logs
- ✅ **No Source Dependency**: Simplified word structure

## Processing Pipeline Details

### Step-by-Step Flow:

1. **Word Reception**: German word added to pending_words
2. **AI Processing**:
   - Creates contextual prompt
   - Calls AI API to generate German sentence and plural
3. **Translation Phase**:
   - Translates German sentence to English
   - Translates German word to English
4. **Final Storage**:
   - Stores complete data in processed_words
   - Removes from pending_words
5. **Error Handling**: Failed words remain in pending with status

### Concurrency Management:

- **Semaphore Control**: Max 3 concurrent processing pipelines
- **Timeout Management**: Separate timeouts for AI (30s) and translation (15s)
- **Graceful Degradation**: Individual word failures don't stop batch processing

This system efficiently processes German vocabulary through a complete AI and translation pipeline while maintaining performance and reliability.
