#!/usr/bin/env python3
"""
Locust Load Testing for AI IDP
Version: 1.0 | Date: 2026-01-12

Run with:
  locust -f locustfile.py --host=http://localhost:8000 --users 10 --spawn-rate 2 --run-time 5m

Web UI: http://localhost:8089
"""

from locust import HttpUser, task, between, events
import json
import time
import os


# Configuration
VLLM_API_KEY = os.getenv("VLLM_API_KEY", "")


class VLLMUser(HttpUser):
    """
    Simulate users hitting vLLM inference server.
    
    Task distribution:
    - 40% short completions (brainstorming)
    - 30% medium completions (analysis)
    - 20% long completions (content generation)
    - 10% health checks
    """
    
    wait_time = between(1, 5)  # 1-5 seconds between requests
    
    def on_start(self):
        """Set up headers on user start."""
        self.headers = {"Content-Type": "application/json"}
        if VLLM_API_KEY:
            self.headers["Authorization"] = f"Bearer {VLLM_API_KEY}"
    
    @task(4)
    def short_completion(self):
        """Short completion - most common use case."""
        self.client.post(
            "/v1/completions",
            headers=self.headers,
            json={
                "model": "llama-3.1-8b",
                "prompt": "Summarize: Machine learning is a subset of artificial intelligence.",
                "max_tokens": 50,
                "temperature": 0.7
            },
            timeout=30,
            name="short_completion"
        )
    
    @task(3)
    def medium_completion(self):
        """Medium completion - analysis tasks."""
        self.client.post(
            "/v1/completions",
            headers=self.headers,
            json={
                "model": "llama-3.1-8b",
                "prompt": "Explain the key differences between supervised and unsupervised learning in machine learning.",
                "max_tokens": 150,
                "temperature": 0.7
            },
            timeout=60,
            name="medium_completion"
        )
    
    @task(2)
    def long_completion(self):
        """Long completion - content generation."""
        self.client.post(
            "/v1/completions",
            headers=self.headers,
            json={
                "model": "llama-3.1-8b",
                "prompt": "Write a detailed technical blog post about containerization with Docker, including best practices and common pitfalls.",
                "max_tokens": 300,
                "temperature": 0.7
            },
            timeout=120,
            name="long_completion"
        )
    
    @task(1)
    def health_check(self):
        """Regular health checks."""
        self.client.get(
            "/v1/models",
            headers=self.headers,
            name="health_check"
        )


class LlamaCppUser(HttpUser):
    """
    Simulate users hitting llama.cpp CPU inference server.
    
    Faster request rate since CPU inference is optimized for quick queries.
    """
    
    wait_time = between(0.5, 2)  # Faster rate for CPU
    host = "http://localhost:8001"  # Override default host
    
    @task(5)
    def quick_completion(self):
        """Quick brainstorming queries."""
        self.client.post(
            "/completion",
            json={
                "prompt": "List 3 innovative ideas for renewable energy storage:",
                "n_predict": 50,
                "temperature": 0.8
            },
            timeout=15,
            name="quick_completion"
        )
    
    @task(3)
    def hypothesis_generation(self):
        """Research hypothesis generation."""
        self.client.post(
            "/completion",
            json={
                "prompt": "Given that climate change affects global crop yields, propose a testable scientific hypothesis:",
                "n_predict": 100,
                "temperature": 0.7
            },
            timeout=30,
            name="hypothesis_generation"
        )
    
    @task(2)
    def code_snippet(self):
        """Quick code generation."""
        self.client.post(
            "/completion",
            json={
                "prompt": "Write a Python function that calculates the Fibonacci sequence:\n```python\n",
                "n_predict": 80,
                "temperature": 0.3
            },
            timeout=20,
            name="code_snippet"
        )
    
    @task(1)
    def health_check(self):
        """Health check."""
        self.client.get("/health", name="health_check")


