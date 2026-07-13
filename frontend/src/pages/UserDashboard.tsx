import { IconListCheck, IconLogout, IconUser } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { api } from "../lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui";

export default function UserDashboard({ onLogout }: { onLogout: () => void }) {
  const [user, setUser] = useState<any>(null);
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [u, d] = await Promise.all([
        api("/api/user/me"),
        api("/api/user/analytics")
      ]);
      setUser(u);
      setData(d);
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="border-b border-border p-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <IconUser size={24} />
          <h1 className="text-xl font-bold">Xin chào, {user?.name || "Khách hàng"}</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm">
            <span className="text-muted-foreground">Số dư: </span>
            <span className="font-semibold text-green-500">
              {new Intl.NumberFormat("vi-VN").format(user?.balance || 0)}đ
            </span>
          </div>
          <div className="text-sm">
            <span className="text-muted-foreground">VIP: </span>
            <span className="font-semibold text-yellow-500">
              Cấp {user?.vip_level || 0}
            </span>
          </div>
          <button
            onClick={onLogout}
            className="flex items-center gap-1 text-red-400 hover:text-red-500 text-sm font-medium"
          >
            <IconLogout size={16} /> Thoát
          </button>
        </div>
      </header>

      <main className="p-6 flex-1 flex flex-col gap-6 max-w-6xl mx-auto w-full">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground font-normal">Đang theo dõi FB Live/Die</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data?.live || 0 + data?.die || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground font-normal">FB Posts đang theo dõi</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{data?.fb_tracks?.length || 0}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground font-normal">TikTok/IG đang theo dõi</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(data?.tk_tracks?.length || 0) + (data?.ig_tracks?.length || 0)}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground font-normal">TikTok/IG Video đang theo dõi</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(data?.tk_videos?.length || 0) + (data?.ig_videos?.length || 0)}</div>
            </CardContent>
          </Card>
        </div>

        <Card className="flex-1">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <IconListCheck size={20} /> Danh sách TikTok đang theo dõi
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data?.tk_tracks?.length > 0 ? (
              <div className="border border-border rounded overflow-hidden">
                <table className="w-full text-left text-sm">
                  <thead className="bg-muted">
                    <tr>
                      <th className="p-2 border-b border-border">Username</th>
                      <th className="p-2 border-b border-border">Follower</th>
                      <th className="p-2 border-b border-border">Likes</th>
                      <th className="p-2 border-b border-border">Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.tk_tracks.map((t: any) => (
                      <tr key={t.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                        <td className="p-2 font-medium">@{t.tiktok_id}</td>
                        <td className="p-2">{new Intl.NumberFormat().format(t.last_follower)}</td>
                        <td className="p-2">{new Intl.NumberFormat().format(t.last_likes)}</td>
                        <td className="p-2">
                          <span className={`px-2 py-0.5 rounded text-xs ${t.is_active ? 'bg-green-500/20 text-green-500' : 'bg-red-500/20 text-red-500'}`}>
                            {t.is_active ? "Đang chạy" : "Tạm dừng"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-10 text-muted-foreground">
                Bạn chưa theo dõi kênh TikTok nào. Dùng lệnh /track trong bot để bắt đầu.
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
