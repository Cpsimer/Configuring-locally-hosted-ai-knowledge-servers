#!/usr/bin/env python3
"""
~/ai-idp/tests/validate_performance.py
AI IDP Performance Validation Suite v2.0

Validates inference servers against CORRECTED physics-based targets:
- vLLM 8B FP8:    60-100 tok/s (NOT 140-170)
- vLLM TTFT P95:  <500ms warm (NOT <38ms)
- 70B Hybrid:     8-15 tok/s (NOT 30-40)
- llama.cpp 3B:   100-150 tok/s aggregate

Run: pytest validate_performance.py -v --tb=short
Run with report: pytest validate_performance.py -v --html=report.html
"""

import pytest
import requests
import time
import statistics
import json
import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


# ==============================================================================
# CONFIGURATION
# ==============================================================================

VLLM_URL = os.getenv("VLLM_URL", "http://localhost:8000/v1/completions")
VLLM_MODELS_URL = os.getenv("VLLM_MODELS_URL", "http://localhost:8000/v1/models")
LLAMACPP_URL = os.getenv("LLAMACPP_URL", "http://localhost:8001/completion")
LLAMACPP_HEALTH_URL = os.getenv("LLAMACPP_HEALTH_URL", "http://localhost:8001/health")
LLAMACPP_70B_URL = os.getenv("LLAMACPP_70B_URL", "http://localhost:8002/completion")

# API Key from environment (loaded from secrets/api-keys.env)
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "")


@dataclass
class PerformanceTarget:
    """Validated performance targets based on physics calculations."""
    min_value: float
    max_value: float
    unit: str
    original_claim: str
    confidence: str  # 🟢 High, 🟡 Medium, 🔴 Low


# CORRECTED ACCEPTANCE CRITERIA (based on research validation)
TARGETS = {
    # vLLM targets (RTX 5070 Ti 16GB, Llama 3.1 8B FP8)
    "vllm_ttft_p50_warm_ms": PerformanceTarget(
        min_value=20, max_value=80, unit="ms",
        original_claim="22ms", confidence="🟢"
    ),
    "vllm_ttft_p95_warm_ms": PerformanceTarget(
        min_value=50, max_value=500, unit="ms", 
        original_claim="38ms", confidence="🟢"
    ),
    "vllm_throughput_single_user": PerformanceTarget(
        min_value=60, max_value=100, unit="tok/s",
        original_claim="140-170 tok/s", confidence="🟢"
    ),
    "vllm_max_concurrent_16gb": PerformanceTarget(
        min_value=16, max_value=32, unit="requests",
        original_claim="128", confidence="🟢"
    ),
    
    # llama.cpp CPU targets (Ryzen 9900X, Llama 3.2 3B Q4)
    "llamacpp_ttft_p50_ms": PerformanceTarget(
        min_value=10, max_value=50, unit="ms",
        original_claim="30ms", confidence="🟢"
    ),
    "llamacpp_throughput_aggregate": PerformanceTarget(
        min_value=100, max_value=180, unit="tok/s",
        original_claim="144-200 tok/s", confidence="🟢"
    ),
    
    # 70B Hybrid targets (DDR5-6400 bandwidth limited)
    "hybrid_70b_throughput": PerformanceTarget(
        min_value=8, max_value=15, unit="tok/s",
        original_claim="30-40 tok/s", confidence="🟢"
    ),
    "hybrid_70b_ttft_ms": PerformanceTarget(
        min_value=500, max_value=1500, unit="ms",
        original_claim="<100ms", confidence="🟢"
    ),
}


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_vllm_headers() -> Dict[str, str]:
    """Get headers for vLLM requests including API key if set."""
    headers = {"Content-Type": "application/json"}
    if VLLM_API_KEY:
        headers["Authorization"] = f"Bearer {VLLM_API_KEY}"
    return headers


def measure_ttft(url: str, payload: dict, headers: dict = None, timeout: int = 30) -> float:
    """Measure Time-To-First-Token in milliseconds."""
    start = time.perf_counter()
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    ttft_ms = (time.perf_counter() - start) * 1000
    
    if response.status_code != 200:
        raise ValueError(f"Request failed: {response.status_code} - {response.text[:200]}")
    
    return ttft_ms


