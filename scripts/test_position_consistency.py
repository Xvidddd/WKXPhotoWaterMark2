#!/usr/bin/env python3
"""
测试脚本：验证预览界面与导出功能中水印位置计算是否一致
"""

import os
import sys
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QColor, QPainter, QFont
from PySide6.QtCore import QRectF

from app.ui.preview_view import PreviewView
from app.ui.main_window import MainWindow


def create_test_image(width=800, height=600, color=(255, 255, 255)):
    """创建测试图片"""
    img = Image.new("RGB", (width, height), color)
    return img


def test_position_consistency():
    """测试预览与导出位置一致性"""
    app = QApplication(sys.argv)
    
    # 创建测试图片
    test_img = create_test_image()
    temp_dir = tempfile.mkdtemp()
    test_path = os.path.join(temp_dir, "test.jpg")
    test_img.save(test_path)
    
    # 创建预览组件
    preview = PreviewView()
    preview.load_image(test_path)
    
    # 测试不同位置的水印设置
    test_positions = [
        "top_left", "top_center", "top_right",
        "center_left", "center", "center_right", 
        "bottom_left", "bottom_center", "bottom_right"
    ]
    
    results = {}
    
    for position in test_positions:
        print(f"\n测试位置: {position}")
        
        # 设置水印参数
        settings = {
            "wm_type": "text",
            "text": "TEST",
            "font_size": 32,
            "color": QColor(255, 0, 0),
            "opacity": 1.0,
            "margin": 20,
            "position": position,
            "shadow_enabled": False,
            "stroke_enabled": False
        }
        
        # 应用设置到预览
        preview.set_watermark_settings(settings)
        
        # 获取预览中水印位置
        if preview._wm_item is not None:
            preview_pos = preview._wm_item.pos()
            preview_rect = preview._wm_item.boundingRect()
            print(f"  预览位置: ({preview_pos.x():.1f}, {preview_pos.y():.1f})")
            print(f"  预览大小: {preview_rect.width():.1f} x {preview_rect.height():.1f}")
        else:
            print("  预览: 无水印项")
            continue
            
        # 获取导出图片
        export_img = preview.compose_qimage_for_path(test_path, settings)
        if export_img is None:
            print("  导出: 失败")
            continue
            
        # 分析导出图片中的水印位置（通过像素检测）
        export_pos = detect_watermark_position(export_img, QColor(255, 0, 0))
        if export_pos:
            print(f"  导出位置: ({export_pos[0]:.1f}, {export_pos[1]:.1f})")
            
            # 计算差异
            diff_x = abs(preview_pos.x() - export_pos[0])
            diff_y = abs(preview_pos.y() - export_pos[1])
            print(f"  位置差异: X={diff_x:.1f}, Y={diff_y:.1f}")
            
            results[position] = {
                "preview_pos": (preview_pos.x(), preview_pos.y()),
                "export_pos": export_pos,
                "diff": (diff_x, diff_y)
            }
        else:
            print("  导出: 未检测到水印")
    
    # 分析结果
    print("\n=== 位置一致性分析 ===")
    for pos, data in results.items():
        diff_x, diff_y = data["diff"]
        status = "一致" if diff_x < 5 and diff_y < 5 else "不一致"
        print(f"{pos:12}: {status} (偏移: X={diff_x:.1f}, Y={diff_y:.1f})")
    
    # 清理
    os.unlink(test_path)
    os.rmdir(temp_dir)
    app.quit()


def detect_watermark_position(qimage, target_color):
    """检测 QImage 中指定颜色的像素位置（简化的水印检测）"""
    width = qimage.width()
    height = qimage.height()
    
    # 扫描图像寻找目标颜色
    for y in range(height):
        for x in range(width):
            pixel_color = QColor(qimage.pixel(x, y))
            if (abs(pixel_color.red() - target_color.red()) < 10 and
                abs(pixel_color.green() - target_color.green()) < 10 and
                abs(pixel_color.blue() - target_color.blue()) < 10):
                return (x, y)  # 返回第一个匹配像素的位置
    
    return None


if __name__ == "__main__":
    test_position_consistency()