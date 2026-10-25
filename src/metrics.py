"""Chỉ số hiệu quả DÙNG CHUNG cho cả nhóm. Chủ file: TV3.

Quy ước bắt buộc (khớp config.yaml):
- Đầu vào là chuỗi lợi suất NGÀY dạng thập phân (0.01 = 1%).
- 252 phiên/năm.
- rf: lãi suất phi rủi ro NĂM dạng thập phân, quy đổi sang ngày bằng (1+rf)**(1/252)-1.
Không ai được tự viết lại các hàm này ở file khác.
"""
import pandas as pd

TRADING_DAYS = 252


def annualized_return(r: pd.Series) -> float:
    """Lợi suất năm hóa hình học: (Π(1+r))**(252/n) - 1. TODO (TV3)."""
    raise NotImplementedError


def annualized_volatility(r: pd.Series) -> float:
    """Độ lệch chuẩn năm hóa: std(r) * sqrt(252). TODO (TV3)."""
    raise NotImplementedError


def sharpe_ratio(r: pd.Series, rf_annual: float | pd.Series) -> float:
    """(Lợi suất vượt rf trung bình ngày * 252) / (std lợi suất vượt * sqrt(252)). TODO (TV3)."""
    raise NotImplementedError


def sortino_ratio(r: pd.Series, rf_annual: float | pd.Series) -> float:
    """Như Sharpe nhưng mẫu số chỉ tính phần lợi suất dưới ngưỡng rf (downside deviation). TODO (TV3)."""
    raise NotImplementedError


def max_drawdown(r: pd.Series) -> float:
    """Mức giảm lớn nhất từ đỉnh xuống đáy của giá trị lũy kế, trả về số âm (vd -0.25). TODO (TV3)."""
    raise NotImplementedError


def turnover(w_new: pd.Series, w_drifted: pd.Series) -> float:
    """Vòng quay một lần tái cân bằng: 0.5 * Σ|w_new - w_drifted|. TODO (TV3)."""
    raise NotImplementedError


def summary(r: pd.Series, rf_annual) -> dict:
    """Gom các chỉ số trên thành một dict để in bảng. TODO (TV3)."""
    raise NotImplementedError
