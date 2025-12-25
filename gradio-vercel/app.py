# gradio-vercel/app.py
# HỆ THỐNG BÁO CÁO THỜI GIAN NHẬP HÀNG - GRADIO VERSION
import gradio as gr
import pandas as pd
import numpy as np
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import io
import time
import json
import re
import os
import sys
from io import BytesIO
import traceback

# ========== CẤU HÌNH HỆ THỐNG ==========
SYSTEM_CONFIG = {
    "app_name": "Hệ Thống Báo Cáo Nhập Hàng - Kho Nguyên Liệu",
    "version": "3.0 - Gradio Edition",
    "default_sheet_url": "https://docs.google.com/spreadsheets/d/1k5tV_bnP6eJ_sj7xm5lTg9_iaYzf14VHbOEWq5jtTWE/edit",
    "supported_months": [f"Tháng {i}" for i in range(1, 13)],
    "month_mapping": {
        "Tháng 1": "T1", "Tháng 2": "T2", "Tháng 3": "T3",
        "Tháng 4": "T4", "Tháng 5": "T5", "Tháng 6": "T6",
        "Tháng 7": "T7", "Tháng 8": "T8", "Tháng 9": "T9",
        "Tháng 10": "T10", "Tháng 11": "T11", "Tháng 12": "T12"
    }
}

# ========== CSS TÙY CHỈNH ==========
CUSTOM_CSS = """
<style>
.gradio-container {
    font-family: 'Inter', sans-serif;
}
.header-section {
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
    padding: 25px;
    border-radius: 20px;
    color: white;
    margin-bottom: 25px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.15);
}
.metric-card {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    padding: 20px;
    border-radius: 12px;
    border-left: 5px solid #3b82f6;
    margin: 10px 0;
}
.data-table {
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}
.tab-button {
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
}
</style>
"""

# ========== HÀM KẾT NỐI GOOGLE SHEETS ==========
def get_google_client():
    """Kết nối đến Google Sheets - An toàn cho production"""
    try:
        # Ưu tiên Environment Variables (Vercel)
        if 'GOOGLE_CREDS_JSON' in os.environ:
            creds_json = os.environ['GOOGLE_CREDS_JSON']
            creds_dict = json.loads(creds_json)
        # Hoặc file local (development)
        elif os.path.exists('credentials.json'):
            with open('credentials.json', 'r', encoding='utf-8') as f:
                creds_dict = json.load(f)
        else:
            print("⚠️ Không tìm thấy Google Sheets credentials")
            return None
        
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Fix newline trong private key
        if 'private_key' in creds_dict:
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        print("✅ Kết nối Google Sheets thành công!")
        return client
        
    except Exception as e:
        print(f"❌ Lỗi kết nối Google Sheets: {str(e)}")
        traceback.print_exc()
        return None

# ========== HÀM XỬ LÝ DỮ LIỆU ==========
def read_sheet_data(client, sheet_name, sheet_url=None):
    """Đọc dữ liệu từ sheet cụ thể"""
    try:
        if sheet_url is None:
            sheet_url = SYSTEM_CONFIG["default_sheet_url"]
        
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Đọc toàn bộ dữ liệu
        all_data = worksheet.get_all_values()
        
        if not all_data:
            return pd.DataFrame()
        
        # Xác định dòng bắt đầu dữ liệu
        start_row = 0
        for i, row in enumerate(all_data):
            if len(row) > 0 and "Ngày/tháng" in str(row[0]):
                start_row = i
                break
        
        # Đọc dữ liệu từ dòng start_row đến 70
        data_rows = all_data[start_row:70]
        
        if len(data_rows) > 1:
            headers = data_rows[0]
            data = data_rows[1:]
            
            # Đảm bảo số cột bằng nhau
            max_cols = max(len(row) for row in data)
            headers = headers + [''] * (max_cols - len(headers))
            
            # Pad các dòng
            padded_data = []
            for row in data:
                padded_row = row + [''] * (max_cols - len(row))
                padded_data.append(padded_row)
            
            df = pd.DataFrame(padded_data, columns=headers)
            
            # Lọc dòng trống
            df = df.replace('', pd.NA)
            df = df.dropna(how='all')
            
            # Đổi tên cột
            column_mapping = {
                'Ngày/tháng': 'date',
                'Số Xe': 'so_xe',
                'Tên nguyên liệu': 'nguyen_lieu',
                'Xe cân VÀO': 'xe_can_vao',
                'Xe cân RA': 'xe_can_ra',
                'Tổng thời gian': 'tong_thoi_gian',
                'Số lượng': 'so_luong',
                'Bag.': 'bag',
                'Net.Wgh. (kg)': 'net_weight',
                'Nguyên nhân': 'nguyen_nhan',
                'Lí do chi tiết': 'ly_do_chi_tiet'
            }
            
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            return df
        else:
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Lỗi đọc sheet {sheet_name}: {str(e)}")
        return pd.DataFrame()

