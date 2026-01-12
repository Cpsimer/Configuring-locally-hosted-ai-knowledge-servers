# Code Review: Perplexity-Labs-003

## 1. Executive Summary
The `Perplexity-Labs-003` module represents a **pivot from a distributed-system approach** (as described in `Perplexity LABS 001.md`) to a **highly optimized, single-node, standalone architecture**.

The code quality is high, with a strong focus on security (hardened Docker containers) and realistic performance tuning (physics-based throughput calculations). However, this implementation effectively decouples the AI services from the existing `Active Production System` (XPS 15 / Proxmox), operating in isolation on the Desktop.

## 2. Architectural Analysis

### The "Single-User" Pivot
-   **Context**: The `Perplexity LABS 001.md` document planned for a "Wave Architecture" where NGINX on the XPS 15 (Proxmox LXC) would route requests to the Desktop (`schlimers-server`).
-   **Implementation**: The `Perplexity-Labs-003` implementation (`docker-compose.production.yml`) binds all services to `127.0.0.1` (localhost).
    -   **Implication**: The services are **inaccessible** from the XPS 15 NGINX proxy or any other device on the network.
    -   **Justification**: `script.py` explicitly demotes "NGINX Reverse Proxy" to "Won't-Have" and cites "localhost only, no network exposure" as a specific optimization for latency and security.
-   **Conclusion**: This is an intentional design choice to maximize local performance and simplify security, but it contradicts the broader "Ecosystem" goals if remote access (e.g., from the XPS 13 client) was still required.

## 3. Code-Level Findings

### Infrastructure (`docker-compose.production.yml`)
-   **Security**: ✅ Excellent security hardening.
    -   `security_opt: no-new-privileges:true`
    -   `cap_drop: ALL`
    -   Uses `env_file` for secrets.
    -   Runs as non-root user (`1000:1000`).
-   **Configuration**:
    -   **vLLM**: Correctly configured for `fp8` quantization and `flashinfer` backend. Resource limits (`gpu-memory-utilization 0.80`) provides a safe OOM buffer.
    -   **Ports**: Binds to `8000`, `8001`, and `8002` on localhost.
-   **Observation**: The `llamacpp-70b-hybrid` service correctly manages expectations (8-15 tok/s) compared to the "physically impossible" earlier claims.

### Scripts
-   **`script.py` vs `script_1.py`**:
    -   ⚠️ **Redundancy**: `script_1.py` appears to be a near-duplicate of `script.py`. They both generate documentation CSVs.
    -   **Recommendation**: Delete `script_1.py` and rename `script.py` to `generate_optimization_report.py` to clearly indicate its purpose (it is not a runtime script).

-   **Shell Scripts (`scripts/`)**:
    -   `generate-secrets.sh`: Implements the required cryptographic key generation.
    -   `thermal-monitor.sh`: A lightweight alternative to DCGM, aligning with the "Single-User" philosophy.
    -   `backup-models.sh`: Robust rsync-based backup.

### Tests (`tests/`)
-   `test_inference_performance.py`: Comprehensive `pytest` suite validating TTFT and throughput against the new "corrected" targets.
-   `locustfile.py`: Standard load testing configuration.

## 4. Recommendations

### Immediate Actions
1.  **Remove Redundant File**: Delete `script_1.py`.
2.  **Rename Script**: Rename `script.py` -> `generate_optimization_report.py`.
3.  **Git Ignore**: Ensure `secrets/` directory is added to `.gitignore` to prevent accidental commit of `api-keys.env`.

### Architecture Decision
-   **Verify Network Isolation**: Confirm that *no* remote access is required (e.g., from the XPS 13 portable client). If remote access is needed later, the `127.0.0.1` binding will need to be changed to `0.0.0.0` or a VPN/Tailscale interface, and TLS/Authentication (Authentik) will need to be reintroduced.

### Minor Improvements
-   **Timezone**: The `docker-compose.yml` hardcodes `TZ=America/Chicago`. Consider making this a variable `${TZ}` for portability, though acceptable for a personal setup.

## 5. Security Checklist
| Item | Status | Notes |
| :--- | :--- | :--- |
| **Container Isolation** | ✅ Pass | `no-new-privileges` active |
| **Network Exposure** | ✅ Pass | Localhost only (127.0.0.1) |
| **Secret Management** | ✅ Pass | Secrets injected via env_file, not hardcoded |
| **Model Integrity** | ⚠️ Note | Backup script exists, but check checksum validation in practice |
