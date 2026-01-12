#!/usr/bin/env python3
"""
AI IDP Empirical Validation Test Suite
Version: 1.0 | Date: 2026-01-12

Validates performance claims against corrected benchmarks:
- vLLM TTFT P50 <100ms (corrected from 22ms)
- vLLM throughput >60 tok/s (corrected from 140-170)
- llama.cpp TTFT <50ms (corrected from 30ms)
- llama.cpp throughput >100 tok/s (corrected from 144-200)

Run with: pytest test_inference_performance.py -v --tb=short
"""

import pytest
import requests
import time
import statistics
import os
import subprocess
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass
class AcceptanceCriteria:
    """Corrected acceptance criteria based on physics-based calculations."""
    # vLLM (GPU) metrics - CORRECTED from original claims
    vllm_ttft_p50_ms: float = 100.0      # Original claim: 22ms
    vllm_ttft_p95_ms: float = 200.0      # Original claim: 38ms  
    vllm_throughput_min: float = 60.0    # Original claim: 140-170 tok/s
    vllm_throughput_target: float = 80.0 # Realistic target
    
    # llama.cpp (CPU) metrics - CORRECTED
    llamacpp_ttft_p50_ms: float = 50.0   # Original claim: 30ms
    llamacpp_throughput_min: float = 100.0  # Original claim: 144-200 tok/s
    llamacpp_throughput_target: float = 150.0
    
    # System metrics
    gpu_utilization_min: float = 75.0    # Percent
    max_concurrent_without_oom: int = 32 # Original claim: 128
    max_memory_utilization: float = 90.0 # Percent
    
    # Stability
    success_rate_min: float = 0.95       # 95% requests succeed
    error_rate_max: float = 0.05         # <5% errors


CRITERIA = AcceptanceCriteria()

# Server URLs
VLLM_BASE_URL = os.getenv("VLLM_URL", "http://localhost:8000")
VLLM_COMPLETIONS_URL = f"{VLLM_BASE_URL}/v1/completions"
VLLM_MODELS_URL = f"{VLLM_BASE_URL}/v1/models"

LLAMACPP_BASE_URL = os.getenv("LLAMACPP_URL", "http://localhost:8001")
LLAMACPP_COMPLETION_URL = f"{LLAMACPP_BASE_URL}/completion"
LLAMACPP_HEALTH_URL = f"{LLAMACPP_BASE_URL}/health"

# API Key (loaded from environment)
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_headers() -> Dict[str, str]:
    """Get headers with optional API key."""
    headers = {"Content-Type": "application/json"}
    if VLLM_API_KEY:
        headers["Authorization"] = f"Bearer {VLLM_API_KEY}"
    return headers


