"""Regresiones del login nativo con servicios aislados de MySQL."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import time
import unittest
from unittest.mock import patch, MagicMock
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QLabel, QDialog
from PySide6.QtTest import QTest
from ui.login_window import LoginWindow
from ui.register_window import RegisterWindow
from ui.widgets.premium import load_fonts, GlassCard
from ui.widgets.login_glass import LoginGlassCard
from ui.appearance import appearance
from crece.interfaz import ESTILO_APLICACION


class Service:
    def __init__(self, setup=False, result=None):
        self.initial=setup
        self.result=result
        self.calls=[]

    def setup_required(self): return self.initial

    def login(self, username, password):
        self.calls.append(('login',username))
        time.sleep(.08)
        return self.result

    def setup(self, username, password):
        self.calls.append(('setup',username))
        return dict(id=1,rol='ADMINISTRADOR',nombre_usuario=username)


class NativeLoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        load_fonts()
        cls.app.setFont(QFont('Open Sans',10))
        cls.app.setStyleSheet(ESTILO_APLICACION)

    def setUp(self):
        self.windows=[]
        self.original_theme=appearance().theme
        self.preference=patch.object(appearance(),'settings',MagicMock())
        self.preference.start()

    def tearDown(self):
        for window in reversed(self.windows):
            self.wait_for(lambda:not window.busy)
            window.close()
            window.deleteLater()
        QTest.qWait(10)
        appearance().theme=self.original_theme
        appearance().changed.emit(self.original_theme)
        self.preference.stop()

    def wait_for(self, condition):
        for _ in range(200):
            if condition(): return
            QTest.qWait(10)
        self.fail('La tarea nativa no terminó.')

    def open(self,service):
        window=LoginWindow(service=service)
        self.windows.append(window)
        window.resize(1440,1000)
        window.show()
        self.wait_for(lambda:window.setup_mode is not None and not window.busy)
        QTest.qWait(120)
        return window

    def test_panel_only_keeps_surroundings_theme_and_window_controls(self):
        window=self.open(Service())
        self.assertIsInstance(window.card,LoginGlassCard)
        self.assertTrue(window.left.isVisible())
        self.assertTrue(window.right.isVisible())
        self.assertIn('Confianza',[label.text() for label in window.left.findChildren(QLabel)])
        self.assertTrue(window.theme_control.isVisible())
        self.assertIs(window.theme_control.parent(),window.scene)
        self.assertFalse(window.heading.isVisible())
        self.assertFalse(window.note.isVisible())
        self.assertEqual([field for field in window.card.findChildren(QLineEdit) if field.isVisible()],[window.username,window.password])
        self.assertEqual([button.text() for button in window.card.findChildren(QPushButton) if button.isVisible()],['Iniciar sesión'])
        self.assertTrue(window.windowFlags() & Qt.WindowMinimizeButtonHint)
        self.assertTrue(window.windowFlags() & Qt.WindowMaximizeButtonHint)
        for width,height in [(390,744),(1024,768),(1440,1000)]:
            window.resize(width,height)
            QTest.qWait(200)
            self.assertEqual(window.scroll.horizontalScrollBar().maximum(),0)
            self.assertLessEqual(window.card.width(),460)
        other=RegisterWindow(service=Service())
        self.windows.append(other)
        self.assertIs(type(other.card),GlassCard)
        self.assertFalse(other.minimal_login)

    def test_unverified_role_is_rejected_and_enter_clears_password(self):
        service=Service(result=dict(id=9,rol='CLIENTE'))
        window=self.open(service)
        window.username.setText('admin')
        window.password.setText('test-password-not-real')
        window.password.toggle_action.setChecked(True)
        QTest.keyClick(window.password,Qt.Key_Return)
        self.assertTrue(window.busy)
        self.assertFalse(window.submit.isEnabled())
        self.wait_for(lambda:not window.busy)
        self.assertIsNone(window.usuario)
        self.assertNotEqual(window.result(),QDialog.Accepted)
        self.assertEqual(window.password.text(),'')
        self.assertEqual(window.password.echoMode(),QLineEdit.Password)
        self.assertIn('no confirmó',window.error.text())
        self.assertEqual(service.calls,[('login','admin')])

    def test_initial_administrator_flow_still_requires_confirmation(self):
        service=Service(setup=True)
        window=self.open(service)
        self.assertTrue(window.confirm.isVisible())
        self.assertTrue(window.heading.isVisible())
        window.username.setText('admin')
        window.password.setText('test-password-not-real')
        window.confirm.setText('different')
        window.authenticate()
        self.assertEqual(service.calls,[])
        window.confirm.setText('test-password-not-real')
        window.authenticate()
        self.wait_for(lambda:not window.busy)
        self.assertEqual(service.calls,[('setup','admin')])
        self.assertEqual(window.result(),QDialog.Accepted)
        self.assertEqual(window.usuario['rol'],'ADMINISTRADOR')

    def test_theme_toggle_preserves_inputs_and_uses_existing_photos(self):
        window=self.open(Service())
        window.username.setText('admin')
        window.password.setText('test-password-not-real')
        for theme in ['light','dark']:
            window.theme_control.setCurrentIndex(window.theme_control.findData(theme))
            QTest.qWait(120)
            self.assertEqual(window.scene.theme,theme)
            self.assertFalse(window.scene.original.isNull())
            self.assertEqual(window.username.text(),'admin')
            self.assertEqual(window.password.text(),'test-password-not-real')
            self.assertIsNone(window.scene.graphicsEffect())


if __name__=='__main__': unittest.main()
