from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class BoostRequest(BaseModel):
    business_name: str
    location: str

@app.get('/')
def root():
    return {"status":"ok"}

@app.post('/boost')
def boost(data: BoostRequest):
    return {
        'message': f"Boosting {data.business_name} in {data.location}",
        'data': data
    }