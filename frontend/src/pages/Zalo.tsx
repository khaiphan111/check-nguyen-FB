import { IconDeviceFloppy, IconPlus, IconTrash, IconEdit } from "@tabler/icons-react";
import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from "../components/ui";
import { api } from "../lib/api";

export default function Zalo() {
  const [tracks, setTracks] = useState<any[]>([]);
  
  const [username, setUsername] = useState("");
  
  const [interval, setInterval] = useState("60");
  
  const [editInterval, setEditInterval] = useState("60");

  async function load() {
    try {
      const t = await api("/api/admin/zalo-tracks");
      setTracks(t);
      
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function addTrack() {
    if (!username) return;
    try {
      await api("/api/admin/zalo-tracks", { method: "POST", body: JSON.stringify({ phone: username }) });
      toast.success("Thêm thành công!");
      setUsername("");
      load();
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  ) 
      });
      toast.success("Thêm thành công!");
      setVideoUrl("");
      load();
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  async function delTrack(phone: string) {
    if (!confirm("Xóa theo dõi tài khoản này?")) return;
    try {
      await api(`/api/admin/zalo-tracks/${phone}`, { method: "DELETE" });
      load();
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  `, { method: "DELETE" });
      load();
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  `, { 
        method: "PUT", 
        body: JSON.stringify({ check_interval: Number(editInterval) * 60 }) 
      });
      toast.success("Sửa thành công!");
      setEditVideoId(null);
      load();
    } catch (e: any) {
      toast.error(e.message);
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      <h1 className="text-2xl font-semibold">Zalo Tracking</h1>

      <Card>
        <CardHeader>
          <CardTitle>Tài khoản (Follower)</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="flex gap-2">
            <Input 
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              placeholder="Username TikTok" 
            />
            <Button onClick={addTrack}><IconPlus size={18} /> Thêm</Button>
          </div>
          
          <div className="rounded-md border border-border">
            <table className="w-full text-sm text-left">
              <thead className="bg-muted border-b border-border">
                <tr>
                  <th className="px-4 py-2 font-medium">Username</th>
                  <th className="px-4 py-2 font-medium">Trạng thái</th>
                  <th className="px-4 py-2 font-medium">Following</th>
                  <th className="px-4 py-2 font-medium">Videos</th>
                  <th className="px-4 py-2 font-medium">Thao tác</th>
                </tr>
              </thead>
              <tbody>
                {tracks.map(t => (
                  <tr key={t.phone} className="border-b border-border last:border-0 hover:bg-muted/50">
                    <td className="px-4 py-2 font-semibold flex items-center gap-3">
                      {t.avatar_url ? (
                        <img src={t.avatar_url} className="w-10 h-10 rounded-full bg-muted object-cover border border-border" alt="" onError={e => (e.target as HTMLImageElement).style.display = 'none'} />
                      ) : null}
                      @{t.phone}
                    </td>
                    <td className="px-4 py-2">{t.status?.toLocaleString()}</td>
                    <td className="px-4 py-2">{t.last_following?.toLocaleString()}</td>
                    <td className="px-4 py-2">{t.last_videos?.toLocaleString()}</td>
                    <td className="px-4 py-2">
                      <Button variant="ghost" size="sm" onClick={() => delTrack(t.phone)} className="text-die hover:text-die/80 h-8 px-2">
                        <IconTrash size={16} />
                      </Button>
                    </td>
                  </tr>
                ))}
                {tracks.length === 0 && (
                  <tr><td colSpan={5} className="px-4 py-4 text-center text-muted-foreground">Chưa có dữ liệu</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      

    </div>
  );
}
