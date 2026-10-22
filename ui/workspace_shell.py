from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPixmap, QRegion
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QButtonGroup, QScrollArea, QWidget
from ui.workspace import label
from ui.appearance import theme_picker
from ui.widgets.premium import ASSETS, symbol


def sidebar(window):
    frame = QFrame()
    frame.setObjectName('workspaceSidebar')
    frame.setFixedWidth(220)
    box = QVBoxLayout(frame)
    box.setContentsMargins(18,26,18,20)
    box.setSpacing(8)
    brand = QLabel()
    brand.setObjectName('appearanceBrand')
    source = QPixmap(str(ASSETS / 'logo-oscuro.png'))
    if not source.isNull():
        # Remove transparent file padding at paint time; preserve original pixels.
        source = source.copy(QRegion(source.mask()).boundingRect())
        brand.setPixmap(source.scaledToWidth(164,Qt.SmoothTransformation))
    brand.setAccessibleName('CRECE+ PRÉSTAMOS')
    brand.setContentsMargins(8,14,8,18)
    box.addWidget(brand)
    box.addSpacing(22)
    box.addWidget(label('ESPACIO DE TRABAJO','sidebarCaption'))
    box.addSpacing(8)
    window.grupo_navegacion = QButtonGroup(window)
    window.grupo_navegacion.setExclusive(True)
    options = [('grid','Resumen',0),('users','Clientes',1),('document','Préstamos',2),
               ('coins','Cobros',3),('calculator','Simulador',4),('chart','Reportes',5)]
    if window.usuario['rol']=='ADMINISTRADOR':
        options.append(('shield','Usuarios',6))
        options.append(('users','Empleados',7))
    navigation=QWidget()
    navigation.setObjectName('workspaceNavigation')
    links=QVBoxLayout(navigation)
    links.setContentsMargins(0,0,0,0)
    links.setSpacing(8)
    for name,title,index in options:
        nav = QPushButton('  '+title)
        nav.setObjectName('workspaceNav')
        nav.setIcon(symbol(name,'#FFFFFF',19))
        nav.setProperty('appearanceIcon',name)
        nav.setIconSize(QSize(19,19))
        nav.setCheckable(True)
        nav.setCursor(Qt.PointingHandCursor)
        nav.setAccessibleName(title)
        nav.clicked.connect(lambda checked=False,destination=index:window.mostrar_pagina(destination))
        window.grupo_navegacion.addButton(nav,index)
        links.addWidget(nav)
    links.addStretch()
    scroll=QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setWidget(navigation)
    window.navigation_scroll=scroll
    scroll.setStyleSheet('QScrollArea, QWidget#workspaceNavigation { background: transparent; border: none; }')
    box.addWidget(scroll,1)
    note = label('Crecemos contigo.','sidebarCaption')
    note.setStyleSheet('font-size: 11px;')
    box.addWidget(note)
    box.addSpacing(15)
    logout = QPushButton('  Cerrar sesión')
    logout.setObjectName('workspaceNav')
    logout.setProperty('appearanceIcon','logout')
    logout.setCursor(Qt.PointingHandCursor)
    logout.setIcon(symbol('logout','#FFFFFF',18))
    logout.clicked.connect(window.cerrar_sesion)
    box.addWidget(logout)
    return frame


def header(window):
    frame = QFrame()
    frame.setObjectName('workspaceHeader')
    frame.setFixedHeight(64)
    box = QHBoxLayout(frame)
    box.setContentsMargins(28,0,28,0)
    window.breadcrumb = label('Espacio de trabajo  /  Resumen','workspaceBreadcrumb')
    box.addWidget(window.breadcrumb)
    box.addStretch()
    box.addWidget(theme_picker(window))
    box.addSpacing(12)
    identity = QVBoxLayout()
    identity.setSpacing(2)
    identity.addWidget(label(window.usuario['nombre_usuario'],'workspaceIdentity'))
    identity.addWidget(label(window.usuario['rol'].capitalize(),'workspaceRole'))
    box.addLayout(identity)
    box.addSpacing(8)
    avatar = label(window.usuario['nombre_usuario'][:1].upper(),'workspaceAvatar')
    avatar.setAlignment(Qt.AlignCenter)
    avatar.setFixedSize(36,36)
    avatar.setStyleSheet('border: 1px solid rgba(0,166,81,80); border-radius: 18px; font-size: 14px; font-weight: 700;')
    box.addWidget(avatar)
    return frame
