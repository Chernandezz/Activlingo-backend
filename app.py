from fastapi import Depends, FastAPI
from routes.user_router import user_router
from routes.chat import chat_router
from routes.message import message_router
from routes.analysis import analysis_router
from fastapi.middleware.cors import CORSMiddleware
from routes.user_dictionary import user_dictionary_router
from routes.auth import auth_router
from routes.tasks import tasks_router
from dependencies.access import check_access

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://147.182.130.162" ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/chats", tags=["chats"], dependencies=[Depends(check_access)] )
app.include_router(user_router, prefix="/user", tags=["user"])
app.include_router(message_router, prefix="/messages", tags=["messages"])
app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
app.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
app.include_router(user_dictionary_router, prefix="/dictionary", tags=["dictionary"])
app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/")
def read_root():
    return {"Hello": "World"}