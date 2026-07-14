import httpx
import re
import json
import random
from . import db

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
]

def parse_yt_username(link: str) -> str:
    link = (link or "").strip()
    if not link: return ""
    match = re.search(r'@([a-zA-Z0-9_.-]+)', link)
    if match: return match.group(1)
    if "youtube.com/channel/" in link:
        return link.split("youtube.com/channel/")[1].split("/")[0]
    if "youtube.com/c/" in link:
        return link.split("youtube.com/c/")[1].split("/")[0]
    if "youtube.com/user/" in link:
        return link.split("youtube.com/user/")[1].split("/")[0]
    return link.split("/")[-1]

async def fetch_yt_info(username: str) -> dict:
    url = f"https://www.youtube.com/@{username}" if not username.startswith("UC") else f"https://www.youtube.com/channel/{username}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    proxy = db.get_random_proxy()
    result = {
        "username": username,
        "subscribers": 0,
        "videos": 0,
        "avatar": "",
    }
    
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, proxy=proxy) as client:
            r = await client.get(url, headers=headers)
            html = r.text
            
            # Find ytInitialData
            match = re.search(r'var ytInitialData = (\{.*?\});</script>', html)
            if match:
                data = json.loads(match.group(1))
                try:
                    header = data["header"]["c4TabbedHeaderRenderer"]
                    result["username"] = header.get("title", username)
                    
                    subs_str = header.get("subscriberCountText", {}).get("simpleText", "0")
                    # "1.5M subscribers" -> parse
                    subs_str = subs_str.split(" ")[0]
                    result["subscribers"] = _parse_num(subs_str)
                    
                    vids_str = header.get("videosCountText", {}).get("runs", [{}])[0].get("text", "0")
                    result["videos"] = _parse_num(vids_str)
                    
                    try:
                        result["avatar"] = header["avatar"]["thumbnails"][-1]["url"]
                    except: pass
                except Exception as e:
                    pass
    except Exception as e:
        if proxy: db.mark_proxy_failed(proxy)
        raise Exception("Không thể kết nối đến YouTube hoặc IP bị chặn")
        
    return result

def _parse_num(s: str) -> int:
    s = s.upper().replace(',', '').replace('.', '')
    if 'K' in s: return int(float(s.replace('K', '')) * 1000)
    if 'M' in s: return int(float(s.replace('M', '')) * 1000000)
    if 'B' in s: return int(float(s.replace('B', '')) * 1000000000)
    try: return int(re.sub(r'[^0-9]', '', s))
    except: return 0

def parse_yt_video_id(link: str) -> str:
    link = (link or "").strip()
    if not link: return ""
    match = re.search(r'(?:v=|/v/|youtu\.be/|/embed/|/shorts/)([a-zA-Z0-9_-]{11})', link)
    if match: return match.group(1)
    return link

async def fetch_yt_video_info(url: str) -> dict:
    video_id = parse_yt_video_id(url)
    if not video_id:
        raise Exception("Không tìm thấy Video ID")
        
    fetch_url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    proxy = db.get_random_proxy()
    result = {
        "id": video_id,
        "views": 0,
        "likes": 0,
        "comments": 0,
        "desc": f"YouTube Video: {video_id}",
        "cover": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "username": "",
    }
    
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True, proxy=proxy) as client:
            r = await client.get(fetch_url, headers=headers)
            html = r.text
            
            match = re.search(r'var ytInitialData = (\{.*?\});</script>', html)
            if match:
                data = json.loads(match.group(1))
                try:
                    contents = data["contents"]["twoColumnWatchNextResults"]["results"]["results"]["contents"]
                    video_primary = contents[0]["videoPrimaryInfoRenderer"]
                    video_secondary = contents[1]["videoSecondaryInfoRenderer"]
                    
                    result["desc"] = video_primary.get("title", {}).get("runs", [{}])[0].get("text", result["desc"])
                    
                    try:
                        views_str = video_primary["viewCount"]["videoViewCountRenderer"]["viewCount"]["simpleText"]
                        result["views"] = _parse_num(views_str)
                    except: pass
                    
                    try:
                        likes_str = video_primary["videoActions"]["menuRenderer"]["topLevelButtons"][0]["segmentedLikeDislikeButtonViewModel"]["likeButtonViewModel"]["likeButtonViewModel"]["toggleButtonViewModel"]["toggleButtonViewModel"]["defaultButtonViewModel"]["buttonViewModel"]["title"]
                        result["likes"] = _parse_num(likes_str)
                    except: pass
                    
                    try:
                        result["username"] = video_secondary["owner"]["videoOwnerRenderer"]["title"]["runs"][0]["text"]
                    except: pass
                    
                except Exception as e:
                    pass
            else:
                # Fallback to regex
                views_match = re.search(r'"viewCount":"(\d+)"', html)
                if views_match: result["views"] = int(views_match.group(1))
                
                title_match = re.search(r'<title>(.*?)</title>', html)
                if title_match: result["desc"] = title_match.group(1).replace(" - YouTube", "")
                
    except Exception as e:
        if proxy: db.mark_proxy_failed(proxy)
        raise Exception("Không thể lấy dữ liệu video YouTube")
        
    return result

def build_yt_caption(info: dict) -> str:
    return (
        f"╭─── <b>[ KẾT QUẢ YOUTUBE ]</b> ───╮\n"
        f"│\n"
        f"├ 👤 <b>Kênh:</b> <code>{info['username']}</code>\n"
        f"├ 👥 <b>Đăng ký:</b> {info['subscribers']:,}\n"
        f"├ 🎥 <b>Video:</b> {info['videos']:,}\n"
        f"│\n"
        f"╰──────────────────────────╯\n\n"
        f"<i>💡 Gõ /trackyt {info['username']} để tự động theo dõi kênh này.</i>"
    )

def build_yt_video_caption(info: dict) -> str:
    return (
        f"╭─── <b>[ KẾT QUẢ VIDEO YOUTUBE ]</b> ───╮\n"
        f"│\n"
        f"├ 👤 <b>Kênh:</b> {info['username']}\n"
        f"├ 👁️ <b>Lượt xem:</b> {info['views']:,}\n"
        f"├ 👍 <b>Lượt thích:</b> {info['likes']:,}\n"
        f"│\n"
        f"╰───────────────────────────────╯\n\n"
        f"<i>💡 Gõ /trackvyt {info['id']} để tự động theo dõi video này.</i>"
    )
