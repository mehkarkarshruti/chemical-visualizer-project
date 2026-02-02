# desktop_app.py
import sys
import os
import requests
import json
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib import font_manager
import webbrowser
import tempfile
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

# API Configuration
API_BASE = "http://127.0.0.1:8000/api"

class ModernButton(QPushButton):
    def __init__(self, text="", icon=None, primary=False, outline=False):
        super().__init__(text)
        self.primary = primary
        self.outline = outline
        if icon:
            self.setIcon(QIcon(icon))
        self.setCursor(Qt.PointingHandCursor)

class StatCard(QFrame):
    def __init__(self, title="", value="--", icon="", color="#4f46e5"):
        super().__init__()
        self.color = color
        self.initUI(title, value, icon)
        
    def initUI(self, title, value, icon):
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumHeight(100)
        self.setMinimumWidth(200)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title row
        title_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("statTitle")
        title_label.setStyleSheet(f"color: #9ca3af;")
        
        icon_label = QLabel(icon)
        icon_label.setObjectName("statIcon")
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(icon_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {self.color};")
        
        layout.addLayout(title_layout)
        layout.addWidget(value_label)
        
    def update_theme(self, dark_mode):
        if dark_mode:
            self.findChild(QLabel, "statTitle").setStyleSheet("color: #94a3b8;")
        else:
            self.findChild(QLabel, "statTitle").setStyleSheet("color: #6b7280;")

class UploadZone(QWidget):
    def __init__(self):
        super().__init__()
        self.drag_active = False
        self.initUI()
        self.setAcceptDrops(True)
        
    def initUI(self):
        self.setMinimumHeight(300)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(15)
        
        # Upload icon
        self.icon_label = QLabel("📤")
        self.icon_label.setObjectName("uploadIcon")
        self.icon_label.setAlignment(Qt.AlignCenter)
        
        # Main text
        self.main_text = QLabel("Drag & drop your CSV file")
        self.main_text.setObjectName("uploadText")
        self.main_text.setAlignment(Qt.AlignCenter)
        
        # Hint text
        self.hint_text = QLabel("or click to browse")
        self.hint_text.setObjectName("uploadHint")
        self.hint_text.setAlignment(Qt.AlignCenter)
        
        # Requirements
        self.req_text = QLabel(
            "Supports: .csv files only\n"
            "Required columns: Equipment Name, Type, Flowrate, Pressure, Temperature"
        )
        self.req_text.setObjectName("uploadRequirements")
        self.req_text.setAlignment(Qt.AlignCenter)
        self.req_text.setWordWrap(True)
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.main_text)
        layout.addWidget(self.hint_text)
        layout.addWidget(self.req_text)
        
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.set_drag_active(True)
        else:
            event.ignore()
            
    def dragLeaveEvent(self, event):
        self.set_drag_active(False)
        
    def dropEvent(self, event):
        self.set_drag_active(False)
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and urls[0].toLocalFile().endswith('.csv'):
                self.file_dropped.emit(urls[0].toLocalFile())
                
    def set_drag_active(self, active):
        self.drag_active = active
        if active:
            self.setStyleSheet("""
                UploadZone {
                    border: 2px dashed #4f46e5;
                    border-radius: 12px;
                    background-color: rgba(79, 70, 229, 0.05);
                }
            """)
        else:
            self.setStyleSheet("""
                UploadZone {
                    border: 2px dashed #e5e7eb;
                    border-radius: 12px;
                    background-color: #f9fafb;
                }
            """)
            
    file_dropped = pyqtSignal(str)

class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
        
    def initUI(self):
        if self.parent():
            self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        else:
            self.setGeometry(0, 0, 800, 600)
            
        self.hide()
        
        # Semi-transparent background
        self.setStyleSheet("background-color: rgba(15, 23, 42, 0.8);")
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Spinner container
        spinner_container = QWidget()
        spinner_layout = QVBoxLayout(spinner_container)
        spinner_layout.setAlignment(Qt.AlignCenter)
        
        # Create spinner using QLabel with HTML/CSS
        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignCenter)
        self.spinner_label.setText("""
            <div style="
                width: 50px;
                height: 50px;
                border: 3px solid rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                border-top-color: white;
                animation: spin 1s linear infinite;
                margin: auto;
            "></div>
        """)
        
        # Text
        self.text = QLabel("Analyzing your CSV data...")
        self.text.setStyleSheet("color: white; font-size: 16px; margin-top: 20px;")
        self.text.setAlignment(Qt.AlignCenter)
        
        spinner_layout.addWidget(self.spinner_label)
        layout.addWidget(spinner_container)
        layout.addWidget(self.text)

