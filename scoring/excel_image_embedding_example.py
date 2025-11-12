"""
Excel 圖片嵌入儲存格 - 使用範例

此文件展示如何使用 utils_excel_image.py 中的工具來實現 Excel 儲存格圖片嵌入功能。
"""

from scoring.utils_excel_image import ExcelImageEmbedder, create_excel_with_embedded_images
import os


def example_1_basic_usage():
    """範例 1: 基本使用 - 單張圖片嵌入"""
    print("=" * 50)
    print("範例 1: 基本使用 - 單張圖片嵌入")
    print("=" * 50)
    
    # 創建 Excel 圖片嵌入工具
    embedder = ExcelImageEmbedder()
    
    # 獲取工作表（或使用默認工作表）
    worksheet = embedder.get_worksheet()
    worksheet.Name = "圖片範例"
    
    # 在 A1 儲存格插入圖片
    # 注意：請替換為實際的圖片路徑
    image_path = "media/route_photos/route_16_20251110_025239.jpeg"
    
    if os.path.exists(image_path):
        picture = embedder.insert_image_to_cell(
            image_path=image_path,
            row_index=1,      # 第 1 行
            column_index=1,   # 第 1 列（A 列）
            offset_x=2,       # 左邊距 2 像素
            offset_y=2,       # 上邊距 2 像素
            auto_resize_cell=True,  # 自動調整儲存格大小
            preserve_aspect_ratio=True  # 保持圖片寬高比
        )
        print(f"✓ 圖片已插入到 A1 儲存格: {image_path}")
    else:
        print(f"⚠ 圖片文件不存在: {image_path}")
        print("  請替換為實際的圖片路徑")
    
    # 保存 Excel 文件
    output_path = "output_example1_basic.xlsx"
    embedder.save(output_path)
    print(f"✓ Excel 文件已保存: {output_path}\n")


def example_2_multiple_images():
    """範例 2: 多張圖片嵌入 - 使用便捷函數"""
    print("=" * 50)
    print("範例 2: 多張圖片嵌入 - 使用便捷函數")
    print("=" * 50)
    
    # 準備圖片數據列表
    image_data_list = [
        {
            'image_path': 'media/route_photos/route_16_20251110_025239.jpeg',
            'row': 1,
            'column': 1,
            'offset_x': 2,
            'offset_y': 2,
            'auto_resize': True
        },
        {
            'image_path': 'media/route_photos/route_17_20251110_100306.jpeg',
            'row': 1,
            'column': 2,
            'offset_x': 2,
            'offset_y': 2,
            'auto_resize': True
        },
        {
            'image_path': 'media/route_photos/route_18_20251110_100330.jpeg',
            'row': 2,
            'column': 1,
            'offset_x': 5,  # 更大的邊距
            'offset_y': 5,
            'auto_resize': True
        }
    ]
    
    # 過濾存在的圖片
    existing_images = [img for img in image_data_list if os.path.exists(img['image_path'])]
    
    if existing_images:
        create_excel_with_embedded_images(
            output_path='output_example2_multiple.xlsx',
            image_data_list=existing_images,
            sheet_name='多張圖片'
        )
        print(f"✓ 已插入 {len(existing_images)} 張圖片\n")
    else:
        print("⚠ 沒有找到可用的圖片文件")
        print("  請確認圖片路徑是否正確\n")


def example_3_custom_cell_size():
    """範例 3: 自定義儲存格大小後插入圖片"""
    print("=" * 50)
    print("範例 3: 自定義儲存格大小後插入圖片")
    print("=" * 50)
    
    embedder = ExcelImageEmbedder()
    worksheet = embedder.get_worksheet()
    worksheet.Name = "自定義大小"
    
    # 先設置儲存格大小（單位：點，1 點 = 1/72 英寸）
    # 例如：設置 A1 為寬 200 點，高 150 點
    embedder.set_cell_size(
        row_index=1,
        column_index=1,
        width_points=200,   # 約 2.78 英寸寬
        height_points=150   # 約 2.08 英寸高
    )
    
    # 在已設置大小的儲存格中插入圖片
    image_path = "media/route_photos/route_16_20251110_025239.jpeg"
    if os.path.exists(image_path):
        # 不自動調整儲存格，使用已設置的大小
        picture = embedder.insert_image_to_cell(
            image_path=image_path,
            row_index=1,
            column_index=1,
            offset_x=5,
            offset_y=5,
            auto_resize_cell=False,  # 不自動調整
            preserve_aspect_ratio=True
        )
        print(f"✓ 圖片已插入到自定義大小的 A1 儲存格")
    else:
        print(f"⚠ 圖片文件不存在: {image_path}")
    
    embedder.save('output_example3_custom_size.xlsx')
    print(f"✓ Excel 文件已保存: output_example3_custom_size.xlsx\n")


