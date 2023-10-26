#!/usr/local/bin/python3
from fastapi import FastAPI, APIRouter
from funkyprompt.ops.entities import AbstractVectorStoreEntry
from funkyprompt.io.stores import insert
from funkyprompt import logger


PROCESS_NAME = "funkyprompt"
app = FastAPI(
    title="FunkyPrompt API",
    openapi_url=f"/{PROCESS_NAME}/openapi.json",
    docs_url=f"/{PROCESS_NAME}/docs",
)
api_router = APIRouter()


@app.get("/")
@app.get("/healthcheck")
async def healthcheck():
    return {"status": "ok"}


@app.get(f"/{PROCESS_NAME}/")
def say_hi():
    return {"message": "Hello Funky World"}


@app.get(f"/{PROCESS_NAME}/ingest/text-entity", status_code=200, response_model=dict)
def upsert_unstructured_data(*, text: AbstractVectorStoreEntry) -> dict:
    """

    this object will be inserted into the store

    """

    logger.info(f"Inserting {text}")
    insert(text)

    return {"done"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8008)
