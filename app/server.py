import asyncio
import io
import threading
from typing import Optional

import soundfile as sf
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.model_manager import ModelManager
from app.voice_profiles import VoiceProfileManager


class TTSRequest(BaseModel):
    text: str
    speaker: Optional[str] = None
    language: Optional[str] = None
    instruct: Optional[str] = None
    ref_audio: Optional[str] = None
    ref_text: Optional[str] = None


class SetActiveProfileRequest(BaseModel):
    name: str


def create_app(model_manager: ModelManager, profile_manager: VoiceProfileManager,
               config_data: dict) -> FastAPI:
    app = FastAPI(title="BetterTTS")

    def _blocking_generate(req: TTSRequest) -> bytes:
        """Run the heavy TTS generation in a thread — returns raw WAV bytes."""

        # Use app config as defaults — request values override if provided
        speaker = req.speaker if req.speaker is not None else config_data.get("speaker", "Ryan")
        language = req.language if req.language is not None else config_data.get("language", "English")
        instruct = req.instruct if req.instruct is not None else config_data.get("instruct", "")

        print(f"[BetterTTS Server] TTS request: text='{req.text[:80]}', speaker={speaker}, lang={language}, instruct='{instruct[:60] if instruct else ''}'")
        print(f"[BetterTTS Server] Config state: speaker={config_data.get('speaker')}, lang={config_data.get('language')}, instruct='{config_data.get('instruct', '')[:60]}'")
        print(f"[BetterTTS Server] Request fields: speaker={req.speaker}, lang={req.language}, instruct={req.instruct}")

        ref_audio = req.ref_audio or ""
        ref_text = req.ref_text or ""

        if not ref_audio and model_manager.current_variant:
            if model_manager.current_variant.supports_cloning:
                active = profile_manager.active_profile
                if active:
                    ref_audio = profile_manager.get_audio_path(active)
                    ref_text = active.transcript

        wav, sr = model_manager.generate(
            text=req.text,
            speaker=speaker,
            language=language,
            instruct=instruct,
            ref_audio=ref_audio,
            ref_text=ref_text,
        )

        buf = io.BytesIO()
        sf.write(buf, wav, sr, format="WAV", subtype="PCM_16")
        wav_bytes = buf.getvalue()

        print(f"[BetterTTS Server] Sending WAV: {len(wav_bytes)} bytes, {len(wav)} samples, {len(wav)/sr:.2f}s")
        return wav_bytes

    @app.post("/tts")
    async def tts_endpoint(req: TTSRequest):
        try:
            loop = asyncio.get_event_loop()
            wav_bytes = await loop.run_in_executor(None, _blocking_generate, req)

            return Response(
                content=wav_bytes,
                media_type="audio/wav",
                headers={
                    "Content-Disposition": "attachment; filename=tts_output.wav",
                },
            )
        except Exception as e:
            print(f"[BetterTTS Server] ERROR: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "model_state": model_manager.state.value,
            "model": model_manager.current_variant.display_name if model_manager.current_variant else None,
        }

    @app.get("/settings")
    async def get_settings():
        return {
            "speaker": config_data.get("speaker", "Ryan"),
            "language": config_data.get("language", "English"),
            "instruct": config_data.get("instruct", ""),
            "port": config_data.get("port", 7861),
        }

    @app.get("/profiles")
    async def list_profiles():
        return {
            "profiles": [
                {"name": p.name, "audio_file": p.audio_file, "transcript": p.transcript}
                for p in profile_manager.profiles
            ],
            "active_profile": profile_manager.active_name,
        }

    @app.post("/profiles/active")
    async def set_active_profile(req: SetActiveProfileRequest):
        try:
            profile_manager.set_active(req.name)
            return {"active_profile": req.name}
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    return app


class ServerManager:
    def __init__(self, model_manager: ModelManager, profile_manager: VoiceProfileManager,
                 config_data: dict, port: int = 7861):
        self.model_manager = model_manager
        self.profile_manager = profile_manager
        self.config_data = config_data
        self.port = port
        self._server: Optional[uvicorn.Server] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.is_running:
            return
        app = create_app(self.model_manager, self.profile_manager, self.config_data)
        config = uvicorn.Config(
            app, host="0.0.0.0", port=self.port, log_level="warning",
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True, name="uvicorn")
        self._thread.start()

    def stop(self):
        if self._server:
            self._server.should_exit = True
            self._thread = None
            self._server = None

    def set_port(self, port: int):
        was_running = self.is_running
        if was_running:
            self.stop()
        self.port = port
        if was_running:
            self.start()