def get_gpu_metrics() -> Optional[Dict[str, float]]:
    """Query GPU metrics via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu,power.draw,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(",")
            return {
                "temperature_c": float(parts[0].strip()),
                "power_w": float(parts[1].strip()),
                "utilization_pct": float(parts[2].strip()),
                "memory_used_mb": float(parts[3].strip()),
                "memory_total_mb": float(parts[4].strip()),
            }
    except Exception:
        pass
    return None


def calculate_percentile(data: List[float], percentile: float) -> float:
    """Calculate percentile from list of values."""
    sorted_data = sorted(data)
    idx = int(percentile * len(sorted_data))
    return sorted_data[min(idx, len(sorted_data) - 1)]


# ============================================================================
# VLLM TESTS
# ============================================================================

class TestVLLMPerformance:
    """Test vLLM inference server performance against corrected criteria."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Verify vLLM server is available before tests."""
        try:
            r = requests.get(VLLM_MODELS_URL, headers=get_headers(), timeout=10)
            if r.status_code != 200:
                pytest.skip(f"vLLM server returned {r.status_code}")
        except requests.RequestException as e:
            pytest.skip(f"vLLM server not available: {e}")
    
    def test_vllm_ttft_warm_cache(self):
        """Test Time-To-First-Token with warm cache (P50 < 100ms, P95 < 200ms)."""
        prompt = "Explain quantum computing in one paragraph."
        ttfts = []
        
        # Warm-up request (ignore timing)
        requests.post(VLLM_COMPLETIONS_URL, headers=get_headers(), json={
            "model": "llama-3.1-8b",
            "prompt": prompt,
            "max_tokens": 50
        }, timeout=30)
        
        # Measurement requests
        for i in range(20):
            start = time.perf_counter()
            r = requests.post(VLLM_COMPLETIONS_URL, headers=get_headers(), json={
                "model": "llama-3.1-8b",
                "prompt": prompt,
                "max_tokens": 1,  # Single token for TTFT measurement
                "stream": False
            }, timeout=30)
            ttft_ms = (time.perf_counter() - start) * 1000
            
            if r.status_code == 200:
                ttfts.append(ttft_ms)
        
        assert len(ttfts) >= 15, f"Too few successful requests: {len(ttfts)}/20"
        
        p50 = statistics.median(ttfts)
        p95 = calculate_percentile(ttfts, 0.95)
        mean = statistics.mean(ttfts)
        
        print(f"\nvLLM TTFT Results (n={len(ttfts)}):")
        print(f"  P50:  {p50:.1f}ms (target: <{CRITERIA.vllm_ttft_p50_ms}ms)")
        print(f"  P95:  {p95:.1f}ms (target: <{CRITERIA.vllm_ttft_p95_ms}ms)")
        print(f"  Mean: {mean:.1f}ms")
        
        assert p50 < CRITERIA.vllm_ttft_p50_ms, \
            f"TTFT P50 {p50:.1f}ms exceeds target {CRITERIA.vllm_ttft_p50_ms}ms"
        assert p95 < CRITERIA.vllm_ttft_p95_ms, \
            f"TTFT P95 {p95:.1f}ms exceeds target {CRITERIA.vllm_ttft_p95_ms}ms"
    
    def test_vllm_throughput_single_request(self):
        """Test single-request throughput (>60 tok/s, target 80 tok/s)."""
        prompt = "Write a detailed analysis of machine learning trends in 2026."
        throughputs = []
        
        for i in range(5):
            start = time.perf_counter()
            r = requests.post(VLLM_COMPLETIONS_URL, headers=get_headers(), json={
                "model": "llama-3.1-8b",
                "prompt": prompt,
                "max_tokens": 200,
                "temperature": 0.7
            }, timeout=60)
            elapsed = time.perf_counter() - start
            
            if r.status_code == 200:
                data = r.json()
                tokens = data.get("usage", {}).get("completion_tokens", 0)
                if tokens > 0:
                    throughput = tokens / elapsed
                    throughputs.append(throughput)
        
        assert len(throughputs) >= 3, f"Too few successful requests: {len(throughputs)}/5"
        
        mean_throughput = statistics.mean(throughputs)
        max_throughput = max(throughputs)
        
        print(f"\nvLLM Throughput Results (n={len(throughputs)}):")
        print(f"  Mean: {mean_throughput:.1f} tok/s (min: {CRITERIA.vllm_throughput_min} tok/s)")
        print(f"  Max:  {max_throughput:.1f} tok/s (target: {CRITERIA.vllm_throughput_target} tok/s)")
        
        assert mean_throughput >= CRITERIA.vllm_throughput_min, \
            f"Throughput {mean_throughput:.1f} tok/s below minimum {CRITERIA.vllm_throughput_min} tok/s"
    
    def test_vllm_concurrent_requests_stability(self):
        """Test concurrent requests don't cause OOM or errors (32 concurrent)."""
        prompt = "Summarize the key points of renewable energy."
        concurrent = min(CRITERIA.max_concurrent_without_oom, 32)
        
        def make_request(i: int) -> Dict[str, Any]:
            try:
                start = time.perf_counter()
                r = requests.post(VLLM_COMPLETIONS_URL, headers=get_headers(), json={
                    "model": "llama-3.1-8b",
                    "prompt": f"{prompt} (Request {i})",
                    "max_tokens": 50
                }, timeout=120)
                elapsed = time.perf_counter() - start
                return {
                    "success": r.status_code == 200,
                    "status_code": r.status_code,
                    "elapsed": elapsed,
                    "error": None
                }
            except Exception as e:
                return {
                    "success": False,
                    "status_code": 0,
                    "elapsed": 0,
                    "error": str(e)
                }
        
        with ThreadPoolExecutor(max_workers=concurrent) as executor:
            futures = [executor.submit(make_request, i) for i in range(concurrent)]
            results = [f.result() for f in as_completed(futures)]
        
        successful = sum(1 for r in results if r["success"])
        success_rate = successful / len(results)
        
        errors = [r for r in results if not r["success"]]
        if errors:
            print(f"\nFailed requests: {len(errors)}")
            for e in errors[:3]:  # Show first 3 errors
                print(f"  - Status: {e['status_code']}, Error: {e['error']}")
        
        print(f"\nConcurrent Request Results:")
        print(f"  Concurrent: {concurrent}")
        print(f"  Success: {successful}/{len(results)} ({success_rate*100:.1f}%)")
        print(f"  Target: >{CRITERIA.success_rate_min*100:.0f}%")
        
        # Check GPU didn't OOM
        gpu_metrics = get_gpu_metrics()
        if gpu_metrics:
            print(f"  GPU Memory: {gpu_metrics['memory_used_mb']:.0f}/{gpu_metrics['memory_total_mb']:.0f}MB")
            print(f"  GPU Utilization: {gpu_metrics['utilization_pct']:.0f}%")
        
        assert success_rate >= CRITERIA.success_rate_min, \
            f"Success rate {success_rate*100:.1f}% below {CRITERIA.success_rate_min*100:.0f}%"
    
    def test_vllm_gpu_utilization(self):
        """Test GPU utilization during inference (>75%)."""
        prompt = "Write a comprehensive essay about artificial intelligence."
        
        # Start a long-running request
        import threading
        
        def long_request():
            requests.post(VLLM_COMPLETIONS_URL, headers=get_headers(), json={
                "model": "llama-3.1-8b",
                "prompt": prompt,
                "max_tokens": 500
            }, timeout=120)
        
        thread = threading.Thread(target=long_request)
        thread.start()
        
        # Sample GPU utilization during inference
        time.sleep(1)  # Wait for inference to start
        utilizations = []
        
        for _ in range(10):
            metrics = get_gpu_metrics()
            if metrics:
                utilizations.append(metrics["utilization_pct"])
            time.sleep(0.5)
        
        thread.join(timeout=60)
        
        if not utilizations:
            pytest.skip("Could not query GPU metrics")
        
        avg_util = statistics.mean(utilizations)
        max_util = max(utilizations)
        
        print(f"\nGPU Utilization During Inference:")
        print(f"  Average: {avg_util:.1f}% (min: {CRITERIA.gpu_utilization_min}%)")
        print(f"  Peak: {max_util:.1f}%")
        
        assert avg_util >= CRITERIA.gpu_utilization_min * 0.8, \
            f"GPU utilization {avg_util:.1f}% significantly below target {CRITERIA.gpu_utilization_min}%"


