import sys
import csv
from collections import Counter

from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QGridLayout, QFrame,
    QFileDialog, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class EquipmentVisualizer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Chemical Equipment Parameter Visualizer")
        self.setMinimumSize(1200, 780)
        self.setStyleSheet("background-color: #f5f7fa;")

        self.value_labels = {}
        self.type_counts = {}

        self.init_ui()

    def init_ui(self):
        # Scroll area wrapper
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        main = QVBoxLayout(container)
        main.setContentsMargins(32, 32, 32, 32)
        main.setSpacing(28)

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        # Title
        title = QLabel("Chemical Equipment Parameter Visualizer")
        title.setFont(QFont("Arial", 22, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #111827;")
        main.addWidget(title)

        # Upload card
        upload_card = self.card()
        self.upload_card = upload_card  # keep reference
        upload = QHBoxLayout(upload_card)

        upload_label = QLabel("Upload CSV File")
        upload_label.setFont(QFont("Arial", 13))

        upload_btn = QPushButton("Choose File")
        upload_btn.setFixedSize(160, 42)
        upload_btn.setStyleSheet(self.button_style())
        upload_btn.clicked.connect(self.load_csv)

        upload.addWidget(upload_label)
        upload.addStretch()
        upload.addWidget(upload_btn)

        main.addWidget(upload_card)

        # OUTPUT (hidden initially)
        self.output_widget = QWidget()
        self.output_layout = QVBoxLayout(self.output_widget)
        self.output_layout.setSpacing(28)
        self.output_widget.hide()

        # Back/Home button
        self.back_btn = QPushButton("Home")
        self.back_btn.setFixedSize(120, 40)
        self.back_btn.setStyleSheet(self.button_style())
        self.back_btn.clicked.connect(self.reset_app)
        self.output_layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)

        # Overview
        overview_title = QLabel("Overview")
        overview_title.setFont(QFont("Arial", 18, QFont.Bold))
        self.output_layout.addWidget(overview_title)

        overview_card = self.card()
        grid = QGridLayout(overview_card)
        grid.setSpacing(28)

        metrics = [
            "Total Equipment",
            "Avg Flowrate",
            "Avg Pressure",
            "Avg Temperature",
        ]

        for i, name in enumerate(metrics):
            block = QVBoxLayout()

            label = QLabel(name)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color:#6b7280; font-size:12px;")

            value = QLabel("—")
            value.setAlignment(Qt.AlignCenter)
            value.setFont(QFont("Arial", 20, QFont.Bold))
            value.setStyleSheet("color:#2563eb;")

            self.value_labels[name] = value

            block.addWidget(label)
            block.addWidget(value)
            grid.addLayout(block, 0, i)

        self.output_layout.addWidget(overview_card)

        # Charts
        self.type_card = self.visual_card("Type Distribution", "#4bc0c0")
        self.avg_card = self.visual_card("Average Parameters", "#9966ff")

        self.output_layout.addWidget(self.type_card["card"])
        self.output_layout.addWidget(self.avg_card["card"])

        main.addWidget(self.output_widget)

    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open CSV", "", "CSV Files (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                raw_headers = [h.strip().lower().replace(" ", "_") for h in reader.fieldnames]

                # Map flexible headers
                header_map = {}
                for h in raw_headers:
                    if "type" in h:
                        header_map[h] = "equipment_type"
                    elif "flow" in h:
                        header_map[h] = "flowrate"
                    elif "press" in h:
                        header_map[h] = "pressure"
                    elif "temp" in h:
                        header_map[h] = "temperature"

                required = ["equipment_type", "flowrate", "pressure", "temperature"]
                if not all(r in header_map.values() for r in required):
                    raise ValueError("CSV must contain: equipment_type, flowrate, pressure, temperature")

                rows = []
                for row in reader:
                    new_row = {}
                    for raw_key, value in row.items():
                        key = header_map.get(raw_key.strip().lower().replace(" ", "_"))
                        if key:
                            new_row[key] = value
                    rows.append(new_row)

            total = len(rows)
            avg_flow = sum(float(r["flowrate"]) for r in rows) / total
            avg_press = sum(float(r["pressure"]) for r in rows) / total
            avg_temp = sum(float(r["temperature"]) for r in rows) / total

            self.type_counts = Counter(r["equipment_type"] for r in rows)

            self.value_labels["Total Equipment"].setText(str(total))
            self.value_labels["Avg Flowrate"].setText(f"{avg_flow:.2f}")
            self.value_labels["Avg Pressure"].setText(f"{avg_press:.2f}")
            self.value_labels["Avg Temperature"].setText(f"{avg_temp:.2f}")

            self.draw_type_chart()
            self.draw_avg_chart(avg_flow, avg_press, avg_temp)

            # Ensure charts are visible again
            self.type_card["card"].show()
            self.avg_card["card"].show()

            # Hide upload section, show results
            self.upload_card.hide()
            self.output_widget.show()

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def visual_card(self, title, color):
        card = self.card()
        layout = QVBoxLayout(card)
        layout.setSpacing(14)

        label = QLabel(title)
        label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(label)

        fig = Figure(figsize=(8, 5))
        canvas = FigureCanvas(fig)
        canvas.setFixedHeight(350)

        layout.addWidget(canvas)

        return {"card": card, "figure": fig, "canvas": canvas, "color": color}

    def draw_type_chart(self):
        fig = self.type_card["figure"]
        fig.clear()
        ax = fig.add_subplot(111)

        names = list(self.type_counts.keys())
        values = list(self.type_counts.values())

        ax.bar(names, values, color=self.type_card["color"], width=0.5)
        ax.set_ylim(0, max(values) + 1)
        ax.set_ylabel("Count")

        ax.spines[['top', 'right']].set_visible(False)
        ax.tick_params(left=True)

        fig.tight_layout()
        self.type_card["canvas"].draw()

    def draw_avg_chart(self, f, p, t):
        fig = self.avg_card["figure"]
        fig.clear()
        ax = fig.add_subplot(111)

        ax.bar(
            ["Flowrate", "Pressure", "Temperature"],
            [f, p, t],
            color=self.avg_card["color"],
            width=0.45
        )
        ax.set_ylabel("Value")

        ax.spines[['top', 'right']].set_visible(False)
        ax.tick_params(left=True)

        fig.tight_layout()
        self.avg_card["canvas"].draw()

    def card(self):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 14px;
                padding: 22px;
            }
        """)
        return frame

    def button_style(self):
        return """
            QPushButton {
                background-color: #2563eb;
                color: white;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """

    def reset_app(self):
        # Hide results
        self.output_widget.hide()

        # Clear values
        for label in self.value_labels.values():
            label.setText("—")

        # Hide charts
        self.type_card["card"].hide()
        self.avg_card["card"].hide()

        # Show upload section again
        self.upload_card.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = EquipmentVisualizer()
    w.show()
    sys.exit(app.exec_())