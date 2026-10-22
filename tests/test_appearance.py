"""Alternar apariencia conserva estado y usa preferencias ajenas a credenciales."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from contextlib import ExitStack
from tempfile import TemporaryDirectory
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QComboBox, QLineEdit
from PySide6.QtTest import QTest
from crece.interfaz import PanelPrincipal
from ui.appearance import Appearance, appearance
from ui.access_dialog import AccessDialog
from ui.widgets.premium import Field


class AppearanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp_root=Path(__file__).resolve().parents[2]/'tmp'
        self.temp=TemporaryDirectory(prefix='appearance-test-',dir=self.temp_root)
        self.settings=QSettings(self.temp.name+'/appearance.ini',QSettings.IniFormat)
        self.controller=appearance()
        self.original_theme=self.controller.theme
        self.patch=patch.object(self.controller,'settings',self.settings)
        self.patch.start()
        self.mocks=ExitStack()
        for name in ['PaginaInicio.cargar_resumen','PaginaClientes.cargar_clientes','PaginaPrestamos.cargar_prestamos','PaginaCobros.cargar_cobros','PaginaReportes.cargar_reporte','PaginaUsuarios.cargar_usuarios']:
            self.mocks.enter_context(patch('crece.interfaz.'+name))

    def tearDown(self):
        self.controller.theme=self.original_theme
        self.controller.changed.emit(self.original_theme)
        self.patch.stop()
        self.mocks.close()
        assert Path(self.temp.name).resolve().is_relative_to(self.temp_root.resolve())
        self.settings=None
        self.temp.cleanup()

    def test_switching_preserves_page_search_and_simulation(self):
        window=PanelPrincipal()
        window.show()
        window.mostrar_pagina(1)
        window.pagina_clientes.buscar.setText('Cliente por revisar')
        simulator=window.paginas[4]
        simulator.calcular_plan()
        amount=simulator.tabla_cuotas.item(0,2).text()
        picker=window.findChild(QComboBox,'appearancePicker')
        for theme in ['light','dark','light']:
            picker.setCurrentIndex(picker.findData(theme))
            QTest.qWait(100)
            self.assertEqual(window.property('appearance'),theme)
            self.assertEqual(window.centralWidget().theme,theme)
            self.assertFalse(window.centralWidget().original.isNull())
            self.assertEqual(window.contenedor_paginas.currentIndex(),1)
            self.assertEqual(window.pagina_clientes.buscar.text(),'Cliente por revisar')
            self.assertEqual(simulator.tabla_cuotas.item(0,2).text(),amount)
            self.assertIsNone(window.contenedor_paginas.graphicsEffect())
        self.assertEqual(self.settings.allKeys(),['theme'])
        self.assertEqual(self.settings.value('theme'),'light')
        with patch('ui.appearance.QSettings',return_value=self.settings):
            self.assertEqual(Appearance().theme,'light')
        window.close()
        window.deleteLater()
        QTest.qWait(1)

    def test_open_access_windows_update_together_without_resetting_inputs(self):
        first=AccessDialog()
        field=Field('Usuario','Usuario')
        field.setText('usuario sin enviar')
        first.add_field('Usuario',field)
        second=AccessDialog(first)
        for theme in ['light','dark']:
            self.controller.set_theme(theme)
            self.assertEqual(first.scene.theme,theme)
            self.assertEqual(second.scene.theme,theme)
            self.assertEqual(field.text(),'usuario sin enviar')
            self.assertEqual(field.echoMode(),QLineEdit.Normal)
        first.close()
        second.close()
        second.deleteLater()
        first.deleteLater()
        QTest.qWait(1)


if __name__=='__main__':
    unittest.main()
