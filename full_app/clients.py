import os
from dataclasses import dataclass

from dotenv import load_dotenv
from googleapiclient.discovery import build
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi


@dataclass
class Clients:
    youtube: object
    openai: OpenAI
    transcript: YouTubeTranscriptApi


def build_clients() -> Clients:
    load_dotenv()
    youtube_key = os.getenv("YOUTUBE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not youtube_key:
        raise ValueError("YOUTUBE_API_KEY가 .env에 없습니다.")
    if not openai_key:
        raise ValueError("OPENAI_API_KEY가 .env에 없습니다.")

    return Clients(
        youtube=build("youtube", "v3", developerKey=youtube_key),
        openai=OpenAI(api_key=openai_key),
        transcript=YouTubeTranscriptApi(),
    )
