#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MSG TO EML 版权所有caoyz001
专业离线 MSG 转 EML 批量处理工具 (蓝色极速版)
"""

import sys
import os
import time  # 新增 time 模块用于计算耗时
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QFileDialog, QMessageBox, 
    QGroupBox, QStyleFactory, QLineEdit, QTableWidget, 
    QTableWidgetItem, QHeaderView, QTextEdit, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QMutexLocker
from PyQt6.QtGui import QFont, QDragEnterEvent, QDropEvent, QColor, QBrush, QIcon

# 邮件生成标准库
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders, policy

# 检查 MSG 核心解析库
try:
    import extract_msg
    EXTRACT_MSG_OK = True
except ImportError:
    EXTRACT_MSG_OK = False


# ========================== 后台转换工作线程 (极速优化版) ==========================
class ConvertWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str, str)  # text, color_hex
    row_status = pyqtSignal(int, str, str, str)  # row_index, status_text, color_hex, duration_text
    finished = pyqtSignal(bool, str)

    def __init__(self, tasks: List[Dict], output_dir: str):
        super().__init__()
        self.tasks = tasks
        self.output_dir = output_dir
        self._is_cancelled = False
        self.mutex = QMutex()

    def cancel(self):
        with QMutexLocker(self.mutex):
            self._is_cancelled = True

    def is_cancelled(self):
        with QMutexLocker(self.mutex):
            return self._is_cancelled

    def run(self):
        if not EXTRACT_MSG_OK:
            self.finished.emit(False, "缺少 extract_msg 库，无法读取 .msg 文件。\n请在终端运行: pip install extract-msg")
            return

        total = len(self.tasks)
        if total == 0:
            self.finished.emit(True, "没有需要转换的任务。")
            return

        success_count = 0
        errors = []

        for idx, task in enumerate(self.tasks):
            if self.is_cancelled():
                self.log.emit("⚠️ 用户已取消转换", "#FF9800")
                break

            row = task['row']
            msg_path = task['path']
            base_name = os.path.basename(msg_path)
            
            self.log.emit(f"🔄 正在极速处理: {base_name}", "#0052CC")
            # 状态更新为处理中，耗时留空
            self.row_status.emit(row, "处理中...", "#FF9800", "-")
            
            start_time = time.time()  # 开始计时

            try:
                out_file = self.convert_msg_to_eml(msg_path, self.output_dir)
                end_time = time.time()  # 结束计时
                duration = f"{end_time - start_time:.2f}s"

                if out_file:
                    success_count += 1
                    self.log.emit(f"✅ 成功: {os.path.basename(out_file)} ({duration})", "#00A854")
                    self.row_status.emit(row, "成功", "#00A854", duration)
                else:
                    raise Exception("转换失败，未能生成 EML 文件")

            except Exception as e:
                end_time = time.time()
                duration = f"{end_time - start_time:.2f}s"
                error_msg = f"❌ 错误 {base_name}: {str(e)}"
                errors.append(error_msg)
                self.log.emit(error_msg, "#F5222D")
                self.row_status.emit(row, "失败", "#F5222D", duration)

            self.progress.emit(int((idx + 1) / total * 100))

        self.progress.emit(100)
        summary = f"执行完毕! 成功: {success_count} / 总计: {total}"
        if errors:
            self.finished.emit(False, summary + f"\n遇到 {len(errors)} 个错误，请查看日志。")
        else:
            self.finished.emit(True, summary)

    def convert_msg_to_eml(self, msg_path: str, out_dir: str) -> Optional[str]:
        os.makedirs(out_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(msg_path))[0]
        out_path = os.path.join(out_dir, f"{base_name}.eml")

        msg = extract_msg.Message(msg_path)
        eml_msg = EmailMessage()
        eml_msg.set_charset('utf-8')

        if msg.subject: eml_msg['Subject'] = msg.subject
        if msg.sender: eml_msg['From'] = msg.sender
        if msg.to: eml_msg['To'] = ', '.join(msg.to) if isinstance(msg.to, list) else msg.to
        if msg.cc: eml_msg['Cc'] = ', '.join(msg.cc) if isinstance(msg.cc, list) else msg.cc
        
        if msg.date: 
            eml_msg['Date'] = msg.date.strftime("%a, %d %b %Y %H:%M:%S %z")
        else: 
            eml_msg['Date'] = formatdate()
        
        eml_msg['Message-ID'] = make_msgid()

        body_plain = msg.body or ""
        body_html = msg.htmlBody or ""

        attachments = []
        for att in msg.attachments:
            att_data = getattr(att, 'data', None)
            if att_data:
                filename = getattr(att, 'longFilename', None) or getattr(att, 'shortFilename', None) or 'attachment.dat'
                mime_type = getattr(att, 'mimeType', 'application/octet-stream')
                attachments.append({
                    'filename': filename,
                    'data': att_data,
                    'mimeType': mime_type
                })

        if attachments:
            eml_msg.make_mixed()
            if body_html or body_plain:
                alternative = MIMEMultipart('alternative')
                if body_plain: alternative.attach(MIMEText(body_plain, 'plain', 'utf-8'))
                if body_html: alternative.attach(MIMEText(body_html, 'html', 'utf-8'))
                eml_msg.attach(alternative)
            
            for att in attachments:
                mime = att['mimeType']
                maintype, subtype = mime.split('/', 1) if '/' in mime else ('application', 'octet-stream')
                part = MIMEBase(maintype, subtype)
                part.set_payload(att['data'])
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment', filename=att['filename'])
                eml_msg.attach(part)
        else:
            if body_html and body_plain:
                eml_msg.make_alternative()
                eml_msg.attach(MIMEText(body_plain, 'plain', 'utf-8'))
                eml_msg.attach(MIMEText(body_html, 'html', 'utf-8'))
            elif body_html:
                eml_msg.set_content(body_html, subtype='html', charset='utf-8')
            else:
                eml_msg.set_content(body_plain, charset='utf-8')

        # 核心加速配置: policy.default
        with open(out_path, 'wb') as f:
            f.write(eml_msg.as_bytes(policy=policy.default))
        
        msg.close() 
        return out_path


# ========================== 主程序 UI ==========================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MSG TO EML 版权所有caoyz001")
        self.setMinimumSize(950, 750)
        self.setAcceptDrops(True)
        self.worker = None
        self.setup_ui()
        self.setup_style()
        self.check_env()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        files = [url.toLocalFile() for url in urls if url.isLocalFile()]
        if files:
            self.add_files(files)
        event.acceptProposedAction()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(25, 25, 25, 25)

        # 头部区域
        header_layout = QHBoxLayout()
        title_label = QLabel("🔷 MSG TO EML 版权所有caoyz001")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #0052CC;")
        
        self.env_status_label = QLabel()
        self.env_status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.env_status_label)
        main_layout.addLayout(header_layout)

        # 显著的拖拽/添加提示横幅
        drop_banner = QLabel("⬇️ 支持拖拽：请将 MSG 邮件文件直接拖拽到本窗口中，或点击下方按钮选择路径 ⬇️")
        drop_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        drop_banner.setStyleSheet("""
            background-color: #E6F7FF; 
            border: 2px dashed #1890FF; 
            color: #1890FF; 
            padding: 15px; 
            font-weight: bold; 
            border-radius: 8px; 
            font-size: 15px;
        """)
        main_layout.addWidget(drop_banner)

        # 控制面板区域
        control_group = QGroupBox("📁 路径设置")
        control_layout = QHBoxLayout()
        
        output_label = QLabel("输出保存目录:")
        output_label.setStyleSheet("font-weight: bold; color: #333;")
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setReadOnly(True)
        default_dir = str(Path.home() / "Desktop")
        self.output_dir_edit.setText(default_dir if os.path.exists(default_dir) else os.getcwd())
        
        self.browse_btn = QPushButton("📂 更改目录")
        self.browse_btn.setProperty("class", "secondary-btn")
        self.browse_btn.clicked.connect(self.select_output_dir)

        control_layout.addWidget(output_label)
        control_layout.addWidget(self.output_dir_edit)
        control_layout.addWidget(self.browse_btn)
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)

        # 表格列表区域 (新增转换耗时列)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["选择", "文件名", "原文件路径", "转换状态", "转换耗时"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 50)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 90) # 耗时列宽度
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.table)

        # 表格控制按钮
        table_btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("➕ 添加 MSG 文件")
        self.add_btn.setProperty("class", "outline-btn")
        self.add_btn.clicked.connect(self.add_files_dialog)
        
        self.select_all_btn = QPushButton("☑️ 全选")
        self.select_all_btn.setProperty("class", "outline-btn")
        self.select_all_btn.clicked.connect(lambda: self.set_table_checks(True))
        
        self.deselect_all_btn = QPushButton("☐ 取消全选")
        self.deselect_all_btn.setProperty("class", "outline-btn")
        self.deselect_all_btn.clicked.connect(lambda: self.set_table_checks(False))
        
        self.remove_selected_btn = QPushButton("➖ 移除勾选项")
        self.remove_selected_btn.setProperty("class", "outline-btn")
        self.remove_selected_btn.clicked.connect(self.remove_checked_rows)
        
        self.clear_btn = QPushButton("🗑️ 清空列表")
        self.clear_btn.setProperty("class", "danger-outline-btn")
        self.clear_btn.clicked.connect(lambda: self.table.setRowCount(0))

        table_btn_layout.addWidget(self.add_btn)
        table_btn_layout.addWidget(self.select_all_btn)
        table_btn_layout.addWidget(self.deselect_all_btn)
        table_btn_layout.addWidget(self.remove_selected_btn)
        table_btn_layout.addStretch()
        table_btn_layout.addWidget(self.clear_btn)
        main_layout.addLayout(table_btn_layout)

        # 进度与日志区域
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        main_layout.addWidget(self.progress_bar)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(120)
        main_layout.addWidget(self.log_text)

        # 底部大按钮
        bottom_layout = QHBoxLayout()
        self.convert_btn = QPushButton("🚀 开始转换")  # 名字已精简
        self.convert_btn.setMinimumHeight(45)
        self.convert_btn.setProperty("class", "primary-btn")
        self.convert_btn.clicked.connect(self.start_conversion)
        
        self.cancel_btn = QPushButton("⏹️ 终止操作")
        self.cancel_btn.setMinimumHeight(45)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setProperty("class", "danger-btn")
        self.cancel_btn.clicked.connect(self.cancel_conversion)
        
        self.open_dir_btn = QPushButton("📂 查看输出结果")
        self.open_dir_btn.setMinimumHeight(45)
        self.open_dir_btn.setProperty("class", "secondary-btn")
        self.open_dir_btn.clicked.connect(self.open_output_folder)

        bottom_layout.addWidget(self.convert_btn, stretch=3)
        bottom_layout.addWidget(self.cancel_btn, stretch=1)
        bottom_layout.addWidget(self.open_dir_btn, stretch=1)
        main_layout.addLayout(bottom_layout)

    def setup_style(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #F0F4F8; }
            QWidget { color: #333333; font-family: "Microsoft YaHei", "Segoe UI"; font-size: 13px; }
            
            QGroupBox { border: 1px solid #DDE4EA; background-color: #FFFFFF; border-radius: 6px; margin-top: 15px; padding-top: 15px; }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 5px; color: #0052CC; font-weight: bold; }
            
            QLineEdit { background-color: #F8FAFC; border: 1px solid #DDE4EA; border-radius: 4px; padding: 6px; color: #555; }
            
            QTableWidget { background-color: #FFFFFF; alternate-background-color: #F8FAFC; border: 1px solid #DDE4EA; border-radius: 4px; gridline-color: #E2E8F0; }
            QHeaderView::section { background-color: #F1F5F9; color: #334155; padding: 5px; border: 1px solid #E2E8F0; font-weight: bold; }
            
            QProgressBar { border: 1px solid #DDE4EA; border-radius: 5px; text-align: center; background-color: #E2E8F0; font-weight: bold; color: #333;}
            QProgressBar::chunk { background-color: #1890FF; border-radius: 4px; }
            
            QTextEdit { background-color: #FFFFFF; border: 1px solid #DDE4EA; border-radius: 4px; padding: 8px; font-family: "Consolas", monospace; font-size: 12px;}
            
            QPushButton { padding: 6px 15px; border-radius: 5px; font-weight: bold; border: none; }
            
            QPushButton[class="primary-btn"] { background-color: #1890FF; color: white; font-size: 15px; }
            QPushButton[class="primary-btn"]:hover { background-color: #40A9FF; }
            QPushButton[class="primary-btn"]:disabled { background-color: #A0CFFF; color: #E6F7FF; }
            
            QPushButton[class="secondary-btn"] { background-color: #64748B; color: white; }
            QPushButton[class="secondary-btn"]:hover { background-color: #94A3B8; }
            
            QPushButton[class="danger-btn"] { background-color: #F5222D; color: white; }
            QPushButton[class="danger-btn"]:hover { background-color: #FF4D4F; }
            QPushButton[class="danger-btn"]:disabled { background-color: #FFA39E; }
            
            QPushButton[class="outline-btn"] { background-color: #FFFFFF; border: 1px solid #1890FF; color: #1890FF; }
            QPushButton[class="outline-btn"]:hover { background-color: #E6F7FF; }
            
            QPushButton[class="danger-outline-btn"] { background-color: #FFFFFF; border: 1px solid #F5222D; color: #F5222D; }
            QPushButton[class="danger-outline-btn"]:hover { background-color: #FFF1F0; }
            
            QMessageBox { background-color: #FFFFFF; }
            QMessageBox QLabel { color: #333333; font-size: 14px; }
            QMessageBox QPushButton { background-color: #1890FF; color: white; padding: 5px 15px; min-width: 60px; border-radius: 3px; }
            QMessageBox QPushButton:hover { background-color: #40A9FF; }
        """)

    def check_env(self):
        if EXTRACT_MSG_OK:
            self.env_status_label.setText("<span style='color:#00A854; font-weight:bold;'>✅ 核心解析引擎就绪</span>")
            self.append_log("系统初始化完成。请拖拽或添加 .msg 文件以进行极速转换。", "#0052CC")
        else:
            self.env_status_label.setText("<span style='color:#F5222D; font-weight:bold;'>❌ 解析引擎缺失</span>")
            self.append_log("严重警告: 未检测到 extract-msg 库！无法读取 MSG 文件。", "#F5222D")
            self.convert_btn.setEnabled(False)

    def add_files(self, files: List[str]):
        existing_paths = {self.table.item(i, 2).text() for i in range(self.table.rowCount())}
        added = 0

        for file in files:
            if file.lower().endswith(".msg") and file not in existing_paths:
                row = self.table.rowCount()
                self.table.insertRow(row)
                
                chk_item = QTableWidgetItem()
                chk_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                chk_item.setCheckState(Qt.CheckState.Checked)
                self.table.setItem(row, 0, chk_item)
                
                self.table.setItem(row, 1, QTableWidgetItem(os.path.basename(file)))
                self.table.setItem(row, 2, QTableWidgetItem(file))
                
                status_item = QTableWidgetItem("待处理")
                status_item.setForeground(QBrush(QColor("#888888")))
                self.table.setItem(row, 3, status_item)

                # 初始化耗时列
                time_item = QTableWidgetItem("-")
                time_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                time_item.setForeground(QBrush(QColor("#888888")))
                self.table.setItem(row, 4, time_item)
                
                added += 1

        if added > 0:
            self.append_log(f"成功载入 {added} 个 MSG 文件准备转换。", "#333333")
        elif files:
            QMessageBox.warning(self, "文件无效", "拖入的文件类型不符（必须为.msg后缀），或者该文件已存在列表中。")

    def add_files_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择要转换的 MSG 文件", "", "Outlook 邮件文件 (*.msg)")
        if files:
            self.add_files(files)

    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择 EML 输出目录")
        if dir_path:
            self.output_dir_edit.setText(dir_path)

    def open_output_folder(self):
        out_dir = self.output_dir_edit.text()
        if os.path.exists(out_dir):
            os.startfile(out_dir) if sys.platform == "win32" else os.system(f'open "{out_dir}"')
        else:
            QMessageBox.warning(self, "提示", "输出目录目前不存在！")

    def set_table_checks(self, checked: bool):
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(state)

    def remove_checked_rows(self):
        for row in range(self.table.rowCount() - 1, -1, -1):
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                self.table.removeRow(row)

    def append_log(self, text, color="#333333"):
        time_str = datetime.now().strftime("%H:%M:%S")
        html_msg = f"<span style='color:#999;'>[{time_str}]</span> <span style='color:{color};'>{text}</span>"
        self.log_text.append(html_msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())

    # 新增了 duration 参数以更新第五列
    def update_row_status(self, row: int, status: str, color_hex: str, duration: str = "-"):
        status_item = self.table.item(row, 3)
        if status_item:
            status_item.setText(status)
            status_item.setForeground(QBrush(QColor(color_hex)))
        
        time_item = self.table.item(row, 4)
        if time_item:
            time_item.setText(duration)
            if duration != "-":
                time_item.setForeground(QBrush(QColor("#333333")))

    def start_conversion(self):
        tasks = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                tasks.append({
                    'row': row,
                    'path': self.table.item(row, 2).text()
                })

        if not tasks:
            QMessageBox.information(self, "提示", "请在列表中打勾选中至少一个需要转换的文件。")
            return

        out_dir = self.output_dir_edit.text()
        if not out_dir or not os.path.exists(out_dir):
            QMessageBox.warning(self, "目录错误", "输出目录无效，请重新选择！")
            return

        self.convert_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.add_btn.setEnabled(False)
        self.clear_btn.setEnabled(False)
        self.remove_selected_btn.setEnabled(False)
        self.table.setEnabled(False)
        
        self.progress_bar.setValue(0)
        self.log_text.clear()
        self.append_log(f"🚀 启动转换引擎，共提交 {len(tasks)} 个任务...", "#0052CC")

        self.worker = ConvertWorker(tasks, out_dir)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.append_log)
        self.worker.row_status.connect(self.update_row_status)
        self.worker.finished.connect(self.on_conversion_finished)
        self.worker.start()

    def cancel_conversion(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.append_log("⏳ 正在安全中止正在进行的转换任务...", "#FF9800")
            self.cancel_btn.setEnabled(False)

    def on_conversion_finished(self, success: bool, message: str):
        self.convert_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.add_btn.setEnabled(True)
        self.clear_btn.setEnabled(True)
        self.remove_selected_btn.setEnabled(True)
        self.table.setEnabled(True)
        
        if success:
            self.append_log(message, "#00A854")
            QMessageBox.information(self, "✅ 转换完成", message)
        else:
            self.append_log(message, "#F5222D")
            QMessageBox.warning(self, "⚠️ 转换结束 (含错误)", message)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(2000)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())