import streamlit as st
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from googleapiclient.discovery import build
import pandas as pd

API_KEY = st.secrets["api"]["key"]
YOUTUBE = build("youtube", "v3", developerKey=API_KEY)

def extract_video_id(url):
    parsed = urlparse(url)
    if 'youtu.be' in parsed.netloc:
        return parsed.path.strip('/')
    if 'youtube.com' in parsed.netloc:
        qs = parse_qs(parsed.query)
        return qs.get('v', [None])[0]
    return None

def extract_channel_id(url):
    if "/channel/" in url:
        return url.split("/channel/")[1].split("/")[0]
    path = urlparse(url).path.strip("/")
    if path.startswith("user/") or path.startswith("c/") or path.startswith("@"):
        identifier = path.split("/")[1] if "/" in path else path
        import streamlit as st
st.write("🧪 video_ids chunk:", chunk)
        response = YOUTUBE.search().list(part="snippet", q=identifier, type="channel", maxResults=1).execute()
        items = response.get("items", [])
        if items:
            return items[0]["snippet"]["channelId"]
    return None

def get_video_info_batch(video_ids):
    results = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        response = YOUTUBE.videos().list(part="snippet,statistics", id=",".join(chunk)).execute()
        for item in response.get("items", []):
            results.append({
                "ID видео": item["id"],
                "Название канала": item["snippet"]["channelTitle"],
                "Название видео": item["snippet"]["title"],
                "Описание": item["snippet"].get("description", ""),
                "Просмотры": item["statistics"].get("viewCount", "0"),
                "Дата сбора": datetime.now().strftime('%Y-%m-%d')
            })
    return results
