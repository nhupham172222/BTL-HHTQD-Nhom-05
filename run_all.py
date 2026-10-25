"""Chạy toàn bộ pipeline từ dữ liệu gốc. Chủ file: TV5.

Thứ tự: đọc config → làm sạch dữ liệu → số liệu Lớp 1 → validation → test → độ nhạy → xuất outputs/.
Mỗi file trong outputs/ ghi kèm thời điểm chạy và config đã dùng.
"""
from src.data_loader import load_config


def main() -> None:
    config = load_config()
    # TODO (TV5): gọi lần lượt các bước khi các module đã xong
    print("Config đã đọc:", list(config.keys()))


if __name__ == "__main__":
    main()
