"""
Excel 圖片嵌入儲存格工具
使用 Spire.XLS for Python 實現圖片精準嵌入 Excel 儲存格的功能

功能特點：
- 在指定儲存格插入圖片
- 自動調整圖片尺寸匹配儲存格
- 調整儲存格列寬與行高
- 設置圖片與儲存格邊界的偏移距離
- 支援多種圖片格式（PNG, JPEG, BMP, GIF 等）
"""

try:
    from spire.xls import *
    from spire.xls.common import *
    SPIRE_XLS_AVAILABLE = True
except ImportError:
    SPIRE_XLS_AVAILABLE = False
    # 不在此處打印，由調用者處理


class ExcelImageEmbedder:
    """Excel 圖片嵌入工具類"""
    
    def __init__(self, workbook_path=None):
        """
        初始化 Excel 圖片嵌入工具
        
        Args:
            workbook_path: 可選，現有 Excel 文件路徑。如果為 None，則創建新工作簿
        """
        if not SPIRE_XLS_AVAILABLE:
            raise ImportError("Spire.XLS for Python 未安裝。請執行: pip install Spire.XLS")
        
        self.workbook = Workbook()
        
        if workbook_path:
            self.workbook.LoadFromFile(workbook_path)
        else:
            # 創建新工作簿，添加默認工作表
            self.workbook.Worksheets[0].Name = "Sheet1"
        
        self.worksheet = self.workbook.Worksheets[0]
    
    def _diagnose_picture_properties(self, picture):
        """
        診斷圖片對象的可用屬性（用於調試）
        
        此方法會列出圖片對象的所有可用屬性和方法，
        幫助確定哪些屬性可以用來鎖定圖片到儲存格。
        """
        import logging
        logger = logging.getLogger(__name__)
        
        logger.debug("=== 圖片對象屬性診斷 ===")
        logger.debug(f"圖片對象類型: {type(picture)}")
        logger.debug(f"圖片對象屬性: {dir(picture)}")
        
        # 檢查關鍵屬性是否存在
        key_attributes = [
            'Placement', 'placement',
            'TopLeftCell', 'top_left_cell',
            'BottomRightCell', 'bottom_right_cell',
            'Anchor', 'anchor',
            'Shape', 'shape',
            'Locked', 'locked',
            'LockAspectRatio', 'lock_aspect_ratio'
        ]
        
        available_attrs = []
        for attr in key_attributes:
            if hasattr(picture, attr):
                try:
                    value = getattr(picture, attr)
                    available_attrs.append(f"{attr} = {value} (類型: {type(value)})")
                except:
                    available_attrs.append(f"{attr} (存在但無法讀取)")
        
        if available_attrs:
            logger.debug("可用的關鍵屬性:")
            for attr in available_attrs:
                logger.debug(f"  - {attr}")
        else:
            logger.debug("未找到任何關鍵屬性")
        
        logger.debug("=== 診斷結束 ===")
    
    def _lock_picture_to_cell(self, picture, cell_range, row_index, column_index):
        """
        鎖定圖片到儲存格的多種策略
        
        此方法嘗試多種方法來確保圖片鎖定到儲存格，無法自由移動：
        1. 設置 Placement 屬性為 MoveAndSize
        2. 設置 TopLeftCell 和 BottomRightCell（如果可用）
        3. 設置 Anchor 屬性（如果可用）
        4. 使用其他可能的鎖定方法
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # 可選：啟用診斷模式（僅在調試時使用）
        # self._diagnose_picture_properties(picture)
        
        # 策略 1: 設置 Placement 屬性
        placement_set = False
        try:
            # 嘗試使用 PlacementType 枚舉
            try:
                from spire.xls.common import PlacementType
                picture.Placement = PlacementType.MoveAndSize
                placement_set = True
                logger.debug("成功使用 PlacementType.MoveAndSize 設置 Placement")
            except (ImportError, NameError, AttributeError):
                # 嘗試直接使用整數值
                try:
                    picture.Placement = 2  # MoveAndSize
                    placement_set = True
                    logger.debug("成功使用整數值 2 設置 Placement")
                except AttributeError:
                    # 嘗試使用小寫屬性名
                    try:
                        picture.placement = 2
                        placement_set = True
                        logger.debug("成功使用小寫屬性名設置 Placement")
                    except AttributeError:
                        logger.warning("無法設置 Placement 屬性（所有方法都失敗）")
        except Exception as e:
            logger.warning(f"設置 Placement 屬性時發生錯誤: {str(e)}")
        
        # 策略 2: 設置 TopLeftCell 和 BottomRightCell（如果可用）
        # 這兩個屬性可以將圖片錨定到特定儲存格
        try:
            try:
                # 嘗試設置 TopLeftCell（左上角儲存格）
                picture.TopLeftCell = cell_range
                logger.debug("成功設置 TopLeftCell")
            except AttributeError:
                try:
                    picture.top_left_cell = cell_range
                    logger.debug("成功設置 top_left_cell")
                except AttributeError:
                    pass
            
            try:
                # 嘗試設置 BottomRightCell（右下角儲存格，與左上角相同以鎖定到單個儲存格）
                picture.BottomRightCell = cell_range
                logger.debug("成功設置 BottomRightCell")
            except AttributeError:
                try:
                    picture.bottom_right_cell = cell_range
                    logger.debug("成功設置 bottom_right_cell")
                except AttributeError:
                    pass
        except Exception as e:
            logger.debug(f"設置 TopLeftCell/BottomRightCell 時發生錯誤: {str(e)}")
        
        # 策略 3: 設置 Anchor 屬性（如果可用）
        try:
            try:
                # 嘗試設置 Anchor 到儲存格範圍
                picture.Anchor = cell_range
                logger.debug("成功設置 Anchor")
            except AttributeError:
                try:
                    picture.anchor = cell_range
                    logger.debug("成功設置 anchor")
                except AttributeError:
                    pass
        except Exception as e:
            logger.debug(f"設置 Anchor 時發生錯誤: {str(e)}")
        
        # 策略 4: 嘗試使用 Shape 對象的屬性（如果 picture 有 Shape 屬性）
        try:
            if hasattr(picture, 'Shape'):
                shape = picture.Shape
                try:
                    # 嘗試設置 Shape 的 Placement
                    shape.Placement = 2
                    logger.debug("成功通過 Shape 對象設置 Placement")
                except AttributeError:
                    try:
                        shape.placement = 2
                        logger.debug("成功通過 Shape 對象（小寫）設置 Placement")
                    except AttributeError:
                        pass
        except Exception as e:
            logger.debug(f"通過 Shape 對象設置屬性時發生錯誤: {str(e)}")
        
        # 策略 5: 嘗試設置 LockAspectRatio 和 Locked 屬性（如果可用）
        try:
            try:
                picture.LockAspectRatio = True
                logger.debug("成功設置 LockAspectRatio")
            except AttributeError:
                try:
                    picture.lock_aspect_ratio = True
                    logger.debug("成功設置 lock_aspect_ratio")
                except AttributeError:
                    pass
            
            try:
                picture.Locked = True
                logger.debug("成功設置 Locked")
            except AttributeError:
                try:
                    picture.locked = True
                    logger.debug("成功設置 locked")
                except AttributeError:
                    pass
        except Exception as e:
            logger.debug(f"設置 LockAspectRatio/Locked 時發生錯誤: {str(e)}")
        
        # 如果所有策略都失敗，記錄警告
        if not placement_set:
            logger.warning(
                "⚠️ 警告：無法設置圖片的 Placement 屬性。"
                "圖片可能仍然可以自由移動。"
                "建議檢查 Spire.XLS 版本和 API 文檔。"
            )
    
    def insert_image_to_cell(
        self,
        image_path,
        row_index,
        column_index,
        offset_x=0,
        offset_y=0,
        auto_resize_cell=True,
        preserve_aspect_ratio=True
    ):
        """
        在指定儲存格插入圖片並精準對齊
        
        Args:
            image_path: 圖片文件路徑
            row_index: 行索引（從 1 開始，例如 A1 為 row=1, column=1）
            column_index: 列索引（從 1 開始，例如 A1 為 row=1, column=1）
            offset_x: 圖片與儲存格左邊界的水平偏移（單位：像素，默認 0）
            offset_y: 圖片與儲存格上邊界的垂直偏移（單位：像素，默認 0）
            auto_resize_cell: 是否自動調整儲存格大小以適應圖片（默認 True）
            preserve_aspect_ratio: 是否保持圖片寬高比（默認 True）
        
        Returns:
            ExcelPicture: 插入的圖片對象，可用於進一步調整
        """
        import os
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"圖片文件不存在: {image_path}")
        
        # 獲取目標儲存格
        cell_range = self.worksheet.Range[row_index, column_index]
        
        # 插入圖片
        picture = self.worksheet.Pictures.Add(row_index, column_index, image_path)
        
        # 獲取儲存格的寬度和高度（單位：像素）
        # Spire.XLS 使用點（points）作為單位，1 點 = 1/72 英寸
        # 需要轉換為像素（通常 1 英寸 = 96 像素，所以 1 點 ≈ 1.33 像素）
        try:
            # 嘗試使用小寫屬性
            cell_width_points = cell_range.column_width
            cell_height_points = cell_range.row_height
        except AttributeError:
            # 如果小寫屬性不存在，嘗試使用大寫
            try:
                cell_width_points = cell_range.ColumnWidth
                cell_height_points = cell_range.RowHeight
            except AttributeError:
                # 如果都不存在，使用默認值
                cell_width_points = 64
                cell_height_points = 15
        
        # 如果儲存格大小為 0 或未設置，使用默認值
        if cell_width_points <= 0:
            cell_width_points = 64  # 默認列寬（點）
        if cell_height_points <= 0:
            cell_height_points = 15  # 默認行高（點）
        
        # 轉換為像素（1 點 ≈ 1.33 像素，但實際轉換可能因 DPI 而異）
        # 使用更精確的轉換：1 點 = 1/72 英寸，假設 96 DPI，則 1 點 = 96/72 = 1.33 像素
        cell_width_pixels = cell_width_points * (96 / 72)
        cell_height_pixels = cell_height_points * (96 / 72)
        
        # 獲取圖片原始尺寸（無論是否自動調整都需要）
        from PIL import Image
        img = Image.open(image_path)
        img_width, img_height = img.size
        
        # 如果啟用自動調整儲存格大小
        if auto_resize_cell:
            # 計算需要的儲存格大小（考慮偏移）
            required_width_points = (img_width + offset_x * 2) * (72 / 96)
            required_height_points = (img_height + offset_y * 2) * (72 / 96)
            
            # 調整列寬和行高
            # Spire.XLS 的 SetColumnWidth 接受 (column_index, width) 兩個參數
            # 注意：Spire.XLS 使用從 1 開始的索引（與 Excel 一致），所以不需要減 1
            self.worksheet.SetColumnWidth(column_index, required_width_points)
            self.worksheet.SetRowHeight(row_index, required_height_points)
            
            # 更新儲存格尺寸變數
            cell_width_pixels = img_width + offset_x * 2
            cell_height_pixels = img_height + offset_y * 2
        
        # 設置圖片位置和大小
        # 計算圖片在儲存格中的位置（考慮偏移）
        # Spire.XLS 使用小寫屬性名稱
        try:
            # 嘗試使用小寫屬性
            left_position = cell_range.left + offset_x
            top_position = cell_range.top + offset_y
        except AttributeError:
            # 如果小寫屬性不存在，嘗試使用其他方法獲取位置
            # 使用列寬和行高計算位置（近似值）
            # 累加前面列的寬度
            left_position = offset_x
            for col in range(1, column_index):
                try:
                    col_width = self.worksheet.GetColumnWidth(col)
                    left_position += col_width * (96 / 72)  # 轉換為像素
                except:
                    left_position += 64 * (96 / 72)  # 使用默認列寬
            
            # 累加前面行的高度
            top_position = offset_y
            for row in range(1, row_index):
                try:
                    row_height = self.worksheet.GetRowHeight(row)
                    top_position += row_height * (96 / 72)  # 轉換為像素
                except:
                    top_position += 15 * (96 / 72)  # 使用默認行高
        
        # 設置圖片位置（使用小寫屬性）
        try:
            picture.left = left_position
            picture.top = top_position
        except AttributeError:
            # 如果小寫屬性不存在，嘗試使用大寫
            picture.Left = left_position
            picture.Top = top_position
        
        # 設置圖片大小（使用小寫屬性）
        try:
            if preserve_aspect_ratio and auto_resize_cell:
                # 如果自動調整了儲存格，圖片使用原始尺寸
                picture.width = img_width
                picture.height = img_height
            else:
                # 否則，圖片填滿儲存格（減去偏移）
                picture.width = cell_width_pixels - (offset_x * 2)
                picture.height = cell_height_pixels - (offset_y * 2)
        except AttributeError:
            # 如果小寫屬性不存在，嘗試使用大寫
            if preserve_aspect_ratio and auto_resize_cell:
                picture.Width = img_width
                picture.Height = img_height
            else:
                picture.Width = cell_width_pixels - (offset_x * 2)
                picture.Height = cell_height_pixels - (offset_y * 2)
        
        # 設置圖片對齊方式（使用小寫屬性）
        try:
            picture.left_column_offset = offset_x
            picture.top_row_offset = offset_y
        except AttributeError:
            # 如果小寫屬性不存在，嘗試使用大寫
            try:
                picture.LeftColumnOffset = offset_x
                picture.TopRowOffset = offset_y
            except AttributeError:
                # 如果都不存在，跳過設置偏移（某些版本可能不支持）
                pass
        
        # 關鍵：設置圖片的 Placement 屬性，使圖片鎖定到儲存格
        # 使用多種策略嘗試鎖定圖片到儲存格
        self._lock_picture_to_cell(picture, cell_range, row_index, column_index)
        
        return picture
    
    def set_cell_size(self, row_index, column_index, width_points=None, height_points=None):
        """
        手動設置儲存格的列寬和行高
        
        Args:
            row_index: 行索引（從 1 開始）
            column_index: 列索引（從 1 開始）
            width_points: 列寬（單位：點，1 點 = 1/72 英寸）。如果為 None，不修改
            height_points: 行高（單位：點）。如果為 None，不修改
        """
        if width_points is not None:
            # Spire.XLS 的 SetColumnWidth 接受 (column_index, width) 兩個參數
            # 注意：Spire.XLS 使用從 1 開始的索引（與 Excel 一致），所以不需要減 1
            self.worksheet.SetColumnWidth(column_index, width_points)
        if height_points is not None:
            # Spire.XLS 使用從 1 開始的索引（與 Excel 一致），所以不需要減 1
            self.worksheet.SetRowHeight(row_index, height_points)
    
    def get_worksheet(self, sheet_name=None, sheet_index=0):
        """
        獲取工作表對象
        
        Args:
            sheet_name: 工作表名稱（優先使用）
            sheet_index: 工作表索引（如果未提供名稱）
        
        Returns:
            Worksheet: 工作表對象
        """
        if sheet_name:
            # 檢查工作表是否存在
            try:
                self.worksheet = self.workbook.Worksheets[sheet_name]
            except (KeyError, TypeError, AttributeError):
                # 工作表不存在，創建新工作表
                self.worksheet = self.workbook.Worksheets.Add(sheet_name)
        else:
            # 使用索引獲取工作表
            if sheet_index < self.workbook.Worksheets.Count:
                self.worksheet = self.workbook.Worksheets[sheet_index]
            else:
                # 索引超出範圍，使用第一個工作表
                self.worksheet = self.workbook.Worksheets[0]
        return self.worksheet
    
    def add_worksheet(self, sheet_name):
        """
        添加新工作表
        
        Args:
            sheet_name: 工作表名稱
        
        Returns:
            Worksheet: 新創建的工作表對象
        """
        worksheet = self.workbook.Worksheets.Add(sheet_name)
        return worksheet
    
    def save(self, output_path):
        """
        保存 Excel 文件
        
        Args:
            output_path: 輸出文件路徑（.xlsx 格式）
        """
        self.workbook.SaveToFile(output_path, ExcelVersion.Version2016)
        self.workbook.Dispose()
    
    def save_to_bytes(self):
        """
        將工作簿保存為字節流（用於 Web 應用）
        
        Returns:
            bytes: Excel 文件的字節數據
        """
        from io import BytesIO
        import tempfile
        import os
        
        # 創建臨時文件
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # 保存到臨時文件
            self.workbook.SaveToFile(tmp_path, ExcelVersion.Version2016)
            
            # 讀取字節數據
            with open(tmp_path, 'rb') as f:
                data = f.read()
            
            return data
        finally:
            # 清理臨時文件
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            self.workbook.Dispose()


def create_excel_with_embedded_images(
    output_path,
    image_data_list,
    sheet_name="Sheet1"
):
    """
    便捷函數：創建包含嵌入圖片的 Excel 文件
    
    Args:
        output_path: 輸出 Excel 文件路徑
        image_data_list: 圖片數據列表，每個元素為字典，包含：
            - 'image_path': 圖片文件路徑
            - 'row': 行索引（從 1 開始）
            - 'column': 列索引（從 1 開始）
            - 'offset_x': 水平偏移（可選，默認 0）
            - 'offset_y': 垂直偏移（可選，默認 0）
            - 'auto_resize': 是否自動調整儲存格（可選，默認 True）
        sheet_name: 工作表名稱（默認 "Sheet1"）
    
    範例:
        image_data_list = [
            {
                'image_path': 'photo1.jpg',
                'row': 1,
                'column': 1,
                'offset_x': 2,
                'offset_y': 2,
                'auto_resize': True
            },
            {
                'image_path': 'photo2.png',
                'row': 1,
                'column': 2
            }
        ]
        create_excel_with_embedded_images('output.xlsx', image_data_list)
    """
    embedder = ExcelImageEmbedder()
    # 獲取或創建工作表
    if sheet_name and sheet_name != "Sheet1":
        # 如果指定了不同的工作表名稱，嘗試獲取或創建
        try:
            embedder.get_worksheet(sheet_name=sheet_name)
        except:
            # 如果獲取失敗，創建新工作表
            embedder.add_worksheet(sheet_name)
            embedder.get_worksheet(sheet_name=sheet_name)
    else:
        # 使用默認工作表
        embedder.get_worksheet()
    
    for img_data in image_data_list:
        embedder.insert_image_to_cell(
            image_path=img_data['image_path'],
            row_index=img_data['row'],
            column_index=img_data['column'],
            offset_x=img_data.get('offset_x', 0),
            offset_y=img_data.get('offset_y', 0),
            auto_resize_cell=img_data.get('auto_resize', True)
        )
    
    embedder.save(output_path)
    print(f"Excel 文件已保存至: {output_path}")


if __name__ == "__main__":
    """
    使用範例
    """
    if not SPIRE_XLS_AVAILABLE:
        print("請先安裝 Spire.XLS for Python:")
        print("pip install Spire.XLS")
        exit(1)
    
    # 範例 1: 基本使用
    print("範例 1: 基本圖片嵌入")
    embedder = ExcelImageEmbedder()
    
    # 假設有圖片文件（請替換為實際路徑）
    # embedder.insert_image_to_cell(
    #     image_path='example.jpg',
    #     row_index=1,
    #     column_index=1,
    #     offset_x=2,  # 2 像素左邊距
    #     offset_y=2,  # 2 像素上邊距
    #     auto_resize_cell=True
    # )
    
    # embedder.save('output_example1.xlsx')
    
    # 範例 2: 使用便捷函數
    print("範例 2: 批量插入圖片")
    # image_list = [
    #     {'image_path': 'img1.jpg', 'row': 1, 'column': 1},
    #     {'image_path': 'img2.png', 'row': 1, 'column': 2, 'offset_x': 5, 'offset_y': 5},
    #     {'image_path': 'img3.jpg', 'row': 2, 'column': 1}
    # ]
    # create_excel_with_embedded_images('output_example2.xlsx', image_list)
    
    print("請參考代碼註釋中的範例進行使用。")

