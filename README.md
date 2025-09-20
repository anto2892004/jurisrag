
# ⚖️ JurisRAG – Agentic RAG for Legal Research

**Team Pico Prode** – Hackathon Project (September 2025)

---

## 📌 Abstract

JurisRAG is an **agentic Retrieval-Augmented Generation (RAG) platform** that transforms plain-English legal questions into **reliable, citation-backed insights** and **structured analytics**.  
Traditional keyword search is slow and incomplete, while generic AI chatbots hallucinate and fail to provide verifiable results.  

Our system integrates **agent-based orchestration with Text→SQL analytics** to support both unstructured and structured queries. Legal judgments are parsed into coherent chunks enriched with metadata (court, jurisdiction, statutes, reliefs, outcomes) and stored in a **hybrid search index (Elasticsearch + Pinecone)**.  

When a query is issued:  
- Specialized agents parse intent  
- Generate **SQL for analytics**  
- Retrieve **semantic + keyword matches**  
- Synthesize plain-language answers with **citations**  
- A **judge model ensures groundedness, jurisdictional fit, and clarity**  

The output combines **summaries, charts, citation panels, and counter-arguments**, drastically reducing research time and improving trust in AI-driven legal insights.

---

## 🛠️ Prototype Overview

**JurisRAG** is designed as a **hybrid legal AI assistant**.

- 📑 **Smart Data Prep** – Judgments are chunked (~4000 words), converted into **1536-d embeddings**, then reduced to **1024 via PCA** for Pinecone efficiency.  
- 🔍 **Hybrid Retrieval** – Combines **cosine similarity (Pinecone)** for semantic depth + **keyword search (Elasticsearch)** for precision.  
- 🗄️ **Text-to-SQL Analytics** – Natural language → **safe SQL queries** for case counts, statutes, yearly trends, and charts.  
- 🤖 **Multi-Model Generation** – **LLaMA3, Nova, Gemini** draft diverse responses.  
- ⚖️ **LLM-as-Judge** – **GPT-4.1-nano** applies RACC (Relevance, Accuracy, Completeness, Clarity) to select or merge the best response.  
- 💻 **User Experience** – A **Streamlit app** showing retrieval context, SQL results, model responses, and the **final judged answer with citations**.

👉 In short: **Hybrid search + SQL analytics + multi-model reasoning + AI judgment** → **trustworthy, explainable, and citation-backed legal insights**.

---

## 🚀 Features

- ✅ Hybrid Retrieval (Semantic + Keyword + SQL)
- ✅ Multi-Model Reasoning (Diverse LLMs for balanced insights)
- ✅ AI Judge for trust & transparency
- ✅ Structured + Unstructured Query Handling
- ✅ Streamlit-based UI for live demonstrations

---

## 📂 Project Structure

```

JurisRAG/
│── data/                # Processed legal documents
│── embeddings.py        # Embedding & Pinecone logic
│── es\_setup.py          # Elasticsearch setup & ingestion
│── text\_to\_sql.py       # Natural language → SQL queries
│── finall.py            # Full pipeline integration
│── app.py               # Streamlit UI
│── jurisrag.db          # SQLite database
│── pca\_model.pkl        # PCA reduction model
│── README.md            # Project overview

````

---

## ▶️ Usage

1. **Clone Repo**
   ```bash
   git clone https://github.com/anto2892004/JurisRAG.git
   cd JurisRAG
````

2. **Setup Environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Mac/Linux
   .venv\Scripts\activate      # Windows
   pip install -r requirements.txt
   ```

3. **Run Full Pipeline**

   ```bash
   python finall.py
   ```

4. **Run Streamlit App**

   ```bash
   streamlit run app.py
   ```


## 🏆 Unique Value (USP)

* **Hybrid Retrieval** – Cosine similarity + Keyword precision + SQL analytics
* **Trust & Transparency** – Citation-backed answers grounded in real data
* **AI Judge** – Ensures only the best response is delivered
* **Time Saver** – Hours of research reduced to minutes

