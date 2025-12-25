# Kieutimes/app.py - Optimized for Vercel
# HỆ THỐNG BÁO CÁO THỜI GIAN NHẬP HÀNG - VERCEL DEPLOYMENT

import os
import json
import pandas as pd
import gradio as gr
from datetime import datetime
import traceback

# ========== IMPORTS FOR GOOGLE SHEETS ==========
try:
    import gspread
    from google.oauth2.service_account import Credentials
    from google.auth.transport.requests import Request
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False
    print("⚠️ Google dependencies not installed")

# ========== CẤU HÌNH HỆ THỐNG ==========
SYSTEM_CONFIG = {
    "app_name": "Hệ Thống Báo Cáo Nhập Hàng - Vercel",
    "version": "4.0 - Production",
    "default_sheet_url": "https://docs.google.com/spreadsheets/d/1k5tV_bnP6eJ_sj7xm5lTg9_iaYzf14VHbOEWq5jtTWE/edit",
    "month_mapping": {
        "Tháng 1": "T1", "Tháng 2": "T2", "Tháng 3": "T3",
        "Tháng 4": "T4", "Tháng 5": "T5", "Tháng 6": "T6",
        "Tháng 7": "T7", "Tháng 8": "T8", "Tháng 9": "T9",
        "Tháng 10": "T10", "Tháng 11": "T11", "Tháng 12": "T12"
    }
}

# ========== CSS CUSTOM ==========
CUSTOM_CSS = """
<style>
.gradio-container {
    max-width: 1400px;
    margin: 0 auto;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif;
}
.header-card {
    background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
    padding: 2rem;
    border-radius: 16px;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.2);
}
.metric-box {
    background: white;
    padding: 1.5rem;
    border-radius: 12px;
    border-left: 5px solid #3b82f6;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.btn-primary-custom {
    background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
    color: white;
    border: none;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s;
}
.btn-primary-custom:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
}
.data-table {
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
}
</style>
"""

# ========== GOOGLE SHEETS HELPER ==========
def get_google_client():
    """Get Google Sheets client with Vercel environment support"""
    try:
        if not GOOGLE_AVAILABLE:
            return None
        
        # Vercel Environment Variable
        if 'GOOGLE_CREDS_JSON' in os.environ:
            creds_json = os.environ['GOOGLE_CREDS_JSON']
            creds_dict = json.loads(creds_json)
        elif os.path.exists('credentials.json'):
            with open('credentials.json', 'r', encoding='utf-8') as f:
                creds_dict = json.load(f)
        else:
            print("❌ No Google credentials found")
            return None
        
        # Fix private key formatting
        if 'private_key' in creds_dict:
            creds_dict['private_key'] = creds_dict['private_key'].replace('\\n', '\n')
        
        scope = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(credentials)
        print("✅ Google Sheets connected!")
        return client
        
    except Exception as e:
        print(f"❌ Google connection error: {e}")
        traceback.print_exc()
        return None

# ========== DATA PROCESSING ==========
def demo_read_data(month):
    """Demo function for testing without Google Sheets"""
    try:
        # Tạo dữ liệu mẫu
        data = {
            'Ngày': ['2025-01-01', '2025-01-02', '2025-01-03'],
            'Số xe': ['86C04510', '86C04511', '86C04512'],
            'Nguyên liệu': ['Thức ăn A', 'Thức ăn B', 'Thức ăn C'],
            'Xe cân vào': ['08:00:00', '09:30:00', '10:15:00'],
            'Xe cân ra': ['08:45:00', '10:15:00', '11:00:00'],
            'Tổng thời gian': ['00:45:00', '00:45:00', '00:45:00'],
            'Số lượng': [5.0, 6.0, 4.5],
            'Net Weight (kg)': [4000, 4500, 3500],
            'Nguyên nhân': ['Đúng giờ', 'Xếp hàng', 'Thời tiết']
        }
        df = pd.DataFrame(data)
        return df, "✅ Dữ liệu DEMO đã tải"
    except Exception as e:
        return pd.DataFrame(), f"❌ Lỗi: {str(e)}"

# ========== UI COMPONENTS ==========
def create_header():
    """Create application header"""
    return gr.HTML(f"""
    <div class="header-card">
        <h1 style="font-size: 2.5rem; margin-bottom: 0.5rem; font-weight: 800;">🚚 HỆ THỐNG BÁO CÁO THỜI GIAN NHẬP HÀNG</h1>
        <h3 style="font-weight: 400; margin-bottom: 1rem; opacity: 0.9;">Kho Nguyên Liệu - Theo dõi xe nhập trễ sau 17h</h3>
        <div style="display: flex; gap: 3rem; margin-top: 1.5rem; flex-wrap: wrap;">
            <div>
                <div style="font-size: 0.9rem; opacity: 0.8;">Phiên bản</div>
                <div style="font-size: 1.2rem; font-weight: 600;">{SYSTEM_CONFIG['version']}</div>
            </div>
            <div>
                <div style="font-size: 0.9rem; opacity: 0.8;">Môi trường</div>
                <div style="font-size: 1.2rem; font-weight: 600;">{'Vercel Production' if 'VERCEL' in os.environ else 'Local'}</div>
            </div>
            <div>
                <div style="font-size: 0.9rem; opacity: 0.8;">Thời gian</div>
                <div style="font-size: 1.2rem; font-weight: 600;" id="current-time">{datetime.now().strftime('%d/%m/%Y %H:%M')}</div>
            </div>
        </div>
    </div>
    """)

