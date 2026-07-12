// FB Live/Die Checker — Tác giả: @nhanxp | Hỗ trợ: Telegram/Facebook nhanxp
import {
  IconCircleCheck,
  IconCircleX,
  IconRefresh,
  IconRobot,
  IconSearch,
  IconUsers,
  IconCoins,
  IconUserPlus,
  IconTrendingUp
} from "@tabler/icons-react";
import { useState, useEffect } from "react";
import toast from "react-hot-toast";
import { Badge, Button, Card, CardContent, Input } from "../components/ui";
import { api } from "../lib/api";
import { fromNow, vnd } from "../lib/utils";

function Stat({ icon: Icon, label, value, sub }: any) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4">
        <div className="h-11 w-11 rounded-md bg-muted flex items-center justify-center">
          <Icon size={22} stroke={1.75} />
        </div>
        <div>
          <div className="text-2xl font-semibold leading-none">{value}</div>
          <div className="text-sm text-muted-foreground mt-1">{label}</div>
        </div>
        {sub}
      </CardContent>
    </Card>
  );
}

export default function Dashboard({ status, onRefresh }: any) {
  const [uid, setUid] = useState("");
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [analytics, setAnalytics] = useState<any>(null);

  useEffect(() => {
    loadAnalytics();
  }, []);

  async function loadAnalytics() {
    try {
      setAnalytics(await api("/api/analytics"));
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  async function check() {
    if (!uid.trim()) return;
    setLoading(true);
    setResult(null);
    try {
      const r = await api("/api/check", {
        method: "POST",
        body: JSON.stringify({ uid: uid.trim() }),
      });
      setResult(r);
    } catch (e: any) {
      toast.error(e.message);
    } finally {
      setLoading(false);
    }
  }

  if (!status) return <div className="text-muted-foreground">Đang tải...</div>;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Tổng quan</h1>
          <p className="text-muted-foreground text-sm mt-1">
            Phiên bản {status.version} · Tác giả {status.author}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => { onRefresh(); loadAnalytics(); }}>
          <IconRefresh size={16} /> Làm mới
        </Button>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {analytics && (
          <>
            <Stat icon={IconCoins} label="Doanh thu Hôm nay" value={vnd(analytics.revenue_today)} />
            <Stat icon={IconTrendingUp} label="Doanh thu Tháng" value={vnd(analytics.revenue_month)} />
            <Stat icon={IconUsers} label="Tổng Người dùng" value={analytics.total_users} />
            <Stat icon={IconUserPlus} label="Khách Mới Hôm Nay" value={analytics.new_users_today} />
          </>
        )}
        <Stat icon={IconCircleCheck} label="Đang LIVE" value={status.watches_live} />
        <Stat icon={IconCircleX} label="Đang DIE" value={status.watches_die} />
        <Stat
          icon={IconRobot}
          label="Trạng thái Bot"
          value={status.bot_running || status.zalo_running ? "Đang chạy" : "Tắt"}
          sub={
            <Badge status={status.bot_running || status.zalo_running ? "live" : "die"} className="ml-auto">
              {status.bot_running || status.zalo_running ? "ON" : "OFF"}
            </Badge>
          }
        />
        <Stat icon={IconUsers} label="Tiktok/IG Accounts" value={status.tracks_total || 0} />
        <Stat icon={IconCircleCheck} label="Tiktok/IG Videos" value={status.video_tracks_total || 0} />
      </div>

      <Card>
        <CardContent className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <IconSearch size={18} />
            <span className="font-medium">Kiểm tra nhanh một UID</span>
          </div>
          <div className="flex gap-2">
            <Input
              value={uid}
              onChange={(e) => setUid(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && check()}
              placeholder="Nhập UID hoặc link Facebook"
            />
            <Button onClick={check} disabled={loading}>
              {loading ? "Đang kiểm tra..." : "Kiểm tra"}
            </Button>
          </div>
          {result && (
            <div className="flex items-center gap-4 rounded-md border border-border p-4">
              <img
                src={result.avatar_url}
                alt=""
                className="h-16 w-16 rounded-md object-cover bg-muted"
                onError={(e) => ((e.target as HTMLImageElement).style.visibility = "hidden")}
              />
              <div>
                <div className="font-medium">UID {result.uid}</div>
                <Badge status={result.status === "live" ? "live" : "die"} className="mt-1">
                  {result.status === "live" ? "LIVE" : result.status === "die" ? "DIE" : "LỖI"}
                </Badge>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <p className="text-xs text-muted-foreground">
        Vòng quét cuối: {fromNow(status.poller_last_run)} ·{" "}
        {status.poller_running ? "Bộ theo dõi đang chạy" : "Bộ theo dõi chưa chạy"}
      </p>
    </div>
  );
}
