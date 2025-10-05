from typing import Any, Dict
from PySide6.QtGui import QColor

def qcolor_to_hex(value: Any) -> str:
    if isinstance(value, QColor):
        return value.name()
    if isinstance(value, str):
        return value
    return QColor(0, 0, 0).name()

def hex_to_qcolor(value: Any) -> QColor:
    if isinstance(value, QColor):
        return value
    try:
        c = QColor(str(value))
        return c if c.isValid() else QColor(0, 0, 0)
    except Exception:
        return QColor(0, 0, 0)

def normalize_settings_for_save(settings: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(settings)
    # 颜色转为十六进制字符串
    data["color"] = qcolor_to_hex(data.get("color"))
    # 处理阴影和描边颜色
    data["shadow_color"] = qcolor_to_hex(data.get("shadow_color"))
    data["stroke_color"] = qcolor_to_hex(data.get("stroke_color"))
    return data

def normalize_settings_for_load(settings: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(settings)
    data["color"] = hex_to_qcolor(data.get("color"))
    # 处理阴影和描边颜色
    data["shadow_color"] = hex_to_qcolor(data.get("shadow_color"))
    data["stroke_color"] = hex_to_qcolor(data.get("stroke_color"))
    # 保持其余字段原样（text, font_size, opacity, margin, position, pos_x_pct/pos_y_pct）
    return data