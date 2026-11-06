"""Phân tích CHẨN ĐOÁN (cấp độ 2). Chủ file: TV3.

    python src/diagnose.py            # ghi CSV và hình vào outputs/ (notebooks/02_chan_doan.ipynb gọi lại các hàm ở đây)

Câu hỏi chẩn đoán (giả thuyết H7 trong docs/A_gia_thuyet.md, viết TRƯỚC khi chạy file này):
    Tương quan đôi trung bình giữa các mã trong 2022 có cao hơn giai đoạn "bình thường" (11/2018–12/2021)?

Phương pháp:
- Thống kê: tương quan Pearson trung bình của các cặp mã (lợi suất ngày) và tỷ lệ phương sai do thành phần chính
  thứ nhất của ma trận tương quan (PC1). Hiệu = 2022 trừ bình thường.
- Chỉ dùng các mã có >= 95% phiên có lợi suất ở CẢ HAI giai đoạn (ROS ngừng giao dịch 11/08/2022 nên bị loại khỏi
  phép so sánh; dòng "co_ROS_cap_du_lieu" ghi số liệu điểm khi dùng các cặp có đủ dữ liệu).
- Bootstrap khối trượt (moving block), lấy mẫu RIÊNG trong từng giai đoạn, B lần; khoảng 95% theo phân vị.
  Độ dài khối mặc định 20 phiên, báo thêm độ nhạy theo 5/10/40. Hạt giống = config.yaml `seed`.
- Quy tắc bác bỏ (A_gia_thuyet.md H7): khoảng 95% của hiệu chứa 0 hoặc âm.
- Đóng góp rủi ro từng mã vào danh mục 1/N: RC_i = w_i (Σw)_i / σ_p² (tổng = 100%), Σ = hiệp phương sai mẫu ngày,
  trên cùng tập mã ở cả ba giai đoạn (bình thường, 2022, Lớp 1).

Diễn giải: đây là LIÊN HỆ, không phải nhân quả; 2022 chỉ là MỘT giai đoạn, không khái quát thành quy luật.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import describe  # noqa: E402
from config import load  # noqa: E402

OUT = ROOT / "outputs"
FIG = OUT / "figures"

B = 5000
BLOCK = 20
BLOCK_SENS = [5, 10, 20, 40]
COVERAGE = 0.95
TD = 252


def common_assets(ret: pd.DataFrame, spans: list[tuple[str, str]], coverage: float = COVERAGE) -> list[str]:
    """Mã có >= coverage phiên có lợi suất ở mọi giai đoạn."""
    ok = pd.Series(True, index=ret.columns)
    for a, b in spans:
        ok &= ret.loc[a:b].notna().mean() >= coverage
    return list(ret.columns[ok])


def avg_pairwise_corr(X: np.ndarray) -> float:
    C = np.corrcoef(X, rowvar=False)
    iu = np.triu_indices_from(C, k=1)
    return float(C[iu].mean())


def pc1_share(X: np.ndarray) -> float:
    C = np.corrcoef(X, rowvar=False)
    w = np.linalg.eigvalsh(C)
    return float(w[-1] / w.sum())


def block_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    """Chỉ số hàng của một mẫu bootstrap khối trượt có độ dài n."""
    nb = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=nb)
    idx = (starts[:, None] + np.arange(block)[None, :]).ravel()
    return idx[:n]


def bootstrap_diff(Xn: np.ndarray, Xs: np.ndarray, stat, block: int, b: int, seed: int) -> np.ndarray:
    """Phân phối bootstrap của stat(2022) - stat(bình thường), lấy mẫu riêng từng giai đoạn."""
    rng = np.random.default_rng(seed)
    out = np.empty(b)
    for i in range(b):
        sn = stat(Xn[block_indices(len(Xn), block, rng)])
        ss = stat(Xs[block_indices(len(Xs), block, rng)])
        out[i] = ss - sn
    return out


COVID_EXCLUDE = ("2020-02-01", "2020-04-30")   # phép thử THÊM sau khi thấy kết quả chính: VN-Index đáy 24/03/2020 (-35,7%)


def correlation_test(ret: pd.DataFrame, p: dict, seed: int, exclude_normal: tuple[str, str] | None = None,
                     blocks: list[int] | None = None, label: str = "chinh_H7") -> tuple[pd.DataFrame, dict]:
    """Bảng kết quả bootstrap cho tương quan trung bình và PC1; trả thêm dữ liệu để vẽ.

    exclude_normal: bỏ các phiên trong khoảng này khỏi giai đoạn "bình thường" (chỉ cho phép thử độ nhạy;
    các phiên còn lại được nối liền khi lấy khối nên có một mối nối nhỏ).
    """
    normal, stress = p["binh_thuong"], p["nam_2022"]
    assets = common_assets(ret, [normal, stress])
    dn = ret.loc[normal[0]:normal[1], assets].dropna()
    if exclude_normal:
        dn = dn.drop(dn.loc[exclude_normal[0]:exclude_normal[1]].index)
    Rn = dn.to_numpy()
    Rs = ret.loc[stress[0]:stress[1], assets].dropna().to_numpy()
    rows, draws = [], {}
    for name, stat in [("tuong_quan_trung_binh", avg_pairwise_corr), ("ty_le_PC1", pc1_share)]:
        point_n, point_s = stat(Rn), stat(Rs)
        for L in (blocks or BLOCK_SENS):
            d = bootstrap_diff(Rn, Rs, stat, L, B, seed)
            lo, hi = np.percentile(d, [2.5, 97.5])
            rows.append({
                "bien_the": label, "thong_ke": name, "do_dai_khoi": L, "so_ma": len(assets),
                "so_phien_binh_thuong": len(Rn), "so_phien_2022": len(Rs),
                "binh_thuong": point_n, "nam_2022": point_s, "hieu_2022_tru_binh_thuong": point_s - point_n,
                "ci95_thap": lo, "ci95_cao": hi, "p_mot_phia_hieu_le_0": float((d <= 0).mean()),
                "ket_luan_H7": "ung_ho (khoang 95% > 0)" if lo > 0 else "khong_ung_ho (khoang 95% chua 0 hoac am)",
                "B": B,
            })
            if L == BLOCK:
                draws[name] = d
    res = pd.DataFrame(rows)
    return res, {"assets": assets, "draws": draws, "Rn": Rn, "Rs": Rs}


def correlation_with_ros(ret: pd.DataFrame, p: dict) -> pd.DataFrame:
    """Độ nhạy: tương quan trung bình dùng mọi cặp có đủ dữ liệu cùng ngày (kể cả ROS, 2022 chỉ tới 11/08)."""
    rows = []
    for k in ["binh_thuong", "nam_2022"]:
        a, b = p[k]
        C = ret.loc[a:b].corr(min_periods=100)
        iu = np.triu_indices_from(C.values, k=1)
        rows.append({"giai_doan": k, "tuong_quan_trung_binh_co_ROS": float(np.nanmean(C.values[iu])), "so_ma": C.shape[0]})
    return pd.DataFrame(rows)


def volatility_context(ret: pd.DataFrame, vret: pd.Series, p: dict, assets: list[str]) -> pd.DataFrame:
    """Biến động trung bình từng mã và của VN-Index ở hai giai đoạn (để diễn giải: tương quan đi cùng biến động)."""
    rows = []
    for k in ["binh_thuong", "nam_2022"]:
        a, b = p[k]
        r = ret.loc[a:b, assets]
        rows.append({
            "giai_doan": k,
            "bien_dong_nam_tb_ma": float((r.std(ddof=1) * np.sqrt(TD)).mean()),
            "bien_dong_nam_vnindex": float(vret.loc[a:b].std(ddof=1) * np.sqrt(TD)),
            "loi_suat_tb_ngay_vnindex": float(vret.loc[a:b].mean()),
        })
    return pd.DataFrame(rows)


def rolling_avg_corr(ret: pd.DataFrame, assets: list[str], window: int = 60) -> pd.Series:
    """Tương quan đôi trung bình trượt `window` phiên (chỉ để vẽ, không dùng để kiểm định)."""
    X = ret[assets].dropna()
    vals = []
    for i in range(window, len(X) + 1):
        vals.append(avg_pairwise_corr(X.iloc[i - window:i].to_numpy()))
    return pd.Series(vals, index=X.index[window - 1:])


def risk_contributions(ret: pd.DataFrame, p: dict, assets: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Đóng góp rủi ro của từng mã trong 1/N (cùng tập mã) ở ba giai đoạn; trả (theo mã, theo danh mục)."""
    parts, summ = [], []
    n = len(assets)
    w = np.full(n, 1.0 / n)
    for k in ["binh_thuong", "nam_2022", "lop1"]:
        a, b = p[k]
        X = ret.loc[a:b, assets].dropna()
        S = np.cov(X.to_numpy(), rowvar=False, ddof=1) * TD
        var = float(w @ S @ w)
        sd = np.sqrt(var)
        rc = w * (S @ w) / var
        vol_i = np.sqrt(np.diag(S))
        parts.append(pd.DataFrame({
            "giai_doan": k, "ma": assets, "ty_trong": w, "do_lech_chuan_nam_ma": vol_i,
            "dong_gop_rui_ro": rc, "ty_so_dong_gop_tren_ty_trong": rc / w,
        }))
        C = np.corrcoef(X.to_numpy(), rowvar=False)
        summ.append({
            "giai_doan": k, "so_phien": len(X), "so_ma": n,
            "bien_dong_nam_danh_muc": sd,
            "bien_dong_nam_tb_ma": float(vol_i.mean()),
            "he_so_da_dang_hoa": float((w * vol_i).sum() / sd),      # >1: càng lớn càng được lợi từ đa dạng hóa
            "tuong_quan_trung_binh": float(C[np.triu_indices(n, 1)].mean()),
            "so_ma_chiem_50pct_rui_ro": int((np.sort(rc)[::-1].cumsum() < 0.5).sum() + 1),
        })
    return pd.concat(parts, ignore_index=True), pd.DataFrame(summ)


