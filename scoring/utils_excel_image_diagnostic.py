"""
Excel 圖片嵌入診斷工具

此工具用於診斷 Spire.XLS 圖片對象的可用屬性，
幫助確定如何正確鎖定圖片到儲存格。
"""

try:
    from spire.xls import *
    from spire.xls.common import *
    SPIRE_XLS_AVAILABLE = True
except ImportError:
    SPIRE_XLS_AVAILABLE = False
    print("Spire.XLS 未安裝")


def diagnose_picture_properties():
    """診斷圖片對象的所有可用屬性"""
    if not SPIRE_XLS_AVAILABLE:
        print("Spire.XLS 未安裝，無法進行診斷")
        return
    
    # 創建測試工作簿
    workbook = Workbook()
    worksheet = workbook.Worksheets[0]
    
    # 創建一個臨時圖片文件（如果不存在）
    import tempfile
    import os
    from PIL import Image
    
    # 創建一個簡單的測試圖片
    temp_img = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
    img = Image.new('RGB', (100, 100), color='red')
    img.save(temp_img.name)
    temp_img.close()
    
    try:
        # 插入圖片
        picture = worksheet.Pictures.Add(1, 1, temp_img.name)
        
        print("=" * 80)
        print("Spire.XLS 圖片對象屬性診斷")
        print("=" * 80)
        print(f"\n圖片對象類型: {type(picture)}")
        print(f"圖片對象模組: {picture.__class__.__module__}")
        
        print("\n所有可用屬性:")
        print("-" * 80)
        attrs = dir(picture)
        for attr in sorted(attrs):
            if not attr.startswith('_'):
                try:
                    value = getattr(picture, attr)
                    if not callable(value):
                        print(f"  {attr:30s} = {value} (類型: {type(value).__name__})")
                except:
                    print(f"  {attr:30s} = <無法讀取>")
        
        print("\n關鍵屬性檢查:")
        print("-" * 80)
        key_attrs = {
            'Placement': '圖片放置模式',
            'placement': '圖片放置模式（小寫）',
            'TopLeftCell': '左上角儲存格',
            'top_left_cell': '左上角儲存格（小寫）',
            'BottomRightCell': '右下角儲存格',
            'bottom_right_cell': '右下角儲存格（小寫）',
            'Anchor': '錨點',
            'anchor': '錨點（小寫）',
            'Shape': '形狀對象',
            'shape': '形狀對象（小寫）',
            'Locked': '是否鎖定',
            'locked': '是否鎖定（小寫）',
            'LockAspectRatio': '鎖定寬高比',
            'lock_aspect_ratio': '鎖定寬高比（小寫）',
        }
        
        for attr, desc in key_attrs.items():
            if hasattr(picture, attr):
                try:
                    value = getattr(picture, attr)
                    print(f"  ✓ {attr:30s} = {value} ({desc})")
                except Exception as e:
                    print(f"  ✗ {attr:30s} = <錯誤: {str(e)}> ({desc})")
            else:
                print(f"  ✗ {attr:30s} = <不存在> ({desc})")
        
        print("\n嘗試設置 Placement 屬性:")
        print("-" * 80)
        # 嘗試不同的方法設置 Placement
        methods = [
            ("picture.Placement = 2", lambda: setattr(picture, 'Placement', 2)),
            ("picture.placement = 2", lambda: setattr(picture, 'placement', 2)),
            ("picture.Placement = PlacementType.MoveAndSize", 
             lambda: setattr(picture, 'Placement', PlacementType.MoveAndSize) if 'PlacementType' in globals() else None),
        ]
        
        for method_name, method_func in methods:
            try:
                method_func()
                if hasattr(picture, 'Placement'):
                    print(f"  ✓ {method_name:50s} -> 成功，值 = {picture.Placement}")
                elif hasattr(picture, 'placement'):
                    print(f"  ✓ {method_name:50s} -> 成功，值 = {picture.placement}")
                else:
                    print(f"  ? {method_name:50s} -> 執行成功但無法驗證")
            except Exception as e:
                print(f"  ✗ {method_name:50s} -> 失敗: {str(e)}")
        
        print("\n" + "=" * 80)
        print("診斷完成")
        print("=" * 80)
        
    finally:
        # 清理臨時文件
        try:
            os.unlink(temp_img.name)
        except:
            pass


if __name__ == '__main__':
    diagnose_picture_properties()