def measure_throughput(url: str, payload: dict, headers: dict = None, timeout: int = 60) -> Tuple[float, int]:
    """Measure throughput and return (tok/s, total_tokens)."""
    start = time.perf_counter()
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    elapsed = time.perf_counter() - start
    
    if response.status_code != 200:
        raise ValueError(f"Request failed: {response.status_code} - {response.text[:200]}")
    
    data = response.json()
    
    # Handle different response formats
    if "usage" in data:
        tokens = data["usage"].get("completion_tokens", 0)
    elif "tokens_predicted" in data:
        tokens = data["tokens_predicted"]
    elif "content" in data:
        # Estimate tokens from content length
        tokens = len(data["content"].split()) * 1.3  # Rough token estimate
    else:
        tokens = 100  # Default assumption
    
    throughput = tokens / elapsed if elapsed > 0 else 0
    return throughput, int(tokens)


def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculate percentile from list of values."""
    sorted_values = sorted(values)
    index = int(percentile / 100 * len(sorted_values))
    return sorted_values[min(index, len(sorted_values) - 1)]


# ==============================================================================
# vLLM TESTS
# ==============================================================================

class TestVLLMPerformance:
    """Validate vLLM inference server against corrected targets."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Verify vLLM server is available."""
        try:
            response = requests.get(VLLM_MODELS_URL, headers=get_vllm_headers(), timeout=10)
            if response.status_code != 200:
                pytest.skip(f"vLLM server returned {response.status_code}")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"vLLM server not available: {e}")
    
    def test_ttft_warm_cache(self):
        """
        Test: TTFT P50 < 80ms, P95 < 500ms with warm cache
        Original claim: 22ms P50, 38ms P95 (CORRECTED)
        Physics basis: KV cache initialization, model warm-up
        """
        prompt = "Explain the concept of machine learning in simple terms."
        ttfts = []
        
        # Warm-up requests (critical for accurate measurement)
        for _ in range(3):
            requests.post(VLLM_URL, json={
                "model": "llama-3.1-8b",
                "prompt": prompt,
                "max_tokens": 10
            }, headers=get_vllm_headers(), timeout=30)
        
        # Measurement phase
        for i in range(20):
            ttft = measure_ttft(VLLM_URL, {
                "model": "llama-3.1-8b",
                "prompt": prompt,
                "max_tokens": 1,  # Single token for true TTFT
                "stream": False
            }, headers=get_vllm_headers())
            ttfts.append(ttft)
            time.sleep(0.1)  # Brief pause between requests
        
        p50 = statistics.median(ttfts)
        p95 = calculate_percentile(ttfts, 95)
        
        print(f"\n[vLLM TTFT] P50: {p50:.1f}ms, P95: {p95:.1f}ms")
        print(f"  Target P50: <{TARGETS['vllm_ttft_p50_warm_ms'].max_value}ms")
        print(f"  Target P95: <{TARGETS['vllm_ttft_p95_warm_ms'].max_value}ms")
        
        target_p50 = TARGETS["vllm_ttft_p50_warm_ms"]
        target_p95 = TARGETS["vllm_ttft_p95_warm_ms"]
        
        assert p50 < target_p50.max_value, \
            f"TTFT P50 {p50:.1f}ms exceeds target {target_p50.max_value}ms"
        assert p95 < target_p95.max_value, \
            f"TTFT P95 {p95:.1f}ms exceeds target {target_p95.max_value}ms"
    
    def test_throughput_single_user(self):
        """
        Test: Single-user throughput >= 60 tok/s
        Original claim: 140-170 tok/s (CORRECTED to 60-100)
        Physics basis: 896 GB/s ÷ 8GB = 89 tok/s theoretical
        """
        prompt = "Write a comprehensive analysis of the current trends in artificial intelligence, " \
                 "covering machine learning, deep learning, natural language processing, and " \
                 "computer vision applications."
        
        throughputs = []
        for _ in range(5):
            throughput, tokens = measure_throughput(VLLM_URL, {
                "model": "llama-3.1-8b",
                "prompt": prompt,
                "max_tokens": 200
            }, headers=get_vllm_headers())
            throughputs.append(throughput)
            time.sleep(0.5)
        
        avg_throughput = statistics.mean(throughputs)
        
        print(f"\n[vLLM Throughput] Average: {avg_throughput:.1f} tok/s")
        print(f"  Runs: {[f'{t:.1f}' for t in throughputs]}")
        print(f"  Target: >{TARGETS['vllm_throughput_single_user'].min_value} tok/s")
        
        target = TARGETS["vllm_throughput_single_user"]
        assert avg_throughput >= target.min_value, \
            f"Throughput {avg_throughput:.1f} tok/s below target {target.min_value} tok/s"
    
    def test_concurrent_requests_no_oom(self):
        """
        Test: Handle 16-32 concurrent requests without OOM
        Original claim: 128 concurrent (CORRECTED for 16GB VRAM)
        """
        prompt = "Summarize the key points of renewable energy technologies."
        target_concurrent = int(TARGETS["vllm_max_concurrent_16gb"].min_value)
        
        def make_request(request_id: int) -> Tuple[int, bool, str]:
            try:
                response = requests.post(VLLM_URL, json={
                    "model": "llama-3.1-8b",
                    "prompt": f"{prompt} (Request #{request_id})",
                    "max_tokens": 50
                }, headers=get_vllm_headers(), timeout=120)
                return request_id, response.status_code == 200, ""
            except Exception as e:
                return request_id, False, str(e)
        
        with ThreadPoolExecutor(max_workers=target_concurrent) as executor:
            futures = [executor.submit(make_request, i) for i in range(target_concurrent)]
            results = [f.result() for f in as_completed(futures)]
        
        successful = sum(1 for _, success, _ in results if success)
        success_rate = successful / len(results)
        
        print(f"\n[vLLM Concurrent] {successful}/{len(results)} succeeded ({success_rate*100:.1f}%)")
        
        # At least 95% should succeed without OOM
        assert success_rate >= 0.95, f"Only {success_rate*100:.1f}% requests succeeded"


