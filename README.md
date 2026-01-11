# Decision Arena (Groq + Gradio)

An agentic AI application that helps you make high-quality decisions using a "Builder vs. Challenger" debate system, adjudicated by a Judge.

**Experiment by:** Rishikesh R Pote  
**Powered by:** Google Antigravity & Jules

---

## 🚀 Features

This app orchestrates **3 AI Agents** (powered by Groq's high-speed inference) to analyze your goals:

1.  **🟢 Builder Agent:** Proposes the strongest possible plan and path to success.
2.  **🔴 Challenger Agent:** ruthlessly critiques the plan, identifying risks, failure modes, and missing constraints.
3.  **🟣 Judge Agent:** Synthesizes both viewpoints to provide a final verdict, including a 7-day action plan, success metrics, and guardrails.

## 🛠️ Tech Stack
-   **Engine:** Groq API (`llama-3.3-70b-versatile`)
-   **UI:** Gradio
-   **Code:** Python

## 📦 Setup & Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/RishieRich/Google_Antigravity_Jules_101.git
    cd Google_Antigravity_Jules_101
    ```

2.  **Install dependencies:**
    ```bash
    # Recommended: create a virtual env
    python -m venv .venv
    .\.venv\Scripts\activate  # Windows
    # source .venv/bin/activate # Mac/Linux

    pip install -r requirements.txt
    ```

3.  **Configure API Key:**
    Create a file named `.env` in the root directory:
    ```env
    GROQ_API_KEY="your_gsk_key_here"
    ```

## ▶️ Usage

Run the application:
```bash
python app.py
```
Open your browser to `http://127.0.0.1:7860`.

1.  **Enter your goal** (e.g., "Launch a SaaS in 30 days").
2.  Select **Risk Preference** and **Depth**.
3.  Click **Run Decision Arena**.