def parse_excel_paste(pasted_text):
    """Xử lý dữ liệu dán từ Excel"""
    try:
        if not pasted_text.strip():
            return []
        
        lines = pasted_text.strip().split('\n')
        parsed_data = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Phân tích định dạng
            if '\t' in line:
                cells = line.split('\t')
            elif '  ' in line:
                cells = re.split(r'\s{2,}', line)
            elif ',' in line and not line.count(',') < 3:
                cells = line.split(',')
            elif '|' in line:
                cells = line.split('|')
            else:
                cells = [line]
            
            # Làm sạch dữ liệu
            cleaned_cells = []
            for cell in cells:
                cell = cell.strip()
                cell = cell.strip('"').strip("'")
                cleaned_cells.append(cell)
            
            if cleaned_cells:
                parsed_data.append(cleaned_cells)
        
        return parsed_data
        
    except Exception as e:
        print(f"Lỗi phân tích dữ liệu: {str(e)}")
        return []

def write_to_sheet(client, sheet_name, data, start_row=7, sheet_url=None):
    """Ghi dữ liệu vào Google Sheets"""
    try:
        if sheet_url is None:
            sheet_url = SYSTEM_CONFIG["default_sheet_url"]
        
        spreadsheet = client.open_by_url(sheet_url)
        worksheet = spreadsheet.worksheet(sheet_name)
        
        # Xóa vùng dữ liệu cũ
        num_rows = len(data)
        clear_range = f"A{start_row}:U{start_row + num_rows + 10}"
        worksheet.batch_clear([clear_range])
        
        # Ghi dữ liệu mới
        cell_list = worksheet.range(f"A{start_row}:{chr(65 + len(data[0]) - 1)}{start_row + num_rows - 1}")
        
        idx = 0
        for i, row in enumerate(data):
            for j, cell in enumerate(row):
                if idx < len(cell_list):
                    cell_list[idx].value = str(cell) if cell is not None else ""
                    idx += 1
        
        worksheet.update_cells(cell_list)
        return True
        
    except Exception as e:
        print(f"Lỗi ghi dữ liệu: {str(e)}")
        return False

# ========== COMPONENTS GIAO DIỆN ==========
def create_header():
    """Tạo header ứng dụng"""
    header_html = f"""
    <div class="header-section">
        <h1 style="font-size: 2.8rem; margin-bottom: 0.5rem;">🚚 HỆ THỐNG BÁO CÁO THỜI GIAN NHẬP HÀNG</h1>
        <h3 style="font-weight: 400; margin-bottom: 1rem;">(Nhập chậm 1 xe quá 2h và nhập trễ sau 17h)</h3>
        <div style="display: flex; gap: 2rem; margin-top: 1.5rem;">
            <div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Bộ phận</div>
                <div style="font-size: 1.2rem; font-weight: 600;">KHO NGUYÊN LIỆU</div>
            </div>
            <div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Phiên bản</div>
                <div style="font-size: 1.2rem; font-weight: 600;">{SYSTEM_CONFIG['version']}</div>
            </div>
            <div>
                <div style="font-size: 0.9rem; opacity: 0.9;">Trạng thái</div>
                <div style="font-size: 1.2rem; font-weight: 600; color: #10b981;">● Đang hoạt động</div>
            </div>
        </div>
    </div>
    """
    return gr.HTML(header_html)

