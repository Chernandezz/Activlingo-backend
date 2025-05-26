from fastapi import FastAPI
from routes.chat import chat_router
from routes.message import message_router
from routes.analysis import analysis_router
from fastapi.middleware.cors import CORSMiddleware
from routes.user_dictionary import user_dictionary_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/chats", tags=["chats"])
app.include_router(message_router, prefix="/messages", tags=["messages"])
app.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
app.include_router(user_dictionary_router, prefix="/dictionary", tags=["dictionary"])


@app.get("/")
def read_root():
    return {"Hello": "World"}