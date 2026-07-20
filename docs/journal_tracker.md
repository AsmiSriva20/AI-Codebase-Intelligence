Day 1: uvicorn:  uvicorn app.main:app --reload --reload-dir app

Note: --reload-dir app restricts the file watcher to backend/app. Without it,
uvicorn watches the whole backend/ cwd, including repos/repository — so
cloning a repo (which drops hundreds of new files there) triggers a reload
mid-request and kills any in-flight /build call.