def create_sidebar():
    """Tạo sidebar điều hướng"""
    with gr.Column(scale=1, min_width=300, variant="panel") as sidebar:
        gr.Markdown("### 🎯 MENU CHỨC NĂNG")
        
        # Chọn tháng
        month_dropdown = gr.Dropdown(
            choices=SYSTEM_CONFIG["supported_months"],
            value="Tháng 1",
            label="📅 CHỌN THÁNG BÁO CÁO",
            interactive=True
        )
        
        gr.Markdown("---")
        
        # Các nút chức năng
        btn_dashboard = gr.Button("📊 Dashboard", variant="primary", size="lg")
        btn_nhap_lieu = gr.Button("📥 Nhập dữ liệu", size="lg")
        btn_bao_cao = gr.Button("📈 Xem báo cáo", size="lg")
        btn_tong_hop = gr.Button("📋 Tổng hợp 12 tháng", size="lg")
        btn_quan_ly = gr.Button("⚙️ Quản lý lý do", size="lg")
        btn_huong_dan = gr.Button("📖 Hướng dẫn", size="lg")
        
        gr.Markdown("---")
        
        # Thông tin hệ thống
        gr.Markdown("### 📊 THÔNG TIN HỆ THỐNG")
        with gr.Group():
            gr.Markdown(f"**Tháng hiện tại:** {month_dropdown.value}")
            gr.Markdown("**Trạng thái:** 🟢 Online")
            gr.Markdown("**Lần cập nhật:** " + datetime.now().strftime("%d/%m/%Y %H:%M"))
        
        gr.Markdown("---")
        
        # Footer
        footer_html = """
        <div style="text-align: center; padding: 1rem; background: #f8fafc; border-radius: 10px;">
            <div style="font-size: 0.8rem; color: #6b7280;">© 2024 Kho Nguyên Liệu</div>
            <div style="font-size: 0.75rem; color: #9ca3af; margin-top: 0.5rem;">Hỗ trợ: 0900-123-456</div>
        </div>
        """
        gr.HTML(footer_html)
    
    return sidebar, month_dropdown, btn_dashboard, btn_nhap_lieu, btn_bao_cao, btn_tong_hop, btn_quan_ly, btn_huong_dan

def create_dashboard_tab():
    """Tạo tab Dashboard"""
    with gr.Column() as tab:
        gr.Markdown("## 📊 DASHBOARD TỔNG QUAN")
        
        # Metrics cards
        with gr.Row():
            with gr.Column():
                metric1 = gr.HTML("""
                <div class="metric-card">
                    <div style="font-size: 0.9rem; color: #6b7280;">THÁNG HIỆN TẠI</div>
                    <div style="font-size: 2rem; font-weight: 700; color: #3b82f6;" id="current-month">Tháng 1</div>
                </div>
                """)
            
            with gr.Column():
                metric2 = gr.HTML("""
                <div class="metric-card">
                    <div style="font-size: 0.9rem; color: #6b7280;">TỔNG SỐ XE</div>
                    <div style="font-size: 2rem; font-weight: 700; color: #10b981;" id="total-vehicles">--</div>
                </div>
                """)
            
            with gr.Column():
                metric3 = gr.HTML("""
                <div class="metric-card">
                    <div style="font-size: 0.9rem; color: #6b7280;">XE NHẬP TRỄ</div>
                    <div style="font-size: 2rem; font-weight: 700; color: #ef4444;" id="late-vehicles">--</div>
                </div>
                """)
            
            with gr.Column():
                metric4 = gr.HTML("""
                <div class="metric-card">
                    <div style="font-size: 0.9rem; color: #6b7280;">TỶ LỆ TRỄ</div>
                    <div style="font-size: 2rem; font-weight: 700; color: #f59e0b;" id="late-percentage">--%</div>
                </div>
                """)
        
        gr.Markdown("---")
        
        # Quick actions
        gr.Markdown("### ⚡ CHỨC NĂNG NHANH")
        with gr.Row():
            quick_btn1 = gr.Button("📥 Nhập dữ liệu nhanh", size="lg")
            quick_btn2 = gr.Button("📈 Xem báo cáo ngay", size="lg")
            quick_btn3 = gr.Button("🔄 Cập nhật dữ liệu", size="lg")
            quick_btn4 = gr.Button("📤 Xuất Excel", size="lg")
        
        gr.Markdown("---")
        
        # Hướng dẫn nhanh
        with gr.Accordion("📖 HƯỚNG DẪN NHANH", open=True):
            gr.Markdown("""
            ### Cách sử dụng hệ thống:
            
            1. **NHẬP DỮ LIỆU:**
               - Copy vùng dữ liệu từ Excel (A7:U...)
               - Dán vào ô trong ứng dụng
               - Hệ thống tự động phân tích
            
            2. **XEM BÁO CÁO:**
               - Chọn tháng cần xem
               - Xem báo cáo chi tiết
               - Tải xuống file Excel
            
            3. **TỔNG HỢP:**
               - Xem tổng hợp 12 tháng
               - Phân tích theo nguyên nhân
               - Biểu đồ trực quan
            """)
    
    return tab

