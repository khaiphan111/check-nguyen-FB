import json, re, logging, time
from typing import Optional
import httpx

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.tiktok.com/",
}


def parse_username(raw: str) -> Optional[str]:
    raw = raw.strip().rstrip("/")
    m = re.search(r"tiktok\.com/@([\w.]+)", raw)
    if m: return m.group(1)
    if raw.startswith("@"): return raw[1:]
    if raw.startswith("http"): return None
    return raw if re.match(r"^[\w.]+$", raw) else None


def parse_video_id(raw: str) -> Optional[str]:
    """Trich xuat video ID tu URL hoac so nguyen."""
    raw = raw.strip().rstrip("/")
    # https://www.tiktok.com/@user/video/1234567890
    m = re.search(r"/video/(\d+)", raw)
    if m: return m.group(1)
    # Truong hop la ID thuan tuy
    if re.match(r"^\d+$", raw): return raw
    return None


def fmt_num(n) -> str:
    try: n = int(n)
    except: return "N/A"
    if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return f"{n:,}"


def _extract_page_data(html: str) -> dict:
    pattern = r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>'
    m = re.search(pattern, html, re.DOTALL)
    if not m:
        m2 = re.search(r"window\['SIGI_STATE'\]\s*=\s*(\{.*?\});\s*window\[", html, re.DOTALL)
        if m2: return json.loads(m2.group(1))
        raise ValueError("TikTok dang chan request. Thu lai sau.")
    return json.loads(m.group(1))


async def _get_html(url: str) -> str:
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=20) as client:
        resp = await client.get(url)
        if resp.status_code == 404:
            raise ValueError(f"Khong tim thay: {url}")
        resp.raise_for_status()
        return resp.text


# ─── FETCH USER INFO ──────────────────────────────────────────
async def fetch_tiktok_info(username: str) -> dict:
    html = await _get_html(f"https://www.tiktok.com/@{username}")
    data = _extract_page_data(html)

    ud = (
        data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-detail", {}).get("userInfo", {})
        or data.get("UserPage", {}).get("userInfo", {})
    )
    user  = ud.get("user",  {})
    stats = ud.get("stats", {})
    if not user:
        raise ValueError(f"Tai khoan @{username} khong ton tai.")

    info = {
        "uid":       user.get("id", "N/A"),
        "username":  user.get("uniqueId", username),
        "nickname":  user.get("nickname", ""),
        "bio":       user.get("signature", ""),
        "verified":  user.get("verified", False),
        "private":   user.get("privateAccount", False),
        "region":    user.get("region", ""),
        "avatar":    user.get("avatarLarger") or user.get("avatarMedium") or "",
        "followers": stats.get("followerCount", 0),
        "following": stats.get("followingCount", 0),
        "hearts":    stats.get("heartCount", 0),
        "videos":    stats.get("videoCount", 0),
        "friends":   stats.get("friendCount", 0),
    }

    # Latest video
    items = (data.get("__DEFAULT_SCOPE__", {}).get("webapp.user-post", {}).get("itemList", [])
             or list((data.get("ItemModule") or {}).values()))
    info["latest_video"] = _extract_video_item(items[0], info["username"]) if items else None
    return info


# ─── FETCH VIDEO INFO ─────────────────────────────────────────
def _extract_video_item(v: dict, username: str = "") -> dict:
    vid_id   = v.get("id", "")
    author   = (v.get("author") or {}).get("uniqueId", username)
    desc     = v.get("desc", "")
    vobj     = v.get("video") or {}
    cover    = vobj.get("cover") or vobj.get("originCover") or vobj.get("dynamicCover") or ""
    duration = vobj.get("duration", 0)
    s        = v.get("stats") or v.get("statsV2") or {}
    return {
        "id":       vid_id,
        "username": author,
        "desc":     desc,
        "cover":    cover,
        "duration": duration,
        "url":      f"https://www.tiktok.com/@{author}/video/{vid_id}" if vid_id else "",
        "plays":    int(s.get("playCount") or s.get("VVCount") or 0),
        "likes":    int(s.get("diggCount") or 0),
        "comments": int(s.get("commentCount") or 0),
        "shares":   int(s.get("shareCount") or 0),
        "favorites": int(s.get("collectCount") or 0),
    }


async def fetch_video_info(video_url: str) -> dict:
    """
    Lay thong tin + stats cua 1 video cu the tu URL.
    video_url: https://www.tiktok.com/@user/video/12345...
    """
    html = await _get_html(video_url)
    data = _extract_page_data(html)

    # Thu cau truc video detail
    scope = data.get("__DEFAULT_SCOPE__", {})
    vd = scope.get("webapp.video-detail", {})
    item_struct = (
        vd.get("itemInfo", {}).get("itemStruct")
        or vd.get("itemList", [None])[0]
        or None
    )

    if not item_struct:
        # Fallback: tim trong ItemModule
        item_module = data.get("ItemModule", {})
        if item_module:
            item_struct = list(item_module.values())[0]

    if not item_struct:
        raise ValueError("Khong the lay thong tin video. TikTok co the da can VIDEO_ID hop le.")

    vid_id = parse_video_id(video_url) or item_struct.get("id", "")
    author = (item_struct.get("author") or {}).get("uniqueId", "")
    return _extract_video_item(item_struct, author)