def create_sidebar():
    """Create sidebar navigation"""
    with gr.Column(scale=1, min_width=280, variant="panel"):
        gr.Markdown("### 🎯 MENU CHÍNH")
        
        month_select = gr.Dropdown(
            choices=list(SYSTEM_CONFIG["month_mapping"].keys()),
            value="Tháng 1",
            label="📅 CHỌN THÁNG",
            interactive=True
        )
        
        gr.Markdown("---")
        
        btn_dashboard = gr.Button("📊 Tổng quan", size="lg", variant="primary")
        btn_input = gr.Button("📥 Nhập dữ liệu", size="lg")
        btn_report = gr.Button("📈 Báo cáo", size="lg")
        btn_stats = gr.Button("📊 Thống kê", size="lg")
        
        gr.Markdown("---")
        
        gr.Markdown("### ⚙️ HỆ THỐNG")
        with gr.Row():
            status_indicator = gr.HTML("<div style='width: 12px; height: 12px; border-radius: 50%; background: #10b981;'></div>")
            gr.Markdown("**Trực tuyến**")
        
        gr.Markdown(f"**Sheets:** {'✅ Kết nối' if GOOGLE_AVAILABLE else '❌ Tắt'}")
        gr.Markdown(f"**Dữ liệu:** DEMO")
        
        gr.Markdown("---")
        gr.Markdown("© 2025 Kho Nguyên Liệu")

