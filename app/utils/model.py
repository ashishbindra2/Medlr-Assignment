from pydantic import BaseModel, Field,EmailStr


class DataModel(BaseModel):
    user_id: str = Field(..., min_length=1, description="User ID must not be empty")
    name: str = Field(..., min_length=2, description="Name must not be empty")
    email: EmailStr = Field(..., min_length=5, description="Email must not be empty")


class JSONDataRequest(BaseModel):
    collection_name: str = ''
    data: DataModel = None



