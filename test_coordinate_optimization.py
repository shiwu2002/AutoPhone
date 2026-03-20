#!/usr/bin/env python3
"""
坐标转换优化测试脚本

测试不同分辨率下的坐标转换精度和偏移效果
"""

from phone_agent.utils.resolution import (
    ResolutionConverter,
    CoordinateMapper,
    load_coordinate_config,
)

def test_coordinate_conversion():
    """测试坐标转换功能"""
    print("=" * 60)
    print("坐标转换优化测试")
    print("=" * 60)

    # 测试配置
    test_cases = [
        # (原始分辨率，1K 坐标点，描述)
        ((1080, 2400), (500, 500), "常见手机分辨率"),
        ((1440, 3200), (500, 500), "2K 屏"),
        ((720, 1600), (500, 500), "低分辨率"),
        ((1920, 1080), (500, 500), "横屏"),
    ]

    config = load_coordinate_config()
    print(f"\n当前配置：{config}\n")

    for original_res, point_1k, desc in test_cases:
        print(f"\n--- {desc} ---")
        print(f"原始分辨率：{original_res[0]}x{original_res[1]}")
        print(f"1K 坐标点：{point_1k}")

        # 创建模拟的 converter 和 mapper
        class MockConverter:
            def __init__(self, orig_w, orig_h):
                self.original_width = orig_w
                self.original_height = orig_h
                self.scale_ratio = min(1920/orig_w, 1080/orig_h, 1.0)
                self.scaled_width = int(orig_w * self.scale_ratio)
                self.scaled_height = int(orig_h * self.scale_ratio)

        converter = MockConverter(original_res[0], original_res[1])
        print(f"压缩后分辨率：{converter.scaled_width}x{converter.scaled_height}")

        mapper = CoordinateMapper(
            converter.original_width,
            converter.original_height,
            converter.scaled_width,
            converter.scaled_height,
            config
        )

        # 测试坐标转换
        orig_x, orig_y = mapper.to_original_coordinate(point_1k[0], point_1k[1])
        print(f"转换后原始坐标：({orig_x}, {orig_y})")

        # 测试区域转换
        x1, y1, x2, y2 = mapper.to_original_region(point_1k[0], point_1k[1])
        print(f"转换后区域：({x1}, {y1}) 到 ({x2}, {y2})")
        print(f"区域大小：{x2-x1}x{y2-y1} 像素")

        # 测试偏移量计算
        offset_x, offset_y = mapper.get_pixel_offset(point_1k[0], point_1k[1])
        print(f"像素偏移量：({offset_x:.3f}, {offset_y:.3f})")

        # 验证往返转换
        back_to_1k = mapper.to_1k_coordinate(orig_x, orig_y)
        print(f"往返转换验证：{back_to_1k} (原始 1K: {point_1k})")


def test_click_offset():
    """测试点击偏移效果"""
    print("\n" + "=" * 60)
    print("点击偏移效果测试")
    print("=" * 60)

    config = load_coordinate_config()
    mapper = CoordinateMapper(1080, 2400, 1080, 608, config)

    test_points = [
        (100, 100),
        (500, 500),
        (900, 500),
        (500, 300),
    ]

    print("\n不带偏移 vs 带偏移的对比：")
    print("-" * 50)

    for x_1k, y_1k in test_points:
        # 不带偏移
        x_no_offset, y_no_offset = mapper.to_original_coordinate(
            x_1k, y_1k, add_click_offset=False
        )

        # 带偏移
        x_offset, y_offset = mapper.to_original_coordinate(
            x_1k, y_1k, add_click_offset=True
        )

        print(f"1K({x_1k}, {y_1k}) -> "
              f"无偏移 ({x_no_offset}, {y_no_offset}) vs "
              f"有偏移 ({x_offset}, {y_offset})")
        print(f"     偏移量：+{x_offset - x_no_offset}, +{y_offset - y_no_offset} 像素")


if __name__ == "__main__":
    test_coordinate_conversion()
    test_click_offset()

    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
