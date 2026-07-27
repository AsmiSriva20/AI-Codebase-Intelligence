import asyncio
import json

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from app import state
from app.storage.db import get_session
from app.storage.models import Repository
from app.realtime import webhooks
from app.realtime.events import registry as graph_events

router = APIRouter()


@router.websocket("/events/graph")
async def graph_events_endpoint(websocket: WebSocket):
    await graph_events.connect(websocket)
    try:
        while True:
            # We don't expect messages from the client — this just blocks until
            # they disconnect, which is what raises WebSocketDisconnect below.
            await websocket.receive_text()
    except WebSocketDisconnect:
        graph_events.disconnect(websocket)


@router.post("/webhook/github")
async def github_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not webhooks.verify_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid or missing webhook signature")

    try:
        payload = json.loads(body)
    except ValueError:
        raise HTTPException(status_code=400, detail="Malformed JSON payload")

    event = webhooks.parse_push_event(payload)

    if not event["branch"]:
        return {"status": "ignored", "reason": "not a branch push"}

    if state.CURRENT_REPOSITORY_ID is None:
        return {"status": "ignored", "reason": "no repository currently loaded"}

    session = get_session()
    try:
        repository = session.get(Repository, state.CURRENT_REPOSITORY_ID)
        current_url = repository.url if repository else None
    finally:
        session.close()

    if webhooks.normalize_repo_url(event["repo_url"]) != webhooks.normalize_repo_url(current_url):
        return {"status": "ignored", "reason": "webhook is for a different repository"}

    if not state.webhook_lock.acquire(blocking=False):
        return {"status": "ignored", "reason": "a rebuild is already in progress"}

    try:
        # analyze_repository() is a slow, synchronous, blocking call — run it off
        # the event loop so other requests and open WebSocket connections aren't
        # frozen for the duration of the rebuild.
        await asyncio.to_thread(state.handle_github_push, event["branch"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Rebuild failed: {e}")
    finally:
        state.webhook_lock.release()

    await graph_events.broadcast({
        "type": "graph_updated",
        "repository_id": str(state.CURRENT_REPOSITORY_ID),
        "branch": event["branch"],
    })

    return {"status": "rebuilt", "branch": event["branch"], "commit": event["commit_sha"]}
