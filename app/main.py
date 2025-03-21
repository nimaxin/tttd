import os
from pathlib import Path
from sqlite3 import OperationalError

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, status
from opentele.api import UseCurrentSession
from opentele.td import APIData, TDesktop
from pydantic import BaseModel
from telethon import TelegramClient

app = FastAPI()


load_dotenv()

sessions_dir = Path(os.getenv("SESSIONS_DIR"))
tdatas_dir = Path(os.getenv("TDATAS_DIR"))
tdatas_dir.mkdir(parents=True, exist_ok=True)


class TDesktopCreate(BaseModel):
    session: str
    api_id: int
    api_hash: str
    device_model: str
    system_version: str
    app_version: str
    lang_code: str
    system_lang_code: str
    lang_pack: str


class TDesktopRead(BaseModel):
    tdata_dir: str


@app.post("/telethon-to-tdesktop", status_code=status.HTTP_201_CREATED)
async def telethon_to_tdesktop(tdesktop_create: TDesktopCreate):
    session_path = Path(sessions_dir.joinpath(tdesktop_create.session + ".session"))
    if not session_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
        )

    telegram_client = TelegramClient(
        session_path,
        api_id=tdesktop_create.api_id,
        api_hash=tdesktop_create.api_hash,
    )
    try:
        tdesktop = await TDesktop.FromTelethon(
            telegram_client,
            flag=UseCurrentSession,
            api=APIData(
                api_id=tdesktop_create.api_id,
                api_hash=tdesktop_create.api_hash,
                device_model=tdesktop_create.device_model,
                system_version=tdesktop_create.system_version,
                app_version=tdesktop_create.app_version,
                lang_code=tdesktop_create.lang_code,
                system_lang_code=tdesktop_create.system_lang_code,
                lang_pack=tdesktop_create.lang_pack,
            ),
        )
    except OperationalError:
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail="session in use")
    tdata_dir = tdatas_dir.joinpath(tdesktop_create.session)
    tdata_dir.mkdir(parents=True, exist_ok=True)
    tdata_dir_tdata = tdata_dir.joinpath("tdata")
    if tdata_dir_tdata.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="tdata already exists"
        )
    tdesktop.SaveTData(tdata_dir_tdata)
    return {"tdata_dir": tdata_dir}
