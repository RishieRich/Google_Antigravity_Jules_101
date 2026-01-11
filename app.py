import os
import time
from typing import List, Dict, Tuple, Optional

import gradio as gr
from dotenv import load_dotenv
from groq import Groq

load_dotenv()  # allows GROQ_API_KEY from a local .env too (optional)

DEFAULT_MODEL = "llama-3.3-70b-versatile"  # recommended production model on Groq :contentReference[oaicite:1]{index=1}
FALLBACK_MODELS = [
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
]

SYSTEM_RULES = """You are a high-signal decision assistant.
Be concrete, pragmatic, and action-oriented.
Avoid generic motivation. Avoid fluff.
If info is missing, state assumptions explicitly.
Format output in Markdown with clear headings and bullets.
"""

_GROQ_CLIENT: Optional[Groq] = None

def _client() -> Groq:
    """
    Returns a singleton instance of the Groq client.
    Raises RuntimeError if GROQ_API_KEY is not set.
    """
    global _GROQ_CLIENT
    if _GROQ_CLIENT is None:
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("Missing GROQ_API_KEY. Set it as an environment variable and restart the app.")
        _GROQ_CLIENT = Groq(api_key=api_key)
    return _GROQ_CLIENT

def call_groq(messages: List[Dict], model: str, temperature: float = 0.4, max_tokens: int = 900) -> str:
    """
    Calls the Groq API with the specified parameters.
    """
    client = _client()
    # Chat Completions API via Groq SDK :contentReference[oaicite:2]{index=2}
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return resp.choices[0].message.content

def robust_chat(messages: List[Dict], temperature: float = 0.4, max_tokens: int = 900) -> Tuple[str, str, float]:
    """
    Attempts to get a response from Groq, falling back to other models on failure.
    Returns: (response_text, model_used, latency_seconds)
    """
    start = time.time()
    # try default model first, then fallbacks
    models_to_try = [DEFAULT_MODEL] + [m for m in FALLBACK_MODELS if m != DEFAULT_MODEL]
    last_err = None
    for m in models_to_try:
        try:
            text = call_groq(messages, model=m, temperature=temperature, max_tokens=max_tokens)
            return text, m, (time.time() - start)
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All model attempts failed. Last error: {last_err}")

def run_decision_arena(problem: str, risk_mode: str, depth: int) -> Tuple[str, str]:
    """
    Main orchestration function for the Decision Arena.
    Runs Builder, Challenger, and Judge agents.
    """
    problem = (problem or "").strip()
    if not problem:
        return "Please enter a decision/goal to analyze.", ""

    # simple knob mapping
    if risk_mode == "Low risk":
        temp = 0.2
    elif risk_mode == "Balanced":
        temp = 0.35
    else:
        temp = 0.55

    # depth controls verbosity (roughly)
    max_tokens = 650 + (depth * 150)

    def agent(role_name: str, role_prompt: str) -> Tuple[str, str, float]:
        messages = [
            {"role": "system", "content": SYSTEM_RULES},
            {"role": "system", "content": f"You are Agent: {role_name}.\n{role_prompt}"},
            {"role": "user", "content": f"Decision/Goal:\n{problem}\n\nRisk preference: {risk_mode}\nDepth: {depth}/5"},
        ]
        start = time.time()
        # Pass max_tokens to robust_chat
        text, used_model, latency = robust_chat(messages, temperature=temp, max_tokens=max_tokens)
        # trim if needed (avoid insane outputs)
        return text.strip(), used_model, (time.time() - start)

    builder_prompt = """Create the strongest possible plan and recommendation.
- Explain why this path could win.
- Provide a simple step-by-step approach.
- Include assumptions and what must be true for success.
"""

    challenger_prompt = """Attack the plan like a critical reviewer.
- Identify risks, hidden constraints, and failure modes.
- List what is missing/uncertain.
- Provide mitigations and "stop doing" advice.
"""

    judge_prompt = """Synthesize Builder + Challenger and decide.
Output MUST include:
1) Final recommendation (1–2 lines)
2) Key assumptions (bullets)
3) 7-day action plan (day-wise bullets)
4) Metrics to track (3–6 metrics)
5) If-then guardrails (e.g., 'If X by Day 3 not true, then do Y')
"""

    b_text, model_b, _ = agent("Builder", builder_prompt)
    c_text, model_c, _ = agent("Challenger", challenger_prompt)

    judge_messages = [
        {"role": "system", "content": SYSTEM_RULES},
        {"role": "system", "content": "You are Agent: Judge.\n" + judge_prompt},
        {"role": "user", "content": f"Decision/Goal:\n{problem}\n\nRisk preference: {risk_mode}\nDepth: {depth}/5"},
        {"role": "user", "content": f"Builder Output:\n{b_text}"},
        {"role": "user", "content": f"Challenger Output:\n{c_text}"},
    ]

    start = time.time()
    # Pass max_tokens to robust_chat for the Judge as well
    judge_text, model_j, judge_latency = robust_chat(judge_messages, temperature=temp, max_tokens=max_tokens)
    used_models = f"Models used: Builder={model_b}, Challenger={model_c}, Judge={model_j} | Judge latency={judge_latency:.2f}s"

    final_md = f"""# 🧠 Decision Arena

## 🟢 Builder
{b_text}

---

## 🔴 Challenger
{c_text}

---

## 🟣 Judge (Final)
{judge_text.strip()}
"""
    return final_md, used_models


with gr.Blocks(title="Decision Arena (Groq + 3 Agents)") as demo:
    gr.Markdown(
        "# ⚡ Decision Arena (Groq)\n"
        "A fast 3-agent decision engine: **Builder → Challenger → Judge**.\n\n"
        "**Only requirement:** set `GROQ_API_KEY` and run."
    )

    with gr.Row():
        problem = gr.Textbox(
            label="Your decision / goal",
            placeholder="Example: I want to launch a GenAI product in 30 days. What should I build and how?",
            lines=5,
        )

    with gr.Row():
        risk_mode = gr.Radio(
            ["Low risk", "Balanced", "High conviction"],
            value="Balanced",
            label="Risk preference",
        )
        depth = gr.Slider(1, 5, value=3, step=1, label="Depth (1=short, 5=deep)")

    run_btn = gr.Button("Run Decision Arena")
    output = gr.Markdown()
    meta = gr.Textbox(label="Run info", interactive=False)

    run_btn.click(
        fn=run_decision_arena,
        inputs=[problem, risk_mode, depth],
        outputs=[output, meta],
    )

if __name__ == "__main__":
    share = os.getenv("SHARE", "false").lower() == "true"
    demo.launch(server_name="0.0.0.0", share=share)