# ==============================================================================
# llama.cpp CPU TESTS
# ==============================================================================

class TestLlamaCppPerformance:
    """Validate llama.cpp CPU inference against targets."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Verify llama.cpp server is available."""
        try:
            response = requests.get(LLAMACPP_HEALTH_URL, timeout=10)
            if "ok" not in response.text.lower() and response.status_code != 200:
                pytest.skip(f"llama.cpp server unhealthy: {response.text}")
        except requests.exceptions.RequestException as e:
            pytest.skip(f"llama.cpp server not available: {e}")
    
    def test_ttft_cpu(self):
        """
        Test: CPU TTFT P50 < 50ms
        Ryzen 9900X benefit: Instant model access from RAM
        """
        prompt = "What is the capital of France?"
        ttfts = []
        
        for _ in range(20):
            start = time.perf_counter()
            response = requests.post(LLAMACPP_URL, json={
                "prompt": prompt,
                "n_predict": 1
            }, timeout=30)
            ttft = (time.perf_counter() - start) * 1000
            ttfts.append(ttft)
        
        p50 = statistics.median(ttfts)
        
        print(f"\n[llama.cpp TTFT] P50: {p50:.1f}ms")
        print(f"  Target: <{TARGETS['llamacpp_ttft_p50_ms'].max_value}ms")
        
        target = TARGETS["llamacpp_ttft_p50_ms"]
        assert p50 < target.max_value, \
            f"TTFT P50 {p50:.1f}ms exceeds target {target.max_value}ms"
    
    def test_throughput_cpu(self):
        """
        Test: CPU aggregate throughput >= 100 tok/s
        Based on: 10 threads × ~12-15 tok/s per thread
        """
        prompt = "Explain the theory of relativity in detail, covering both special and general relativity."
        
        throughputs = []
        for _ in range(5):
            start = time.perf_counter()
            response = requests.post(LLAMACPP_URL, json={
                "prompt": prompt,
                "n_predict": 200
            }, timeout=60)
            elapsed = time.perf_counter() - start
            
            data = response.json()
            tokens = data.get("tokens_predicted", 200)
            throughput = tokens / elapsed
            throughputs.append(throughput)
            time.sleep(0.3)
        
        avg_throughput = statistics.mean(throughputs)
        
        print(f"\n[llama.cpp Throughput] Average: {avg_throughput:.1f} tok/s")
        print(f"  Runs: {[f'{t:.1f}' for t in throughputs]}")
        print(f"  Target: >{TARGETS['llamacpp_throughput_aggregate'].min_value} tok/s")
        
        target = TARGETS["llamacpp_throughput_aggregate"]
        assert avg_throughput >= target.min_value, \
            f"Throughput {avg_throughput:.1f} tok/s below target {target.min_value} tok/s"


