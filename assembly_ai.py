import os

import assemblyai as aai

aai.settings.api_key = os.getenv("ASSEMBLY_AI")

transcriber = aai.Transcriber()
config = aai.TranscriptionConfig(speaker_labels=True)


def transcribe(video_url: str):
    transcription = transcriber.transcribe(video_url, config=config)
    paragraphs = transcription.get_paragraphs()
    return "\n\n".join([p.text for p in paragraphs])