class HistoryDrawer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 600)
        
        main_widget = QWidget()
        main_widget.setObjectName("historyDrawer")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = QWidget()
        header.setObjectName("drawerHeader")
        header_layout = QHBoxLayout(header)
        
        title = QLabel("📋 Upload History")
        title.setObjectName("drawerTitle")
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(30, 30)
        close_btn.clicked.connect(self.hide)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        
        # Scroll area for history
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.history_content = QWidget()
        self.history_layout = QVBoxLayout(self.history_content)
        self.history_layout.setSpacing(10)
        
        scroll.setWidget(self.history_content)
        
        layout.addWidget(header)
        layout.addWidget(scroll)
        
    def update_history(self, history_data):
        # Clear existing items
        for i in reversed(range(self.history_layout.count())): 
            widget = self.history_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        if not history_data:
            empty_label = QLabel("📭 No upload history yet")
            empty_label.setAlignment(Qt.AlignCenter)
            empty_label.setObjectName("emptyHistory")
            self.history_layout.addWidget(empty_label)
            return
            
        for item in history_data:
            try:
                # Create history card
                card = QWidget()
                card.setObjectName("historyItem")
                card.setMinimumHeight(80)
                
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(15, 15, 15, 15)
                
                # Time
                uploaded_at = item.get('uploaded_at', '')
                try:
                    time_str = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M")
                except:
                    time_str = str(uploaded_at)[:16]
                
                time_label = QLabel(f"🕒 {time_str}")
                time_label.setObjectName("historyTime")
                
                # Stats row
                stats_row = QHBoxLayout()
                
                stats = [
                    f"📊 {item.get('total_equipment', 'N/A')} equipment",
                    f"🌡️ {float(item.get('avg_temperature', 0)):.1f}°C",
                    f"⚡ {float(item.get('avg_flowrate', 0)):.1f} flow"
                ]
                
                for stat in stats:
                    stat_label = QLabel(stat)
                    stat_label.setObjectName("historyStat")
                    stats_row.addWidget(stat_label)
                
                stats_row.addStretch()
                
                # View button
                view_btn = QPushButton("View Details")
                view_btn.setObjectName("viewBtn")
                view_btn.setFixedSize(100, 30)
                view_btn.clicked.connect(lambda checked, data=item: self.view_details(data))
                
                card_layout.addWidget(time_label)
                card_layout.addLayout(stats_row)
                card_layout.addWidget(view_btn)
                
                self.history_layout.addWidget(card)
                
            except Exception as e:
                print(f"Error creating history item: {e}")
        
        self.history_layout.addStretch()
        
    def view_details(self, data):
        try:
            # Parse timestamp
            uploaded_at = data.get('uploaded_at', 'Unknown')
            try:
                time_str = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S")
            except:
                time_str = str(uploaded_at)
            
            # Get all available stats
            total_eq = data.get('total_equipment', data.get('count', 'N/A'))
            avg_temp = data.get('avg_temperature', data.get('avg_temp', 0))
            avg_flow = data.get('avg_flowrate', data.get('avg_flow', 0))
            avg_pressure = data.get('avg_pressure', data.get('avg_press', 0))
            type_dist = data.get('type_distribution', {})
            
            # Format type distribution
            type_dist_text = ""
            if type_dist:
                for eq_type, count in type_dist.items():
                    type_dist_text += f"{eq_type}: {count}<br>"
            
            msg = QMessageBox()
            msg.setWindowTitle("📋 Upload Details")
            msg.setIcon(QMessageBox.Information)
            msg.setText(
                f"<b>Upload Time:</b> {time_str}<br><br>"
                f"<b>📊 Total Equipment:</b> {total_eq}<br>"
                f"<b>🌡️ Average Temperature:</b> {float(avg_temp):.2f}°C<br>"
                f"<b>⚡ Average Flowrate:</b> {float(avg_flow):.2f}<br>"
                f"<b>📈 Average Pressure:</b> {float(avg_pressure):.2f}<br><br>"
                f"<b>Equipment Type Distribution:</b><br>{type_dist_text}"
            )
            msg.exec_()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to show details: {str(e)}")

class ChemicalEquipmentApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.dark_mode = False
        self.sidebar_collapsed = False
        self.summary_data = None
        self.history_data = []
        self.developer_info = {
            "name": "Shruti Mehkarkar", 
            "university": "VIT Bhopal University", 
            "email": "mehkarkars1211@gmail.com"  
        }
        self.initUI()
        self.load_history()
        
    def initUI(self):
        self.setWindowTitle("🧪 Chemical Equipment Visualizer")
        self.setMinimumSize(1400, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = self.create_sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Main content area
        self.main_content = self.create_main_content()
        main_layout.addWidget(self.main_content, 1)
        
        # Loading overlay
        self.loading_overlay = LoadingOverlay(self.main_content)
        self.loading_overlay.hide()
        
        # History drawer
        self.history_drawer = HistoryDrawer(self)
        self.history_drawer.hide()
        
        # Apply initial theme
        self.apply_theme()
        
    def create_sidebar(self):
        sidebar = QWidget()
        sidebar.setFixedWidth(250)
        sidebar.setObjectName("sidebar")
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setFixedHeight(80)
        header.setObjectName("sidebarHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        title = QLabel("Navigation")
        title.setObjectName("sidebarTitle")
        
        self.collapse_btn = QPushButton("◀")
        self.collapse_btn.setObjectName("collapseBtn")
        self.collapse_btn.setFixedSize(30, 30)
        self.collapse_btn.clicked.connect(self.toggle_sidebar)
        
        header_layout.addWidget(title)
        header_layout.addWidget(self.collapse_btn)
        
        # Navigation
        nav_widget = QWidget()
        nav_widget.setObjectName("navWidget")
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(15, 20, 15, 20)
        nav_layout.setSpacing(5)
        
        # Navigation buttons
        self.home_btn = self.create_nav_button("🏠 Home", "home")
        self.dashboard_btn = self.create_nav_button("📊 Dashboard", "dashboard")
        self.reports_btn = self.create_nav_button("📄 Reports", "reports")
        
        nav_layout.addWidget(self.home_btn)
        nav_layout.addWidget(self.dashboard_btn)
        nav_layout.addWidget(self.reports_btn)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("navDivider")
        nav_layout.addWidget(divider)
        
        # History button
        self.history_btn = self.create_nav_button("📋 History", "history")
        self.history_badge = QLabel("0")
        self.history_badge.setObjectName("historyBadge")
        self.history_badge.setAlignment(Qt.AlignCenter)
        self.history_badge.setFixedSize(20, 20)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.history_btn)
        btn_layout.addWidget(self.history_badge)
        nav_layout.addLayout(btn_layout)
        
        nav_layout.addStretch()
        
        layout.addWidget(header)
        layout.addWidget(nav_widget)
        
        return sidebar
        
    def create_nav_button(self, text, view_name):
        btn = QPushButton(text)
        btn.setFixedHeight(45)
        btn.setObjectName("navBtn")
        btn.setProperty("view", view_name)
        
        if view_name == "history":
            btn.clicked.connect(self.show_history_drawer)
        else:
            btn.clicked.connect(lambda: self.switch_view(view_name))
            
        return btn
        
    def create_main_content(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        self.header = self.create_header()
        layout.addWidget(self.header)
        
        # Content stack
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")
        
        # Create views
        self.home_view = self.create_home_view()
        self.dashboard_view = self.create_dashboard_view()
        self.reports_view = self.create_reports_view()
        
        self.content_stack.addWidget(self.home_view)
        self.content_stack.addWidget(self.dashboard_view)
        self.content_stack.addWidget(self.reports_view)
        
        layout.addWidget(self.content_stack, 1)
        
        # Footer
        self.footer = self.create_footer()
        layout.addWidget(self.footer)
        
        return widget
        
    def create_header(self):
        header = QWidget()
        header.setFixedHeight(80)
        header.setObjectName("header")
        
        layout = QHBoxLayout(header)
        layout.setContentsMargins(30, 10, 30, 10)
        
        # Left side
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("🧪 Chemical Equipment Visualizer")
        title.setObjectName("mainTitle")
        
        subtitle = QLabel("Real-time analytics for chemical equipment parameters")
        subtitle.setObjectName("subtitle")
        
        left_layout.addWidget(title)
        left_layout.addWidget(subtitle)
        
        # Right side
        right_widget = QWidget()
        right_layout = QHBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.theme_btn = QPushButton("🌙 Dark Mode")
        self.theme_btn.setObjectName("themeBtn")
        self.theme_btn.setFixedSize(120, 35)
        self.theme_btn.clicked.connect(self.toggle_theme)
        
        right_layout.addWidget(self.theme_btn)
        
        layout.addWidget(left_widget)
        layout.addStretch()
        layout.addWidget(right_widget)
        
        return header
        
    def create_footer(self):
        footer = QWidget()
        footer.setFixedHeight(50)
        footer.setObjectName("footer")
        
        layout = QHBoxLayout(footer)
        layout.setContentsMargins(30, 5, 30, 5)
        
        developer_text = QLabel(
            f"Developed by: {self.developer_info['name']} | "
            f"Email: {self.developer_info['email']} | "
            f"{self.developer_info['university']}"
        )
        developer_text.setObjectName("developerText")
        
        layout.addWidget(developer_text)
        layout.addStretch()
        
        return footer
        
    def create_home_view(self):
        widget = QWidget()
        widget.setObjectName("homeView")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(30)
        
        # Upload section
        upload_section = self.create_upload_section()
        layout.addWidget(upload_section)
        
        # Error card (hidden by default)
        self.error_card = self.create_error_card()
        self.error_card.hide()
        layout.addWidget(self.error_card)
        
        # Quick stats (hidden by default)
        self.quick_stats = self.create_quick_stats()
        self.quick_stats.hide()
        layout.addWidget(self.quick_stats)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll)
        
        return container
        
    def create_upload_section(self):
        widget = QWidget()
        widget.setObjectName("uploadSection")
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)
        
        # Header
        header = QWidget()
        header_layout = QVBoxLayout(header)
        header_layout.setAlignment(Qt.AlignCenter)
        
        icon = QLabel("📁")
        icon.setObjectName("sectionIcon")
        icon.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Upload Equipment Data")
        title.setObjectName("sectionTitle")
        title.setAlignment(Qt.AlignCenter)
        
        subtitle = QLabel("Upload a CSV file to analyze chemical equipment parameters")
        subtitle.setObjectName("sectionSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        
        header_layout.addWidget(icon)
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        
        # Upload zone
        self.upload_zone = UploadZone()
        self.upload_zone.file_dropped.connect(self.handle_file_drop)
        
        # Browse button
        self.browse_btn = QPushButton("📁 Browse Files")
        self.browse_btn.setObjectName("browseBtn")
        self.browse_btn.setFixedSize(200, 45)
        self.browse_btn.clicked.connect(self.upload_csv)
        
        # Sample CSV button
        self.sample_btn = QPushButton("📥 Download Sample CSV")
        self.sample_btn.setObjectName("sampleBtn")
        self.sample_btn.setFixedSize(200, 35)
        self.sample_btn.clicked.connect(self.download_sample_csv)
        
        # Button container
        btn_container = QWidget()
        btn_layout = QHBoxLayout(btn_container)
        btn_layout.addStretch()
        btn_layout.addWidget(self.browse_btn)
        btn_layout.addWidget(self.sample_btn)
        btn_layout.addStretch()
        
        layout.addWidget(header)
        layout.addWidget(self.upload_zone)
        layout.addWidget(btn_container)
        
        return widget
        
    def create_error_card(self):
        widget = QWidget()
        widget.setObjectName("errorCard")
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("⚠️ Upload Error")
        title.setObjectName("errorTitle")
        
        self.error_message = QLabel("")
        self.error_message.setObjectName("errorMessage")
        self.error_message.setWordWrap(True)
        
        layout.addWidget(title)
        layout.addWidget(self.error_message)
        
        return widget
        
    def create_quick_stats(self):
        widget = QWidget()
        widget.setObjectName("quickStats")
        
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        title = QLabel("📊 Recent Activity")
        title.setObjectName("quickStatsTitle")
        
        stats_container = QWidget()
        stats_layout = QHBoxLayout(stats_container)
        
        # Last upload
        last_widget = QWidget()
        last_layout = QVBoxLayout(last_widget)
        last_label = QLabel("Last Upload")
        last_label.setObjectName("statLabel")
        self.last_upload_value = QLabel("—")
        self.last_upload_value.setObjectName("statValue")
        last_layout.addWidget(last_label)
        last_layout.addWidget(self.last_upload_value)
        
        # Total records
        total_widget = QWidget()
        total_layout = QVBoxLayout(total_widget)
        total_label = QLabel("Total Records")
        total_label.setObjectName("statLabel")
        self.total_records_value = QLabel("—")
        self.total_records_value.setObjectName("statValue")
        total_layout.addWidget(total_label)
        total_layout.addWidget(self.total_records_value)
        
        # View dashboard button
        view_btn = QPushButton("View Full Dashboard →")
        view_btn.setObjectName("viewDashboardBtn")
        view_btn.setFixedSize(200, 40)
        view_btn.clicked.connect(lambda: self.switch_view("dashboard"))
        
        stats_layout.addWidget(last_widget)
        stats_layout.addWidget(total_widget)
        stats_layout.addStretch()
        stats_layout.addWidget(view_btn)
        
        layout.addWidget(title)
        layout.addWidget(stats_container)
        
        return widget
        
    def create_dashboard_view(self):
        widget = QWidget()
        widget.setObjectName("dashboardView")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(30)
        
        # Dashboard header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        
        title = QLabel("Equipment Analytics Dashboard")
        title.setObjectName("dashboardTitle")
        
        self.export_btn = QPushButton("📄 Export PDF")
        self.export_btn.setObjectName("exportBtn")
        self.export_btn.setFixedSize(150, 40)
        self.export_btn.clicked.connect(self.download_pdf)
        self.export_btn.setEnabled(False)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.export_btn)
        
        # Stats grid
        self.stats_grid = QWidget()
        stats_layout = QHBoxLayout(self.stats_grid)
        stats_layout.setSpacing(20)
        
        # Create stat cards
        self.stat_cards = []
        stat_info = [
            ("Total Equipment", "—", "", "#4f46e5"),
            ("Avg Flowrate", "—", "", "#10b981"),
            ("Avg Pressure", "—", "", "#f59e0b"),
            ("Avg Temperature", "—", "", "#ef4444")
        ]
        
        for title_text, value, icon, color in stat_info:
            card = StatCard(title_text, value, icon, color)
            self.stat_cards.append(card)
            stats_layout.addWidget(card)
            
        stats_layout.insertStretch(0, 1)
        stats_layout.addStretch(1)
        
        # Charts container
        charts_container = QWidget()
        charts_layout = QHBoxLayout(charts_container)
        charts_layout.setSpacing(30)
        
        # Type distribution chart
        type_chart_widget = QWidget()
        type_chart_widget.setObjectName("chartCard")
        type_layout = QVBoxLayout(type_chart_widget)
        
        type_title = QLabel("Equipment Type Distribution")
        type_title.setObjectName("chartTitle")
        
        self.type_figure = Figure(figsize=(8, 4))
        self.type_canvas = FigureCanvas(self.type_figure)
        self.type_canvas.setMinimumHeight(300)
        
        type_layout.addWidget(type_title)
        type_layout.addWidget(self.type_canvas)
        
        # Average parameters chart
        avg_chart_widget = QWidget()
        avg_chart_widget.setObjectName("chartCard")
        avg_layout = QVBoxLayout(avg_chart_widget)
        
        avg_title = QLabel("Average Parameters")
        avg_title.setObjectName("chartTitle")
        
        self.avg_figure = Figure(figsize=(8, 4))
        self.avg_canvas = FigureCanvas(self.avg_figure)
        self.avg_canvas.setMinimumHeight(300)
        
        avg_layout.addWidget(avg_title)
        avg_layout.addWidget(self.avg_canvas)
        
        charts_layout.addWidget(type_chart_widget)
        charts_layout.addWidget(avg_chart_widget)
        
        layout.addWidget(header)
        layout.addWidget(self.stats_grid)
        layout.addWidget(charts_container)
        
        layout.addStretch()
        
        scroll.setWidget(content)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll)
        
        return container
        
    def create_reports_view(self):
        widget = QWidget()
        widget.setObjectName("reportsView")
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(20)
        
        title = QLabel("📄 Generated Reports")
        title.setObjectName("reportsTitle")
        
        # Current report
        self.current_report = self.create_report_card(
            "Current Analysis Report",
            "Latest equipment data analysis",
            "",
            True
        )
        
        # Historical reports container
        self.historical_reports_container = QWidget()
        historical_layout = QVBoxLayout(self.historical_reports_container)
        historical_layout.setSpacing(15)
        
        layout.addWidget(title)
        layout.addWidget(self.current_report)
        layout.addWidget(self.historical_reports_container)
        layout.addStretch()
        
        scroll.setWidget(content)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(scroll)
        
        return container
        
    def create_report_card(self, title, description, stats, current=True):
        widget = QWidget()
        widget.setObjectName("reportCard")
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Info section
        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        
        title_label = QLabel(title)
        title_label.setObjectName("reportTitle")
        
        desc_label = QLabel(description)
        desc_label.setObjectName("reportDesc")
        
        stats_label = QLabel(stats)
        stats_label.setObjectName("reportStats")
        
        info_layout.addWidget(title_label)
        info_layout.addWidget(desc_label)
        info_layout.addWidget(stats_label)
        
        # Button
        if current:
            btn = QPushButton("Download PDF")
            btn.setObjectName("downloadBtn")
            btn.clicked.connect(self.download_pdf)
            btn.setEnabled(False)
            self.current_report_btn = btn
        else:
            btn = QPushButton("Regenerate")
            btn.setObjectName("regenerateBtn")
            btn.setEnabled(False)  # Disable for now
            
        btn.setFixedSize(150, 40)
        
        layout.addWidget(info_widget)
        layout.addStretch()
        layout.addWidget(btn)
        
        return widget
        
    def apply_theme(self):
        if self.dark_mode:
            css = self.get_dark_theme_css()
            self.theme_btn.setText("☀️ Light Mode")
        else:
            css = self.get_light_theme_css()
            self.theme_btn.setText("🌙 Dark Mode")
            
        self.setStyleSheet(css)
        
        # Update stat cards theme
        for card in self.stat_cards:
            card.update_theme(self.dark_mode)
            
        # Refresh if data exists
        if self.summary_data:
            self.update_dashboard()
            
    def get_light_theme_css(self):
        return """
            /* Main Window */
            QMainWindow, QWidget {
                background-color: #ffffff;
                color: #111827;
            }
            
            /* Scroll Area */
            QScrollArea {
                background-color: #ffffff;
                border: none;
            }
            
            QScrollBar:vertical {
                background: #e5e7eb;
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background: #4f46e5;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #4338ca;
            }
            
            /* Sidebar */
            #sidebar {
                background-color: #ffffff;
                border-right: 1px solid #e5e7eb;
            }
            
            #sidebarHeader {
                border-bottom: 1px solid #e5e7eb;
            }
            
            #sidebarTitle {
                font-size: 16px;
                font-weight: bold;
                color: #111827;
            }
            
            #collapseBtn {
                background: none;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                color: #6b7280;
                font-size: 12px;
            }
            
            #collapseBtn:hover {
                background: #f9fafb;
            }
            
            /* Navigation */
            #navBtn {
                background: none;
                border: none;
                border-radius: 8px;
                color: #6b7280;
                font-size: 14px;
                text-align: left;
                padding-left: 15px;
            }
            
            #navBtn:hover {
                background: #f9fafb;
                color: #111827;
            }
            
            QPushButton#navBtn[view="home"]:checked,
            QPushButton#navBtn[view="dashboard"]:checked,
            QPushButton#navBtn[view="reports"]:checked {
                background: #4f46e5;
                color: white;
            }
            
            #navDivider {
                background: #e5e7eb;
                max-height: 1px;
            }
            
            #historyBadge {
                background: #4f46e5;
                color: white;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }
            
            /* Header */
            #header {
                background-color: #ffffff;
                border-bottom: 1px solid #e5e7eb;
            }
            
            #mainTitle {
                font-size: 24px;
                font-weight: 800;
                color: #111827;
            }
            
            #subtitle {
                font-size: 14px;
                color: #6b7280;
            }
            
            #themeBtn {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                color: #111827;
                font-size: 14px;
            }
            
            #themeBtn:hover {
                background-color: #e5e7eb;
            }
            
            /* Footer */
            #footer {
                background-color: #ffffff;
                border-top: 1px solid #e5e7eb;
            }
            
            #developerText {
                font-size: 12px;
                color: #6b7280;
            }
            
            /* Home View */
            #homeView {
                background-color: #ffffff;
            }
            
            #sectionIcon {
                font-size: 32px;
            }
            
            #sectionTitle {
                font-size: 32px;
                font-weight: 700;
                color: #111827;
                margin: 10px 0 5px 0;
            }
            
            #sectionSubtitle {
                font-size: 18px;
                color: #6b7280;
            }
            
            /* Upload Zone */
            UploadZone {
                border: 2px dashed #e5e7eb;
                border-radius: 12px;
                background-color: #f9fafb;
            }
            
            #uploadIcon {
                font-size: 48px;
            }
            
            #uploadText {
                font-size: 24px;
                font-weight: bold;
                color: #111827;
            }
            
            #uploadHint {
                font-size: 18px;
                color: #9ca3af;
            }
            
            #uploadRequirements {
                font-size: 14px;
                color: #9ca3af;
                line-height: 1.4;
            }
            
            /* Buttons */
            #browseBtn {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
            }
            
            #browseBtn:hover {
                background-color: #4338ca;
            }
            
            #sampleBtn {
                background: transparent;
                color: #4f46e5;
                border: 1px solid #4f46e5;
                border-radius: 8px;
                font-size: 14px;
            }
            
            #sampleBtn:hover {
                background: #4f46e5;
                color: white;
            }
            
            /* Error Card */
            #errorCard {
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.05));
                border-left: 4px solid #ef4444;
                border-radius: 8px;
            }
            
            #errorTitle {
                color: #ef4444;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            #errorMessage {
                color: #6b7280;
            }
            
            /* Quick Stats */
            #quickStatsTitle {
                color: #111827;
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            
            #statLabel {
                font-size: 14px;
                color: #9ca3af;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            
            #statValue {
                font-size: 24px;
                font-weight: 700;
                color: #111827;
            }
            
            #viewDashboardBtn {
                background: transparent;
                color: #4f46e5;
                border: 1px solid #4f46e5;
                border-radius: 8px;
                font-size: 14px;
            }
            
            #viewDashboardBtn:hover {
                background: #4f46e5;
                color: white;
            }
            
            /* Dashboard */
            #dashboardTitle {
                font-size: 28px;
                font-weight: bold;
                color: #111827;
            }
            
            #exportBtn {
                background: transparent;
                color: #4f46e5;
                border: 1px solid #4f46e5;
                border-radius: 8px;
                font-size: 14px;
            }
            
            #exportBtn:hover {
                background: #4f46e5;
                color: white;
            }
            
            #exportBtn:disabled {
                background: #9ca3af;
                color: #6b7280;
                border-color: #9ca3af;
            }
            
            /* Stat Cards */
            QFrame#statCard {
                background: white;
                border-radius: 12px;
                border-left: 4px solid #4f46e5;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            }
            
            QFrame#statCard:hover {
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
            }
            
            #statTitle {
                font-size: 14px;
                color: #6b7280;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            
            #statIcon {
                font-size: 18px;
            }
            
            /* Chart Cards */
            #chartCard {
                background: white;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
                padding: 20px;
            }
            
            #chartTitle {
                color: #111827;
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 15px;
            }
            
            /* Reports */
            #reportsTitle {
                font-size: 28px;
                font-weight: bold;
                color: #111827;
                margin-bottom: 15px;
            }
            
            #reportCard {
                background: white;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
            
            #reportCard:hover {
                border-color: #4f46e5;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            }
            
            #reportTitle {
                color: #111827;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            #reportDesc {
                color: #6b7280;
                font-size: 14px;
                margin-bottom: 5px;
            }
            
            #reportStats {
                font-size: 12px;
                color: #9ca3af;
            }
            
            #downloadBtn, #regenerateBtn {
                background: #4f46e5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            
            #downloadBtn:hover, #regenerateBtn:hover {
                background: #4338ca;
            }
            
            #downloadBtn:disabled {
                background: #9ca3af;
                color: #6b7280;
            }
            
            #regenerateBtn {
                background: transparent;
                color: #4f46e5;
                border: 1px solid #4f46e5;
            }
            
            #regenerateBtn:hover {
                background: #4f46e5;
                color: white;
            }
            
            /* History Drawer */
            #historyDrawer {
                background: white;
                border-left: 1px solid #e5e7eb;
                border-radius: 0;
            }
            
            #drawerHeader {
                border-bottom: 1px solid #e5e7eb;
                padding: 20px;
            }
            
            #drawerTitle {
                font-size: 20px;
                font-weight: 600;
                color: #111827;
            }
            
            #closeBtn {
                background: none;
                border: none;
                color: #6b7280;
                font-size: 16px;
            }
            
            #closeBtn:hover {
                background: #f9fafb;
                border-radius: 4px;
            }
            
            #historyItem {
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
            }
            
            #historyItem:hover {
                border-color: #4f46e5;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
            }
            
            #historyTime {
                font-size: 13px;
                color: #6b7280;
                font-weight: 500;
            }
            
            #historyStat {
                font-size: 12px;
                color: #6b7280;
                background: #f9fafb;
                padding: 4px 8px;
                border-radius: 6px;
            }
            
            #viewBtn {
                background: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                font-size: 14px;
                color: #111827;
                padding: 6px 12px;
            }
            
            #viewBtn:hover {
                background: #e5e7eb;
            }
            
            #emptyHistory {
                font-size: 14px;
                color: #9ca3af;
                font-style: italic;
                padding: 20px;
            }
        """
        
    def get_dark_theme_css(self):
        return """
            /* Main Window */
            QMainWindow, QWidget {
                background-color: #0f172a;
                color: #f1f5f9;
            }
            
            /* Scroll Area */
            QScrollArea {
                background-color: #0f172a;
                border: none;
            }
            
            QScrollBar:vertical {
                background: #1e293b;
                width: 12px;
                border-radius: 6px;
            }
            
            QScrollBar::handle:vertical {
                background: #4f46e5;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #4338ca;
            }
            
            /* Sidebar */
            #sidebar {
                background-color: #1e293b;
                border-right: 1px solid #334155;
            }
            
            #sidebarHeader {
                border-bottom: 1px solid #334155;
            }
            
            #sidebarTitle {
                font-size: 16px;
                font-weight: bold;
                color: #f1f5f9;
            }
            
            #collapseBtn {
                background: none;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #94a3b8;
                font-size: 12px;
            }
            
            #collapseBtn:hover {
                background: #1e293b;
            }
            
            /* Navigation */
            #navBtn {
                background: none;
                border: none;
                border-radius: 8px;
                color: #cbd5e1;
                font-size: 14px;
                text-align: left;
                padding-left: 15px;
            }
            
            #navBtn:hover {
                background: #1e293b;
                color: #f1f5f9;
            }
            
            QPushButton#navBtn[view="home"]:checked,
            QPushButton#navBtn[view="dashboard"]:checked,
            QPushButton#navBtn[view="reports"]:checked {
                background: #4f46e5;
                color: white;
            }
            
            #navDivider {
                background: #334155;
                max-height: 1px;
            }
            
            #historyBadge {
                background: #4f46e5;
                color: white;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }
            
            /* Header */
            #header {
                background-color: #1e293b;
                border-bottom: 1px solid #334155;
            }
            
            #mainTitle {
                font-size: 24px;
                font-weight: 800;
                color: #f1f5f9;
            }
            
            #subtitle {
                font-size: 14px;
                color: #cbd5e1;
            }
            
            #themeBtn {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f1f5f9;
                font-size: 14px;
            }
            
            #themeBtn:hover {
                background-color: #334155;
            }
            
            /* Footer */
            #footer {
                background-color: #1e293b;
                border-top: 1px solid #334155;
            }
            
            #developerText {
                font-size: 12px;
                color: #94a3b8;
            }
            
            /* Home View */
            #homeView {
                background-color: #0f172a;
            }
            
            #sectionIcon {
                font-size: 32px;
            }
            
            #sectionTitle {
                font-size: 32px;
                font-weight: 700;
                color: #f1f5f9;
                margin: 10px 0 5px 0;
            }
            
            #sectionSubtitle {
                font-size: 18px;
                color: #cbd5e1;
            }
            
            /* Upload Zone */
            UploadZone {
                border: 2px dashed #334155;
                border-radius: 12px;
                background-color: #1e293b;
            }
            
            #uploadIcon {
                font-size: 48px;
            }
            
            #uploadText {
                font-size: 24px;
                font-weight: bold;
                color: #f1f5f9;
            }
            
            #uploadHint {
                font-size: 18px;
                color: #94a3b8;
            }
            
            #uploadRequirements {
                font-size: 14px;
                color: #94a3b8;
                line-height: 1.4;
            }
            
            /* Buttons */
            #browseBtn {
                background-color: #4f46e5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
            }
            
            #browseBtn:hover {
                background-color: #4338ca;
            }
            
            #sampleBtn {
                background: transparent;
                color: #4f46e5;
                border: 1px solid #4f46e5;
                border-radius: 8px;
                font-size: 14px;
            }
            
            #sampleBtn:hover {
                background: #4f46e5;
                color: white;
            }
            
            /* Error Card */
            #errorCard {
                background: linear-gradient(135deg, rgba(239, 68, 68, 0.1), rgba(239, 68, 68, 0.05));
                border-left: 4px solid #ef4444;
                border-radius: 8px;
            }
            
            #errorTitle {
                color: #ef4444;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            #errorMessage {
                color: #cbd5e1;
            }
            
            /* Quick Stats */
            #quickStatsTitle {
                color: #f1f5f9;
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 10px;
            }
            
            #statLabel {
                font-size: 14px;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            
            #statValue {
                font-size: 24px;
                font-weight: 700;
                color: #f1f5f9;
            }
            
            #viewDashboardBtn {
                background: transparent;
                color: #4f46e5;
                border: 1px solid #4f46e5;
                border-radius: 8px;
                font-size: 14px;
            }
            
            #viewDashboardBtn:hover {
                background: #4f46e5;
                color: white;
            }
            
            /* Dashboard */
            #dashboardTitle {
                font-size: 28px;
                font-weight: bold;
                color: #f1f5f9;
            }
            
            #exportBtn {
                background: transparent;
                color: #4f46e5;
                border: 1px solid #4f46e5;
                border-radius: 8px;
                font-size: 14px;
            }
            
            #exportBtn:hover {
                background: #4f46e5;
                color: white;
            }
            
            #exportBtn:disabled {
                background: #475569;
                color: #94a3b8;
                border-color: #475569;
            }
            
            /* Stat Cards */
            QFrame#statCard {
                background: #1e293b;
                border-radius: 12px;
                border-left: 4px solid #4f46e5;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px 0 rgba(0, 0, 0, 0.3);
            }
            
            QFrame#statCard:hover {
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.4), 0 4px 6px -2px rgba(0, 0, 0, 0.3);
            }
            
            #statTitle {
                font-size: 14px;
                color: #94a3b8;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }
            
            #statIcon {
                font-size: 18px;
            }
            
            /* Chart Cards */
            #chartCard {
                background: #1e293b;
                border-radius: 12px;
                border: 1px solid #334155;
                padding: 20px;
            }
            
            #chartTitle {
                color: #f1f5f9;
                font-size: 20px;
                font-weight: bold;
                margin-bottom: 15px;
            }
            
            /* Reports */
            #reportsTitle {
                font-size: 28px;
                font-weight: bold;
                color: #f1f5f9;
                margin-bottom: 15px;
            }
            
            #reportCard {
                background: #1e293b;
                border-radius: 8px;
                border: 1px solid #334155;
            }
            
            #reportCard:hover {
                border-color: #4f46e5;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px 0 rgba(0, 0, 0, 0.3);
            }
            
            #reportTitle {
                color: #f1f5f9;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            
            #reportDesc {
                color: #cbd5e1;
                font-size: 14px;
                margin-bottom: 5px;
            }
            
            #reportStats {
                font-size: 12px;
                color: #94a3b8;
            }
            
            #downloadBtn, #regenerateBtn {
                background: #4f46e5;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
            }
            
            #downloadBtn:hover, #regenerateBtn:hover {
                background: #4338ca;
            }
            
            #downloadBtn:disabled {
                background: #475569;
                color: #94a3b8;
            }
            
            #regenerateBtn {
                background: transparent;
                color: #4f46e5;
                border: 1px solid #4f46e5;
            }
            
            #regenerateBtn:hover {
                background: #4f46e5;
                color: white;
            }
            
            /* History Drawer */
            #historyDrawer {
                background: #1e293b;
                border-left: 1px solid #334155;
                border-radius: 0;
            }
            
            #drawerHeader {
                border-bottom: 1px solid #334155;
                padding: 20px;
            }
            
            #drawerTitle {
                font-size: 20px;
                font-weight: 600;
                color: #f1f5f9;
            }
            
            #closeBtn {
                background: none;
                border: none;
                color: #94a3b8;
                font-size: 16px;
            }
            
            #closeBtn:hover {
                background: #1e293b;
                border-radius: 4px;
            }
            
            #historyItem {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
            
            #historyItem:hover {
                border-color: #4f46e5;
                box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px 0 rgba(0, 0, 0, 0.3);
            }
            
            #historyTime {
                font-size: 13px;
                color: #94a3b8;
                font-weight: 500;
            }
            
            #historyStat {
                font-size: 12px;
                color: #cbd5e1;
                background: #1e293b;
                padding: 4px 8px;
                border-radius: 6px;
                border: 1px solid #334155;
            }
            
            #viewBtn {
                background: #1e293b;
                border: 1px solid #334155;
                border-radius: 6px;
                font-size: 14px;
                color: #f1f5f9;
                padding: 6px 12px;
            }
            
            #viewBtn:hover {
                background: #334155;
            }
            
            #emptyHistory {
                font-size: 14px;
                color: #94a3b8;
                font-style: italic;
                padding: 20px;
            }
        """
        
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.apply_theme()
        
    def toggle_sidebar(self):
        if self.sidebar_collapsed:
            self.sidebar.setFixedWidth(250)
            self.collapse_btn.setText("◀")
        else:
            self.sidebar.setFixedWidth(70)
            self.collapse_btn.setText("▶")
            
        self.sidebar_collapsed = not self.sidebar_collapsed
        
    def switch_view(self, view_name):
        # Update button states
        for btn in [self.home_btn, self.dashboard_btn, self.reports_btn]:
            btn.setProperty("checked", False)
            
        if view_name == "home":
            self.home_btn.setProperty("checked", True)
            self.content_stack.setCurrentIndex(0)
            self.update_home_view()
        elif view_name == "dashboard":
            if not self.summary_data:
                QMessageBox.information(self, "No Data", 
                    "Please upload a CSV file first to view the dashboard.")
                self.switch_view("home")
                return
            self.dashboard_btn.setProperty("checked", True)
            self.content_stack.setCurrentIndex(1)
            self.update_dashboard()
        elif view_name == "reports":
            self.reports_btn.setProperty("checked", True)
            self.content_stack.setCurrentIndex(2)
            self.update_reports_view()
            
        self.apply_theme()  # Refresh styles
        
    def show_history_drawer(self):
        self.history_drawer.update_history(self.history_data)
        self.history_drawer.show()
        
    def update_home_view(self):
        if self.history_data:
            self.quick_stats.show()
            try:
                last_item = self.history_data[0]
                
                # Parse timestamp
                uploaded_at = last_item.get('uploaded_at', '')
                try:
                    date_str = datetime.fromisoformat(uploaded_at.replace('Z', '+00:00')).strftime("%Y-%m-%d")
                except:
                    date_str = str(uploaded_at)[:10]
                
                self.last_upload_value.setText(date_str)
                self.total_records_value.setText(str(last_item.get('total_equipment', 'N/A')))
            except Exception as e:
                print(f"[ERROR] Error updating home view: {e}")
                self.last_upload_value.setText("—")
                self.total_records_value.setText("—")
        else:
            self.quick_stats.hide()
        
        # Hide error card
        self.error_card.hide()
        
    def handle_file_drop(self, file_path):
        self.upload_file(file_path)
        
    def upload_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV File", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            self.upload_file(file_path)
            
    def upload_file(self, file_path):
        try:
            self.show_loading()
            
            # Validate CSV
            with open(file_path, 'r') as f:
                first_line = f.readline()
                required_cols = ["Equipment Name", "Type", "Flowrate", "Pressure", "Temperature"]
                if not all(col in first_line for col in required_cols):
                    raise Exception("CSV missing required columns. Needs: Equipment Name, Type, Flowrate, Pressure, Temperature")
                    
            # Upload file
            with open(file_path, 'rb') as f:
                files = {'file': f}
                response = requests.post(f"{API_BASE}/upload/", files=files)
                
            if response.status_code != 200:
                raise Exception(f"Upload failed: {response.text}")
                
            # Get summary
            summary_response = requests.get(f"{API_BASE}/summary/")
            if summary_response.status_code != 200:
                raise Exception("Failed to get summary")
                
            self.summary_data = summary_response.json()
            
            # Update all views
            self.load_history()
            self.update_home_view()
            self.update_reports_view()
            
            # Switch to dashboard
            self.switch_view("dashboard")
            
            self.hide_loading()
            
            QMessageBox.information(self, "Success", 
                f"✅ Successfully processed {self.summary_data['total_equipment']} equipment records!")
                
        except Exception as e:
            self.hide_loading()
            self.show_error(str(e))
            
    def show_error(self, message):
        self.error_message.setText(message)
        self.error_card.show()
        
    def show_loading(self):
        self.loading_overlay.show()
        QApplication.processEvents()
        
    def hide_loading(self):
        self.loading_overlay.hide()
        
    def load_history(self):
        try:
            response = requests.get(f"{API_BASE}/history/")
            if response.status_code == 200:
                self.history_data = response.json()
                
                # Debug: Print API response
                print(f"[DEBUG] History data received: {len(self.history_data)} items")
                if self.history_data:
                    print(f"[DEBUG] First item keys: {self.history_data[0].keys()}")
                    print(f"[DEBUG] First item values: {self.history_data[0]}")
                
                # Update badge
                self.history_badge.setText(str(len(self.history_data)))
                
                # Update drawer
                self.history_drawer.update_history(self.history_data)
                
                # Update home view quick stats
                self.update_home_view()
        except Exception as e:
            print(f"[ERROR] Error loading history: {e}")
            import traceback
            traceback.print_exc()
            
    def update_dashboard(self):
        if not self.summary_data:
            return
            
        # Update stat cards
        stats_data = [
            str(self.summary_data['total_equipment']),
            f"{self.summary_data['avg_flowrate']:.2f}",
            f"{self.summary_data['avg_pressure']:.2f}",
            f"{self.summary_data['avg_temperature']:.2f}"
        ]
        
        for card, value in zip(self.stat_cards, stats_data):
            # Find the value label
            for child in card.findChildren(QLabel):
                if child.objectName() == "statValue":
                    child.setText(value)
                    
        # Update charts
        self.update_charts()
        
        # Enable export button
        self.export_btn.setEnabled(True)
        
    def update_charts(self):
        if not self.summary_data:
            return
            
        # Determine colors based on theme
        if self.dark_mode:
            bg_color = '#1e293b'
            text_color = '#f1f5f9'
            grid_color = '#334155'
            spine_color = '#475569'
        else:
            bg_color = 'white'
            text_color = '#111827'
            grid_color = '#e5e7eb'
            spine_color = '#d1d5db'
            
        # Update type distribution chart
        self.type_figure.clear()
        ax1 = self.type_figure.add_subplot(111)
        
        types = list(self.summary_data['type_distribution'].keys())
        counts = list(self.summary_data['type_distribution'].values())
        
        # Chart.js-like colors
        colors = ['#4f46e5', '#6366f1', '#818cf8', '#93c5fd', '#60a5fa'][:len(types)]
        
        bars = ax1.bar(types, counts, color=colors, edgecolor='white', linewidth=2)
        ax1.set_title('Equipment Type Distribution', color=text_color, fontsize=14, fontweight='bold', pad=20)
        ax1.set_ylabel('Count', color=text_color, fontsize=12)
        
        # Style the chart
        ax1.tick_params(axis='x', rotation=45, colors=text_color, labelsize=10)
        ax1.tick_params(axis='y', colors=text_color, labelsize=10)
        
        self.type_figure.patch.set_facecolor(bg_color)
        ax1.set_facecolor(bg_color)
        
        for spine in ax1.spines.values():
            spine.set_color(spine_color)
            spine.set_linewidth(1)
            
        ax1.grid(True, axis='y', alpha=0.3, color=grid_color, linestyle='--', linewidth=0.5)
        ax1.set_axisbelow(True)
        
        # Add value labels like Chart.js
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                    f'{int(height)}', ha='center', va='bottom',
                    color=text_color, fontsize=10, fontweight='bold')
                    
        self.type_figure.tight_layout()
        self.type_canvas.draw()
        
        # Update average parameters chart
        self.avg_figure.clear()
        ax2 = self.avg_figure.add_subplot(111)
        
        params = ['Flowrate', 'Pressure', 'Temperature']
        values = [
            self.summary_data['avg_flowrate'],
            self.summary_data['avg_pressure'],
            self.summary_data['avg_temperature']
        ]
        
        bar_colors = ['#10b981', '#f59e0b', '#ef4444']
        bars2 = ax2.bar(params, values, color=bar_colors, edgecolor='white', linewidth=2)
        ax2.set_title('Average Parameters', color=text_color, fontsize=14, fontweight='bold', pad=20)
        ax2.set_ylabel('Value', color=text_color, fontsize=12)
        
        # Style the chart
        ax2.tick_params(axis='x', colors=text_color, labelsize=11)
        ax2.tick_params(axis='y', colors=text_color, labelsize=10)
        
        self.avg_figure.patch.set_facecolor(bg_color)
        ax2.set_facecolor(bg_color)
        
        for spine in ax2.spines.values():
            spine.set_color(spine_color)
            spine.set_linewidth(1)
            
        ax2.grid(True, axis='y', alpha=0.3, color=grid_color, linestyle='--', linewidth=0.5)
        ax2.set_axisbelow(True)
        
        # Add value labels
        for bar, value in zip(bars2, values):
            height = bar.get_height()
            formatted_value = f'{value:.2f}'
            ax2.text(bar.get_x() + bar.get_width()/2., height + (max(values) * 0.05),
                    formatted_value, ha='center', va='bottom',
                    color=text_color, fontsize=11, fontweight='bold')
                    
        y_max = max(values) * 1.2 if values else 1
        ax2.set_ylim(0, y_max)
        
        self.avg_figure.tight_layout()
        self.avg_canvas.draw()
        
    def update_reports_view(self):
        # Update current report
        if self.summary_data:
            stats_text = f"📊 {self.summary_data['total_equipment']} equipment • 📅 {datetime.now().strftime('%Y-%m-%d')}"
            # Update current report card
            for child in self.current_report.findChildren(QLabel):
                if child.objectName() == "reportStats":
                    child.setText(stats_text)
            self.current_report_btn.setEnabled(True)
            
        # Clear historical reports
        layout = self.historical_reports_container.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        # Add historical reports
        for i, item in enumerate(self.history_data[:5]):
            try:
                time_str = datetime.fromisoformat(
                    item['uploaded_at'].replace('Z', '+00:00')
                ).strftime("%Y-%m-%d %H:%M")
                
                stats = f"📊 {item.get('total_equipment', 'N/A')} equipment • ⚡ {float(item.get('avg_flowrate', 0)):.2f} flowrate"
                
                report_card = self.create_report_card(
                    f"Historical Report #{i + 1}",
                    time_str,
                    stats,
                    False
                )
                
                layout.addWidget(report_card)
            except:
                continue
                
    def download_pdf(self):
        webbrowser.open(f"{API_BASE}/report/")
        
    def download_sample_csv(self):
        try:
            # Create sample CSV data
            csv_content = """Equipment Name,Type,Flowrate,Pressure,Temperature
Reactor A,CSTR,150,2.5,85
Reactor B,PFR,200,3.2,90
Separator A,Centrifuge,75,1.8,60
Mixer X,Agitated,120,1.2,45
Tank Y,Storage,50,0.8,25
Filter Z,Plate,95,1.5,70
Reactor C,CSTR,180,2.8,88
Separator B,Decanter,65,1.6,55"""
            
            # Save to file
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Sample CSV", "sample_equipment_data.csv", "CSV Files (*.csv)"
            )
            
            if file_path:
                with open(file_path, 'w') as f:
                    f.write(csv_content)
                QMessageBox.information(self, "Success", f"Sample CSV saved to:\n{file_path}")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save sample CSV: {str(e)}")
            
    def closeEvent(self, event):
        print(f"[{datetime.now().isoformat()}] Application closed")
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application font
    font = QFont("Inter", 10)
    app.setFont(font)
    
    window = ChemicalEquipmentApp()
    window.show()
    
    # Print startup message
    print(f"[{datetime.now().isoformat()}] Chemical Equipment Visualizer Desktop App started")
    print(f"[DEBUG] Developer: {window.developer_info['name']}")
    print(f"[DEBUG] Backend API: {API_BASE}")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()