#!/usr/bin/env python3
"""
~/ai-idp/scripts/cloud_fallback.py
Cloud Fallback & A/B Testing Script
Integrates Azure Education Hub and Google AI Pro credits.
"""

import os
import sys
import json
import requests
from typing import Optional, Dict, Any

# Configuration
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

LOCAL_VLLM = "http://localhost:8000/v1/completions"

def call_local(prompt: str) -> Optional[str]:
    """Try local vLLM first."""
    try:
        resp = requests.post(LOCAL_VLLM, json={
            "model": "llama-3.1-8b",
            "prompt": prompt,
            "max_tokens": 100
        }, timeout=5)
        if resp.status_code == 200:
            return f"[LOCAL] {resp.json()['choices'][0]['text']}"
    except Exception as e:
        print(f"Local inference failed: {e}", file=sys.stderr)
    return None

def call_azure(prompt: str) -> Optional[str]:
    """Fallback to Azure OpenAI (Education Hub)."""
    if not AZURE_ENDPOINT or not AZURE_API_KEY:
        return None
        
    try:
        headers = {"api-key": AZURE_API_KEY, "Content-Type": "application/json"}
        # Assuming deployment name 'gpt-4o' or similar setup in Azure AI Foundry
        url = f"{AZURE_ENDPOINT}/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-15-preview"
        
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 100
        }
        
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        if resp.status_code == 200:
            return f"[AZURE] {resp.json()['choices'][0]['message']['content']}"
    except Exception as e:
        print(f"Azure inference failed: {e}", file=sys.stderr)
    return None

def call_google(prompt: str) -> Optional[str]:
    """Fallback to Google Gemini (AI Pro)."""
    if not GOOGLE_API_KEY:
        return None
        
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GOOGLE_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            return f"[GOOGLE] {resp.json()['candidates'][0]['content']['parts'][0]['text']}"
    except Exception as e:
        print(f"Google inference failed: {e}", file=sys.stderr)
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 cloud_fallback.py 'Your prompt here'")
        sys.exit(1)
        
    prompt = sys.argv[1]
    
    # 1. Try Local
    result = call_local(prompt)
    if result:
        print(result)
        sys.exit(0)
        
    print("Local instance unavailable, attempting cloud fallback...", file=sys.stderr)
    
    # 2. Try Azure (Education Credits)
    result = call_azure(prompt)
    if result:
        print(result)
        sys.exit(0)
        
    # 3. Try Google (AI Pro)
    result = call_google(prompt)
    if result:
        print(result)
        sys.exit(0)
        
    print("All inference endpoints failed.", file=sys.stderr)
    sys.exit(1)

if __name__ == "__main__":
    main()
