# SENTINEL — AI-Native OSINT Investigation System

A crowd-driven, hypothesis-validated missing persons investigation platform.

## Quick Start

```bash
npm install
npm run dev
```

Then open http://localhost:5173

## Architecture

**11-Step Intelligence Pipeline:**
1. Case Created
2. Community Ingestion (Reddit, Twitter, TikTok, Forums)
3. Claim Extraction (AI layer)
4. Claim Clustering
5. Credibility Scoring (crowd + source quality + consistency)
6. AI Verification (OSINT + image matching + contradiction detection)
7. Misinformation Filtering (bot detection, image reuse)
8. Lead Generation
9. Knowledge Graph Update
10. Agent Chat (contextual Q&A)
11. Law Enforcement Mode

## Pages
- `/` — Dashboard (case list)
- `/case` — Investigation view (5 tabs)
- `/new-case` — Create new case (3-step wizard)

## Key Components
- `ClaimClusters` — Crowd-extracted claim clusters with scoring
- `Leads` — Validated actionable leads with evidence chains
- `KnowledgeGraph` — SVG knowledge graph (claims → evidence → contradictions)
- `AgentChat` — Contextual AI agent with case awareness
- `CommunityIntelligence` — Pipeline visualization + raw data view
