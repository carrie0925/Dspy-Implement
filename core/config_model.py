"""
Configure DSPy LM backend (OpenAI)
- Works with both User API Key (sk-...) and Project Key (sk-proj-...)
- Sets all env vars that openai/litellm might look at (ORG_ID / ORGANIZATION / PROJECT / API_BASE)
"""

import os
from dotenv import load_dotenv, find_dotenv
import dspy

def configure_lm():
    # load .env from current working directory
    env_path = find_dotenv(usecwd=True) or ".env"
    load_dotenv(env_path, override=True)

    key   = (os.getenv("OPENAI_API_KEY") or "").strip()
    model = (os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip()
    org   = (os.getenv("OPENAI_ORG_ID") or os.getenv("OPENAI_ORGANIZATION") or "").strip()
    proj  = (os.getenv("OPENAI_PROJECT") or "").strip()
    api_base = (os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1").strip()

    if not key:
        raise RuntimeError("Missing OPENAI_API_KEY in .env")

    # Ensure all env vars are present for both openai & litellm code paths
    os.environ["OPENAI_API_KEY"] = key
    os.environ["OPENAI_API_BASE"] = api_base
    if org:
        os.environ["OPENAI_ORG_ID"] = org          # new
        os.environ["OPENAI_ORGANIZATION"] = org    # legacy
    if proj:
        os.environ["OPENAI_PROJECT"] = proj

    kind = "PROJECT" if key.startswith("sk-proj-") else "USER"
    print(f"[INFO] OpenAI key type: {kind}, model={model}, org_set={bool(org)}, project_set={bool(proj)}")

    # Configure DSPy (litellm provider: openai/<model>)
    dspy.configure(lm=dspy.LM(f"openai/{model}"))
    print(f"[INFO] DSPy configured with OpenAI: {model}")
