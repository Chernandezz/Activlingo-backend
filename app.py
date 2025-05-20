from fastapi import FastAPI
from routes.chat import chat_router
from routes.message import message_router
from routes.user import user_router

app = FastAPI()

app.include_router(chat_router, prefix="/chats", tags=["chats"])
app.include_router(message_router, prefix="/messages", tags=["messages"])
app.include_router(user_router, prefix="/users", tags=["users"])

@app.get("/")
def read_root():
    return {"Hello": "World"}