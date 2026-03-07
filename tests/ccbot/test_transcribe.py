"""Unit tests for transcribe — voice-to-text via OpenAI API."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from ccbot import transcribe


@pytest.fixture(autouse=True)
def _reset_client():
    """Ensure each test starts with a fresh client."""
    transcribe._client = None
    yield
    transcribe._client = None


@pytest.fixture
def mock_config():
    """Patch config with test values for OpenAI backend."""
    with patch.object(transcribe, "config") as cfg:
        cfg.openai_api_key = "sk-test-key"
        cfg.openai_base_url = "https://api.openai.com/v1"
        cfg.whisper_backend = "openai"
        yield cfg


@pytest.fixture
def ogg_file(tmp_path):
    """Create a temporary OGG file with fake data."""
    f = tmp_path / "test.ogg"
    f.write_bytes(b"fake-ogg-data")
    return f


def _mock_response(*, json_data: dict, status_code: int = 200) -> httpx.Response:
    """Build a fake httpx.Response."""
    request = httpx.Request("POST", "https://api.openai.com/v1/audio/transcriptions")
    resp = httpx.Response(status_code=status_code, json=json_data, request=request)
    return resp


class TestTranscribeOpenAI:
    @pytest.mark.asyncio
    async def test_success(self, mock_config, ogg_file):
        resp = _mock_response(json_data={"text": "Hello world"})
        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=resp
        ) as mock_post:
            result = await transcribe.transcribe(ogg_file)

        assert result == "Hello world"
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "Bearer sk-test-key" in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_empty_transcription_raises(self, mock_config, ogg_file):
        resp = _mock_response(json_data={"text": ""})
        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=resp
        ):
            with pytest.raises(
                transcribe.TranscriptionError, match="Empty transcription"
            ):
                await transcribe.transcribe(ogg_file)

    @pytest.mark.asyncio
    async def test_whitespace_only_raises(self, mock_config, ogg_file):
        resp = _mock_response(json_data={"text": "   "})
        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=resp
        ):
            with pytest.raises(
                transcribe.TranscriptionError, match="Empty transcription"
            ):
                await transcribe.transcribe(ogg_file)

    @pytest.mark.asyncio
    async def test_missing_text_field_raises(self, mock_config, ogg_file):
        resp = _mock_response(json_data={"result": "something"})
        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=resp
        ):
            with pytest.raises(
                transcribe.TranscriptionError, match="Empty transcription"
            ):
                await transcribe.transcribe(ogg_file)

    @pytest.mark.asyncio
    async def test_api_error_raises(self, mock_config, ogg_file):
        resp = _mock_response(json_data={"error": "Unauthorized"}, status_code=401)
        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=resp
        ):
            with pytest.raises(httpx.HTTPStatusError):
                await transcribe.transcribe(ogg_file)

    @pytest.mark.asyncio
    async def test_custom_base_url(self, mock_config, ogg_file):
        mock_config.openai_base_url = "https://proxy.example.com/v1"
        resp = _mock_response(json_data={"text": "Transcribed"})
        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=resp
        ) as mock_post:
            result = await transcribe.transcribe(ogg_file)

        assert result == "Transcribed"
        url_arg = mock_post.call_args[0][0]
        assert url_arg == "https://proxy.example.com/v1/audio/transcriptions"

    @pytest.mark.asyncio
    async def test_base_url_trailing_slash_stripped(self, mock_config, ogg_file):
        mock_config.openai_base_url = "https://proxy.example.com/v1/"
        resp = _mock_response(json_data={"text": "OK"})
        with patch.object(
            httpx.AsyncClient, "post", new_callable=AsyncMock, return_value=resp
        ) as mock_post:
            await transcribe.transcribe(ogg_file)

        url_arg = mock_post.call_args[0][0]
        assert url_arg == "https://proxy.example.com/v1/audio/transcriptions"

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_disabled(self, mock_config, ogg_file):
        mock_config.openai_api_key = ""
        with pytest.raises(transcribe.TranscriptionDisabled, match="OPENAI_API_KEY"):
            await transcribe.transcribe(ogg_file)


class TestTranscribeDisabled:
    @pytest.mark.asyncio
    async def test_off_backend_raises(self, ogg_file):
        with patch.object(transcribe, "config") as cfg:
            cfg.whisper_backend = "off"
            with pytest.raises(transcribe.TranscriptionDisabled, match="disabled"):
                await transcribe.transcribe(ogg_file)


class TestCloseClient:
    @pytest.mark.asyncio
    async def test_close_client_when_open(self):
        transcribe._client = httpx.AsyncClient()
        assert transcribe._client is not None
        await transcribe.close_client()
        assert transcribe._client is None

    @pytest.mark.asyncio
    async def test_close_client_when_none(self):
        assert transcribe._client is None
        await transcribe.close_client()
        assert transcribe._client is None
