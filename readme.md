# Personalized News Curator

An AI‑powered CLI news recommendation engine that learns your preferences through feedback and continuously delivers relevant articles. Built with LangChain, Groq, and ChromaDB.

---

## Overview

The Personalized News Curator is a command‑line tool that asks for your initial interests, suggests articles, and refines its understanding of your preferences with every like or dislike. It uses:

- **Topic extraction & scoring** – Each article is tagged with 3‑5 topics; your feedback adjusts their scores.
- **Semantic vector search** – Article embeddings are stored in ChromaDB; recommendations are reranked by similarity to your preference vector.
- **Multi‑signal reranking** – Combines semantic similarity, recency, source authority, and content quality.
- **Explainable AI** – Every recommendation comes with a natural‑language explanation, telling you *why* that article was chosen.

The system persists your history (SQLite), topic scores (JSON), and embeddings (ChromaDB) so your preferences carry across sessions.

---

## Key Features

| Feature | Description |
| :--- | :--- |
| **Interactive CLI** | Rich, colourful terminal interface powered by `rich`. |
| **Initial topic seeding** | Enter 3 topics to bootstrap your profile. |
| **Continuous feedback loop** | Like (1) or dislike (d) each article to update your model. |
| **Smart topic selection** | Weighted random selection of topics based on your scores – higher‑scored topics appear more often. |
| **Semantic reranking** | Candidate articles are reranked by cosine similarity to your positive (and negative) preference vectors. |
| **Multi‑signal scoring** | Combines similarity, recency, source authority, and content quality into a final score. |
| **Recommendation explanations** | Each suggested article includes a natural‑language explanation of why it was chosen, referencing your specific interests. |
| **Trending discovery** | Press `t` to fetch trending topics from NewsAPI and explore outside your usual interests. |
| **Persistent storage** | SQLite for article history, JSON for topic scores, ChromaDB for embeddings. |

---

## Architecture

```
news_curator/
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── .env                    # API keys (not committed)
├── history.db              # SQLite database (article history)
├── topic_scores.json       # Topic scores
├── chroma_db/              # ChromaDB vector store
└── src/
    ├── __init__.py
    ├── authority.py        # Domain authority scoring
    ├── cli.py              # Main CLI loop & orchestration
    ├── config.py           # Configuration & weights
    ├── database.py         # SQLite CRUD operations
    ├── display.py          # Rich terminal output
    ├── enrichment.py       # Article summarisation & tagging
    ├── explain.py          # Recommendation explanation generation
    ├── feedback.py         # User input (topics, likes/dislikes)
    ├── preferences.py      # Preference profile generation
    ├── quality.py          # Content quality heuristics
    ├── search.py           # Tavily search integration
    ├── topics.py           # Topic extraction & scoring
    ├── trending.py         # NewsAPI trending topics
    └── vector_store.py     # ChromaDB embedding storage & reranking
```

### Data Flow

1. **User enters 3 topics** → system searches Tavily and shows one article per topic.
2. **User rates each article** (like/dislike) → system extracts topics, updates topic scores, stores embedding in ChromaDB.
3. **User presses `y` (continue)** → system selects a weighted random topic, performs a broad Tavily search, computes preference vectors from liked/disliked articles, reranks candidates using multi‑signal scoring, and returns the top article with an explanation.
4. **User can press `t` (trending)** → fetches trending topics from NewsAPI; selecting one adds it to the topic pool.
5. **User can press `p` (preferences)** → shows a detailed profile of their interests, including topic scores.

