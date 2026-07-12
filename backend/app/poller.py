import asyncio, logging, time
from typing import Optional
from . import config, db, fb
from . import bot as botmod
from .util import now

log = logging.getLogger(__name__)


class FollowerPoller:
    def __init__(self):
        self._account_task: Optional[asyncio.Task] = None
        self._video_task:   Optional[asyncio.Task] = None
        self._backup_task:  Optional[asyncio.Task] = None
        self.last_run: int = 0
        self._bot = None
        self._zalo_bot = None

    @property
    def running(self) -> bool:
        t1 = self._account_task and not self._account_task.done()
        t2 = self._video_task   and not self._video_task.done()
        t3 = self._backup_task  and not self._backup_task.done()
        return bool(t1 or t2 or t3)

    def set_bot(self, bot): self._bot = bot

    def set_zalo_bot(self, bot): self._zalo_bot = bot

    def start(self):
        if not (self._account_task and not self._account_task.done()):
            self._account_task = asyncio.create_task(self._account_loop())
        if not (self._video_task and not self._video_task.done()):
            self._video_task = asyncio.create_task(self._video_loop())
        if not (self._backup_task and not self._backup_task.done()):
            self._backup_task = asyncio.create_task(self._backup_loop())
        log.info("Poller khoi dong (account + video + backup).")

    async def stop(self):
        for t in [self._account_task, self._video_task, self._backup_task]:
            if t:
                t.cancel()
                try: await t
                except: pass
        self._account_task = self._video_task = self._backup_task = None

    # ══ BACKUP LOOP ═══════════════════════════════════════════
    async def _backup_loop(self):
        await asyncio.sleep(60)
        while True:
            try:
                now_t = time.localtime()
                last_backup_str = db.get_setting("last_backup_date", "")
                today_str = time.strftime("%Y-%m-%d", now_t)
                
                if now_t.tm_hour == 0 and last_backup_str != today_str:
                    admin_tg_id = db.get_setting("admin_tg_id", "")
                    if admin_tg_id and self._bot:
                        from aiogram.types import FSInputFile
                        file_path = config.DB_PATH
                        await self._bot.send_document(
                            int(admin_tg_id),
                            document=FSInputFile(file_path),
                            caption=f"📦 Backup Auto - {today_str}"
                        )
                        db.set_setting("last_backup_date", today_str)
            except Exception as e:
                log.error("Loi backup DB: %s", e)
            await asyncio.sleep(300)

    # ══ ACCOUNT LOOP ═══════════════════════════════════════════
    async def _account_loop(self):
        await asyncio.sleep(30)
        while True:
            try:
                await self._check_accounts()
                await self._check_ig_accounts()
                await self._check_fb_accounts()
                await self._check_fb_watches()
            except Exception as e:
                log.exception("Loi account poller: %s", e)
            interval = max(60, int(db.get_setting("poll_interval", str(config.POLL_INTERVAL))))
            await asyncio.sleep(interval)

    async def _filter_expired_tracks(self, tracks):
        valid = []
        for t in tracks:
            tg_id = t.get("tg_user_id")
            if not tg_id:
                valid.append(t)
                continue
            u = db.get_user(tg_id)
            if not u:
                valid.append(t)
                continue
            if u["sub_until"] > time.time():
                valid.append(t)
            else:
                if u["expired_notified"] == 0:
                    with db._lock:
                        db.get_conn().execute("UPDATE tg_users SET expired_notified=1 WHERE tg_id=?", (tg_id,))
                        db.get_conn().commit()
                    if self._bot:
                        try:
                            await self._bot.send_message(tg_id, "⚠️ <b>Gói VIP của bạn đã hết hạn.</b>\nHệ thống tạm dừng tất cả các tác vụ theo dõi. Vui lòng nạp thêm (hoặc gia hạn) để tiếp tục sử dụng!", parse_mode="HTML")
                        except: pass
        return valid

    async def _check_accounts(self):
        from . import tiktok as tk
        tracks = await self._filter_expired_tracks(db.all_active_tracks())
        if not tracks: return
        self.last_run = int(time.time())
        log.info("Account poller: check %d tai khoan.", len(tracks))

        for track in tracks:
            try:
                info = await tk.fetch_tiktok_info(track["tiktok_username"])
                new_fl, old_fl = info["followers"], track["last_followers"]
                new_vid, old_vid = info["videos"], track["last_videos"]
                latest  = info.get("latest_video")
                new_vid_id  = (latest or {}).get("id", "") or ""
                last_vid_id = track.get("last_video_id", "") or ""

                db.update_track_stats(track["id"], new_fl, info["following"], new_vid, new_vid_id)

                # Follower change notify
                fl_diff = new_fl - old_fl
                if fl_diff != 0:
                    sign = "+" if fl_diff > 0 else ""
                    dir_ = "tăng 📈" if fl_diff > 0 else "giảm 📉"
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())
                    msg = (f"🔔 <b>Follower {dir_}</b>\n\n"
                           f"📱 <b>@{info['username']}</b>\n"
                           f"👥 Thay đổi: {sign}{fl_diff:,} → Tổng: <b>{tk.fmt_num(new_fl)}</b>\n"
                           f"➡️ Đang follow: <b>{tk.fmt_num(info['following'])}</b>\n"
                           f"❤️ Tổng likes: <b>{tk.fmt_num(info['hearts'])}</b>\n"
                           f"🎬 Tổng videos: <b>{tk.fmt_num(new_vid)}</b>\n\n"
                           f"⏰ Thời gian: <b>{now_str}</b>\n\n"
                           f"🤖 <i>TikTok Checker V2 by @khaikhai998</i>")
                    
                    zalo_id = track.get("zalo_user_id")
                    tg_id = track.get("tg_user_id")
                    
                    if zalo_id and self._zalo_bot:
                        try: await self._zalo_bot.send_message(zalo_id, msg)
                        except Exception as e: log.warning("Notify Zalo: %s", e)
                    elif tg_id and self._bot:
                        try: await self._bot.send_message(tg_id, msg)
                        except Exception as e: log.warning("Notify Telegram: %s", e)
                        
                    db.add_log("follower_change", f"@{info['username']}: {old_fl:,}→{new_fl:,} ({sign}{fl_diff:,})",
                               tg_id or zalo_id, info["username"])

                # New video notify
                is_new = ((new_vid_id and last_vid_id and new_vid_id != last_vid_id)
                          or (not last_vid_id and new_vid > old_vid > 0))
                if is_new:
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())
                    caption = tk.build_video_caption(latest) if latest and latest.get("id") else (
                        f"🎬 <b>@{info['username']}</b> vừa đăng video mới!\n"
                        f"🎬 Tổng: <b>{tk.fmt_num(new_vid)}</b> videos\n\n"
                        f"⏰ Thời gian: <b>{now_str}</b>\n\n"
                        f"🔗 <a href='https://www.tiktok.com/@{info['username']}'>Xem trang TikTok</a>\n\n"
                        f"🤖 <i>TikTok Checker V2 by @khaikhai998</i>")
                    
                    zalo_id = track.get("zalo_user_id")
                    tg_id = track.get("tg_user_id")
                    
                    try:
                        if zalo_id and self._zalo_bot:
                            await self._zalo_bot.send_message(zalo_id, caption)
                        elif tg_id and self._bot:
                            if latest and latest.get("cover"):
                                from aiogram.types import URLInputFile
                                await self._bot.send_photo(tg_id, photo=URLInputFile(latest["cover"], filename="thumb.jpg"), caption=caption)
                            else:
                                await self._bot.send_message(tg_id, caption)
                    except Exception as e: log.warning("Notify video: %s", e)
                    db.add_log("video_new", f"@{info['username']}: video moi", tg_id or zalo_id, info["username"])

            except Exception as e:
                log.warning("Loi check @%s: %s", track["tiktok_username"], e)
            await asyncio.sleep(3)

    # ══ VIDEO LOOP ═════════════════════════════════════════════
    async def _video_loop(self):
        await asyncio.sleep(45)
        while True:
            try:
                await self._check_videos()
                await self._check_ig_videos()
                await self._check_fb_posts()
            except Exception as e:
                log.exception("Loi video poller: %s", e)
            await asyncio.sleep(60)

    async def _check_videos(self):
        from . import tiktok as tk
        now = int(time.time())
        vtracks = await self._filter_expired_tracks(db.all_active_video_tracks())
        if not vtracks: return

        for vt in vtracks:
            if vt["last_checked"] + vt["check_interval"] > now:
                continue
            try:
                info = await tk.fetch_video_info(vt["video_url"])
                old = {
                    "plays":    vt["last_plays"],
                    "likes":    vt["last_likes"],
                    "comments": vt["last_comments"],
                    "shares":   vt["last_shares"],
                    "favorites": vt.get("last_favorites", 0),
                }
                new_p, new_l, new_c, new_s, new_f = info["plays"], info["likes"], info["comments"], info["shares"], info.get("favorites", 0)

                db.update_video_track_stats(vt["id"], new_p, new_l, new_c, new_s, new_f)

                changed = (new_p != old["plays"] or new_l != old["likes"]
                           or new_c != old["comments"] or new_s != old["shares"]
                           or new_f != old["favorites"])

                if changed:
                    caption = tk.build_video_caption(info, old)
                    zalo_id = vt.get("zalo_user_id")
                    tg_id = vt.get("tg_user_id")
                    
                    try:
                        if zalo_id and self._zalo_bot:
                            await self._zalo_bot.send_message(zalo_id, caption)
                        elif tg_id and self._bot:
                            if info.get("cover"):
                                from aiogram.types import URLInputFile
                                await self._bot.send_photo(tg_id, photo=URLInputFile(info["cover"], filename="thumb.jpg"), caption=caption)
                            else:
                                await self._bot.send_message(tg_id, caption)
                    except Exception as e:
                        log.warning("Notify video track: %s", e)

                    dp = new_p - old["plays"]
                    dl = new_l - old["likes"]
                    db.add_log("video_stats",
                               f"Video @{info['username']}: +{dp:,} views, +{dl:,} likes",
                               vt["tg_user_id"], info.get("username",""))
            except Exception as e:
                log.warning("Loi check video %s: %s", vt["video_url"], e)
            await asyncio.sleep(2)

    async def _check_fb_posts(self):
        from . import fb
        now = int(time.time())
        vtracks = await self._filter_expired_tracks(db.all_active_fb_post_tracks())
        if not vtracks: return

        for vt in vtracks:
            if vt["last_checked"] + vt["check_interval"] > now:
                continue
            try:
                info = await fb.fetch_fb_post_info(vt["post_url"])
                old = {
                    "likes":    vt["last_likes"],
                    "comments": vt["last_comments"],
                    "shares":   vt["last_shares"],
                }
                new_l, new_c, new_s = info["likes"], info["comments"], info["shares"]

                db.update_fb_post_track_stats(vt["id"], new_l, new_c, new_s)

                changed = (new_l != old["likes"] or new_c != old["comments"] or new_s != old["shares"])

                if changed:
                    caption = fb.build_fb_post_caption(info)
                    caption += f"\n\n📈 Tăng: +{new_l - old['likes']:,} Thích, +{new_c - old['comments']:,} Bình luận, +{new_s - old['shares']:,} Chia sẻ."
                    zalo_id = vt.get("zalo_user_id")
                    tg_id = vt.get("tg_user_id")
                    
                    try:
                        if zalo_id and self._zalo_bot:
                            await self._zalo_bot.send_message(zalo_id, caption)
                        elif tg_id and self._bot:
                            if info.get("cover"):
                                from aiogram.types import URLInputFile
                                await self._bot.send_photo(tg_id, photo=URLInputFile(info["cover"], filename="thumb.jpg"), caption=caption)
                            else:
                                await self._bot.send_message(tg_id, caption, disable_web_page_preview=True)
                    except Exception as e:
                        log.warning("Notify FB post track: %s", e)

                    dl = new_l - old["likes"]
                    db.add_log("fb_post_stats",
                               f"FB Post {info['post_id']}: +{dl:,} likes",
                               vt["tg_user_id"], info.get("post_id",""))
            except Exception as e:
                log.warning("Loi check fb post %s: %s", vt["post_url"], e)
            await asyncio.sleep(2)

    # ══ IG CHECKERS ════════════════════════════════════════════
    async def _check_ig_accounts(self):
        from . import ig
        tracks = await self._filter_expired_tracks(db.all_active_ig_tracks())
        if not tracks: return
        log.info("IG Account poller: check %d tai khoan.", len(tracks))

        for track in tracks:
            try:
                info = await ig.fetch_ig_info(track["ig_username"])
                new_fl, old_fl = info["followers"], track["last_followers"]
                db.update_ig_track_stats(track["id"], new_fl, info["following"], info["posts"])

                fl_diff = new_fl - old_fl
                if fl_diff != 0 and old_fl > 0:
                    sign = "+" if fl_diff > 0 else ""
                    dir_ = "tăng 📈" if fl_diff > 0 else "giảm 📉"
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())
                    msg = (f"🔔 <b>IG Follower {dir_}</b>\n\n"
                           f"📸 <b>@{info['username']}</b>\n"
                           f"👥 Thay đổi: {sign}{fl_diff:,} → Tổng: <b>{ig.fmt_num(new_fl)}</b>\n"
                           f"➡️ Đang follow: <b>{ig.fmt_num(info['following'])}</b>\n"
                           f"🖼️ Bài viết: <b>{ig.fmt_num(info['posts'])}</b>\n\n"
                           f"⏰ Thời gian: <b>{now_str}</b>\n\n"
                           f"🤖 <i>Instagram Checker V2 by @khaikhai998</i>")
                    
                    zalo_id = track.get("zalo_user_id")
                    tg_id = track.get("tg_user_id")
                    if zalo_id and self._zalo_bot:
                        try: await self._zalo_bot.send_message(zalo_id, msg)
                        except Exception as e: log.warning("Notify Zalo IG: %s", e)
                    elif tg_id and self._bot:
                        try: await self._bot.send_message(tg_id, msg)
                        except Exception as e: log.warning("Notify Telegram IG: %s", e)
                        
                    db.add_log("follower_change", f"IG @{info['username']}: {old_fl:,}→{new_fl:,} ({sign}{fl_diff:,})",
                               tg_id or zalo_id, info["username"])
            except Exception as e:
                log.warning("Loi check IG @%s: %s", track["ig_username"], e)
            await asyncio.sleep(4)

    async def _check_fb_watches(self):
        for w in db.active_watches():
            if w["expire_at"] and now() > w["expire_at"]:
                db.deactivate_watch(w["id"])
                db.add_log("system", f"Hết hạn theo dõi UID {w['uid']}", w["tg_id"], w["uid"])
                continue

            res = await fb.check_uid(w["uid"])
            if not res["ok"]:
                continue
            new_status = "live" if res["alive"] else "die"
            avatar = res["avatar_url"] or w["avatar_url"] or fb.avatar_url(w["uid"])
            old = w["last_status"]
            db.update_watch_status(w["id"], new_status, avatar)

            if old and old != new_status:
                db.add_log(
                    "change",
                    f"UID {w['uid']}: {old} → {new_status}",
                    w["tg_id"],
                    w["uid"],
                )
                bot = botmod.manager.bot
                if bot:
                    try:
                        await botmod._send_card(
                            bot, w["tg_id"], w["uid"], new_status, w["note"], w["price"],
                            avatar, header="Thay đổi trạng thái:",
                        )
                    except Exception as e:
                        db.add_log("system", f"Lỗi gửi thông báo {w['tg_id']}: {e}")
            await asyncio.sleep(0.3)

    async def _check_fb_accounts(self):
        from . import fb
        tracks = await self._filter_expired_tracks(db.all_active_fb_tracks())
        if not tracks: return
        log.info("FB Account poller: check %d tai khoan.", len(tracks))

        for track in tracks:
            try:
                res = await fb.check_uid(track["fb_uid"])
                new_status = "live" if res["alive"] else "die"
                old_status = track["last_status"]

                db.update_fb_track_status(track["id"], new_status, res.get("avatar_url", ""))

                if old_status and new_status != old_status:
                    icon = "🟢 MỞ KHOÁ (LIVE)" if res["alive"] else "🔴 BỊ KHOÁ (DIE)"
                    now_str = time.strftime("%d/%m/%Y %H:%M:%S", time.localtime())
                    msg = (f"🔔 <b>Cảnh Báo Facebook {icon}</b>\n\n"
                           f"👤 <b>UID:</b> <code>{res['uid']}</code>\n"
                           f"🔄 <b>Thay đổi:</b> {old_status.upper()} ➡️ {new_status.upper()}\n"
                           f"⏰ Thời gian: <b>{now_str}</b>\n\n"
                           f"🤖 <i>Facebook Checker by @khaikhai998</i>")
                    
                    zalo_id = track.get("zalo_user_id")
                    tg_id = track.get("tg_user_id")
                    
                    if zalo_id and self._zalo_bot:
                        try: await self._zalo_bot.send_message(zalo_id, msg)
                        except Exception as e: log.warning("Notify Zalo FB: %s", e)
                    elif tg_id and self._bot:
                        try: await self._bot.send_message(tg_id, msg)
                        except Exception as e: log.warning("Notify Telegram FB: %s", e)
                        
                    db.add_log("fb_status_change", f"FB {res['uid']}: {old_status.upper()} -> {new_status.upper()}",
                               tg_id or zalo_id, res["uid"])
            except Exception as e:
                log.warning("Loi check FB %s: %s", track["fb_uid"], e)
            await asyncio.sleep(3)

    async def _check_ig_videos(self):
        from . import ig
        now = int(time.time())
        vtracks = await self._filter_expired_tracks(db.all_active_ig_video_tracks())
        if not vtracks: return

        for vt in vtracks:
            if vt["last_checked"] + vt["check_interval"] > now:
                continue
            try:
                info = await ig.fetch_ig_post_info(vt["post_url"])
                old = {
                    "likes":    vt["last_likes"],
                    "comments": vt["last_comments"],
                    "views":    vt["last_views"],
                }
                new_l, new_c, new_v = info["likes"], info["comments"], info.get("views", 0)

                db.update_ig_video_track_stats(vt["id"], new_l, new_c, new_v)

                changed = (new_l != old["likes"] or new_c != old["comments"] or new_v != old["views"])

                if changed and old["likes"] > 0:
                    caption = ig.build_ig_video_caption(info, old)
                    zalo_id = vt.get("zalo_user_id")
                    tg_id = vt.get("tg_user_id")
                    try:
                        if zalo_id and self._zalo_bot:
                            await self._zalo_bot.send_message(zalo_id, caption)
                        elif tg_id and self._bot:
                            if info.get("cover"):
                                from aiogram.types import URLInputFile
                                await self._bot.send_photo(tg_id, photo=URLInputFile(info["cover"], filename="thumb.jpg"), caption=caption)
                            else:
                                await self._bot.send_message(tg_id, caption)
                    except Exception as e:
                        log.warning("Notify IG video track: %s", e)

                    dl = new_l - old["likes"]
                    dc = new_c - old["comments"]
                    db.add_log("video_stats",
                               f"IG Post @{info['username']}: +{dl:,} likes, +{dc:,} cmt",
                               vt["tg_user_id"], info.get("username",""))
            except Exception as e:
                log.warning("Loi check IG post %s: %s", vt["post_url"], e)
            await asyncio.sleep(4)


poller = FollowerPoller()
