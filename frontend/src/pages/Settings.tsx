// FB Live/Die Checker — Tác giả: @nhanxp | Hỗ trợ: Telegram/Facebook nhanxp
import { IconCircleCheck, IconCircleX, IconDeviceFloppy, IconPlugConnected } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from "../components/ui";
import { api } from "../lib/api";
import { vnd } from "../lib/utils";

function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {ok ? (
        <IconCircleCheck size={18} className="text-live" />
      ) : (
        <IconCircleX size={18} className="text-die" />
      )}
      {label}
    </div>
  );
}

export default function Settings({ onSaved }: { onSaved: () => void }) {
  const [s, setS] = useState<any>(null);
  const [prereq, setPrereq] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setS(await api("/api/settings"));
      setPrereq(await api("/api/prereq"));
    } catch (e: any) {
      toast.error(e.message);
    }
  }
  useEffect(() => {
    load();
  }, []);

  function up(k: string, v: string) {
    setS((p: any) => ({ ...p, [k]: v }));
  }

  async function save() {
    setSaving(true);
    try {
      const r = await api("/api/settings", { method: "POST", body: JSON.stringify(s) });
      toast.success(r.bot_started ? "Đã lưu & khởi động bot" : "Đã lưu cấu hình");
      await load();
      onSaved();
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  }

  if (!s) return <div className="text-muted-foreground">Đang tải...</div>;
  const p1 = Number(s.price_1m) || 0;

  async function handleUploadQr(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    setSaving(true);
    try {
      const res = await fetch("/api/upload-qr", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("fbc_token") || ""}` },
        body: fd
      });
      if (!res.ok) throw new Error("Upload thất bại");
      toast.success("Đã tải ảnh lên");
      await load();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function handleDeleteQr(filename: string) {
    if (!confirm("Bạn có chắc chắn xoá ảnh này?")) return;
    setSaving(true);
    try {
      await api(`/api/upload-qr/${filename}`, { method: "DELETE" });
      toast.success("Đã xoá ảnh");
      await load();
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <h1 className="text-2xl font-semibold">Cấu hình</h1>

      <Card>
        <CardHeader>
          <CardTitle>Điều kiện hoạt động</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-2">
          {prereq ? (
            <>
              <Check ok={prereq.telegram} label="Kết nối tới Telegram API" />
              <Check ok={prereq.facebook} label="Kết nối tới Facebook Graph" />
              <Check ok={prereq.bot_token} label="Bot Token hợp lệ" />
            </>
          ) : (
            <span className="text-sm text-muted-foreground">Đang kiểm tra...</span>
          )}
          <Button variant="outline" size="sm" className="self-start mt-1" onClick={load}>
            <IconPlugConnected size={16} /> Kiểm tra lại
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Bot Telegram</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Bot Token Telegram</Label>
            <Input
              value={s.bot_token || ""}
              onChange={(e) => up("bot_token", e.target.value)}
              placeholder="123456:ABC-..."
            />
            <p className="text-xs text-muted-foreground">
              Lấy token từ @BotFather.
            </p>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Zalo Bot Token (Tùy chọn)</Label>
            <Input
              value={s.zalo_bot_token || ""}
              onChange={(e) => up("zalo_bot_token", e.target.value)}
              placeholder="Zalo OA Proxy Token..."
            />
            <p className="text-xs text-muted-foreground">
              Sử dụng Zalo Proxy. Nếu để trống sẽ tắt.
            </p>
          </div>
          <div className="flex flex-col gap-1.5 mt-2 border-t border-border pt-4">
            <Label>Admin Telegram ID (Nhận Backup DB Hàng ngày)</Label>
            <Input
              value={s.admin_tg_id || ""}
              onChange={(e) => up("admin_tg_id", e.target.value)}
              placeholder="Ví dụ: 123456789"
            />
            <p className="text-xs text-muted-foreground">
              Hệ thống sẽ gửi file data.db backup tự động vào lúc 00:00 cho ID này qua Telegram Bot.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Giá gói & theo dõi</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Giá 1 tháng (VNĐ)</Label>
            <Input
              type="number"
              value={s.price_1m || ""}
              onChange={(e) => up("price_1m", e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              Tự nhân: 2 tháng = {vnd(p1 * 2)} · 3 tháng = {vnd(p1 * 3)}
            </p>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Chu kỳ quét (giây)</Label>
            <Input
              type="number"
              value={s.poll_interval || ""}
              onChange={(e) => up("poll_interval", e.target.value)}
            />
            <p className="text-xs text-muted-foreground">Tối thiểu 60 giây.</p>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Token avatar Facebook (công khai)</Label>
            <Input
              value={s.fb_avatar_token || ""}
              onChange={(e) => up("fb_avatar_token", e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Cookie Facebook (cào số Like/Cmt)</Label>
            <Input
              value={s.fb_cookie || ""}
              onChange={(e) => up("fb_cookie", e.target.value)}
              placeholder="Nhập Cookie của acc clone FB (để trống nếu không dùng)"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Phương thức check Instagram</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={s.ig_method || "public"}
              onChange={(e) => up("ig_method", e.target.value)}
            >
              <option value="public">Check bằng Web (Miễn phí)</option>
              <option value="instaloader">Instaloader (Dùng Session Cookie)</option>
              <option value="rapidapi">RapidAPI (Cần cấu hình API Key)</option>
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>RapidAPI Key (Instagram)</Label>
            <Input
              value={s.ig_rapidapi_key || ""}
              onChange={(e) => up("ig_rapidapi_key", e.target.value)}
              placeholder="Dùng cho RocketAPI"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>IG Session Cookie</Label>
            <Input
              value={s.ig_session_cookie || ""}
              onChange={(e) => up("ig_session_cookie", e.target.value)}
              placeholder="sessionid=..."
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Chính sách dùng thử (Free Trial)</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Bật tính năng tặng dùng thử</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
              value={s.enable_free_trial || "1"}
              onChange={(e) => up("enable_free_trial", e.target.value)}
            >
              <option value="1">Bật (Cho phép /trial)</option>
              <option value="0">Tắt</option>
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Số ngày dùng thử mặc định</Label>
            <Input
              type="number"
              value={s.free_trial_days || ""}
              onChange={(e) => up("free_trial_days", e.target.value)}
              placeholder="Ví dụ: 3"
            />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ngân hàng (Bank & Nạp tiền)</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <Label>Tên Ngân Hàng</Label>
            <Input
              value={s.bank_name || ""}
              onChange={(e) => up("bank_name", e.target.value)}
              placeholder="VD: MB Bank, Vietcombank"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Số Tài Khoản</Label>
            <Input
              value={s.bank_account || ""}
              onChange={(e) => up("bank_account", e.target.value)}
              placeholder="Nhập số tài khoản"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label>Tên Chủ Tài Khoản</Label>
            <Input
              value={s.bank_owner || ""}
              onChange={(e) => up("bank_owner", e.target.value)}
              placeholder="Nhập tên in hoa không dấu"
            />
          </div>
          <div className="flex flex-col gap-1.5 pt-2 border-t border-border/50">
            <Label>Admin Zalo Chat ID (Để nhận thông báo nạp tiền)</Label>
            <Input
              value={s.admin_zalo_id || ""}
              onChange={(e) => up("admin_zalo_id", e.target.value)}
              placeholder="ID Zalo của bạn (Dùng Zalo gửi tin nhắn cho Bot Zalo để lấy)"
            />
          </div>
          <div className="flex flex-col gap-2 pt-2 border-t border-border/50">
            <Label>Ảnh QR Code ({s.qr_images?.length || 0}/2)</Label>
            {s.qr_images && s.qr_images.length > 0 && (
              <div className="flex gap-4">
                {s.qr_images.map((img: string) => (
                  <div key={img} className="relative group rounded-md border p-1 border-border/50 bg-background/50">
                    <img src={`/images/${img}?t=${Date.now()}`} alt={img} className="w-24 h-24 object-cover rounded" />
                    <button
                      onClick={() => handleDeleteQr(img)}
                      className="absolute -top-2 -right-2 bg-destructive text-destructive-foreground rounded-full w-6 h-6 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity shadow-sm hover:bg-destructive/90"
                      title="Xoá ảnh"
                    >
                      <IconCircleX size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
            {(!s.qr_images || s.qr_images.length < 2) && (
              <label className="flex items-center justify-center border-2 border-dashed border-border/50 hover:border-primary/50 transition-colors h-10 rounded-md cursor-pointer text-sm text-muted-foreground w-fit px-4">
                <input type="file" className="hidden" accept="image/*" onChange={handleUploadQr} />
                + Tải ảnh QR lên
              </label>
            )}
            <p className="text-xs text-muted-foreground mt-1">Ảnh sẽ hiển thị khi khách gõ /bank</p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Bảo mật</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-1.5">
          <Label>Mật khẩu quản trị mới</Label>
          <Input
            type="password"
            value={s.admin_password || ""}
            onChange={(e) => up("admin_password", e.target.value)}
            placeholder="Để trống nếu không đổi"
          />
        </CardContent>
      </Card>

      <Button onClick={save} disabled={saving} className="self-start">
        <IconDeviceFloppy size={18} />
        {saving ? "Đang lưu..." : "Lưu cấu hình"}
      </Button>
    </div>
  );
}
