"""
simple app for convenience, install the [web] components
"""

from fastapi import (
    APIRouter,
    FastAPI,
    Response,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
)
from http import HTTPStatus
from starlette.responses import HTMLResponse
from fastapi.responses import StreamingResponse
from funkyprompt.core.agents import ApiCallingContext, Runner
import typing
from pathlib import Path


def get_custom_redoc_html(
    *,
    openapi_url: str,
    title: str,
    redoc_favicon_url: str = "https://fastapi.tiangolo.com/img/favicon.png",
    with_google_fonts: bool = True,
) -> HTMLResponse:
    """
    This is added to include the try-it-out feature in the redocly documentation at /documentation
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <title>{title}</title>
    <!-- needed for adaptive design -->
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    """
    if with_google_fonts:
        html += """
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
    """
    html += f"""
        <link rel="shortcut icon" href="{redoc_favicon_url}">
        <!--
        ReDoc doesn't change outer page styles
        -->
        <style>
          body {{
            margin: 5;
            padding: 5;
          }}
        </style>
        </head>
        <body>
            <div id="redoc-container"></div>
              <script src="https://cdn.jsdelivr.net/npm/redoc@2.0.0-rc.55/bundles/redoc.standalone.min.js"> </script>
              <script src="https://cdn.jsdelivr.net/gh/wll8/redoc-try@1.4.9/dist/try.js"></script>
              <script>
                initTry({{
                openApi: `{openapi_url}`,
                  redocOptions: {{scrollYOffset: 50}},
                }})
              </script>
        </body>
        </html>
        """
    return HTMLResponse(html)


app = FastAPI(
    summary="Funkyprompt API",
    description=f"""Provides a simple shell for testing APIs with agents""",
    title="ONE",
    openapi_url=f"/openapi.json",
    docs_url=f"/docs",
    version="0.6.1",
)

api_router = APIRouter()


@app.post("/ask")
async def ask(
    question: str,
    # the response context is merged into the form data to work with files - its not posted by the client - see swagger
    response_context: ApiCallingContext = Depends(),
    files: typing.Optional[typing.List[UploadFile]] = File(..., default_factory=list),
) -> StreamingResponse:
    """
    illustrate a simple web client for the bits
    """

    try:
        """interact and respond"""
        r = Runner()
        stream = r(question=question, context=response_context)

        def iterate_s():
            """this is a bit of a hack because i cannot ensure yet that i am streaming non null things from above"""
            for s in stream:
                if s:
                    yield s

        return (
            StreamingResponse(iterate_s(), media_type="text/event-stream")
            if response_context.prefers_streaming
            else Response(content=stream)
        )

    except Exception as ex:

        raise HTTPException(status_code=500, detail=str(ex))
    
def start():
    import uvicorn

    uvicorn.run(
        f"{Path(__file__).stem}:app",
        host="0.0.0.0",
        port=5005,
        log_level="debug",
        reload=True,
    )


if __name__ == "__main__":
    """
    You can start the dev with this in the root
    uvicorn funkyprompt.app.main:app --port 5005 --reload
    
    #the swagger will be at the /funky/docs location
    #the redocly will be at the /funky/documentation location
    http://127.0.0.1:5005/funky/docs
    
    """
    
    start()
    
