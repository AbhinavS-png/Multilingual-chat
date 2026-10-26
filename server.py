import asyncio
import datetime
import os
import uuid
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from translator import ChatTranslator, SUPPORTED_LANGUAGES, get_language_display_name

app = FastAPI(title="Sarvam Multilingual WhatsApp Chat")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

translator = ChatTranslator()

# Ensure static folder exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


class UserSession:
    def __init__(self, websocket: WebSocket, user_id: str, username: str, language: str, room_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.username = username
        self.language = language
        self.room_id = room_id


class RoomManager:
    def __init__(self):
        # room_id -> list of UserSession
        self.rooms: Dict[str, List[UserSession]] = {}

    def get_room(self, room_id: str) -> List[UserSession]:
        return self.rooms.get(room_id, [])

    async def connect(self, session: UserSession):
        await session.websocket.accept()
        if session.room_id not in self.rooms:
            self.rooms[session.room_id] = []
        self.rooms[session.room_id].append(session)
        await self.broadcast_room_state(session.room_id, f"{session.username} joined the chat")

    def disconnect(self, session: UserSession):
        if session.room_id in self.rooms:
            if session in self.rooms[session.room_id]:
                self.rooms[session.room_id].remove(session)
            if not self.rooms[session.room_id]:
                del self.rooms[session.room_id]

    async def broadcast_room_state(self, room_id: str, notification: Optional[str] = None):
        sessions = self.get_room(room_id)
        users = [
            {
                "user_id": s.user_id,
                "username": s.username,
                "language": s.language,
                "language_name": SUPPORTED_LANGUAGES.get(s.language, s.language),
            }
            for s in sessions
        ]
        payload = {
            "type": "room_state",
            "users": users,
            "notification": notification,
            "timestamp": datetime.datetime.now().strftime("%I:%M %p"),
        }
        for s in list(sessions):
            try:
                await s.websocket.send_json(payload)
            except Exception:
                pass

    async def broadcast_message(self, sender: UserSession, original_text: str):
        sessions = self.get_room(sender.room_id)
        if not sessions:
            return

        msg_id = str(uuid.uuid4())
        time_str = datetime.datetime.now().strftime("%I:%M %p")

        # 1. Identify language using Sarvam AI
        source_lang, script = translator.detect_language(original_text)
        source_lang_name = get_language_display_name(source_lang, script)

        # 2. Collect unique target languages needed
        needed_languages = {s.language for s in sessions}

        # 3. Translate for needed languages (using in-memory cache)
        translations: Dict[str, str] = {}
        for target_lang in needed_languages:
            try:
                translations[target_lang] = translator.translate_message(
                    text=original_text,
                    target_language_code=target_lang,
                    source_language_code=source_lang,
                    script_code=script,
                )
            except Exception as e:
                translations[target_lang] = original_text

        # 4. Dispatch personalized payload to each user
        for s in list(sessions):
            is_self = s.user_id == sender.user_id
            user_translation = translations.get(s.language, original_text)

            payload = {
                "type": "chat_message",
                "message_id": msg_id,
                "sender_id": sender.user_id,
                "sender_name": sender.username,
                "original_text": original_text,
                "translated_text": user_translation,
                "source_language_code": source_lang,
                "source_language_name": source_lang_name,
                "target_language_code": s.language,
                "target_language_name": SUPPORTED_LANGUAGES.get(s.language, s.language),
                "script": script,
                "timestamp": time_str,
                "is_self": is_self,
            }
            try:
                await s.websocket.send_json(payload)
            except Exception:
                pass


manager = RoomManager()


@app.get("/")
async def get_index():
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)


@app.get("/api/languages")
async def get_languages():
    return [
        {"code": code, "name": name}
        for code, name in SUPPORTED_LANGUAGES.items()
    ]


class TranslateRequest(BaseModel):
    text: str
    target_language: str
    source_language: Optional[str] = None


@app.post("/api/translate")
async def translate_text(req: TranslateRequest):
    translated = translator.translate_message(
        text=req.text,
        target_language_code=req.target_language,
        source_language_code=req.source_language,
    )
    return {"translated_text": translated}


@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    # Query parameters
    user_id = websocket.query_params.get("user_id") or str(uuid.uuid4())[:8]
    username = websocket.query_params.get("username") or f"User_{user_id[:4]}"
    language = websocket.query_params.get("language") or "hi-IN"

    session = UserSession(
        websocket=websocket,
        user_id=user_id,
        username=username,
        language=language,
        room_id=room_id,
    )

    await manager.connect(session)

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("type")

            if action == "chat_message":
                text = (data.get("text") or "").strip()
                if text:
                    await manager.broadcast_message(session, text)

            elif action == "change_language":
                new_lang = data.get("language")
                if new_lang in SUPPORTED_LANGUAGES:
                    session.language = new_lang
                    await manager.broadcast_room_state(session.room_id)

    except WebSocketDisconnect:
        manager.disconnect(session)
        await manager.broadcast_room_state(session.room_id, f"{session.username} left the chat")
    except Exception as e:
        manager.disconnect(session)
        await manager.broadcast_room_state(session.room_id)
