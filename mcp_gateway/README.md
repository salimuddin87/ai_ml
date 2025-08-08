## Introduction
A complete, self-contained example that implements a simple Model Context Protocol (MCP) Gateway in Python with:
* a Control Plane to register / list / unregister MCP servers
* a Data Plane to create sessions, open a stream (SSE) to clients, forward streaming data from an MCP server, and send subsequent RPC-style requests (math calls) to the registered MCP server using `session_id`
* a sample MCP server that implements math operations and an SSE streaming endpoint (so you can test end-to-end)
* Kubernetes manifests (Deployments + Services) and `Dockerfiles` for both services
* `requirements.txt` and simple instructions

This is a minimal, `production-minded prototype` — in real production you’d add auth, persistence, TLS, retries, rate-limits, observability, health checks, scaling controls, and secure image registries.

## How to run locally
1. Create a Python virtual environment and install dependencies:
   ```bash
    python3 -m venv mcp-gateway-env
    source mcp-gateway-env/bin/activate  # or mcp-gateway-env\Scripts\activate on Windows
    pip install -r requirements.txt
   ```

2. Start the MCP server:
    ```bash
      # from mcp-gateway-example/mcp_server
      pip install -r requirements.txt
      uvicorn mcp_server:app --host 0.0.0.0 --port 8001
    ```

3. Start Gateway
   ```bash
      # from mcp-gateway-example/gateway
      pip install -r requirements.txt
      uvicorn gateway:app --host 0.0.0.0 --port 8000 --reload
   ```

4. Register the MCP server with the Gateway(control plane):
   ```bash
      curl -X POST "http://localhost:8000/control/register" -H "Content-Type: application/json" -d '{"name":"math1","base_url":"http://host.docker.internal:8001"}'
      # If running everything locally on same host and not inside docker, use: "http://localhost:8001"
   ```

5. Create a session
    ```bash
        curl -X POST "http://localhost:8000/data/connect" -H "Content-Type: application/json" -d '{"server":"math1"}'
        # response -> {"session_id": "..."}
    ```

6. Open SSE stream
    ```bash
        # Replace <session_id> with returned id
        curl -N http://localhost:8000/data/stream/<session_id>
    ```
   
7. Make math calls via session
    ```bash
        curl -X POST "http://localhost:8000/data/request/<session_id>/add" -H "Content-Type: application/json" -d '{"a":10,"b":5}'
        # -> {"result": 15}
    ```
   

# Explanation of components and Design decisions

## Control Plane
* `/control/register` — register an MCP server (name + base_url)
* `/control/list` — list registered MCP servers
* `/control/unregister` — remove a registration
* Registry is stored in-memory (`MCP_REGISTRY`) — swap to DB (Redis/Postgres) in production

## Data Plane
* `/data/connect` — creates `session_id`, starts a background task _`bridge_backend_stream` to connect to backend `/stream` and forward lines to an `asyncio.Queue`
* `/data/stream/{session_id}` — SSE endpoint for the client; streams data: `<payload>\n\n` as events; uses heartbeat if no events
* `/data/request/{session_id}/{method}` — forwards RPC calls (math) to backend `POST /math/{method}`

## Session Lifecycle
* Session stored with background task and queue
* When stream is closed (client disconnects), gateway cancels background task and cleans up resources

## Streaming and SSE
* Gateway uses `httpx` async streaming to consume SSE from backend and forwards to the client
* Format used: standard SSE `data: ...\n\n`
* Heartbeats are implemented by sending comment lines `:\n\n` (so client-side connections don't time out) when queue has no events

## Security & Production Concerns(not implemented)
* Authentication & Authorization for control plane & data plane endpoints
* TLS/HTTPS for all endpoints
* Persistent registry (use Redis or DB)
* Health checks & liveness/readiness probes in K8s
* Circuit breakers, timeouts, backpressure for streaming
* Observability: metrics, tracing, structured logs
* Autoscaling and resource limits

## Improvements (How to extend this prototype)
* `Persistent registry`: use Redis or Postgres for registered MCP servers and sessions
* `Multi-backend load balancing`: register multiple MCP server instances and load balance or do health-based failover
* `Authentication`: issue JWTs to clients and require token for connect/stream/request
* `Authorization`: restrict which client can access which server/session
* `Message broker`: (Kafka/Redis streams) to decouple gateway & backend bridging for scale
* `Deployment automation`: Helm charts, readiness probes, RBAC
* `SLA-aware routing`: health checks and latency-based routing between multiple MCP instances
* `Versioning & contract`: MCP server advertisement includes version & capabilities; gateway enforces compatibility

## Packaging and Deployment
* Build Docker images for both services (use the `Dockerfiles`).
* Push images to your container registry (or use local kind load `docker-image`).
* Apply `k8s/namespace.yaml` then the deployments:
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/mcpserver-deployment.yaml
kubectl apply -f k8s/gateway-deployment.yaml
```
* Expose gateway via an Ingress or kubectl port-forward svc/mcp-gateway -n mcp-demo 8000:8000 for local testing.