---

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- API keys for:
  - [Groq](https://console.groq.com) (free tier available)
  - [Tavily](https://tavily.com) (free tier available)
  - [NewsAPI](https://newsapi.org) (optional, for trending)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/anaumsharif/Personlized-News-Currator-.git
   cd Personlized-News-Currator-
   git checkout groq_model
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux/macOS
   # or
   venv\Scripts\activate         # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file** in the project root
   ```env
   GROQ_API_KEY=your_groq_api_key
   TAVILY_API_KEY=your_tavily_api_key
   NEWSAPI_KEY=your_newsapi_key   # optional
   HUGGINGFACEHUB_API_TOKEN=your_hf_token   # only if using HF API for embeddings
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

---

## Usage

### First Run

- You'll be prompted to enter **3 topics** you're interested in.
- The system will fetch one article per topic and ask for feedback (like/dislike).

### Main Loop Options

| Command | Action |
| :--- | :--- |
| `y` | Get the next recommended article (reranked based on your preferences). |
| `n` | Manually add a new topic and rate an article. |
| `p` | Show your current preference profile (detailed summary). |
| `t` | Fetch trending topics from NewsAPI and explore one. |
| `e` | Exit the application. |

### Example Session

```
Welcome to your Personalized News Curator!
To get started, please tell me three topics you're interested in.
Topic 1: artificial intelligence
Topic 2: renewable energy
Topic 3: space exploration

Great! Searching for the latest articles on your topics...

╭──────────────────────────────────────────────────────────────────── Article for 'artificial intelligence' ─────────────────────────────────────────────────────────────────────╮
│ Source: techcrunch.com                                                                                                                                                       │
│ Summary: OpenAI announced a new language model that can reason through complex math problems...                                                                             │
│ Tags: AI, Language Models, Research                                                                                                                                         │
│ URL: https://techcrunch.com/...                                                                                                                                              │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
Like (1) or Dislike (d)? 1
You liked this article. Updating preferences...

... (more seeding articles)

Options: (y) continue | (n) new topic | (p) show preferences | (t) trending | (e) exit
Your choice: y

Selected topic: 'artificial intelligence' based on your interests

╭────────────────────────────────────────────────────────────────────────── Your Next Suggested Article (Reranked) ──────────────────────────────────────────────────────────────────────────╮
│ Source: reuters.com                                                                                                                                                                 │
│ Summary: EU regulators propose new framework for AI liability...                                                                                                                   │
│ Why this? This article discusses AI regulation, which relates to your interest in 'artificial intelligence'. You've liked articles about AI policy before, and this one is recent   │
│ and from a reputable source (Reuters). It scored high on relevance and authority, which is why it was chosen.                                                                      │
│ URL: https://reuters.com/...                                                                                                                                                      │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
Like (1) or Dislike (d)?
```

---

## Configuration

All tunable parameters are in `src/config.py`:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `WEIGHT_SIMILARITY` | 0.35 | Weight of semantic similarity in final score |
| `WEIGHT_RECENCY` | 0.25 | Weight of article freshness |
| `WEIGHT_AUTHORITY` | 0.20 | Weight of source credibility |
| `WEIGHT_QUALITY` | 0.20 | Weight of content quality |
| `RECENCY_DECAY_RATE` | 0.3 | Exponential decay rate per day (higher = faster decay) |
| `TAVILY_MAX_RESULTS` | 10 | Number of candidates fetched per search |
| `TOPICS_PER_ARTICLE` | 5 | Number of topics extracted per article |

You can adjust these to fine‑tune the recommendation behaviour.

---

## Technology Stack

| Component | Technology |
| :--- | :--- |
| **LLM** | Groq (`llama-3.1-8b-instant`) – fast inference |
| **Embeddings** | Hugging Face Inference API (or local `sentence-transformers` fallback) |
| **Vector Store** | ChromaDB – persistent, local vector database |
| **Search** | Tavily – real‑time news search API |
| **Trending** | NewsAPI – top headlines |
| **Storage** | SQLite (history), JSON (topic scores) |
| **CLI** | Rich – beautiful terminal output |
| **Language** | Python 3.10+ |

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit your changes (`git commit -m 'Add some feature'`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a Pull Request.

---

## License

This project is open source and available under the [MIT License](https://opensource.org/licenses/MIT).

---

## Acknowledgements

- [LangChain](https://www.langchain.com/) for the orchestration framework.
- [Groq](https://groq.com) for the lightning‑fast LLM inference.
- [Tavily](https://tavily.com) for the search API.
- [ChromaDB](https://www.trychroma.com) for the vector database.
- [Rich](https://github.com/Textualize/rich) for the beautiful terminal formatting.

---