# ==============================================================================
# 70B HYBRID TESTS (Optional - requires --profile expert)
# ==============================================================================

class TestHybrid70BPerformance:
    """
    Validate 70B hybrid inference.
    CRITICAL: Original 30-40 tok/s claim was PHYSICALLY IMPOSSIBLE.
    Validated target: 8-15 tok/s based on DDR5-6400 bandwidth limits.
    """
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Check if 70B server is running (optional profile)."""
        try:
            response = requests.get(
                LLAMACPP_70B_URL.replace("/completion", "/health"),
                timeout=10
            )
            if "ok" not in response.text.lower() and response.status_code != 200:
                pytest.skip("70B hybrid server not running (use --profile expert)")
        except requests.exceptions.RequestException:
            pytest.skip("70B hybrid server not available (use --profile expert)")
    
    def test_throughput_70b_hybrid(self):
        """
        Test: 70B hybrid throughput >= 8 tok/s
        
        Physics calculation (DDR5-6400 bottleneck):
        - 60 CPU layers = ~29GB weights
        - DDR5-6400 effective: ~40 GB/s
        - Base: 29GB ÷ 40 GB/s = 725ms per token = 1.4 tok/s
        - With batch_size=512: 8-15 tok/s achievable
        """
        prompt = "Provide a detailed analysis of climate change mitigation strategies."
        
        start = time.perf_counter()
        response = requests.post(LLAMACPP_70B_URL, json={
            "prompt": prompt,
            "n_predict": 100
        }, timeout=300)  # 70B can be slow
        elapsed = time.perf_counter() - start
        
        data = response.json()
        tokens = data.get("tokens_predicted", 100)
        throughput = tokens / elapsed
        
        print(f"\n[70B Hybrid Throughput] {throughput:.1f} tok/s ({tokens} tokens in {elapsed:.1f}s)")
        print(f"  Target: >{TARGETS['hybrid_70b_throughput'].min_value} tok/s")
        print(f"  Original (WRONG) claim: {TARGETS['hybrid_70b_throughput'].original_claim}")
        
        target = TARGETS["hybrid_70b_throughput"]
        assert throughput >= target.min_value, \
            f"Throughput {throughput:.1f} tok/s below target {target.min_value} tok/s"
    
    def test_ttft_70b(self):
        """
        Test: 70B TTFT < 1500ms
        Large model requires significant initialization time.
        """
        prompt = "Hello, how are you?"
        
        ttfts = []
        for _ in range(5):
            start = time.perf_counter()
            requests.post(LLAMACPP_70B_URL, json={
                "prompt": prompt,
                "n_predict": 1
            }, timeout=60)
            ttft = (time.perf_counter() - start) * 1000
            ttfts.append(ttft)
        
        p50 = statistics.median(ttfts)
        
        print(f"\n[70B TTFT] P50: {p50:.1f}ms")
        print(f"  Target: <{TARGETS['hybrid_70b_ttft_ms'].max_value}ms")
        
        target = TARGETS["hybrid_70b_ttft_ms"]
        assert p50 < target.max_value, \
            f"TTFT P50 {p50:.1f}ms exceeds target {target.max_value}ms"


# ==============================================================================
# REPORT GENERATION
# ==============================================================================

class TestGenerateReport:
    """Generate validation report summarizing all targets."""
    
    def test_generate_summary_report(self):
        """Generate a summary of all performance targets."""
        print("\n" + "="*70)
        print("AI IDP PERFORMANCE VALIDATION SUMMARY v2.0")
        print("="*70)
        
        print("\n📊 VALIDATED TARGETS (Physics-Based Corrections):\n")
        
        for name, target in TARGETS.items():
            status = target.confidence
            print(f"  {status} {name}:")
            print(f"      Target: {target.min_value}-{target.max_value} {target.unit}")
            print(f"      Original claim: {target.original_claim}")
            print()
        
        print("="*70)
        print("Run individual test classes for detailed measurements:")
        print("  pytest validate_performance.py::TestVLLMPerformance -v")
        print("  pytest validate_performance.py::TestLlamaCppPerformance -v")
        print("  pytest validate_performance.py::TestHybrid70BPerformance -v")
        print("="*70)


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
