# OS-Level Multi-Threaded Web Server with Monitoring Dashboard

A full-stack educational project that demonstrates OS concepts through a manually implemented HTTP server built with Python sockets and a React/Tailwind monitoring dashboard.

Repository: `C-Core-Server-v2.0`

## Project Layout

```text
server/   Python backend, manual HTTP parsing, thread pool, cache, logging
client/   React + Tailwind dashboard
logs/     Runtime request logs
tools/    Load testing and performance comparison scripts
```

## Features

- Manual TCP socket server, no Flask or Django
- Manual HTTP request parsing
- Threaded multi-client handling
- Fixed-size worker thread pool
- FIFO request queue to simulate OS scheduling
- Shared-state synchronization with locks
- File serving with in-memory cache
- Request logging to file and in-memory log viewer
- Rate limiting per client IP
- API endpoints for stats, logs, and thread monitoring
- React dashboard with polling updates
- Bonus load testing and single-thread vs multi-thread comparison tools

## Run the Backend

```bash
cd server
python server.py
```

Backend default:

- Host: `127.0.0.1`
- Port: `8080`

Useful overrides:

```bash
python server.py --port 9000 --threads 8
python server.py --mode single
```

## Run the Frontend

```bash
cd client
npm install
npm run dev
```

Set `VITE_API_BASE_URL` if the backend is on a different host or port.

On Render, the React build is copied into the Python server during deployment, so the UI and API share one service URL.

## Open in Browser

- Backend status page: `http://127.0.0.1:8080/`
- React dashboard: `http://127.0.0.1:5173/`

## OS Concepts for Viva

- Thread lifecycle: worker threads are created at startup, execute queued tasks, and terminate on shutdown.
- Thread pool: a fixed number of workers handles concurrent requests efficiently.
- Request queue: accepted sockets are queued FIFO before workers process them, similar to scheduling.
- Synchronization: locks protect shared data such as logs, metrics, cache state, and rate-limit buckets.
- File I/O: static files are read from disk and returned as HTTP responses.
- Caching: frequently requested static files stay in memory to reduce disk access.
- Rate limiting: per-IP request windows reduce spam and resource exhaustion.
- Benchmarking: the optional `/api/benchmark` route simulates blocking I/O for clearer single-thread vs multi-thread comparisons.
- Concurrency vs parallelism: multiple request-handling threads can make progress concurrently, and on multi-core systems they may run in parallel.

## Render Deployment

This repository is ready for a single Render web service deployment.

- Blueprint file: [`render.yaml`](./render.yaml)
- Build command: `bash render-build.sh`
- Start command: `cd server && python server.py`
- Health check path: `/healthz`
- The build script installs the React client, builds it, and copies the output into `server/public`
- The Python server automatically binds to Render's `PORT` and uses `0.0.0.0` in Render mode
- The React client uses same-origin requests in production, so no separate frontend service is needed

## Sample Test Cases

### 1. Basic Browser Check

- Visit `/`
- Confirm the backend status page loads
- Confirm `/api/stats`, `/api/logs`, and `/api/threads` return JSON

### 2. Multiple Client Simulation

```bash
python tools/load_test.py --host 127.0.0.1 --port 8080 --clients 20 --requests 200
```

### 3. Compare Single vs Multi-Thread

```bash
python tools/compare_modes.py --clients 30 --requests 300
```

By default the comparator uses a small blocking benchmark route:

- `GET /api/benchmark?delay_ms=25`
- It simulates blocking I/O so the thread pool advantage is easier to observe
- You can override it with `--path` or `--paths`

### 4. Rate Limiting Check

- Run a high-concurrency load test against the same IP
- Verify some requests return `429 Too Many Requests`

### 5. Cache Behavior

- Request `/styles.css` repeatedly
- Confirm cache hits increase in `/api/stats`

## Notes

- The backend is intentionally low-level and educational.
- The React client polls the backend instead of using a framework shortcut.
- The server uses standard library modules only.
