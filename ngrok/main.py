from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/", response_class=JSONResponse)
async def read_root():
  return {"message": "Hello World!"}