class MixedWorkloadUser(HttpUser):
    """
    Simulate realistic mixed workload hitting both servers.
    
    This user alternates between GPU (vLLM) for quality
    and CPU (llama.cpp) for speed.
    """
    
    wait_time = between(2, 8)
    
    def on_start(self):
        """Set up configuration."""
        self.vllm_headers = {"Content-Type": "application/json"}
        if VLLM_API_KEY:
            self.vllm_headers["Authorization"] = f"Bearer {VLLM_API_KEY}"
        
        # Alternate between servers
        self.llamacpp_url = "http://localhost:8001"
    
    @task(3)
    def research_query_gpu(self):
        """Quality research query on GPU."""
        self.client.post(
            "/v1/completions",
            headers=self.vllm_headers,
            json={
                "model": "llama-3.1-8b",
                "prompt": "Analyze the implications of quantum computing for cryptography:",
                "max_tokens": 200,
                "temperature": 0.5
            },
            timeout=60,
            name="[GPU] research_query"
        )
    
    @task(4)
    def brainstorm_cpu(self):
        """Quick brainstorming on CPU."""
        # Note: This goes to a different host
        import requests
        try:
            requests.post(
                f"{self.llamacpp_url}/completion",
                json={
                    "prompt": "Brainstorm 5 research directions:",
                    "n_predict": 60,
                    "temperature": 0.9
                },
                timeout=15
            )
        except Exception:
            pass


# ============================================================================
# CUSTOM EVENT HANDLERS
# ============================================================================

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """Log request metrics for analysis."""
    if exception:
        print(f"[FAIL] {name}: {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test."""
    print("=" * 60)
    print("AI IDP Load Test Starting")
    print("=" * 60)
    print(f"Host: {environment.host}")
    print(f"Users: {environment.parsed_options.num_users if hasattr(environment, 'parsed_options') else 'N/A'}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Summarize test results."""
    print("\n" + "=" * 60)
    print("AI IDP Load Test Complete")
    print("=" * 60)
    
    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Failed Requests: {stats.total.num_failures}")
    print(f"Failure Rate: {stats.total.fail_ratio * 100:.2f}%")
    
    if stats.total.num_requests > 0:
        print(f"\nResponse Times:")
        print(f"  Median: {stats.total.median_response_time:.0f}ms")
        print(f"  95th %: {stats.total.get_response_time_percentile(0.95):.0f}ms")
        print(f"  99th %: {stats.total.get_response_time_percentile(0.99):.0f}ms")
        print(f"\nThroughput: {stats.total.total_rps:.2f} req/s")


# ============================================================================
# ACCEPTANCE CRITERIA VALIDATION
# ============================================================================

ACCEPTANCE_CRITERIA = {
    "median_response_time_ms": 5000,  # 5 seconds max median
    "p95_response_time_ms": 15000,    # 15 seconds max P95
    "failure_rate_max": 0.05,          # <5% failures
    "min_throughput_rps": 0.5,         # At least 0.5 req/s
}


def validate_results(stats) -> bool:
    """Validate test results against acceptance criteria."""
    passed = True
    
    print("\n" + "=" * 60)
    print("Acceptance Criteria Validation")
    print("=" * 60)
    
    # Median response time
    median = stats.total.median_response_time
    target = ACCEPTANCE_CRITERIA["median_response_time_ms"]
    status = "✓ PASS" if median <= target else "✗ FAIL"
    print(f"{status}: Median response time {median:.0f}ms <= {target}ms")
    if median > target:
        passed = False
    
    # P95 response time
    p95 = stats.total.get_response_time_percentile(0.95)
    target = ACCEPTANCE_CRITERIA["p95_response_time_ms"]
    status = "✓ PASS" if p95 <= target else "✗ FAIL"
    print(f"{status}: P95 response time {p95:.0f}ms <= {target}ms")
    if p95 > target:
        passed = False
    
    # Failure rate
    fail_rate = stats.total.fail_ratio
    target = ACCEPTANCE_CRITERIA["failure_rate_max"]
    status = "✓ PASS" if fail_rate <= target else "✗ FAIL"
    print(f"{status}: Failure rate {fail_rate*100:.2f}% <= {target*100:.0f}%")
    if fail_rate > target:
        passed = False
    
    # Throughput
    rps = stats.total.total_rps
    target = ACCEPTANCE_CRITERIA["min_throughput_rps"]
    status = "✓ PASS" if rps >= target else "✗ FAIL"
    print(f"{status}: Throughput {rps:.2f} req/s >= {target} req/s")
    if rps < target:
        passed = False
    
    print("\n" + ("=" * 60))
    print(f"Overall: {'✓ ALL CRITERIA PASSED' if passed else '✗ SOME CRITERIA FAILED'}")
    print("=" * 60)
    
    return passed