def create_data_input_tab():
    """Tạo tab Nhập dữ liệu"""
    with gr.Column() as tab:
        gr.Markdown("## 📥 NHẬP DỮ LIỆU THÔNG MINH")
        
        # Tabs cho các phương thức nhập
        with gr.Tabs():
            with gr.TabItem("📋 Dán từ Excel"):
                gr.Markdown("### 📋 DÁN DỮ LIỆU TỪ EXCEL")
                
                with gr.Accordion("🎬 HƯỚNG DẪN CHI TIẾT", open=True):
                    gr.Markdown("""
                    **Bước 1:** Mở file Excel → Chọn sheet tháng hiện tại  
                    **Bước 2:** Chọn vùng A7 đến cột U (hết dữ liệu)  
                    **Bước 3:** Copy (Ctrl+C) → Dán (Ctrl+V) vào ô bên dưới  
                    **Bước 4:** Kiểm tra preview → Lưu dữ liệu
                    """)
                
                paste_area = gr.Textbox(
                    label="📍 **DÁN (Ctrl+V) DỮ LIỆU TỪ EXCEL VÀO ĐÂY:**",
                    placeholder="Paste dữ liệu từ Excel vào đây...\nHệ thống tự động nhận diện cột.\n\n📝 Ví dụ:\n2025-01-23\t86C04510 L1\tThức ăn Bổ Sung\t16:42:00\t17:04:00\t00:22:00\t5.0\t4000.0",
                    lines=10
                )
                
                preview_table = gr.Dataframe(
                    label="👁️ PREVIEW DỮ LIỆU",
                    headers=["Cột 1", "Cột 2", "Cột 3", "Cột 4", "Cột 5"],
                    visible=False
                )
                
                with gr.Row():
                    stats1 = gr.Markdown("**Số dòng:** 0")
                    stats2 = gr.Markdown("**Số cột:** 0")
                    stats3 = gr.Markdown("**Tổng SL:** N/A")
                
                save_btn = gr.Button("💾 LƯU DỮ LIỆU VÀO GOOGLE SHEETS", variant="primary", size="lg")
                save_status = gr.Markdown("")
            
            with gr.TabItem("📤 Tải file lên"):
                gr.Markdown("### 📤 TẢI FILE EXCEL LÊN")
                
                file_upload = gr.File(
                    label="Chọn file Excel (.xlsx, .xls)",
                    file_types=[".xlsx", ".xls"],
                    file_count="single"
                )
                
                upload_preview = gr.Dataframe(label="Preview file", visible=False)
                upload_btn = gr.Button("📤 Tải dữ liệu này lên", size="lg")
                upload_status = gr.Markdown("")
            
            with gr.TabItem("✏️ Nhập thủ công"):
                gr.Markdown("### ✏️ NHẬP DỮ LIỆU THỦ CÔNG")
                
                with gr.Row():
                    with gr.Column():
                        entry_date = gr.Textbox(label="Ngày nhập (YYYY-MM-DD)", value=datetime.now().strftime("%Y-%m-%d"))
                        vehicle_number = gr.Textbox(label="Số xe")
                        material_name = gr.Textbox(label="Tên nguyên liệu")
                    
                    with gr.Column():
                        time_in = gr.Textbox(label="Xe cân vào (HH:MM:SS)", value="08:00:00")
                        time_out = gr.Textbox(label="Xe cân ra (HH:MM:SS)", value="08:30:00")
                        total_time = gr.Textbox(label="Tổng thời gian", value="00:30:00")
                    
                    with gr.Column():
                        quantity = gr.Number(label="Số lượng", value=0.0)
                        net_weight = gr.Number(label="Net Weight (kg)", value=0.0)
                        reason = gr.Textbox(label="Nguyên nhân", value="Lý do khác")
                
                detail_reason = gr.Textbox(label="Lý do chi tiết", lines=2)
                manual_add_btn = gr.Button("➕ THÊM VÀO DANH SÁCH", size="lg")
                manual_list = gr.Dataframe(
                    label="📋 DANH SÁCH ĐÃ NHẬP",
                    headers=['Ngày', 'Số xe', 'Nguyên liệu', 'Vào', 'Ra', 'TG', 'SL', 'Kg', 'Nguyên nhân', 'Chi tiết'],
                    visible=False
                )
                manual_save_btn = gr.Button("💾 LƯU TẤT CẢ", variant="primary", size="lg")
                manual_status = gr.Markdown("")
        
        # Xử lý sự kiện
        def on_paste_change(text):
            data = parse_excel_paste(text)
            if data:
                df = pd.DataFrame(data[:20])  # Hiển thị 20 dòng đầu
                stats = f"**Số dòng:** {len(data)}"
                return gr.Dataframe(visible=True, value=df), stats, f"**Số cột:** {len(data[0]) if data else 0}"
            else:
                return gr.Dataframe(visible=False), "**Số dòng:** 0", "**Số cột:** 0"
        
        paste_area.change(
            on_paste_change,
            inputs=[paste_area],
            outputs=[preview_table, stats1, stats2]
        )
    
    return tab

