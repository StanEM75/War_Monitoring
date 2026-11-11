
# War Monitoring

![War Monitoring](https://img.magnific.com/free-photo/cruel-war-scenes-digital-painting_456031-162.jpg?semt=ais_hybrid&w=740&q=80)

## Overview

Collect and analyze military conflict reports using AI agents to monitor geopolitical developments and understand modern warfare tactics and strategies.

## Tech Stack

| Technology | Purpose |
|---|---|
| ![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white) | Web scraping, data processing and automation |
| ![OpenAI](https://img.shields.io/badge/OpenAI_API-412991?style=flat&logo=openai&logoColor=white) | Semantic deduplication and event synthesis using LLMs |
| ![AI Agents](https://img.shields.io/badge/AI-Agents-8A2BE2?style=flat) | Coordinate data analysis and question answering |
| ![JSON](https://img.shields.io/badge/JSON-000000?style=flat&logo=json&logoColor=white) | Structured data storage and knowledge artifacts |
| ![pytest](https://img.shields.io/badge/pytest-0A9EDC?style=flat&logo=pytest&logoColor=white) | Automated testing |

## Data Sources

| Source | Purpose |
|---|---|
| [**Institute for the Study of War (ISW)**](https://understandingwar.org/) | Military conflict assessments and geopolitical developments |

## Pipeline Architecture

The project follows four main steps:

### 1. Data Ingestion

- Collect military conflict reports from ISW using Python, Requests and BeautifulSoup.
- Extract article titles, content, publication information and source URLs.
- Incrementally ingest new articles while avoiding previously collected reports.

### 2. Semantic Deduplication

- Use TF-IDF and cosine similarity to identify potentially redundant articles.
- Use the OpenAI API to compare articles and remove confidently identified duplicates.
- Preserve updates, corrections and new developments.

### 3. Information Organization & Event Synthesis

- Group articles by topic and organize their content chronologically.
- Use LLMs with structured outputs to identify and summarize major events.
- Generate JSON knowledge artifacts containing event summaries, reporting periods and supporting evidence.

### 4. AI-Powered Question Answering

- Use a dedicated AI agent to answer questions about military conflicts.
- Retrieve relevant information from the generated knowledge artifacts.
- Provide evidence-based answers with references to original reports.

## Agent Architecture

The project separates data processing from question answering through two specialized agents:

| Agent | Responsibility |
|---|---|
| **Analyze ISW Articles** | Collect new reports and coordinate deduplication, organization and event synthesis tools |
| **Answer to User** | Answer conflict-related questions using existing knowledge artifacts without triggering new ingestion |

## Project Structure

- [`src/ingestion/`](src/ingestion/) — ISW article collection and extraction.
- [`src/tools/analyze_isw_articles/`](src/tools/analyze_isw_articles/) — Deduplication, organization and event synthesis tools.
- [`src/agents/`](src/agents/) — Specialized AI agent instructions.
- [`documentation/`](documentation/) — Data definitions and project documentation.
- [`tests/`](tests/) — Automated ingestion tests.

*Personal project focused on AI agents, LLM-powered information processing and geopolitical monitoring.*
