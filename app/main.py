import os
import time

from datetime import datetime
import validators

from app.config import settings
from app.utils.logger import logger
from app.utils.metrics import record_metrics
from app.utils.model import JSONDataRequest
from app.scrap import get_medicine_detail_scrap, scap_medicine
from app.db import mongo, insert_document, fetch_user

from fastapi import FastAPI, Request, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse, Response

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(
    title="MedlrAPI",
    description="Medlr API: High-Performance API and Service",
    summary="Medlr Assignment: High-Performance API and Service (Go or Python)",
    version="0.0.1",
    contact={
        "name": "Ashish Bindra",
        "url": "https://github.com/ashishbindra2",
        "email": "ashishbindra2@gmail.com",
    }
)
scheduler = AsyncIOScheduler()


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        latency = time.time() - start_time
        record_metrics(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
            latency=latency,
        )
        return response


app.add_middleware(MetricsMiddleware)


# logger = structlog.get_logger()
# Instrumentator().instrument(app).expose(app)


@app.get("/extract-medicine")
async def api_extract_medicine(request: Request, url: str):
    """
    Extract medicine details from URL
    :return:
    """
    logger.info("Processing medicine details extraction", url=request.url)
    if not validators.url(url):
        logger.error("The URL you entered is not acceptable by the system")
        raise HTTPException(status_code=400,
                            detail="The URL you entered is not acceptable by the system. "
                                   "Please verify and ensure it meets the required format.")
    try:
        async for data in get_medicine_detail_scrap(url):
            logger.info("Extraction successful", medicine_details=data)
            return data
    except Exception as e:
        logger.error("Extraction failed", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/upload-image")
async def api_upload_image(file: UploadFile, user_uuid: str = Form(...), filename: str = Form(...)):
    """
      Upload an image and associate it with a user UUID and filename.
      and check that image extension is .img
    """
    if not file.filename.endswith('.img'):
        logger.error("File must have .img extension")
        raise HTTPException(status_code=400, detail="File must have .img extension")

    user_path = os.path.join(settings.upload_path, user_uuid)
    os.makedirs(user_path, exist_ok=True)

    image_path = os.path.join(user_path, filename)
    if os.path.isfile(image_path):
        logger.info("Image is already available please change the name")
        raise HTTPException(status_code=400, detail="File already available by this name. Please change file name")
    logger.info(f"Image is going to save this {image_path} location", )
    # with open(image_path, "wb+") as file_object:
    #     shutil.copyfileobj(file.file, file_object)

    try:
        with open(image_path, "wb") as f:
            f.write(await file.read())
        logger.info("File save Successfully!!")
    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {e}")

    return {
        "status": "success",
        "message": "Image uploaded successfully",
        "file_path": image_path
    }


@app.post('/store-data')
async def api_store_data_db(request: JSONDataRequest):
    """
    Store JSON data in a MongoDB collection.

    This API endpoint allows users to add arbitrary JSON data to a specified MongoDB collection.
    The user must provide a valid collection name and the JSON data to be stored.

    Args:
        request (JSONDataRequest): A request body containing:
            - collection_name (str): The name of the MongoDB collection where the data should be stored.
            - data (Dict): The JSON data to be stored in the collection.

    Returns:
        dict: A response message indicating success or failure, along with relevant information.

    """
    collection_name = request.collection_name
    data = request.data
    if not collection_name:
        logger.error("Invalid collection name provided. The collection name is empty or missing.")
        return {
            "message": "Please enter collection name",
            "collection_name": '',
            "data": data
        }
    if not data:
        logger.error("Invalid data provided. The data is empty or missing.")

        return {
            "message": "Data is empty!",
            "collection_name": collection_name,
            "data": None
        }

    try:
        inserted_id = await insert_document(collection_name, data.dict())
        logger.info(f"Data inserted successfully into the collection {collection_name}. Inserted ID: {inserted_id}")
        return {
            "status": "success",
            "message": "Data stored successfully",
            "inserted_id": str(inserted_id)
        }
    except Exception as e:
        logger.critical(f"Critical error occurred during data insertion in the collection {collection_name}. Error:"
                        f" {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/retrieve-image/")
async def api_retrieve_image(uuid: str, filename: str):
    """
        Retrieve an image by UUID and filename.

        This endpoint retrieves an image stored in the server's upload directory based on the user's UUID and the filename.

        Args:
            uuid (str): The unique identifier of the user.
            filename (str): The name of the image file to retrieve.

        Returns:
            FileResponse: The requested image file if it exists.
    """
    img_path = os.path.join(settings.upload_path, uuid, filename)
    logger.info(f"Attempting to retrieve image. UUID: {uuid}, Filename: {filename}")

    if not os.path.exists(img_path):
        logger.warning(f"Image not found. UUID: {uuid}, Filename: {filename}. Checked path: {img_path}")
        return {
            "status": "error",
            "message": "File not found"
        }
    logger.info(f"Image found. Serving file from path: {img_path}")

    try:
        return FileResponse(img_path)
    except Exception as e:
        logger.critical(f"An error occurred while serving the file. UUID: {uuid}, Filename: {filename}. "
                        f"Error:{str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while retrieving the image.")


@app.get("/get-data/")
async def api_get_data(user_id: str):
    """
       Retrieve user data by user ID.

       This endpoint fetches user data from the database based on the provided user ID.

       Args:
           user_id (str): The unique identifier of the user.

       Returns:
           dict: A response indicating the success or failure of the data retrieval
    """
    logger.info(f"Received request to fetch user data for user_id: {user_id}")
    try:

        user_data = await fetch_user({"user_id": user_id})

        if not user_data:
            logger.warning(f"No user data found for user_id: {user_id}")

            return {
                "status": "error",
                "message": "User data not found"
            }
        logger.info(f"Successfully retrieved user data for user_id: {user_id}")

        return {
            "status": "success",
            "data": user_data
        }
    except Exception as e:
        logger.critical(f"An error occurred while retrieving user data for user_id: {user_id}. Error: {str(e)}",
                        exc_info=True)
        raise HTTPException(status_code=500, detail="An error occurred while retrieving user data.")


@app.get("/run-scheduled-scraping")
async def api_run_scheduled_scraping():
    """
    Scheduled task to scrape and update medicine details in the database.

    This endpoint simulates a scheduled task that scrapes medicine details from a collection of URLs
    and updates the information in the MongoDB database.

    Returns:
        dict: A response containing the list of scraped data.
    """
    logger.info("Scheduled scraping task started.")

    response = await scap_medicine()
    return response


@app.get("/metrics")
async def api_metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get('/medicine', tags=["developer"])
async def api_medicine_detail(number: int):
    """
    All medicine details display for self testing purpose
    :param number: Number of results you want to display
    :return:
    """
    data = []
    logger.info(f"Fetching medicine details for number: {number}")

    try:
        async for item in mongo.get_medicine_details(number):
            data.append(item)
            logger.debug("Fetched item: %s", item)  # Log each item fetched

        logger.info("Successfully retrieved %d items", len(data))

    except Exception as e:
        logger.error("Error occurred while fetching medicine details: %s", e)
        raise

    return {"data": data}


@app.get("/users", tags=["developer"])
async def users():
    """
    This is for developer endpoint only ro list of users available
    :return:
    """
    cursor = await mongo.fetch_users()
    print(cursor)
    print(datetime.now())
    return {"users list": cursor}


@app.on_event("startup")
async def startup_event():
    try:

        logger.info("Task scheduled to run every day at 6:00 PM.")
        scheduler.add_job(api_run_scheduled_scraping, CronTrigger(second='*/10'), id="daily scrap")
        scheduler.start()
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start scheduler")


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    logger.info("Scheduler has been shut down.")