# ========== MAIN APP ==========
def create_app():
    """Create main Gradio application"""
    with gr.Blocks(
        title=SYSTEM_CONFIG["app_name"],
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            font=[gr.themes.GoogleFont("Inter"), "sans-serif"]
        ),
        css=CUSTOM_CSS
    ) as app:
        
        create_header()
        
        with gr.Row():
            # Sidebar
            with gr.Column(scale=1, min_width=280):
                create_sidebar()
            
            # Main content
            with gr.Column(scale=4):
                with gr.Tabs():
                    # Tab 1: Dashboard
                    with gr.Tab("📊 Dashboard"):
                        gr.Markdown("## 📊 TỔNG QUAN HỆ THỐNG")
                        
                        # Metrics
                        with gr.Row():
                            with gr.Column():
                                metric1 = gr.HTML("""
                                <div class="metric-box">
                                    <div style="color: #6b7280; font-size: 0.9rem;">THÁNG HIỆN TẠI</div>
                                    <div style="font-size: 2rem; font-weight: 700; color: #3b82f6;">Tháng 1</div>
                                    <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 0.5rem;">Dữ liệu cập nhật</div>
                                </div>
                                """)
                            
                            with gr.Column():
                                metric2 = gr.HTML("""
                                <div class="metric-box">
                                    <div style="color: #6b7280; font-size: 0.9rem;">TỔNG XE NHẬP</div>
                                    <div style="font-size: 2rem; font-weight: 700; color: #10b981;">48</div>
                                    <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 0.5rem;">Từ 01/01/2025</div>
                                </div>
                                """)
                            
                            with gr.Column():
                                metric3 = gr.HTML("""
                                <div class="metric-box">
                                    <div style="color: #6b7280; font-size: 0.9rem;">XE NHẬP TRỄ</div>
                                    <div style="font-size: 2rem; font-weight: 700; color: #ef4444;">12</div>
                                    <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 0.5rem;">25% tổng số xe</div>
                                </div>
                                """)
                        
                        # Quick Actions
                        gr.Markdown("### ⚡ HÀNH ĐỘNG NHANH")
                        with gr.Row():
                            quick1 = gr.Button("🔄 Tải dữ liệu mới", size="lg")
                            quick2 = gr.Button("📥 Nhập Excel", size="lg", variant="primary")
                            quick3 = gr.Button("📊 Xem báo cáo", size="lg")
                        
                        # Data Table
                        gr.Markdown("### 📋 DỮ LIỆU MẪU")
                        sample_df, _ = demo_read_data("Tháng 1")
                        data_table = gr.Dataframe(
                            value=sample_df,
                            headers=list(sample_df.columns),
                            height=300,
                            interactive=False
                        )
                    
                    # Tab 2: Nhập dữ liệu
                    with gr.Tab("📥 Nhập dữ liệu"):
                        gr.Markdown("## 📥 NHẬP DỮ LIỆU TỪ EXCEL")
                        
                        with gr.Row():
                            with gr.Column(scale=2):
                                gr.Markdown("### 📋 Hướng dẫn:")
                                gr.Markdown("""
                                1. Copy vùng dữ liệu từ Excel (từ A7)
                                2. Dán vào ô bên cạnh
                                3. Kiểm tra preview
                                4. Lưu vào hệ thống
                                
                                **Định dạng hỗ trợ:**
                                - Excel copy/paste
                                - CSV file
                                - Text với tab
                                """)
                            
                            with gr.Column(scale=3):
                                paste_area = gr.Textbox(
                                    label="Dán dữ liệu từ Excel:",
                                    placeholder="Copy từ Excel và dán vào đây...",
                                    lines=8
                                )
                                
                                preview_btn = gr.Button("👁️ Xem trước", size="lg")
                                save_btn = gr.Button("💾 Lưu dữ liệu", size="lg", variant="primary")
                                
                                status_display = gr.Markdown("**Trạng thái:** Chờ nhập dữ liệu")
                        
                        # Preview area
                        preview_table = gr.Dataframe(
                            label="Preview dữ liệu",
                            visible=False,
                            height=200
                        )
                    
                    # Tab 3: Báo cáo
                    with gr.Tab("📈 Báo cáo"):
                        gr.Markdown("## 📈 BÁO CÁO CHI TIẾT")
                        
                        with gr.Row():
                            report_month = gr.Dropdown(
                                choices=list(SYSTEM_CONFIG["month_mapping"].keys()),
                                value="Tháng 1",
                                label="Chọn tháng báo cáo"
                            )
                            load_btn = gr.Button("🔄 Tải dữ liệu", variant="primary")
                            export_btn = gr.Button("📤 Xuất Excel")
                        
                        report_data = gr.Dataframe(
                            label="Dữ liệu báo cáo",
                            height=400,
                            interactive=False
                        )
                        
                        report_status = gr.Markdown("**Trạng thái:** Chờ tải dữ liệu")
                    
                    # Tab 4: Thống kê
                    with gr.Tab("📊 Thống kê"):
                        gr.Markdown("## 📊 THỐNG KÊ & PHÂN TÍCH")
                        
                        # Statistics cards
                        with gr.Row():
                            stats_col1 = gr.HTML("""
                            <div class="metric-box">
                                <div style="color: #6b7280; font-size: 0.9rem;">NGUYÊN NHÂN PHỔ BIẾN</div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #3b82f6; margin: 1rem 0;">Xếp hàng đợi</div>
                                <div style="font-size: 0.9rem; color: #6b7280;">Chiếm 40% các trường hợp</div>
                            </div>
                            """)
                            
                            stats_col2 = gr.HTML("""
                            <div class="metric-box">
                                <div style="color: #6b7280; font-size: 0.9rem;">THỜI GIAN TRUNG BÌNH</div>
                                <div style="font-size: 1.5rem; font-weight: 700; color: #10b981; margin: 1rem 0;">52 phút</div>
                                <div style="font-size: 0.9rem; color: #6b7280;">Mỗi lượt nhập hàng</div>
                            </div>
                            """)
                        
                        # Chart placeholder
                        gr.Markdown("### 📈 BIỂU ĐỒ PHÂN BỐ")
                        chart_placeholder = gr.Plot(value=None, label="Biểu đồ sẽ hiển thị ở đây")
        
        # ========== EVENT HANDLERS ==========
        def load_report_handler(month):
            """Handle report loading"""
            try:
                df, status = demo_read_data(month)
                if not df.empty:
                    return df, f"✅ Đã tải dữ liệu {month}: {len(df)} dòng"
                else:
                    return pd.DataFrame(), "📭 Không có dữ liệu"
            except Exception as e:
                return pd.DataFrame(), f"❌ Lỗi: {str(e)}"
        
        load_btn.click(
            load_report_handler,
            inputs=[report_month],
            outputs=[report_data, report_status]
        )
        
        def preview_paste_handler(text):
            """Handle paste preview"""
            try:
                if not text.strip():
                    return gr.Dataframe(visible=False), "❌ Chưa có dữ liệu"
                
                # Simple parsing
                lines = [line.split('\t') for line in text.strip().split('\n') if line.strip()]
                if lines and len(lines) > 0:
                    df = pd.DataFrame(lines[:10])  # Show first 10 rows
                    return df, f"✅ Đã phân tích: {len(lines)} dòng"
                else:
                    return gr.Dataframe(visible=False), "❌ Dữ liệu không hợp lệ"
            except Exception as e:
                return gr.Dataframe(visible=False), f"❌ Lỗi phân tích: {str(e)}"
        
        preview_btn.click(
            preview_paste_handler,
            inputs=[paste_area],
            outputs=[preview_table, status_display]
        )
    
    return app

# ========== VERCEL DEPLOYMENT ==========
# Vercel cần biến môi trường
app = create_app()

# For Vercel serverless function
if __name__ == "__main__":
    # Local development
    print(f"🚀 Khởi động {SYSTEM_CONFIG['app_name']}")
    print(f"📅 Thời gian: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🌐 Môi trường: {'Vercel' if 'VERCEL' in os.environ else 'Local'}")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("GRADIO_SERVER_PORT", 7860)),
        share=False,
        debug=True
    )