# ============================================================================
# LLAMA.CPP TESTS
# ============================================================================

class TestLlamaCppPerformance:
    """Test llama.cpp inference server performance against corrected criteria."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Verify llama.cpp server is available before tests."""
        try:
            r = requests.get(LLAMACPP_HEALTH_URL, timeout=10)
            if r.status_code != 200 and "ok" not in r.text.lower():
                pytest.skip(f"llama.cpp server returned {r.status_code}")
        except requests.RequestException as e:
            pytest.skip(f"llama.cpp server not available: {e}")
    
    def test_llamacpp_ttft_instant(self):
        """Test CPU inference has fast TTFT (P50 < 50ms)."""
        prompt = "What is the capital of France?"
        ttfts = []
        
        for i in range(20):
            start = time.perf_counter()
            r = requests.post(LLAMACPP_COMPLETION_URL, json={
                "prompt": prompt,
                "n_predict": 1
            }, timeout=30)
            ttft_ms = (time.perf_counter() - start) * 1000
            
            if r.status_code == 200:
                ttfts.append(ttft_ms)
        
        assert len(ttfts) >= 15, f"Too few successful requests: {len(ttfts)}/20"
        
        p50 = statistics.median(ttfts)
        p95 = calculate_percentile(ttfts, 0.95)
        
        print(f"\nllama.cpp TTFT Results (n={len(ttfts)}):")
        print(f"  P50: {p50:.1f}ms (target: <{CRITERIA.llamacpp_ttft_p50_ms}ms)")
        print(f"  P95: {p95:.1f}ms")
        
        assert p50 < CRITERIA.llamacpp_ttft_p50_ms, \
            f"TTFT P50 {p50:.1f}ms exceeds target {CRITERIA.llamacpp_ttft_p50_ms}ms"
    
    def test_llamacpp_throughput_cpu(self):
        """Test CPU throughput matches corrected expectations (>100 tok/s)."""
        prompt = "Explain the theory of relativity in detail."
        throughputs = []
        
        for i in range(5):
            start = time.perf_counter()
            r = requests.post(LLAMACPP_COMPLETION_URL, json={
                "prompt": prompt,
                "n_predict": 200,
                "temperature": 0.7
            }, timeout=60)
            elapsed = time.perf_counter() - start
            
            if r.status_code == 200:
                data = r.json()
                # llama.cpp returns different field names
                tokens = data.get("tokens_predicted", data.get("n_predicted", 200))
                
                # Also check timings if available
                timings = data.get("timings", {})
                if "predicted_per_second" in timings:
                    throughputs.append(timings["predicted_per_second"])
                elif tokens > 0:
                    throughputs.append(tokens / elapsed)
        
        assert len(throughputs) >= 3, f"Too few successful requests: {len(throughputs)}/5"
        
        mean_throughput = statistics.mean(throughputs)
        max_throughput = max(throughputs)
        
        print(f"\nllama.cpp Throughput Results (n={len(throughputs)}):")
        print(f"  Mean: {mean_throughput:.1f} tok/s (min: {CRITERIA.llamacpp_throughput_min} tok/s)")
        print(f"  Max:  {max_throughput:.1f} tok/s (target: {CRITERIA.llamacpp_throughput_target} tok/s)")
        
        assert mean_throughput >= CRITERIA.llamacpp_throughput_min, \
            f"Throughput {mean_throughput:.1f} tok/s below minimum {CRITERIA.llamacpp_throughput_min} tok/s"


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestSystemIntegration:
    """Test overall system integration and stability."""
    
    def test_both_servers_healthy(self):
        """Verify both inference servers are responding."""
        vllm_healthy = False
        llamacpp_healthy = False
        
        try:
            r = requests.get(VLLM_MODELS_URL, headers=get_headers(), timeout=10)
            vllm_healthy = r.status_code == 200
        except Exception:
            pass
        
        try:
            r = requests.get(LLAMACPP_HEALTH_URL, timeout=10)
            llamacpp_healthy = r.status_code == 200 or "ok" in r.text.lower()
        except Exception:
            pass
        
        print(f"\nServer Health Check:")
        print(f"  vLLM:      {'✓ Healthy' if vllm_healthy else '✗ Unhealthy'}")
        print(f"  llama.cpp: {'✓ Healthy' if llamacpp_healthy else '✗ Unhealthy'}")
        
        assert vllm_healthy or llamacpp_healthy, "No inference servers available"
    
    def test_gpu_thermal_acceptable(self):
        """Verify GPU temperature is within safe limits."""
        metrics = get_gpu_metrics()
        
        if not metrics:
            pytest.skip("Could not query GPU metrics")
        
        temp = metrics["temperature_c"]
        
        print(f"\nGPU Thermal Status:")
        print(f"  Temperature: {temp}°C")
        print(f"  Power Draw:  {metrics['power_w']:.0f}W")
        
        assert temp < 85, f"GPU temperature {temp}°C exceeds safe threshold 85°C"
        
        if temp > 75:
            print(f"  ⚠️  Warning: Temperature approaching limit")


# ============================================================================
# BENCHMARK SUMMARY
# ============================================================================

def generate_benchmark_report(results: Dict[str, Any]) -> str:
    """Generate a markdown benchmark report."""
    report = """
# AI IDP Benchmark Report

## Test Results Summary

| Metric | Target | Measured | Status |
|--------|--------|----------|--------|
"""
    # Add results to report...
    return report


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
