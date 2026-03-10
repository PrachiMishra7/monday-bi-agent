# 📊 Monday.com Business Intelligence Agent

AI-powered Business Intelligence agent that answers founder-level business questions using data from monday.com boards.

This project was built as part of the **Skylark Drones Technical Assignment**.

---

## 🚀 Overview

Founders often need quick answers to business questions like:

- How healthy is our pipeline?
- What is our total deal value?
- Which sectors generate the most revenue?
- Who are the top performers?

This project builds an **AI-powered BI agent** that connects to **monday.com boards**, processes messy business data, and provides **actionable insights** through a conversational interface.

---

## 🧠 Key Features

### 1️⃣ Monday.com Integration
- Connects directly to monday.com using GraphQL API
- Dynamically fetches data from multiple boards
- Supports pagination for large datasets

### 2️⃣ Data Resilience
Handles messy real-world data including:
- Missing values
- Inconsistent column names
- Different date formats
- Unassigned owners

### 3️⃣ Business Intelligence Metrics
The system automatically computes:

- Total deals in pipeline
- Pipeline value
- Deals by owner
- Deals by sector
- Work order revenue
- Completion rates
- Cross-board revenue insights

### 4️⃣ Conversational AI Agent
Users can ask natural questions such as:

```
How many deals are in the pipeline?
Which sectors generate the most revenue?
Who are the top performers?
How healthy is our pipeline?
```

The agent interprets metrics and generates **founder-level insights**.

### 5️⃣ Leadership Update Generator
Automatically generates executive reports including:

- Pipeline health
- Operations performance
- Top sectors
- Wins and risks
- Recommended actions

---

## 🏗️ Architecture

```
monday.com API
        │
        ▼
Data Extraction Layer
(agent.py)
        │
        ▼
Metrics Engine
(pipeline analytics)
        │
        ▼
AI Insights Generator
(Groq LLM)
        │
        ▼
Streamlit Interface
(app.py)
```

---

## 🖥️ Tech Stack

- Python
- Streamlit – Web interface
- Groq LLM – AI insights generation
- Monday.com GraphQL API
- Data processing with Python

---

## 📂 Project Structure

```
monday-bi-agent
│
├── app.py              # Streamlit UI
├── agent.py            # Data processing + AI agent
├── monday_api.py       # monday.com API integration
├── requirements.txt    # Python dependencies
└── README.md
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the repository

```
git clone https://github.com/PrachiMishra7/monday-bi-agent.git
cd monday-bi-agent
```

---

### 2️⃣ Install dependencies

```
pip install -r requirements.txt
```

---

### 3️⃣ Set Environment Variables

Create a `.env` file:

```
MONDAY_API_KEY=your_monday_api_key
GROQ_API_KEY=your_groq_api_key
```

---

### 4️⃣ Run the application

```
streamlit run app.py
```

Open in browser:

```
http://localhost:8501
```

---

## 📊 Example Questions

Try asking:

- How many deals are in the pipeline?
- Which sectors generate the most revenue?
- Who are the top performers on the deals team?
- What is our win rate and average deal size?
- Give me a cross-board view of the energy sector.

---

## 📈 Future Improvements

With more time, the following features could be added:

- Revenue forecasting
- Deal conversion prediction
- Interactive charts and dashboards
- Slack / email leadership updates
- Role-based analytics dashboards

---

## 👩‍💻 Author

**Prachi Mishra**  
Christ University  
BTech – Computer Science

---

## 📌 Assignment

Skylark Drones – Technical Assignment  
**Monday.com Business Intelligence Agent**

---

## 🔗 Links

GitHub Repository  
https://github.com/PrachiMishra7/monday-bi-agent

Live Demo  
https://monday-bi-agent-2lwwkwxl5vcke4fl2cai6b.streamlit.app/
