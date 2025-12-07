# Semantic Similarity Feature

## Overview
The spelling practice app now uses semantic similarity (meaning-based word grouping) in addition to spelling similarity for creating practice batches.

## How It Works

### 50/50 Random Selection
When selecting a batch of words to practice:
- **50% chance**: Words are grouped by **spelling similarity** (existing behavior)
  - Uses Levenshtein distance to find words that look similar
  - Example: "happy", "happily", "unhappy"

- **50% chance**: Words are grouped by **semantic similarity** (NEW)
  - Uses embeddings to find words with similar meanings
  - Example: "happy", "joyful", "cheerful"

### Implementation Details

1. **Embedding Model**: Uses `all-MiniLM-L6-v2` from sentence-transformers
   - Lightweight (90MB)
   - Runs locally on your machine
   - Downloaded and cached on first use

2. **Database Storage**: 
   - New `word_embeddings` table stores vector representations
   - Embeddings are generated once and cached
   - 384-dimensional vectors per word

3. **Similarity Calculation**:
   - Cosine similarity between embedding vectors
   - Min similarity threshold: 0.5 (50%)
   - Returns top semantically related words

## First Run
On the first run after this update, the app will:
1. Download the sentence-transformer model (~90MB, one-time)
2. Generate embeddings for all 469 words
3. Cache them in the database for instant future use

Progress bars will show the status of both operations.

## Benefits
- **Better Learning**: Practice words with similar meanings together
- **Variety**: Alternates between spelling and meaning groupings
- **Smart Grouping**: Helps you learn word relationships and synonyms
- **No Manual Work**: Everything is automatic

## Example Batches

**Spelling-based batch** (traditional):
- "practice", "practical", "practiced", "practicing"

**Semantic-based batch** (new):
- "practice", "rehearse", "train", "exercise"

## Performance
- Embedding generation: ~1-2 seconds for all 469 words
- Semantic similarity lookup: <10ms per query
- No performance impact during practice