# ---------------------------------------------------------------- hình
def plot_two_heatmaps(ret: pd.DataFrame, p: dict, assets: list[str]):
    Cn = ret.loc[p["binh_thuong"][0]:p["binh_thuong"][1], assets].corr()
    Cs = ret.loc[p["nam_2022"][0]:p["nam_2022"][1], assets].corr()
    order = describe._cluster_order(Cn)
    fig, axes = plt.subplots(1, 2, figsize=(16, 7.2))
    describe.plot_heatmap(Cn, "Bình thường 11/2018–12/2021", order, ax=axes[0], vmin=0.0, vmax=0.9)
    describe.plot_heatmap(Cs, "Năm 2022", order, ax=axes[1], vmin=0.0, vmax=0.9)
    fig.suptitle(f"Tương quan lợi suất ngày ({len(assets)} mã, cùng thứ tự sắp xếp, cùng thang màu)")
    fig.tight_layout()
    return fig


def plot_rolling(roll: pd.Series, p: dict, res: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.plot(roll.index, roll, color="#1f77b4", lw=1.2, label="Trượt 60 phiên")
    r = res[(res.thong_ke == "tuong_quan_trung_binh") & (res.do_dai_khoi == BLOCK)].iloc[0]
    for k, v, c in [("binh_thuong", r.binh_thuong, "#2ca02c"), ("nam_2022", r.nam_2022, "#d62728")]:
        a, b = p[k]
        ax.hlines(v, pd.Timestamp(a), pd.Timestamp(b), color=c, lw=2.2,
                  label=f"{'Bình thường' if k == 'binh_thuong' else '2022'}: {v:.3f}")
    ax.axvspan(pd.Timestamp(p["nam_2022"][0]), pd.Timestamp(p["nam_2022"][1]), color="grey", alpha=0.15)
    ax.set_ylabel("Tương quan đôi trung bình")
    ax.set_title("Tương quan đôi trung bình giữa các mã theo thời gian")
    ax.legend(loc="upper left")
    fig.tight_layout()
    return fig


def plot_bootstrap(draws: np.ndarray, row: pd.Series):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.hist(draws, bins=60, color="#7f9fd0", edgecolor="white")
    ax.axvline(0, color="k", lw=1)
    ax.axvline(row.hieu_2022_tru_binh_thuong, color="#d62728", lw=2, label=f"Điểm ước lượng {row.hieu_2022_tru_binh_thuong:.3f}")
    ax.axvspan(row.ci95_thap, row.ci95_cao, color="#d62728", alpha=0.12, label=f"Khoảng 95% [{row.ci95_thap:.3f}; {row.ci95_cao:.3f}]")
    ax.set_xlabel("Tương quan trung bình 2022 trừ bình thường")
    ax.set_title(f"Bootstrap khối (khối {BLOCK} phiên, B = {B})")
    ax.legend()
    fig.tight_layout()
    return fig


def plot_risk_contrib(rc: pd.DataFrame):
    pv = rc.pivot(index="ma", columns="giai_doan", values="dong_gop_rui_ro")[["binh_thuong", "nam_2022", "lop1"]]
    pv = pv.sort_values("nam_2022")
    fig, ax = plt.subplots(figsize=(9, 8))
    y = np.arange(len(pv))
    h = 0.27
    for i, (k, lab, c) in enumerate([("binh_thuong", "Bình thường 11/2018–12/2021", "#2ca02c"),
                                     ("nam_2022", "2022", "#d62728"),
                                     ("lop1", "10/2023–09/2026", "#1f77b4")]):
        ax.barh(y + (i - 1) * h, pv[k] * 100, height=h, label=lab, color=c)
    ax.axvline(100 / len(pv), color="k", ls="--", lw=1, label=f"Tỷ trọng 1/N = {100 / len(pv):.2f}%")
    ax.set_yticks(y)
    ax.set_yticklabels(pv.index, fontsize=8)
    ax.set_xlabel("Đóng góp vào rủi ro (phương sai) của danh mục 1/N (%)")
    ax.set_title("Đóng góp rủi ro từng mã trong danh mục 1/N")
    ax.legend(loc="lower right")
    fig.tight_layout()
    return fig


def run() -> dict:
    FIG.mkdir(parents=True, exist_ok=True)
    cfg = load()
    seed = int(cfg.get("seed", 42))
    P, V, R = describe.load_data()
    ret, vret = describe.daily_returns(P, V)
    p = describe.periods()

    res, aux = correlation_test(ret, p, seed)
    res_covid, _ = correlation_test(ret, p, seed, exclude_normal=COVID_EXCLUDE, blocks=[BLOCK],
                                    label="tham_do_bo_02-04/2020")
    pd.concat([res, res_covid], ignore_index=True).round(6).to_csv(
        OUT / "chan_doan_tuong_quan.csv", index=False, encoding="utf-8-sig")
    assets = aux["assets"]
    ros = correlation_with_ros(ret, p)
    vol = volatility_context(ret, vret, p, assets)
    ctx = pd.concat([ros.set_index("giai_doan"), vol.set_index("giai_doan")], axis=1).reset_index()
    ctx.round(6).to_csv(OUT / "chan_doan_boi_canh_bien_dong.csv", index=False, encoding="utf-8-sig")

    rc, summ = risk_contributions(ret, p, assets)
    rc.round(6).to_csv(OUT / "chan_doan_dong_gop_rui_ro.csv", index=False, encoding="utf-8-sig")
    summ.round(6).to_csv(OUT / "chan_doan_danh_muc_theo_giai_doan.csv", index=False, encoding="utf-8-sig")

    roll = rolling_avg_corr(ret.loc[p["toan_ky"][0]:p["toan_ky"][1]], assets)
    for name, fig in [
        ("chan_doan_heatmap_2_giai_doan", plot_two_heatmaps(ret, p, assets)),
        ("chan_doan_tuong_quan_theo_thoi_gian", plot_rolling(roll, p, res)),
        ("chan_doan_bootstrap", plot_bootstrap(aux["draws"]["tuong_quan_trung_binh"],
                                               res[(res.thong_ke == "tuong_quan_trung_binh") & (res.do_dai_khoi == BLOCK)].iloc[0])),
        ("chan_doan_dong_gop_rui_ro", plot_risk_contrib(rc)),
    ]:
        fig.savefig(FIG / f"{name}.png", dpi=150)
        plt.close(fig)
    return {"test": res, "test_covid": res_covid, "context": ctx, "rc": rc, "portfolio": summ, "assets": assets}


if __name__ == "__main__":
    pd.set_option("display.width", 220, "display.max_columns", 30)
    out = run()
    print(f"Số mã so sánh: {len(out['assets'])}")
    print(out["test"][["thong_ke", "do_dai_khoi", "binh_thuong", "nam_2022", "hieu_2022_tru_binh_thuong",
                       "ci95_thap", "ci95_cao", "p_mot_phia_hieu_le_0"]].round(4).to_string(index=False))
    print("\nTHAM DÒ (làm thêm sau khi thấy kết quả chính; không thay H7):")
    print(out["test_covid"][["thong_ke", "binh_thuong", "nam_2022", "hieu_2022_tru_binh_thuong", "ci95_thap", "ci95_cao"]].round(4).to_string(index=False))
    print(out["context"].round(4).to_string(index=False))
    print(out["portfolio"].round(4).to_string(index=False))
    top = out["rc"][out["rc"].giai_doan == "nam_2022"].sort_values("dong_gop_rui_ro", ascending=False).head(5)
    print(top[["ma", "dong_gop_rui_ro"]].round(4).to_string(index=False))
