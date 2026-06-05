# Fanqie Index

[![中文](https://img.shields.io/badge/lang-中文-red)](README.md)

> Comprehensive tracking of Fanqie Novel's four major rankings (Male New/Read, Female New/Read), with daily automated data scraping and AI-powered trend analysis, deployed as a premium online dashboard.

---

## Features

| Feature | Description |
|---------|-------------|
| Auto Scraping | Daily automated scraping of Top 30 books across all sub-categories for all four rankings |
| Resume Support | Scraper can resume from where it left off if interrupted, via `task_state_*.json` |
| Font Decoding | Automatic decoding of Fanqie's custom font encryption (Unicode 0xE3E0 offset cipher) |
| Trend Analysis | Automatic day-over-day comparison: new entries / dropped / rank changes / readership growth |
| AI Summary | OpenAI-compatible API integration for per-category market trend analysis |
| Trend Compass | Independent trend page with multi-period analysis (7/14/30/all days) and market heat charts |
| Author Inspiration | Author analysis page with theme trends, competitive analysis, reader profiles, and writing suggestions |
| Data Export | Export data in Excel (.xlsx), CSV, or JSON formats |
| Dashboard | Dark editorial-style dashboard with typewriter animation and waterfall book cards |
| Responsive | Full mobile support with slide-out sidebar menu |
| Navigation | Unified navigation bar for switching between four rankings, with gear icon for API configuration |
| History View | Date picker supports viewing historical ranking data from any available date |
| Data API | Static JSON API endpoints for reading latest data by rank type |

---

## Getting Started

### Prerequisites

- **Python 3.9+**
- **Git** (optional, for version control)
- (Optional) An OpenAI-compatible API key for AI analysis

### Step 1: Clone/Download

```bash
git clone <repository-url>
cd FanqieRankTracker
```

Or download and extract the ZIP directly.

### Step 2: Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### Step 3: Run the Scraper

```bash
# Scrape all four rankings (Female New/Read, Male New/Read), Top 30 per category
python scrape_fanqie_ranks.py
```

The scraper automatically discovers all categories and saves data to the `data/` directory.

### Step 4: Build Dashboard Data

```bash
# Without AI analysis (uses rule-based summaries)
python scripts/build_latest.py

# With AI analysis (requires environment variables)
export API_BASE_URL="https://your-api-endpoint/v1"
export API_KEY="your-api-key"
export API_MODEL="your-model-name"
python scripts/build_latest.py
```

### Step 5: Local Preview

```bash
python -m http.server 8000
```

Open `http://localhost:8000` in your browser. The top navigation bar allows switching between the four rankings.

---

## API Configuration

There are two ways to configure the AI analysis API:

1. **Environment variables** (for build script): Set `API_BASE_URL`, `API_KEY`, `API_MODEL`
2. **Web UI** (for real-time frontend calls): Click the gear icon in the top navigation bar, fill in and save. Data is stored in browser localStorage.

Supports any OpenAI-compatible API (e.g., Moonshot / DeepSeek / self-hosted endpoints). If not configured, the system automatically falls back to rule-based summaries -- **core functionality is unaffected**.

---

## Data API Endpoints

The build script generates static JSON endpoints:

| Type | Path | Description |
|------|------|-------------|
| Index | `api/latest.json` | Returns all available types with corresponding URLs |
| Full Data | `api/latest/{prefix}_all.json` | All categories, trends, and books for a specific ranking |
| Single Category | `api/latest/{prefix}_{category}.json` | Data for a single category in a specific ranking |

Where `{prefix}` is one of: `female_new`, `female_read`, `male_new`, `male_read`.

---

## Project Structure

```
FanqieZhiShu/
├── scrape_fanqie_ranks.py      # Fanqie Novel scraper (Playwright)
├── verify_font_mapping.py      # Font mapping verification tool
├── setup.bat                   # Windows one-click setup script
├── requirements.txt            # Python dependencies
├── .env / .env.example         # Environment variables
│
├── scripts/
│   ├── build_latest.py         # Trend comparison + AI analysis build script
│   └── migrate_md_to_json.py   # One-time migration utility
│
├── js/
│   ├── config.js               # Rank type registry + URL parameter parsing
│   ├── nav.js                  # Top navigation bar + API config modal
│   ├── utils.js                # Shared utility functions
│   ├── app.js                  # Dashboard page logic
│   ├── trend.js                # Trend compass page logic
│   ├── author.js               # Author inspiration page logic
│   └── export.js               # Data export (CSV, Excel, JSON)
│
├── css/
│   ├── style.css               # Dark editorial theme styles
│   └── author.css              # Author page styles
│
├── index.html                  # Dashboard entry page
├── trend.html                  # Trend compass analysis page
├── author.html                 # Author inspiration page
│
├── data/                       # Data directory (auto-generated)
│   ├── fanqie_{prefix}_ranks_YYYYMMDD.json  # Daily raw snapshots
│   ├── latest_{prefix}_ranks.json           # Latest aggregated data
│   ├── market_summary_{prefix}.json         # Market hot-spot analysis
│   ├── dates_{prefix}.json                  # Date index
│   ├── task_state_{prefix}_YYYYMMDD.json    # Scraper resume state
│   ├── trends/
│   │   └── {prefix}_YYYY-MM-DD.json         # Trend archives
│   └── author/
│       ├── theme_trends_{prefix}.json       # Theme trends
│       ├── competitive_analysis_{prefix}.json # Competitive analysis
│       ├── reader_profile_{prefix}.json     # Reader profiles
│       └── creation_suggestions_{prefix}.json # Writing suggestions
│
├── api/latest/                 # Static JSON API endpoints
│   ├── {prefix}_all.json       # Full data
│   ├── {prefix}_index.json     # Category index
│   └── {prefix}_{category}.json # Single category data
│
├── README.md                   # Chinese documentation
├── README_EN.md                # English documentation
├── TUTORIAL.md                 # Beginner tutorial
├── 使用教程.md                  # Detailed usage guide
└── PROJECT_MAP.md              # Project map
```

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                        Data Collection                          │
│  Playwright Scraper ──→ Decode Font ──→ Save Daily Snapshot     │
│  (scrape_fanqie_ranks.py)        (data/fanqie_*_YYYYMMDD.json) │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Processing                          │
│  build_latest.py ──→ Trend Compare ──→ AI Summary ──→ Output    │
│  (scripts/build_latest.py)                                      │
│     ↓              ↓              ↓              ↓              │
│  latest_*.json   trends/      market_summary  api/latest/      │
│                                  data/author/                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend Display                         │
│  index.html ──→ app.js      (Dashboard: categories/books/trends)│
│  trend.html ──→ trend.js    (Trend Compass: multi-period analysis)│
│  author.html ──→ author.js  (Author: themes/competition/readers)│
│  Shared: config.js / nav.js / utils.js / export.js              │
└─────────────────────────────────────────────────────────────────┘
```

---

## FAQ

**Q: What if the scraper runs slowly?**
Each ranking requires scraping multiple categories, with scroll loading per category. A full run taking 10-15 minutes is normal. You can modify `RANK_CONFIGS` in `scrape_fanqie_ranks.py` to keep only the rankings you need.

**Q: What if the scraper gets interrupted?**
Simply re-run `python scrape_fanqie_ranks.py`. The scraper will automatically resume from where it left off. Progress is saved in `data/task_state_*.json` files.

**Q: Can I use it without configuring AI?**
Yes! The system automatically falls back to rule-based summaries (e.g., "3 new entries; Book X rose +5 ranks"). You just won't have the AI natural language analysis.

**Q: Can I track different rankings?**
Yes, modify `RANK_CONFIGS` in `scrape_fanqie_ranks.py` to adjust gender, type, and entry_cat as needed.

**Q: How to view historical data?**
Use the date navigation at the bottom of the dashboard page. Click `◀` `▶` to switch dates, or click the date number to open a calendar picker.

**Q: What if data files get too large?**
- `data/fanqie_*_ranks_YYYYMMDD.json` are daily snapshots and can be deleted for old dates
- `data/trends/` contains trend archives that can be cleaned up
- After deletion, trend analysis for those dates will no longer be available

**Q: How to run automatically on a schedule?**
- Windows: Use Task Scheduler to set up daily scraper runs
- Linux/Mac: Use cron jobs
- See [TUTORIAL.md](TUTORIAL.md) "Advanced Usage" section for details

---

## License

MIT

---

<p align="center">
  <sub>Made with coffee and AI -- Data updates daily via automation, zero manual maintenance required</sub>
</p>
