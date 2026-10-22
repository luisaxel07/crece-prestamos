"""Componentes compartidos del espacio administrativo nativo."""
from pathlib import Path
import unicodedata
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QRectF
from PySide6.QtGui import QColor, QPainter, QFont, QPen, QRegion
from PySide6.QtWidgets import (QFrame, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QStyledItemDelegate, QStyleOptionViewItem, QStyle, QHeaderView,
    QAbstractItemView, QSizePolicy, QApplication)
from ui.widgets.premium import ROOT, ASSETS, symbol, load_fonts


def workspace_styles():
    return (ROOT / 'styles/workspace.qss').read_text(encoding='utf-8').replace('__ASSETS__',ASSETS.as_posix())


def label(text, name='workspaceSubtitle', wrap=False):
    widget = QLabel(text)
    widget.setObjectName(name)
    widget.setTextFormat(Qt.PlainText)
    widget.setWordWrap(wrap)
    widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
    return widget


def button(text, callback, primary=True, icon=None):
    widget = QPushButton(text)
    widget.setObjectName('workspacePrimary' if primary else 'workspaceSecondary')
    widget.setCursor(Qt.PointingHandCursor)
    if icon:
        widget.setIcon(symbol(icon,'#FFFFFF' if primary else '#003366',18))
        widget.setIconSize(QSize(18,18))
        widget.setProperty('appearanceIcon',icon)
        widget.setProperty('appearancePrimary',primary)
    widget.clicked.connect(callback)
    return widget


def surface():
    frame = QFrame()
    frame.setObjectName('workspaceSurface')
    return frame


class Metric(QFrame):
    def __init__(self, title, value='—', description='', icon='growth', compact=False):
        super().__init__()
        self.setObjectName('metricSurface')
        box = QVBoxLayout(self)
        box.setContentsMargins(18,15,18,15)
        box.setSpacing(7)
        top = QHBoxLayout()
        top.addWidget(label(title,'metricLabel'))
        top.addStretch()
        mark = QLabel()
        mark.setPixmap(symbol(icon,'#006633',20).pixmap(20,20))
        mark.setProperty('appearanceSymbol',icon)
        top.addWidget(mark)
        box.addLayout(top)
        self.value = label(value,'metricValue')
        if compact:
            self.value.setStyleSheet('font-size: 21px;')
        box.addWidget(self.value)
        self.description = label(description,'metricDescription')
        box.addWidget(self.description)
        self.setFixedHeight(110 if compact else 128)

    def actualizar(self, value, description=None):
        self.value.setText(value)
        if description is not None:
            self.description.setText(description)


class FinancialDelegate(QStyledItemDelegate):
    def paint(self,painter,option,index):
        header = str(index.model().headerData(index.column(),Qt.Horizontal) or '').upper()
        text = str(index.data() or '')
        if header not in ('ESTADO','ACCIÓN','ROL'):
            super().paint(painter,option,index)
            return
        painter.save()
        style = QStyleOptionViewItem(option)
        self.initStyleOption(style,index)
        style.text = ''
        (option.widget.style() if option.widget else QApplication.style()).drawControl(QStyle.CE_ItemViewItem,style,painter,option.widget)
        positive = text.casefold() in ('activo','activa','pagada','pagado','administrador')
        neutral = text.casefold() in ('inactivo','inactiva','cliente','empleado','finalizado')
        dark = bool(option.widget and option.widget.window().property('appearance') == 'dark')
        color = QColor(('#B0E3CA' if positive else '#FFFFFF') if dark else ('#006633' if positive else '#666666' if neutral else '#003366'))
        fill = QColor(color)
        fill.setAlpha(35 if dark else 18)
        width = min(option.rect.width()-20,option.fontMetrics.horizontalAdvance(text)+26)
        pill = QRectF(option.rect.center().x()-width/2,option.rect.center().y()-13,width,26)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill)
        painter.drawRoundedRect(pill,6,6)
        painter.setPen(color)
        font = QFont(option.font)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.drawText(pill,Qt.AlignCenter,text)
        painter.restore()


class DataTable(QTableWidget):
    contentChanged = Signal()

    def __init__(self, columns):
        super().__init__(0,len(columns))
        self.setObjectName('workspaceTable')
        self.setHorizontalHeaderLabels(columns)
        self.verticalHeader().hide()
        self.verticalHeader().setDefaultSectionSize(52)
        self.horizontalHeader().setFixedHeight(43)
        self.horizontalHeader().setMinimumSectionSize(75)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setTextElideMode(Qt.ElideRight)
        self.setWordWrap(False)
        self.setItemDelegate(FinancialDelegate(self))
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.contentChanged)
        self.itemChanged.connect(lambda *_:self.refresh_timer.start(0))
        self.empty = label('','workspaceEmpty',True)
        self.empty.setParent(self.viewport())
        self.empty.setAlignment(Qt.AlignCenter)
        self.empty.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.empty.hide()

    def setRowCount(self,count):
        super().setRowCount(count)
        if hasattr(self,'refresh_timer'):
            self.refresh_timer.start(0)

    def setItem(self,row,column,item):
        item.setToolTip(item.text())
        if item.text().strip().startswith(('C$','$')):
            item.setTextAlignment(Qt.AlignRight|Qt.AlignVCenter)
        super().setItem(row,column,item)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.empty.setGeometry(20,max(35,self.viewport().height()//2-75),max(0,self.viewport().width()-40),150)

    def show_empty(self,text):
        self.empty.setText(text)
        self.empty.setVisible(bool(text))
        self.empty.raise_()


def normalized(text):
    return ''.join(char for char in unicodedata.normalize('NFD',str(text).casefold()) if unicodedata.category(char)!='Mn')
