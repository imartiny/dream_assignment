from fastapi import Body, FastAPI, Depends, HTTPException, BackgroundTasks, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app import models
from app import schemas
from app.config import settings
from app.database import engine, SessionLocal
from app.services.data_organizer import DataOrganizer
from app.services.query_engine import SmartQueryEngine

from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Smart Process Analyzer API",
    description="API for analyzing and querying process data",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url=None,
    redoc_url=None
)

@app.on_event("startup")
async def startup_event():
    models.Base.metadata.drop_all(bind=engine)
    models.Base.metadata.create_all(bind=engine)
    print("Database initialized successfully.")

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print("Validation errors:", exc.errors())
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()},
    )

@app.post(f"{settings.API_V1_STR}/ingest", response_model=schemas.IngestDataResponse)
async def ingest_data(data: schemas.IngestDataRequest, background_tasks: BackgroundTasks):
    """
    Ingest process data.

    - **os_type**: Type of operating system (e.g., 'windows', 'linux')
    - **content**: Raw process data content
    - **meta_info**: Metadata about the ingested data
    """
    try:
        batch_id, num_of_records = await DataOrganizer.receive_and_parse_data(data.dict())
        background_tasks.add_task(DataOrganizer.process_and_store_data, batch_id)
        return schemas.IngestDataResponse(
            message="Data received and processing started",
            records_processed=num_of_records
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post(f"{settings.API_V1_STR}/query", response_model=schemas.QueryResponse)
async def query_data(query_params: schemas.QueryParams = Body(...), db: Session = Depends(get_db)):
    """
    Query process data based on specified parameters.

    - **start_time**: Start time for the query range
    - **end_time**: End time for the query range
    - **os_type**: Type of operating system to filter by
    - **machine_id**: ID of the machine to filter by
    - **command**: Name of the process to filter by
    - **cpu_usage_gt**: Filter for CPU usage greater than this value
    - **memory_usage_gt**: Filter for memory usage greater than this value
    - **limit**: Maximum number of records to return
    - **offset**: Number of records to skip
    """
    try:
        total_count, records = SmartQueryEngine.execute_query(query_params.model_dump(), db)
        return schemas.QueryResponse(
            total_count=total_count,
            records=records
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get(f"{settings.API_V1_STR}/process/{{process_id}}", response_model=schemas.ProcessDataResponse)
async def get_process(process_id: int, db: Session = Depends(get_db)):
    """
    Retrieve a specific process by its ID.

    - **process_id**: The ID of the process to retrieve
    """
    process = db.query(models.ProcessData).filter(models.ProcessData.id == process_id).first()
    if process is None:
        raise HTTPException(status_code=404, detail="Process not found")
    return schemas.ProcessDataResponse(
        process=schemas.ProcessData.from_orm(process),
    )

@app.get(f"{settings.API_V1_STR}/health")
async def health_check():
    """
    Check the health status of the API.
    """
    return {"status": "healthy"}

# Swagger UI setup
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - ReDoc",
        redoc_js_url="/static/redoc.standalone.js",
    )

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Smart Process Analyzer API",
        version="1.0.0",
        description="API for analyzing and querying process data",
        routes=app.routes,
    )
    openapi_schema["openapi"] = "3.0.2"  # Add this line to specify the OpenAPI version
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Mount the static files
app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)