def create_report_tab():
    """Tạo tab Báo cáo"""
    with gr.Column() as tab:
        gr.Markdown("## 📊 BÁO CÁO CHI TIẾT")
        
        # Filters
        with gr.Row():
            report_month = gr.Dropdown(
                choices=SYSTEM_CONFIG["supported_months"],
                value="Tháng 1",
                label="Chọn tháng báo cáo"
            )
            refresh_btn = gr.Button("🔄 Tải dữ liệu", variant="primary")
            export_csv = gr.Button("📥 Tải CSV")
            export_excel = gr.Button("📥 Tải Excel")
        
        # Data table
        report_table = gr.Dataframe(
            label="DỮ LIỆU CHI TIẾT",
            headers=['Ngày', 'Số xe', 'Nguyên liệu', 'Vào', 'Ra', 'TG', 'SL', 'Kg', 'Nguyên nhân', 'Chi tiết'],
            wrap=True,
            height=500
        )
        
        # Statistics
        gr.Markdown("### 📈 THỐNG KÊ")
        with gr.Row():
            stat1 = gr.Markdown("**Tổng số xe:** --")
            stat2 = gr.Markdown("**Xe nhập trễ (>17h):** --")
            stat3 = gr.Markdown("**Tổng khối lượng:** -- kg")
            stat4 = gr.Markdown("**TG trung bình/xe:** --")
        
        # Charts
        with gr.Tabs():
            with gr.TabItem("📊 Phân bố nguyên nhân"):
                reason_chart = gr.Plot(label="Biểu đồ nguyên nhân")
            
            with gr.TabItem("📋 Bảng số liệu"):
                reason_table = gr.Dataframe(label="Thống kê nguyên nhân")
    
    return tab

