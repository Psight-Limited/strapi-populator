import asyncio
import os

import aiohttp
import assemblyai as aai

aai.settings.api_key = os.getenv("ASSEMBLY_AI")
transcriber = aai.Transcriber()
aai.Transcript.get_redacted_audio_url
config = aai.TranscriptionConfig(speaker_labels=True)
_get_all_transcripts_cache = None
_fetch_lock = asyncio.Lock()


async def transcribe(video_url: str):
    try:
        transcript = await find_video_url_in_completed(video_url)
        if not transcript:
            print(f"transcribing")
            transcript = await asyncio.wrap_future(
                transcriber.transcribe_async(video_url, config=config)
            )
            print(f"done transcribing")
        paragraphs = transcript.get_paragraphs()
        return "\n\n".join([p.text for p in paragraphs])
    except Exception as e:
        print(e)
        raise


async def find_video_url_in_completed(video_url: str):
    for t in await get_all_transcripts():
        if t["audio_url"] == video_url:
            return await asyncio.wrap_future(aai.Transcript.get_by_id_async(t["id"]))


async def get_all_transcripts():
    async with _fetch_lock:
        global _get_all_transcripts_cache
        if _get_all_transcripts_cache is not None:
            return _get_all_transcripts_cache

        url = "https://api.assemblyai.com/v2/transcript?limit=200&status=completed"

        async def fetch(url):
            async with aiohttp.ClientSession() as session:
                try:
                    response = await session.get(
                        url=url,
                        headers={"Authorization": aai.settings.api_key},
                    )
                    data = await response.json()
                    return data
                except Exception as e:
                    print(f"Failed to fetch data: {e}")
                    return None

        results = []
        while url:
            data = await fetch(url)
            if data:
                results.extend(data["transcripts"])
                url = data["page_details"].get("prev_url")
                print("Next URL:", url)
            else:
                break
        _get_all_transcripts_cache = results
        return results
