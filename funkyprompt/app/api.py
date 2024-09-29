from fastapi import APIRouter, FastAPI, Response
from fastapi.responses import JSONResponse

from pydantic import BaseModel, Field
from http import HTTPStatus
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import funkyprompt
from pathlib import Path
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import json
from typing import Annotated, Literal

from fastapi import FastAPI, Query

"""security bits"""
bearer = HTTPBearer()
async def get_current_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
):
    token = credentials.credentials

    """hard coded token for testing"""
    if token != 'getfunky':
        raise HTTPException(
            status_code=401,
            detail="Invalid API KET in token check.",
        )

    return token

"""setup app"""

PROCESS_NAME = 'api'
app = FastAPI(
    summary="An API for testing funkyprompt",
    description=f"""Funkyprompt can generate functions from OpenAPI specs. This API is used to test different scenarios
    """,
    title="Funkyprompt",
    openapi_url=f"/{PROCESS_NAME}/openapi.json",
    docs_url=f"/{PROCESS_NAME}/docs",
    version="0.1.0" #funkyprompt.__version__
)


class TaskParam(BaseModel):
    category: str = Field(description="The category of data you wish to retrieve")
    entity_key: str = Field(description="The key you wish to lookup for the given category")
    
@app.get('/creature/details', dependencies=[Depends(get_current_token)],status_code=HTTPStatus.OK )
async def get_task_data( category: str = Query(...,description="The category of data you wish to retrieve"),
                         category_key: str = Query(..., description="The key you wish to lookup for the given category"))->str:
    """Supply a category and a value to retrieve a new value. The categories are 'animals', 'towns'  
    For example you can look for an animal by name; category=animals, category_key='John'
    or you can look for the town for the given animal category; category=town, category_key='dog'
    
    This is how you can full resolve details given a name; name->category->town. You may need to call the function twice.
    """
    
    category = category.lower()
    category_key = category_key.lower()
    #lame 
    if category == 'town':
        category = 'towns'
    
    category_data = {
          "animals": {'bob': 'dog', 'delia': 'cat', 'xian': 'fish' },
          "towns": {'dog': 'paris', 'fish': 'seoul', 'cat': 'austin'} 
      }
      
    if category not in category_data:
        raise HTTPException(status_code=404, detail= f'The category=`{category}` is not one of the allowed categories {list(category_data.keys())}')

    data = category_data[category.lower()]
    
    
    if category_key not in data:
        raise HTTPException(status_code=404, detail= f'The entity_key=`{category_key}` is not one of the allowed keys {list(data.keys())} - you can try to run a search')

    return JSONResponse(content={'result': data[category_key.lower()], 'hint': "you can call this function again to find out other details in different categories"}, status_code=200)


class TaskResponse(BaseModel):
    name: str = Field(description="The name of the entity")
    category: str = Field(description="The type of the entity")
    town: str = Field(description="The town where the entity is from")
    
@app.post('/creature', dependencies=[Depends(get_current_token)],status_code=HTTPStatus.ACCEPTED)
async def save_result(data: TaskResponse)->str:
    """save the details 
    """
    
    return Response(content=json.dumps({'detail': data.model_dump(), 'message': "we have received the details. thank you."}), status_code=200)

    
@app.get('/scrape/site', dependencies=[Depends(get_current_token)],status_code=HTTPStatus.ACCEPTED)
async def scrape_text(uri: str)->dict:
    """scrape text from the website to enhanced content in notes
    provided a uri to the target web page.
    """
    from funkyprompt.core.utils.parsing import web
    
    content = web.scrape_text(uri)
    return JSONResponse(content=json.dumps({'detail': content, 'message': "we have scraped the text provided from the uri", "uri": uri}),
                        status_code=200)



api_router = APIRouter()

origins = [
    "http://localhost:5005",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(api_router)
 

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
    uvicorn funkyprompt.app.api:app --port 5005 --reload
     
    browse : http://127.0.0.1:5005/api/docs
    """
    
    start()
    