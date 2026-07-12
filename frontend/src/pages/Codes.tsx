import { useEffect, useState } from "react";
import toast from "react-hot-toast";
import { Badge, Card, CardContent, Button } from "../components/ui";
import { api } from "../lib/api";
import { IconRefresh } from "@tabler/icons-react";

function formatMoney(amount: number) {
  return new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(amount);
}

function formatDate(ts: number) {
  if (!ts) return "—";
  return new Date(ts * 1000).toLocaleString("vi-VN");
}

export default function Codes() {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any[]>([]);

  async function loadData() {
    try {
      setLoading(true);
      const res = await api("/api/codes");
      setData(res);
    } catch (e: any) {
      toast.error("Lỗi: " + e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Kho Giftcode & Lịch sử</h1>
          <p className="text-sm text-muted-foreground mt-1">Các mã code tự động sinh khi Admin xác nhận nạp tiền</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadData}>
          <IconRefresh size={16} /> Làm mới
        </Button>
      </div>

      {data.length === 0 && !loading && (
        <Card>
          <CardContent className="text-sm text-muted-foreground">
            Kho chứa đang trống. Mã code sẽ được tự động tạo khi có khách nạp tiền.
          </CardContent>
        </Card>
      )}

      <div className="flex flex-col gap-3">
        {data.map((c: any) => (
          <Card key={c.id}>
            <CardContent className="flex flex-wrap items-center gap-4">
              <div className="min-w-44">
                <div className="font-mono font-medium">{c.code}</div>
                <div className="text-sm text-muted-foreground">
                  Tạo lúc: {formatDate(c.created_at)}
                </div>
              </div>
              <div className="min-w-32">
                <div className="text-xs text-muted-foreground">Mệnh giá</div>
                <div className="font-medium text-green-600 dark:text-green-400">
                  {formatMoney(c.amount)}
                </div>
              </div>
              <div className="min-w-32">
                <div className="text-xs text-muted-foreground">Trạng thái</div>
                <Badge status={c.is_used ? "die" : "live"}>
                  {c.is_used ? "Đã sử dụng" : "Chưa sử dụng"}
                </Badge>
              </div>
              {c.is_used ? (
                <div className="ml-auto text-sm text-right">
                  <div className="text-muted-foreground">Sử dụng bởi ID: <span className="text-foreground">{c.used_by}</span></div>
                  <div className="text-muted-foreground text-xs">{formatDate(c.used_at)}</div>
                </div>
              ) : (
                <div className="ml-auto text-sm text-right text-muted-foreground">
                  Sẵn sàng
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
