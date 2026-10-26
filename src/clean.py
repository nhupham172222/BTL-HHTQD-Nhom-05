"""ETL 4 bước: dữ liệu thô (data/raw) -> dữ liệu sạch (data/processed) + Nhật ký ETL.

Bước 1  Chuẩn hóa      : tên cột, kiểu ngày, đơn vị giá (về VND), bỏ trùng ngày, giá <= 0 -> NaN
Bước 2  Căn lịch       : lịch chung = các phiên của VN-Index; mọi mã reindex theo lịch này
Bước 3  Xử lý thiếu    : điền giá phiên trước tối đa MAX_FFILL phiên + cột cờ imputed;
                         thiếu dài hơn -> giữ NaN và ghi lại
Bước 4  Kiểm tra cuối  : loại mã thiếu lịch sử / còn NaN, kiểm tra nhảy giá > 7% (nghi chưa điều chỉnh)

Đầu ra:
  data/processed/prices.csv          giá đóng cửa (VND), cột = mã còn lại, dòng = ngày
  data/processed/prices_imputed.csv  cờ 1 = giá ô đó được điền từ phiên trước
  data/processed/vnindex.csv         VN-Index đóng cửa
  data/processed/rf.csv              lãi suất phi rủi ro: date, rf_annual, rf_daily, rf_annual_avg_year
  data/processed/etl_log.json        số liệu thô của nhật ký
  05_Phu_luc/Nhat_ky_ETL.md          nhật ký ETL dạng văn bản (dán lên Drive)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from config import load as _load_cfg  # noqa: E402

_CFG = _load_cfg()
START = pd.Timestamp(_CFG["data"]["start"])                        # A14
END = pd.Timestamp(_CFG["data"]["end"])
HISTORY_FROM = pd.Timestamp(_CFG["universe"]["require_history_from"])  # A1/A14
MAX_FFILL = int(_CFG["data"]["max_ffill_days"])                    # điền tối đa N phiên
TRADING_DAYS = int(_CFG["conventions"]["trading_days_per_year"])
INDEX_SYMBOL = _CFG["data"]["benchmark"]
# Ngưỡng kỹ thuật của bước kiểm tra dữ liệu (không phải giả định mô hình):
HISTORY_TOLERANCE = 10   # ngày: dữ liệu đầu tiên sau HISTORY_FROM + 10 ngày -> thiếu lịch sử
END_TOLERANCE = 10       # ngày: dữ liệu cuối trước END - 10 ngày -> nghi hủy niêm yết
JUMP_THRESHOLD = 0.075   # HOSE biên độ ±7% (làm tròn bước giá có thể tới ~7,2%) -> >7,5%/ngày mới nghi chưa điều chỉnh
FIRST_DECISION = pd.Timestamp(_CFG["periods"]["validation"][0])  # kỳ quyết định đầu tiên của backtest


# ---------------------------------------------------------------- bước 1
def _read_price_file(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    t = pd.to_datetime(df["time"], errors="coerce", utc=True)   # vnstock trả "2025-09-30 07:00:00+07:00"
    df["time"] = t.dt.tz_convert("Asia/Ho_Chi_Minh").dt.tz_localize(None).dt.normalize()  # về ngày thuần
    df = df.dropna(subset=["time"]).sort_values("time")
    return df


def standardize_one(path: Path) -> tuple[pd.Series, dict]:
    """Trả về chuỗi close (VND, index = ngày) và dict thống kê cho nhật ký."""
    raw = _read_price_file(path)
    n_raw = len(raw)
    dup = int(raw["time"].duplicated().sum())
    raw = raw.drop_duplicates(subset="time", keep="last")
    s = pd.to_numeric(raw["close"], errors="coerce")
    s.index = raw["time"]
    nonpos = int((s <= 0).sum())
    s[s <= 0] = np.nan

    # Đơn vị: vnstock thường trả nghìn đồng (vd 95.3). Cổ phiếu VN30 hiếm khi < 1.000 đồng/cp.
    median = float(s.median())
    scaled = False
    if median < 1000:
        s = s * 1000.0
        scaled = True
    s = s[(s.index >= START) & (s.index <= END)]
    return s, {"rows_raw": n_raw, "dup_dates": dup, "nonpositive": nonpos, "scaled_x1000": scaled,
               "first_date": str(s.dropna().index.min().date()) if s.notna().any() else None,
               "last_date": str(s.dropna().index.max().date()) if s.notna().any() else None}


# ---------------------------------------------------------------- bước 3 helper
def _gap_runs(series: pd.Series) -> list[tuple[str, str, int]]:
    """Các đoạn NaN liên tiếp (sau ngày có dữ liệu đầu tiên): (từ, đến, số phiên)."""
    first = series.first_valid_index()
    if first is None:
        return []
    s = series.loc[first:]
    isna = s.isna()
    runs, start, count = [], None, 0
    for d, flag in isna.items():
        if flag:
            if start is None:
                start = d
            count += 1
            last = d
        elif start is not None:
            runs.append((str(start.date()), str(last.date()), count))
            start, count = None, 0
    if start is not None:
        runs.append((str(start.date()), str(last.date()), count))
    return runs


# ---------------------------------------------------------------- đọc file tải tay (Investing EN/VN)
_DATE_COLS = ("date", "ngày", "time")
_VALUE_COLS = ("yield_pct", "price", "lần cuối", "close", "yield")


def _parse_dates(col: pd.Series) -> pd.Series:
    """Chọn đúng định dạng ngày (Investing EN: tháng/ngày/năm; VN: ngày/tháng/năm), báo lỗi nếu mơ hồ."""
    col = col.astype(str).str.strip()
    cands = {}
    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d", "%d.%m.%Y", "%b %d, %Y"):
        d = pd.to_datetime(col, format=fmt, errors="coerce")
        if d.notna().mean() > 0.99:
            cands[fmt] = d
    if not cands:
        raise ValueError(f"Không nhận ra định dạng ngày, ví dụ: {col.iloc[:3].tolist()}")
    if len(cands) > 1 and not all((v == list(cands.values())[0]).all() for v in cands.values()):
        raise ValueError(f"Định dạng ngày mơ hồ {list(cands)} – kiểm tra file, ví dụ: {col.iloc[:3].tolist()}")
    return list(cands.values())[0]


def _parse_numbers(col: pd.Series) -> pd.Series:
    """Đọc số theo quy ước của CẢ FILE: '1,234.56' (EN) hoặc '1.234,56' / '4,581' (VN, phẩy thập phân)."""
    s = col.astype(str).str.strip().str.replace("%", "", regex=False).str.replace("\u00a0", "", regex=False)
    both = s[s.str.contains(",") & s.str.contains(r"\.")]
    if len(both):
        decimal_comma = (both.str.rfind(",") > both.str.rfind(".")).mean() > 0.5
    elif s.str.contains(",").any():
        # chỉ có dấu phẩy: Investing VN ghi lợi suất '4,581' (phẩy thập phân); EN không bao giờ ghi số không có '.'
        decimal_comma = True
    else:
        decimal_comma = False
    if decimal_comma:
        s = s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    else:
        s = s.str.replace(",", "", regex=False)
    return pd.to_numeric(s, errors="coerce")


def read_manual_series(path: Path) -> pd.Series:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip().lower() for c in df.columns]
    dcol = next((c for c in _DATE_COLS if c in df.columns), df.columns[0])
    vcol = next((c for c in _VALUE_COLS if c in df.columns), df.columns[1])
    v = _parse_numbers(df[vcol])
    v.index = _parse_dates(df[dcol])
    v = v[~v.index.isna()].sort_index()
    return v[~v.index.duplicated(keep="last")].dropna()


# ---------------------------------------------------------------- rf
def build_rf(raw_dir: Path, calendar: pd.DatetimeIndex) -> tuple[pd.DataFrame, dict]:
    path = raw_dir / "tpcp10y.csv"
    if not path.exists():
        raise FileNotFoundError(f"Thiếu {path}. Tải tay lợi suất TPCP 10 năm (xem src/data_loader.py::check_tpcp_file).")
    y = read_manual_series(path)
    n_src = len(y)
    # Đồng bộ lịch: lấy giá trị gần nhất trước/ngày đó (không nhìn trước tương lai)
    y = y.reindex(y.index.union(calendar)).sort_index().ffill().reindex(calendar)
    n_before_first = int(y.isna().sum())
    y = y.bfill(limit=MAX_FFILL)
    if y.isna().any() or n_src < 0.5 * len(calendar) / 5:
        raise ValueError(
            f"File TPCP chỉ có {n_src} dòng, không phủ giai đoạn {calendar.min().date()} → {calendar.max().date()} "
            f"({int(y.isna().sum())}/{len(calendar)} phiên không có rf). Tải lại tpcp10y.csv với khoảng ngày đầy đủ "
            "(Investing: chọn Daily + đặt ngày bắt đầu/kết thúc trước khi bấm Download).")
    out = pd.DataFrame({"rf_annual": y / 100.0})
    out["rf_daily"] = (1.0 + out["rf_annual"]) ** (1.0 / TRADING_DAYS) - 1.0
    # A9 "bình quân theo năm": trung bình lợi suất trong năm dương lịch (dùng khi tính Sharpe/Sortino theo năm).
    # Khi ra quyết định tại ngày t (CAPM) phải dùng rf_annual tại t, không dùng cột này (tránh nhìn trước tương lai).
    out["rf_annual_avg_year"] = out.groupby(out.index.year)["rf_annual"].transform("mean")
    out.index.name = "date"
    info = {"rows_source": n_src, "calendar_days": len(calendar), "na_after_fill": int(out["rf_annual"].isna().sum()),
            "na_before_first_obs": n_before_first,
            "rf_annual_min": float(out["rf_annual"].min()), "rf_annual_max": float(out["rf_annual"].max())}
    return out, info


# ---------------------------------------------------------------- main
def run(raw_dir: Path = ROOT / "data" / "raw",
        out_dir: Path = ROOT / "data" / "processed",
        doc_dir: Path = ROOT / "05_Phu_luc") -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    doc_dir.mkdir(parents=True, exist_ok=True)
    universe = pd.read_csv(raw_dir / "vn30_2020.csv")["ticker"].astype(str).str.upper().tolist()
    log: dict = {"universe_size": len(universe), "window": [str(START.date()), str(END.date())],
                 "max_ffill": MAX_FFILL, "per_ticker": {}, "excluded": {}, "notes": []}

    # --- VN-Index quyết định lịch chung
    idx_path = raw_dir / f"{INDEX_SYMBOL.lower()}.csv"
    if not idx_path.exists():
        raise FileNotFoundError(f"Thiếu {idx_path}")
    idx_raw = _read_price_file(idx_path)
    idx_raw = idx_raw.drop_duplicates(subset="time", keep="last")
    vnindex = pd.to_numeric(idx_raw["close"], errors="coerce")
    vnindex.index = idx_raw["time"]
    vnindex = vnindex[(vnindex.index >= START) & (vnindex.index <= END) & (vnindex > 0)]
    calendar = vnindex.index   # lịch giao dịch luôn lấy từ file vnstock
    # vnstock (nguồn VCI) trả VN-Index theo nghìn điểm, làm tròn 2 chữ số (vd 0.91 = 910 ± 5 điểm)
    # -> lợi suất ngày bị "bậc thang" ~1%, KHÔNG dùng được cho beta/Sharpe. Nếu có file thủ công
    # data/raw/vnindex_manual.csv (vd xuất từ Investing: Date, Price) thì lấy giá trị từ file đó.
    manual = raw_dir / "vnindex_manual.csv"
    if manual.exists():
        mv = read_manual_series(manual)
        vnindex = mv.reindex(calendar).ffill(limit=MAX_FFILL)
        log["vnindex_source"] = f"vnindex_manual.csv ({int(mv.reindex(calendar).notna().sum())}/{len(calendar)} phiên khớp lịch)"
        log["vnindex_low_precision"] = False
    else:
        log["vnindex_source"] = "vnstock"
        log["vnindex_low_precision"] = bool(vnindex.median() < 100)
        if log["vnindex_low_precision"]:
            vnindex = vnindex * 1000.0
            log["notes"].append("CẢNH BÁO: VN-Index từ vnstock chỉ chính xác tới ±5 điểm (nghìn điểm, 2 chữ số) – "
                                "lợi suất ngày của VN-Index không tin cậy. Cần thêm data/raw/vnindex_manual.csv.")
    log["vnindex_scaled_x1000"] = log["vnindex_low_precision"]
    log["vnindex_range"] = [round(float(vnindex.min()), 2), round(float(vnindex.max()), 2)]
    log["calendar"] = {"trading_days": len(calendar), "first": str(calendar.min().date()), "last": str(calendar.max().date())}

    # --- bước 1 + 2 cho từng mã
    series: dict[str, pd.Series] = {}
    for t in universe:
        p = raw_dir / f"px_{t}.csv"
        if not p.exists():
            log["excluded"][t] = "không có file dữ liệu thô"
            continue
        s, st = standardize_one(p)
        s = s.reindex(calendar)           # bước 2: căn lịch
        st["rows_after_calendar"] = int(s.notna().sum())
        log["per_ticker"][t] = st
        series[t] = s

    # --- bước 3: xử lý thiếu
    prices, flags = {}, {}
    for t, s in series.items():
        first = s.first_valid_index()
        last = s.last_valid_index()
        st = log["per_ticker"][t]
        if first is None:
            log["excluded"][t] = "toàn bộ giá rỗng"
            continue
        # Chỉ điền trong khoảng [first, last]; không điền trước ngày niêm yết / sau ngày hủy
        filled = s.copy()
        inside = filled.loc[first:last]
        na_before = int(inside.isna().sum())
        inside_f = inside.ffill(limit=MAX_FFILL)
        filled.loc[first:last] = inside_f
        flag = (s.isna() & filled.notna()).astype(int)
        st["imputed_cells"] = int(flag.sum())
        st["na_before_fill_inside"] = na_before
        # độ dài thật của đoạn thiếu tính trên chuỗi trước khi điền, chỉ trong khoảng [first, last]
        st["gaps_over_limit"] = [g for g in _gap_runs(s.loc[first:last]) if g[2] > MAX_FFILL]
        prices[t] = filled
        flags[t] = flag

    P = pd.DataFrame(prices)
    F = pd.DataFrame(flags)

    # --- bước 4: kiểm tra cuối + loại mã
    events: list[dict] = []
    for t in list(P.columns):
        s = P[t]
        st = log["per_ticker"][t]
        first, last = s.first_valid_index(), s.last_valid_index()
        reasons = []
        if first > HISTORY_FROM + pd.Timedelta(days=HISTORY_TOLERANCE):
            reasons.append(f"thiếu lịch sử: dữ liệu bắt đầu {first.date()} (> {HISTORY_FROM.date()} + {HISTORY_TOLERANCE} ngày)")
        if last < END - pd.Timedelta(days=END_TOLERANCE):
            if last < FIRST_DECISION:
                reasons.append(f"dữ liệu dừng {last.date()}, trước kỳ quyết định đầu {FIRST_DECISION.date()}")
            else:
                # KHÔNG loại khỏi file: loại mã hủy niêm yết khỏi toàn bộ giai đoạn = thiên lệch sống sót.
                # Giữ giá tới ngày cuối, sau đó NaN; backtest bán/loại mã ở kỳ tái cân bằng kế tiếp.
                events.append({"ticker": t, "event": "dung_giao_dich", "start": str(last.date()), "end": "",
                               "sessions": int(s.loc[last:].iloc[1:].shape[0]), "last_close": float(s.loc[last]),
                               "note": "giữ trong prices.csv, NaN sau ngày cuối; loại ở kỳ tái cân bằng kế tiếp"})
        for g in st["gaps_over_limit"]:
            if pd.Timestamp(g[1]) < FIRST_DECISION:
                reasons.append(f"đoạn thiếu {g[2]} phiên ({g[0]} → {g[1]}) trước kỳ quyết định đầu → không đủ giá liên tục (A1)")
            else:
                events.append({"ticker": t, "event": "thieu_dai", "start": g[0], "end": g[1], "sessions": g[2],
                               "last_close": float("nan"), "note": "giữ NaN; loại ở kỳ tái cân bằng kế tiếp"})
        # nhảy giá nghi chưa điều chỉnh
        ret = s.pct_change(fill_method=None)
        jumps = ret[ret.abs() > JUMP_THRESHOLD]
        st["jumps_over_limit"] = [(str(d.date()), round(float(v), 4)) for d, v in jumps.items()]
        if reasons:
            log["excluded"][t] = "; ".join(reasons)
    keep = [t for t in P.columns if t not in log["excluded"]]
    P, F = P[keep], F[keep]
    log["kept"] = keep
    log["final_shape"] = {"rows": int(P.shape[0]), "tickers": int(P.shape[1])}
    log["final_na_cells"] = int(P.isna().sum().sum())
    log["final_imputed_cells"] = int(F.values.sum())
    suspect = {t: log["per_ticker"][t]["jumps_over_limit"] for t in keep if log["per_ticker"][t]["jumps_over_limit"]}
    log["suspect_unadjusted"] = suspect
    events = [e for e in events if e["ticker"] in keep]
    log["events"] = events
    if log["final_na_cells"]:
        log["notes"].append("Ô NaN còn lại thuộc các sự kiện trong data/processed/events.csv (mã ngừng giao dịch/thiếu dài "
                            "sau kỳ quyết định đầu). Backtest (TV5) phải bán/loại các mã này ở kỳ tái cân bằng kế tiếp.")

    # --- rf
    rf, rf_info = build_rf(raw_dir, calendar)
    log["rf"] = rf_info

    # --- ghi file
    P.index.name = F.index.name = "date"
    P.to_csv(out_dir / "prices.csv", float_format="%.2f")
    F.to_csv(out_dir / "prices_imputed.csv")
    vnindex.rename("close").to_frame().rename_axis("date").to_csv(out_dir / "vnindex.csv", float_format="%.2f")
    rf.to_csv(out_dir / "rf.csv", float_format="%.8f")
    pd.DataFrame(events, columns=["ticker", "event", "start", "end", "sessions", "last_close", "note"]).to_csv(
        out_dir / "events.csv", index=False)
    (out_dir / "etl_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    md = render_log_md(log)
    notes = doc_dir / "ghi_chu_thu_cong.md"   # ghi chú tay của TV2, không bị ghi đè
    if notes.exists():
        md += "\n" + notes.read_text(encoding="utf-8").replace("# Ghi chú thủ công", "## Ghi chú thủ công", 1)
    (doc_dir / "Nhat_ky_ETL.md").write_text(md, encoding="utf-8")
    return log


def render_log_md(log: dict) -> str:
    L = ["# Nhật ký ETL", "",
         f"- Cửa sổ dữ liệu: {log['window'][0]} → {log['window'][1]}",
         f"- Lịch giao dịch chung (theo VN-Index): {log['calendar']['trading_days']} phiên "
         f"({log['calendar']['first']} → {log['calendar']['last']})",
         f"- Vũ trụ ban đầu: {log['universe_size']} mã (VN30 kỳ 01/2020) | giữ lại: {log['final_shape']['tickers']} mã",
         f"- Quy tắc điền thiếu: ffill tối đa {log['max_ffill']} phiên + cột cờ `imputed` (file prices_imputed.csv)",
         f"- Số ô giá được điền: {log['final_imputed_cells']} | ô NaN còn lại: {log['final_na_cells']}",
         f"- VN-Index: nguồn {log.get('vnindex_source')}{' – ĐỘ CHÍNH XÁC THẤP (±5 điểm), cần vnindex_manual.csv' if log.get('vnindex_low_precision') else ''}; "
         f"khoảng {log.get('vnindex_range')} điểm", "",
         "## Quy tắc làm sạch (4 bước)",
         "1. Chuẩn hóa: tên cột thường, ngày dạng datetime, bỏ ngày trùng (giữ bản cuối), giá ≤ 0 → NaN, "
         "nếu trung vị giá < 1.000 thì nhân 1.000 (nghìn đồng → VND).",
         "2. Căn lịch: reindex theo các phiên của VN-Index.",
         f"3. Xử lý thiếu: điền giá phiên trước tối đa {log['max_ffill']} phiên (chỉ trong khoảng đã niêm yết), gắn cờ imputed; "
         "thiếu dài hơn giữ NaN và ghi lại.",
         "4. Kiểm tra cuối: loại mã thiếu lịch sử hoặc thiếu dài trước kỳ quyết định đầu; mã ngừng giao dịch/thiếu dài sau đó được GIỮ (tránh thiên lệch sống sót) và ghi vào events.csv; quét biến động ngày > 7,5% (vượt biên độ ±7%) để nghi ngờ giá chưa điều chỉnh.", "",
         "## Số dòng trước/sau theo mã",
         "| Mã | Dòng thô | Trùng ngày | Giá ≤0 | Nhân 1000 | Dòng sau căn lịch | Ô điền (imputed) | Trạng thái |",
         "|---|---|---|---|---|---|---|---|"]
    for t, st in log["per_ticker"].items():
        status = "LOẠI: " + log["excluded"][t] if t in log["excluded"] else "giữ"
        L.append(f"| {t} | {st['rows_raw']} | {st['dup_dates']} | {st['nonpositive']} | {'có' if st['scaled_x1000'] else 'không'} "
                 f"| {st['rows_after_calendar']} | {st.get('imputed_cells', 0)} | {status} |")
    miss = {t: r for t, r in log["excluded"].items() if t not in log["per_ticker"]}
    for t, r in miss.items():
        L.append(f"| {t} | - | - | - | - | - | - | LOẠI: {r} |")
    L += ["", "## Mã bị loại và lý do"]
    L += [f"- **{t}**: {r}" for t, r in log["excluded"].items()] or ["- (không có)"]
    L += ["", "## Sự kiện giữ lại trong dữ liệu (data/processed/events.csv)"]
    L += [f"- **{e['ticker']}** – {e['event']}: từ {e['start']} {('đến ' + e['end']) if e['end'] else ''} "
          f"({e['sessions']} phiên). {e['note']}" for e in log.get("events", [])] or ["- (không có)"]
    L += ["", f"## Mã nghi chưa điều chỉnh giá (biến động > {JUMP_THRESHOLD:.1%}/ngày, vượt biên độ ±7% HOSE) — cần đối chiếu tay",
          *( [f"- **{t}**: {v[:5]}" for t, v in log["suspect_unadjusted"].items()] or ["- (không phát hiện)"] ), "",
          "## Lãi suất phi rủi ro (TPCP 10 năm)", f"- {json.dumps(log['rf'], ensure_ascii=False)}", ""]
    if log["notes"]:
        L += ["## Ghi chú", *[f"- {n}" for n in log["notes"]], ""]
    return "\n".join(L)


if __name__ == "__main__":
    out = run()
    print(f"Giữ {out['final_shape']['tickers']}/{out['universe_size']} mã, {out['final_shape']['rows']} phiên.")
    print("Loại:", out["excluded"] or "không")
    print("Nghi chưa điều chỉnh giá:", list(out["suspect_unadjusted"]) or "không")
