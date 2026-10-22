"""Regresiones visuales de Qt sin conexiones ni cambios a la base de datos."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import unittest
from contextlib import ExitStack
from unittest.mock import patch
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QFont
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton, QLineEdit, QFrame
from crece.interfaz import PanelPrincipal, AnimadorInterfaz, ESTILO_APLICACION
from ui.access_dialog import AccessDialog
from ui.widgets.premium import load_fonts


class DesktopRenderingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        load_fonts()
        cls.app.setStyleSheet(ESTILO_APLICACION)
        cls.app.setFont(QFont('Open Sans', 10))
        cls.animator = AnimadorInterfaz()
        cls.app.installEventFilter(cls.animator)

    def setUp(self):
        self.mocks = ExitStack()
        for name in ['PaginaInicio.cargar_resumen', 'PaginaClientes.cargar_clientes',
                     'PaginaPrestamos.cargar_prestamos', 'PaginaCobros.cargar_cobros',
                     'PaginaReportes.cargar_reporte', 'PaginaUsuarios.cargar_usuarios']:
            self.mocks.enter_context(patch('crece.interfaz.' + name))
        self.window = PanelPrincipal({'id': 1, 'nombre_usuario': 'Prueba', 'rol': 'ADMINISTRADOR'})
        self.window.resize(1400, 900)
        self.window.show()
        QTest.qWait(300)

    def tearDown(self):
        self.window.close()
        self.mocks.close()

    def test_hover_and_focus_do_not_add_nested_effects(self):
        for index in range(7):
            self.window.mostrar_pagina(index)
            QTest.qWait(60)
            page = self.window.contenedor_paginas.currentWidget()
            self.assertIsNone(self.window.contenedor_paginas.graphicsEffect())
            for control in page.findChildren(QPushButton) + page.findChildren(QLineEdit):
                previous = control.graphicsEffect()
                QTest.mouseMove(control, control.rect().center())
                control.setFocus()
                QTest.qWait(10)
                self.assertIs(control.graphicsEffect(), previous)
            self.assertTrue(page.isVisible())

    def test_summary_pixels_remain_after_hover(self):
        card = self.window.pagina_inicio.tarjetas_metricas[0]
        before = card.grab().toImage()
        button = self.window.pagina_inicio.findChild(QPushButton)
        QTest.mouseMove(button, button.rect().center())
        QTest.qWait(350)
        QTest.mouseMove(self.window.pagina_inicio, QPoint(20, 200))
        QTest.qWait(350)
        self.assertEqual(before, card.grab().toImage())

    def test_headers_are_compact_and_tables_take_available_height(self):
        self.assertEqual(self.window.findChild(QFrame, 'workspaceHeader').height(), 64)
        self.window.mostrar_pagina(1)
        QTest.qWait(50)
        self.assertGreaterEqual(self.window.pagina_clientes.tabla.height(), 230)

    def test_login_supports_minimize_and_maximize(self):
        dialog = AccessDialog()
        dialog.show()
        QTest.qWait(100)
        flags = dialog.windowFlags()
        self.assertTrue(flags & Qt.WindowMinimizeButtonHint)
        self.assertTrue(flags & Qt.WindowMaximizeButtonHint)
        dialog.showMaximized()
        QTest.qWait(80)
        self.assertTrue(dialog.isMaximized())
        dialog.showNormal()
        dialog.close()


if __name__ == '__main__':
    unittest.main()
