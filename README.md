<p align="center">
  <img src="https://raw.githubusercontent.com/Ajakovski/YourStockNews/main/banner.svg" 
       alt="StockAI Banner" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-active-brightgreen" />
  <img src="https://img.shields.io/badge/python-3.12-blue" />
  <img src="https://img.shields.io/badge/backend-FastAPI-orange" />
  <img src="https://img.shields.io/badge/license-AGPL3.0-lightgrey" />
</p>

*A full‑stack system combining real‑time news ingestion, AI filtering,
and a customizable user dashboard.*

## 🚀 Overview

**YourStockNews** is a modern full‑stack Web App designed to give users
a personalized and intelligent view of stock‑related news.\
Instead of overwhelming users with endless articles, the system filters,
classifies, and organizes financial news so each user can quickly see
what truly matters.

The backend data engine is maintained in a **private repository**
(`AI-Stock-Automatization`).\
This repository focuses on the **Web Application layer**, combining: -
Real‑time AI-filtered data\
- Personalized user experience\
- Scalable backend API\
- Clean, intuitive frontend

------------------------------------------------------------------------

## 🧩 Core Concept

YourStockNews uses a fully automated backend (hosted privately) that: -
Fetches stock market and business news\
- Cleans & preprocesses text\
- Classifies each article by sentiment, severity, and ticker relevance\
- Stores structured results in a database

This Web App then pulls that processed data through a secure API and
presents it in a customizable interface.

You get the **power of an AI‑processed data pipeline**, wrapped in a
modern, user-friendly frontend.

------------------------------------------------------------------------

## 🎯 Features

### ✔ AI‑Powered News Feed

-   Sentiment scoring (Bullish / Bearish / Neutral)\
-   Severity ranking (High, Medium, Low)\
-   Fully deduplicated and noise‑filtered\
-   Custom watchlist-based article relevance

### ✔ Personalized Dashboard

-   User watchlists\
-   Adjustable scan intervals\
-   Custom severity sensitivity\
-   Clean and fast UI

### ✔ Modular Full‑Stack Architecture

-   Backend API (FastAPI or Flask planned)\
-   Frontend (React / Next.js planned)\
-   Secure data delivery from private backend repository\
-   Designed for multi-user systems

### ✔ Real-Time Data (via Private Backend)

The backend repository (`AI-Stock-Automatization`) handles: - News API
integrations\
- Database migrations\
- AI classification logic\
- Logging & monitoring\
- Stability and performance

This separation makes YourStockNews: - **more secure** (sensitive logic
hidden)\
- **more scalable** (frontends can be replaced anytime)\
- **more flexible** (easy integrations and new platforms)

------------------------------------------------------------------------

## 🏗 System Architecture

    YourStockNews/
    │
    ├── frontend/
    │   ├── components/
    │   ├── pages/
    │   ├── services/
    │   └── hooks/
    │
    ├── backend-api/
    │   ├── routes/
    │   ├── models/
    │   ├── controllers/
    │   └── utils/
    │
    └── external-data-engine (private)
        └── AI-Stock-Automatization/
            ├── StockAI-Bot2.4.py
            ├── mvp_alerts.py
            ├── med_alerts.db
            ├── watchlist.txt
            ├── company_map.json
            └── bot.log

------------------------------------------------------------------------

## 🌐 How YourStockNews Works

1.  **Backend engine (private repo)**\
    Fetches news → filters articles → runs AI scoring → updates
    database.

2.  **API layer (this repo)**\
    Exposes secure endpoints for:

    -   latest news\
    -   article severity\
    -   sentiment distribution\
    -   personalized filters

3.  **Frontend Web App**\
    Displays data dynamically with:

    -   user dashboards\
    -   stock watchlist pages\
    -   severity views\
    -   company‑specific feeds

4.  **User customizations**\
    Persisted in database to tailor future alerts.

------------------------------------------------------------------------

## 🛠 Tech Stack (Planned & In Progress)

### **Frontend**

-   React.js / Next.js\
-   TailwindCSS\
-   Charting (Recharts / ECharts)\
-   Authentication UI

### **Backend API**

-   FastAPI / Flask\
-   SQLAlchemy\
-   JWT Auth (future)\
-   Async calls to backend data engine

### **Private Data Engine (External)**

-   Python 3\
-   SQLite\
-   OpenAI GPT Models\
-   News APIs\
-   Custom severity pipeline

------------------------------------------------------------------------

## 🧪 Development Milestones

### ✅ Completed (Private Repo)

-   AI classification v2.4.0\
-   News ingestion engine\
-   DB schema migration system\
-   Company → ticker mapping\
-   Severity logic refactor\
-   Full logging

### 🟡 Active (This Repo)

-   API layer (backend for frontend)\
-   Dashboard UI\
-   Global feed view\
-   Watchlist-based filtering

### 🔵 Upcoming

-   Authentication system\
-   User profiles & preferences\
-   Real-time live updates (WebSockets)\
-   Exportable news summaries\
-   Mobile UI layout

------------------------------------------------------------------------

## 🔮 Roadmap

### Short‑Term

-   Connect Web App to backend API\
-   Display real-time AI-filtered news

### Mid‑Term

-   Add interactive visualizations\
-   Extend filtering options\
-   Add push notifications

### Long‑Term

-   Custom LLM sentiment model\
-   Portfolio risk scoring\
-   Full mobile PWA support

------------------------------------------------------------------------

## ⭐ Vision

YourStockNews aims to be the **smartest stock news dashboard available
to everyday users**, not by predicting markets, but by: - removing
noise\
- highlighting real risks\
- surfacing relevant insights\
- empowering users to react quickly

This project brings together **backend automation**, **AI
intelligence**, and **clean UI** to create a real, practical financial
information tool.

------------------------------------------------------------------------

## 🙌 Contributing

Feedback, ideas, and pull requests are welcome.\
Feature requests are encouraged --- the project is rapidly evolving.