# ─── CAPTIONS ────────────────────────────────────────────────
def build_info_caption(info: dict) -> str:
    verified = "Da xac minh ✅" if info["verified"] else "Chua xac minh ❌"
    privacy  = "🔒 Rieng tu"   if info["private"]  else "🌐 Cong khai"
    lines = [
        "╔══════════════════════════╗",
        "  📱  <b>CHECK THÔNG TIN TIKTOK V2</b>",
        "╚══════════════════════════╝",
        "",
        f"👤 Username  : <b>@{info['username']}</b>",
        f"📛 Tên hiển thị: <b>{info['nickname']}</b>",
        f"🆔 UID       : <code>{info['uid']}</code>",
        f"🌍 Quốc gia  : <b>{info['region'] or 'N/A'}</b>",
        f"🔑 Xác minh  : {verified}",
        f"🔐 Trang cá nhân: {privacy}",
        "",
        "━━━━━━ 📊 THỐNG KÊ ━━━━━━",
        f"👥 Followers : <b>{fmt_num(info['followers'])}</b>",
        f"➡️  Following : <b>{fmt_num(info['following'])}</b>",
        f"❤️  Likes     : <b>{fmt_num(info['hearts'])}</b>",
        f"🎬 Videos    : <b>{fmt_num(info['videos'])}</b>",
    ]
    if info.get("bio"):
        lines += ["", f"📝 Bio:\n<i>{info['bio']}</i>"]
    lv = info.get("latest_video")
    if lv and lv.get("id"):
        d = (lv['desc'][:80] + "...") if len(lv.get("desc","")) > 80 else lv.get("desc","")
        lines += [
            "", "━━━━ 🎬 VIDEO MỚI NHẤT ━━━━",
            f"📝 {d or 'Khong co mo ta'}",
            f"▶️ {fmt_num(lv['plays'])} views  ❤️ {fmt_num(lv['likes'])} likes  💬 {fmt_num(lv['comments'])} cmt  🔁 {fmt_num(lv['shares'])} shares  ⭐ {fmt_num(lv.get('favorites', 0))} favs",
            f"🔗 <a href=\"{lv['url']}\">Xem video</a>",
        ]
    lines += [
        "",
        f"🔗 <a href=\"https://www.tiktok.com/@{info['username']}\">➜ Xem trang TikTok</a>",
        "", "──────────────────────────",
        "🤖 <i>TikTok Checker V2 by @khaikhai998</i>",
    ]
    return "\n".join(lines)


def build_video_caption(v: dict, old: dict = None) -> str:
    """Caption thong bao tuong tac video."""
    desc = (v["desc"][:100] + "...") if len(v.get("desc","")) > 100 else v.get("desc","Khong co mo ta")
    lines = [
        "📊 <b>CẬP NHẬT VIDEO TIKTOK</b>",
        "",
        f"📱 <b>@{v['username']}</b>",
        f"📝 {desc}",
        "",
        "━━━━ 📈 THỐNG KÊ TƯƠNG TÁC ━━━━",
        f"▶️ Lượt xem  : <b>{fmt_num(v['plays'])}</b>",
        f"❤️  Likes     : <b>{fmt_num(v['likes'])}</b>",
        f"💬 Bình luận : <b>{fmt_num(v['comments'])}</b>",
        f"🔁 Chia sẻ   : <b>{fmt_num(v['shares'])}</b>",
        f"⭐ Yêu thích : <b>{fmt_num(v['favorites'])}</b>",
    ]
    if old:
        dp = v["plays"]    - old.get("plays", 0)
        dl = v["likes"]    - old.get("likes", 0)
        dc = v["comments"] - old.get("comments", 0)
        ds = v["shares"]   - old.get("shares", 0)
        df = v["favorites"] - old.get("favorites", 0)
        def d2s(x): return (f"+{x:,}" if x > 0 else f"{x:,}") if x != 0 else "—"
        lines += [
            "", "━━━━ 📊 THAY ĐỔI ━━━━",
            f"▶️ Views    : <b>{d2s(dp)}</b>",
            f"❤️  Likes   : <b>{d2s(dl)}</b>",
            f"💬 Comments: <b>{d2s(dc)}</b>",
            f"🔁 Shares  : <b>{d2s(ds)}</b>",
            f"⭐ Favorites: <b>{d2s(df)}</b>",
        ]
    now_str = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())
    lines += [
        "", f"⏰ Thời gian: <b>{now_str}</b>",
        "", f"🔗 <a href=\"{v['url']}\">▶ Xem video ngay</a>",
        "", "🤖 <i>TikTok Checker V2 by @khaikhai998</i>",
    ]
    return "\n".join(lines)
