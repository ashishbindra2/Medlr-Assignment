from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings
from app.utils.logger import logger


class MongoDB:
    """
    MongoDB client for handling operations related to the database.
    """

    def __init__(self):
        # Establish connection with MongoDB using Motor
        self.client = AsyncIOMotorClient(settings.mongo_url)
        self.db = self.client[settings.db_name]
        self.medicine_collection = self.db["medicine_urls"]
        self.users = self.db['users']

    async def get_medicine_details(self, limit: int):
        """
        Asynchronously fetches medicine details from the collection.
        Args:
            limit (int): The number of documents to fetch.
        Yields:
            dict: The documents retrieved from the medicine collection.
        """
        cursor = self.medicine_collection.find({}, {'_id': 0}).limit(limit)
        async for document in cursor:
            yield document

    async def fetch_users(self):
        """
        Asynchronously fetches all users from the users collection.
        Returns:
            list: List of user documents.
        """
        users = []
        user_cursor = self.users.find({}, {'_id': 0})
        async for user in user_cursor:
            users.append(user)
        return users

    def update_medicine_details(self, url: str, scraped_data: dict):
        """
        Updates or inserts medicine details based on the URL.
        Args:
            url (str): The unique URL for medicine.
            scraped_data (dict): The data to be inserted or updated.
        Returns:
            result: The result of the update operation.
        """
        result = self.medicine_collection.update_one(
            {"url": url},  # Ensure idempotence using URL as a unique key
            {"$set": scraped_data},
            upsert=True  # Insert a new or update existing document
        )
        return result


# Instantiate the MongoDB client
mongo = MongoDB()


async def insert_document(collection_name: str, document: dict):
    """
    Asynchronously inserts a document into the specified collection.
    Args:
        collection_name (str): The name of the MongoDB collection.
        document (dict): The document to insert.
    Returns:
        ObjectId: The inserted document's unique identifier.
    """
    result = await mongo.db[collection_name].insert_one(document)
    logger.info(f"Document inserted successfully with id {result.inserted_id}")
    return result.inserted_id


async def fetch_user(query: dict):
    """
    Fetches a user document based on a query.
    Args:
        query (dict): The query to find a user.
    Returns:
        dict: The user document, or None if no user is found.
    """
    user_document = await mongo.db['users'].find_one(query, {'_id': 0})
    return user_document


async def add_urls_to_medicine(url: dict):
    """
    Inserts a URL document into the medicine URLs collection.
    Args:
        url (dict): The URL document to insert.
    """
    result = await mongo.medicine_collection.insert_one(url)
    logger.info(f"URL inserted successfully with id {result.inserted_id}")