# ========== TẠO ỨNG DỤNG CHÍNH ==========
def create_app():
    """Tạo ứng dụng Gradio chính"""
    with gr.Blocks(
        title=SYSTEM_CONFIG["app_name"],
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS
    ) as app:
        
        # Header
        header = create_header()
        
        # Main layout
        with gr.Row():
            # Sidebar
            sidebar_col = gr.Column(scale=1, min_width=300)
            with sidebar_col:
                sidebar, month_dropdown, *buttons = create_sidebar()
            
            # Main content with Tabs
            main_col = gr.Column(scale=4)
            with main_col:
                with gr.Tabs() as tabs:
                    # Tab 1: Dashboard
                    with gr.TabItem("📊 Dashboard", id=0):
                        dashboard_tab = create_dashboard_tab()
                    
                    # Tab 2: Nhập dữ liệu
                    with gr.TabItem("📥 Nhập dữ liệu", id=1):
                        input_tab = create_data_input_tab()
                    
                    # Tab 3: Xem báo cáo
                    with gr.TabItem("📈 Xem báo cáo", id=2):
                        report_tab = create_report_tab()
                    
                    # Tab 4: Tổng hợp
                    with gr.TabItem("📋 Tổng hợp 12 tháng", id=3):
                        gr.Markdown("## 📈 TỔNG HỢP 12 THÁNG")
                        gr.Markdown("Chức năng đang được phát triển...")
                    
                    # Tab 5: Quản lý lý do
                    with gr.TabItem("⚙️ Quản lý lý do", id=4):
                        gr.Markdown("## ⚙️ QUẢN LÝ DANH SÁCH LÝ DO")
                        gr.Markdown("Chức năng đang được phát triển...")
                    
                    # Tab 6: Hướng dẫn
                    with gr.TabItem("📖 Hướng dẫn", id=5):
                        gr.Markdown("## 📋 HƯỚNG DẪN SỬ DỤNG")
                        with gr.Accordion("🎯 Tổng quan hệ thống", open=True):
                            gr.Markdown("""
                            Hệ thống giúp theo dõi thời gian nhập nguyên liệu, phát hiện xe nhập trễ,
                            thống kê nguyên nhân chậm trễ, và lưu trữ trên Google Sheets.
                            """)
        
        # ========== XỬ LÝ SỰ KIỆN ==========
        def switch_to_tab(tab_index):
            """Chuyển sang tab cụ thể"""
            return gr.Tabs(selected=tab_index)
        
        # Kết nối nút sidebar với tabs
        btn_dashboard, btn_nhap_lieu, btn_bao_cao, btn_tong_hop, btn_quan_ly, btn_huong_dan = buttons
        
        btn_dashboard.click(
            fn=lambda: switch_to_tab(0),
            outputs=[tabs]
        )
        
        btn_nhap_lieu.click(
            fn=lambda: switch_to_tab(1),
            outputs=[tabs]
        )
        
        btn_bao_cao.click(
            fn=lambda: switch_to_tab(2),
            outputs=[tabs]
        )
        
        btn_tong_hop.click(
            fn=lambda: switch_to_tab(3),
            outputs=[tabs]
        )
        
        btn_quan_ly.click(
            fn=lambda: switch_to_tab(4),
            outputs=[tabs]
        )
        
        btn_huong_dan.click(
            fn=lambda: switch_to_tab(5),
            outputs=[tabs]
        )
        
        # ========== XỬ LÝ DỮ LIỆU THỰC ==========
        def load_report_data(month):
            """Tải dữ liệu báo cáo"""
            try:
                client = get_google_client()
                if client is None:
                    return pd.DataFrame(), "❌ Không thể kết nối Google Sheets", "--", "--", "--", "--"
                
                sheet_name = SYSTEM_CONFIG["month_mapping"].get(month, "T1")
                df = read_sheet_data(client, sheet_name)
                
                if df.empty:
                    return pd.DataFrame(), "📭 Chưa có dữ liệu", "--", "--", "--", "--"
                
                # Tính toán thống kê
                total_vehicles = len(df)
                
                # Đếm xe nhập trễ (giả sử cột 'xe_can_ra' có thời gian)
                late_count = 0
                if 'xe_can_ra' in df.columns:
                    try:
                        # Logic đếm xe sau 17h
                        pass
                    except:
                        pass
                
                # Tổng khối lượng
                total_weight = 0
                if 'net_weight' in df.columns:
                    try:
                        total_weight = pd.to_numeric(df['net_weight'], errors='coerce').sum()
                    except:
                        pass
                
                stats = [
                    f"**Tổng số xe:** {total_vehicles}",
                    f"**Xe nhập trễ (>17h):** {late_count}",
                    f"**Tổng khối lượng:** {total_weight:,.0f} kg",
                    f"**TG trung bình/xe:** Đang tính..."
                ]
                
                return df, "✅ Đã tải dữ liệu", *stats
                
            except Exception as e:
                return pd.DataFrame(), f"❌ Lỗi: {str(e)}", "--", "--", "--", "--"
        
        # Kết nối nút refresh trong tab báo cáo
        refresh_btn = None  # Cần tìm component thực tế
        
    return app

# ========== CHẠY ỨNG DỤNG ==========
if __name__ == "__main__":
    # Kiểm tra môi trường
    print("=" * 50)
    print(f"🚀 KHỞI ĐỘNG {SYSTEM_CONFIG['app_name']}")
    print(f"📅 Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"📦 Pandas: {pd.__version__}")
    print("=" * 50)
    
    # Tạo và chạy app
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True,
        favicon_path=None
    )