def example_4_grid_layout():
    """範例 4: 網格佈局 - 創建圖片網格"""
    print("=" * 50)
    print("範例 4: 網格佈局 - 創建圖片網格")
    print("=" * 50)
    
    embedder = ExcelImageEmbedder()
    worksheet = embedder.get_worksheet()
    worksheet.Name = "圖片網格"
    
    # 獲取可用的圖片文件
    route_photos_dir = "media/route_photos"
    if os.path.exists(route_photos_dir):
        image_files = [
            f for f in os.listdir(route_photos_dir)
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp'))
        ][:9]  # 只取前 9 張，創建 3x3 網格
        
        if image_files:
            row = 1
            col = 1
            for idx, img_file in enumerate(image_files):
                image_path = os.path.join(route_photos_dir, img_file)
                
                embedder.insert_image_to_cell(
                    image_path=image_path,
                    row_index=row,
                    column_index=col,
                    offset_x=2,
                    offset_y=2,
                    auto_resize_cell=True
                )
                
                # 移動到下一個位置（3 列後換行）
                col += 1
                if col > 3:
                    col = 1
                    row += 1
            
            embedder.save('output_example4_grid.xlsx')
            print(f"✓ 已創建 {len(image_files)} 張圖片的網格佈局")
            print(f"✓ Excel 文件已保存: output_example4_grid.xlsx\n")
        else:
            print("⚠ 在 media/route_photos 目錄中未找到圖片文件\n")
    else:
        print(f"⚠ 目錄不存在: {route_photos_dir}\n")


def example_5_with_text():
    """範例 5: 圖片與文字結合 - 在圖片旁邊添加說明文字"""
    print("=" * 50)
    print("範例 5: 圖片與文字結合")
    print("=" * 50)
    
    embedder = ExcelImageEmbedder()
    worksheet = embedder.get_worksheet()
    worksheet.Name = "圖片與文字"
    
    # 在 A1 插入圖片
    image_path = "media/route_photos/route_16_20251110_025239.jpeg"
    if os.path.exists(image_path):
        embedder.insert_image_to_cell(
            image_path=image_path,
            row_index=1,
            column_index=1,
            offset_x=2,
            offset_y=2,
            auto_resize_cell=True
        )
        
        # 在 B1 添加說明文字
        cell_b1 = worksheet.Range[1, 2]
        cell_b1.Text = "路線照片 #16"
        cell_b1.Style.Font.Size = 12
        cell_b1.Style.Font.IsBold = True
        cell_b1.Style.VerticalAlignment = VerticalAlignType.Center
        
        # 設置 B 列寬度
        worksheet.SetColumnWidth(2, 2, 150)
        
        print("✓ 圖片和文字已添加")
    else:
        print(f"⚠ 圖片文件不存在: {image_path}")
    
    embedder.save('output_example5_with_text.xlsx')
    print(f"✓ Excel 文件已保存: output_example5_with_text.xlsx\n")


def main():
    """運行所有範例"""
    print("\n" + "=" * 50)
    print("Excel 圖片嵌入儲存格 - 使用範例")
    print("=" * 50 + "\n")
    
    try:
        # 檢查 Spire.XLS 是否可用
        from scoring.utils_excel_image import SPIRE_XLS_AVAILABLE
        if not SPIRE_XLS_AVAILABLE:
            print("❌ 錯誤: Spire.XLS for Python 未安裝")
            print("   請執行: pip install Spire.XLS")
            return
        
        # 運行範例
        example_1_basic_usage()
        example_2_multiple_images()
        example_3_custom_cell_size()
        example_4_grid_layout()
        example_5_with_text()
        
        print("=" * 50)
        print("所有範例執行完成！")
        print("=" * 50)
        print("\n提示:")
        print("- 如果圖片文件不存在，請替換為實際的圖片路徑")
        print("- 生成的 Excel 文件保存在當前目錄")
        print("- 可以在 Excel 中打開查看效果\n")
        
    except Exception as e:
        print(f"❌ 發生錯誤: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

