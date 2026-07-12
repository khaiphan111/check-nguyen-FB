# FB Live/Die Checker — Tác giả: @nhanxp | Hỗ trợ: Telegram/Facebook nhanxp
import httpx
import random

from . import config, db


USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 10; SM-G981B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.162 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 12; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.58 Mobile Safari/537.36",
]

import re

def extract_uid(link: str) -> str:
    link = (link or "").strip()
    if not link:
        return ""
    if "facebook.com" in link or "fb.com" in link:
        if "profile.php?id=" in link:
            match = re.search(r'id=(\d+)', link)
            if match: return match.group(1)
        else:
            match = re.search(r'(?:facebook\.com|fb\.com)/([^/?]+)', link)
            if match:
                # Tránh lấy nhầm các path mặc định của facebook
                if match.group(1).lower() not in ["home.php", "login.php", "watch", "groups", "marketplace"]:
                    return match.group(1)
    
    # Fallback cho trường hợp chỉ là UID thuần
    for sep in ("@", "?", "/", " ", "|"):
        if sep in link and not ("http" in link):
            link = link.split(sep)[0]
    return link.replace("https://", "").replace("http://", "").split("/")[0]


async def check_uid(uid: str) -> dict:
    uid = extract_uid(uid)
    result = {"uid": uid, "alive": False, "avatar_url": None, "ok": False}
    if not uid:
        return result

    # Dùng www.facebook.com thay vì mbasic để tránh lỗi 400 Bad Request
    url = f"https://www.facebook.com/{uid}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1"
    }

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(url, headers=headers)
            
            result["ok"] = True
            
            html = r.text
            
            # Extract og:image as avatar
            og_img_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
            if og_img_match:
                result["avatar_url"] = og_img_match.group(1).replace("&amp;", "&")
            else:
                result["avatar_url"] = avatar_url(uid)
            
            # Logic check: Nếu có meta property="al:android:url" thì là nick đang LIVE
            if 'al:android:url' in html or 'al:ios:url' in html:
                result["alive"] = True
            else:
                result["alive"] = False
                
    except Exception as e:
        # Lỗi mạng
        pass

    return result


def avatar_url(uid: str, size: int = 500) -> str:
    uid = extract_uid(uid)
    token = db.get_setting("fb_avatar_token", config.DEFAULT_FB_AVATAR_TOKEN)
    base = f"{config.FB_GRAPH}/{uid}/picture?height={size}&width={size}"
    if token:
        base += f"&access_token={token}"
    return base


def build_fb_caption(res: dict) -> str:
    if not res.get("ok"):
        return f"❌ <b>Lỗi kết nối hoặc không thể lấy thông tin UID {res.get('uid')}!</b>"
    
    alive = res.get("alive")
    status_icon = "🟢" if alive else "🔴"
    status_text = "HOẠT ĐỘNG (LIVE)" if alive else "BỊ KHOÁ (DIE)"
    
    return (
        f"╭─── <b>[ KẾT QUẢ FACEBOOK ]</b> ───╮\n"
        f"│\n"
        f"├ 👤 <b>UID:</b> <code>{res.get('uid')}</code>\n"
        f"├ 🔗 <b>Link:</b> <a href='https://www.facebook.com/profile.php?id={res.get('uid')}'>Mở Trang Cá Nhân</a>\n"
        f"├ {status_icon} <b>Tình trạng:</b> <b>{status_text}</b>\n"
        f"│\n"
        f"╰────────────────────────────╯\n\n"
        f"<i>💡 Gõ /trackfb {res.get('uid')} để tự động theo dõi và nhận thông báo khi nick bị khoá/mở khoá.</i>"
    )

def extract_fb_post_id(link: str) -> str:
    link = (link or "").strip()
    if not link: return ""
    
    # VD: https://www.facebook.com/zuck/posts/10114008298711461
    # Hoặc: https://www.facebook.com/photo.php?fbid=12345
    # Hoặc: https://www.facebook.com/groups/abc/permalink/12345
    match = re.search(r'(?:posts/|fbid=|permalink/|videos/|share/p/|/p/)([a-zA-Z0-9_]+)', link)
    if match: return match.group(1)
    
    parts = [p for p in link.split("/") if p]
    return parts[-1] if parts else link

async def fetch_fb_post_info(url: str) -> dict:
    post_id = extract_fb_post_id(url)
    cookie = db.get_setting("fb_cookie", "")
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    if cookie:
        headers["Cookie"] = cookie
        
    result = {
        "post_id": post_id,
        "url": url,
        "likes": 0,
        "comments": 0,
        "shares": 0,
        "desc": f"Bài viết FB: {post_id}",
        "cover": "",
    }
    
    try:
        # Construct mbasic URL by replacing domain
        fetch_url = url
        if cookie:
            fetch_url = re.sub(r'https?://(?:www\.|m\.)?facebook\.com', 'https://mbasic.facebook.com', url)
            
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            r = await client.get(fetch_url, headers=headers)
            html = r.text
            
            # Simple heuristic regex for likes, comments, shares (may be inaccurate without proper API)
            likes_match = re.search(r'([0-9.,KMB]+)\s*Thích', html, re.IGNORECASE) or re.search(r'([0-9.,KMB]+)\s*Like', html, re.IGNORECASE)
            comments_match = re.search(r'([0-9.,KMB]+)\s*Bình luận', html, re.IGNORECASE) or re.search(r'([0-9.,KMB]+)\s*Comment', html, re.IGNORECASE)
            shares_match = re.search(r'([0-9.,KMB]+)\s*Lượt chia sẻ', html, re.IGNORECASE) or re.search(r'([0-9.,KMB]+)\s*Share', html, re.IGNORECASE)
            
            def parse_num(s):
                if not s: return 0
                s = s.upper().replace(',', '').replace('.', '')
                if 'K' in s: return int(float(s.replace('K', '')) * 1000)
                if 'M' in s: return int(float(s.replace('M', '')) * 1000000)
                try: return int(s)
                except: return 0
                
            if likes_match: result["likes"] = parse_num(likes_match.group(1))
            if comments_match: result["comments"] = parse_num(comments_match.group(1))
            if shares_match: result["shares"] = parse_num(shares_match.group(1))
            
    except Exception:
        pass
        
    return result

def build_fb_post_caption(info: dict) -> str:
    return (
        f"╭─── <b>[ THEO DÕI BÀI VIẾT FACEBOOK ]</b> ───╮\n"
        f"│\n"
        f"├ 🆔 <b>ID:</b> <code>{info['post_id']}</code>\n"
        f"├ 👍 <b>Lượt thích:</b> {info['likes']:,}\n"
        f"├ 💬 <b>Bình luận:</b> {info['comments']:,}\n"
        f"├ 🔄 <b>Chia sẻ:</b> {info['shares']:,}\n"
        f"│\n"
        f"├ 🔗 <b>Link:</b> <a href='{info['url']}'>Mở bài viết</a>\n"
        f"│\n"
        f"╰────────────────────────────────╯\n\n"
        f"<i>💡 Gõ /trackvfb {info['url']} để theo dõi tương tác bài viết này.</i>"
    )


