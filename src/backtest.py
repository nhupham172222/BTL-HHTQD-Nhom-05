"""Backtest cuốn chiếu. Chủ file: TV5.

Quy trình mỗi quý (theo config.yaml):
1. Ngày quyết định = phiên cuối quý. Cắt dữ liệu cửa sổ 756 phiên KẾT THÚC tại ngày này.
2. Ước lượng μ, Σ (estimators) → tỷ trọng mục tiêu (optimizers).
3. Giao dịch tại giá đóng cửa phiên đầu quý sau: làm tròn xuống lô 100, trừ phí mỗi chiều và thuế khi bán, tiền dư lãi 0.
4. Nắm giữ đến kỳ sau; tỷ trọng trôi theo giá; ghi turnover (metrics.turnover).
Đầu ra: lợi suất ngày của từng chiến lược (trước và sau phí), tỷ trọng từng kỳ, số mã có w > 0.

Không bao giờ dùng dữ liệu sau ngày quyết định. Tập test chỉ chạy 1 lần sau khi đóng băng.
"""
import pandas as pd


def run_backtest(prices: pd.DataFrame, benchmark: pd.Series, rf: pd.DataFrame,
                 strategy: str, config: dict, start: str, end: str) -> dict:
    """TODO (TV5): trả về dict gồm returns_gross, returns_net, weights, turnover, n_holdings."""
    raise NotImplementedError
