"""La recuperación nativa valida entradas, llama al servicio y vuelve al login."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
from PySide6.QtWidgets import QApplication,QDialog,QLineEdit
from PySide6.QtTest import QTest
from ui.recovery_dialog import RecoveryDialog
from ui.register_window import RegisterWindow

class Service:
    def __init__(self):self.calls=[]
    def recover(self,*args):
        self.calls.append(args)
        return dict(accepted=True,message='Contraseña actualizada. Vuelve a iniciar sesión.')

class NativeRecoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=QApplication.instance() or QApplication([])
    def test_invalid_fields_do_not_call_backend(self):
        service=Service();window=RecoveryDialog(service=service)
        try:
            window.recover();self.assertEqual(service.calls,[])
            window.username.setText('asesor_prueba');window.code.setText('A'*43);window.password.setText('ClavePrueba2026');window.confirm.setText('diferente')
            window.recover();self.assertEqual(service.calls,[]);self.assertIn('no coinciden',window.error.text())
        finally:window.deleteLater();QTest.qWait(10)
    def test_success_does_not_auto_login_and_clears_secrets(self):
        service=Service();window=RecoveryDialog(service=service)
        try:
            window.username.setText('asesor_prueba');window.code.setText('A'*43);window.password.setText('ClavePrueba2026');window.confirm.setText('ClavePrueba2026')
            with patch('ui.recovery_dialog.QMessageBox.information'):
                window.recover()
                for _ in range(300):
                    if not window.busy:break
                    QTest.qWait(10)
            self.assertFalse(window.busy);self.assertEqual(window.result(),QDialog.Accepted)
            self.assertEqual(service.calls,[('asesor_prueba','A'*43,'ClavePrueba2026','ClavePrueba2026')])
            for field in (window.code,window.password,window.confirm):self.assertEqual(field.text(),'')
            self.assertFalse(hasattr(window,'usuario'))
        finally:window.deleteLater();QTest.qWait(10)
    def test_registration_is_informational_without_fake_inputs(self):
        window=RegisterWindow(service=Service())
        try:self.assertEqual(window.findChildren(QLineEdit),[]);self.assertEqual(window.submit.text(),'Volver a iniciar sesión')
        finally:window.deleteLater();QTest.qWait(10)

if __name__=='__main__':unittest.main()
