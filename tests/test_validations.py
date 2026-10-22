"""Datos literales, calendario de cédula, ORM y captura idéntica en Qt/web."""
import unittest
from datetime import date
from unittest.mock import patch
from decimal import Decimal
from pathlib import Path
from sqlalchemy import select,func
from mysql_support import preparar_mysql
from crece.nucleo.validaciones import normalizar_nombre,normalizar_cedula,normalizar_persona,normalizar_correo,ErrorValidacion
from crece.infraestructura.base_datos import configurar_motor,transaccion
from crece.infraestructura.modelos import Base,Usuario,Cliente,Empleado
from crece.servicios.permisos import establecer_actor
from crece.servicios import gestion as s,cuentas_orm as cuentas
from portal_web.app_web import aplicacion

class ValidationRulesTests(unittest.TestCase):
    def test_names_allow_accents_unicode_and_spaces_but_no_digits_or_punctuation(self):
        self.assertEqual(normalizar_nombre('  María   José  '),'María José')
        self.assertEqual(normalizar_nombre('Mun\u0303oz'),'Muñoz')
        for value in ['Ana3','José-Ángel',"D'Ávila",'Ana@','123','👤','Ana\nPérez','Ana\tPérez','', ' ']:
            with self.subTest(value=value),self.assertRaises(ErrorValidacion):normalizar_nombre(value)
    def test_id_uppercase_auto_format_and_calendar(self):
        self.assertEqual(normalizar_cedula('0011508900001a'),'001-150890-0001A')
        self.assertEqual(normalizar_cedula('001-150890-0001z'),'001-150890-0001Z')
        self.assertEqual(normalizar_cedula('001-290200-0000A'),'001-290200-0000A')
        for value in ['001-310290-0001A','001-290201-0001A','001-000000-0001A','001-321290-0001A','001-151390-0001A','001-150890-0001AB','001-150890-0001Ñ','001-150890-00011','٠٠١-150890-0001A','001--150890-0001A','001-150890-001A']:
            with self.subTest(value=value),self.assertRaises(ErrorValidacion):normalizar_cedula(value)
    def test_phone_and_email_are_literal(self):
        self.assertEqual(normalizar_persona('0011508900001a','Ana','Muñoz','88888888','ANA@EXAMPLE.TEST')['correo'],'ana@example.test')
        for phone in ['telefono','8888ABCD','8888-8888','8888 8888','123','+50588888888']:
            with self.subTest(phone=phone),self.assertRaises(ErrorValidacion):normalizar_persona('0011508900001a','Ana','Muñoz',phone)
        for email in ['no-es-correo','a@@b.com','a..b@example.test','a@-ejemplo.com','a @ejemplo.com','a.@example.test']:
            with self.subTest(email=email),self.assertRaises(ErrorValidacion):normalizar_correo(email)

    def test_numeric_text_rejects_letters_symbols_exponents_and_decimal_months(self):
        from crece.nucleo.validaciones import validar_numero_texto,validar_plazo
        self.assertEqual(validar_numero_texto('10000.50','monto'),'10000.50')
        self.assertEqual(validar_numero_texto('2.1234','tasa'),'2.1234')
        self.assertEqual(validar_plazo('12'),12)
        for key,value in [('monto','1e3'),('monto','C$ 1000'),('monto','1.005'),('tasa','2%'),('tasa','NaN'),('meses','1.5'),('meses','+12')]:
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):validar_numero_texto(value,key)
        for value in ['0','601']:
            with self.assertRaises(ValueError):validar_plazo(value)

class SharedValidationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine=preparar_mysql()
        with transaccion() as db:
            u=Usuario(nombre_usuario='admin_test',hash_contrasena='sin_acceso',rol='ADMINISTRADOR');db.add(u);db.flush();self.admin=u.id
        establecer_actor(self.admin)
        aplicacion.config['TESTING']=True
        self.browser=aplicacion.test_client()
        with self.browser.session_transaction() as sess:sess.update(version_sesion=1,usuario_id=self.admin,rol='ADMINISTRADOR',nombre_usuario='admin_test',token_csrf='validar')
    def tearDown(self):establecer_actor(None)
    def test_client_create_update_normalize_and_invalid_data_never_persist(self):
        id=s.registrar_cliente('0011508900001a',' María  José ','Pérez López','88888888')
        self.assertEqual(s.obtener_cliente(id)['cedula'],'001-150890-0001A')
        for changed in [dict(nombres='Ana2'),dict(apellidos='Pérez7'),dict(cedula='001-310290-0001A'),dict(telefono='telefono')]:
            data=dict(cedula='001-150890-0001a',nombres='Ana',apellidos='Pérez',telefono='88888888');data.update(changed)
            with self.assertRaises(ValueError):s.actualizar_cliente(id,**data)
        self.assertEqual(s.obtener_cliente(id)['nombres'],'María José')
        self.assertEqual(s.obtener_cliente(id)['cedula'],'001-150890-0001A')
    def test_employee_uses_same_rules_and_email_access_has_no_fake_person_data(self):
        id=s.guardar_empleado('001-180894-0002b','Luis','Muñoz','88888888','Luis@example.test','Asesor de crédito','asesor_test','ClaveSegura-2026')
        e=s.listar_empleados()[0];self.assertEqual(e['id'],id);self.assertEqual(e['cedula'],'001-180894-0002B');self.assertEqual(e['correo'],'luis@example.test')
        with self.assertRaises(ValueError):s.guardar_empleado('001-180894-0002b','Luis3','Muñoz','88888888','','Asesor','asesor_test','',empleado_id=id)
        c=s.registrar_cliente('001-190895-0003C','Ana','López','88888888')
        cuentas.crear_cuenta_cliente(c,'ana@example.test','ClaveSegura-2026')
        cuentas.actualizar_correo_cliente_portal(c,'nuevo@example.test')
        self.assertIsNotNone(cuentas.iniciar_sesion_web('nuevo@example.test','ClaveSegura-2026'))
    def test_web_rejects_tampered_data_and_marks_the_field(self):
        valid=dict(token_csrf='validar',cedula='001-150890-0001a',nombres='Ana',apellidos='Muñoz',telefono='88888888',correo='',direccion='')
        for field,value in [('nombres','Ana9'),('apellidos','López!'),('cedula','001-310299-0001A'),('telefono','no es teléfono')]:
            with self.subTest(field=field):
                r=self.browser.post('/gestion/clientes/nuevo',data={**valid,field:value})
                self.assertEqual(r.status_code,400)
                self.assertIn(f'id="campo-{field}" name="{field}" aria-describedby="campo-{field}-ayuda campo-{field}-error" aria-invalid="true"',r.get_data(as_text=True))
        with transaccion() as db:self.assertEqual(db.scalar(select(func.count()).select_from(Cliente)),0)
        r=self.browser.post('/gestion/clientes/nuevo',data=valid);self.assertEqual(r.status_code,302)
        with transaccion() as db:self.assertEqual(db.scalar(select(Cliente.cedula)),'001-150890-0001A')
    def test_web_fields_show_real_examples_and_help_for_clients_and_employees(self):
        for path in ['/gestion/clientes/nuevo','/gestion/empleados/nuevo']:
            r=self.browser.get(path);html=r.get_data(as_text=True)
            self.assertEqual(r.status_code,200);self.assertIn('001-150890-0001A',html);self.assertIn('María José',html);self.assertNotIn('001-000000-0000A',html)

class QtCaptureValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app=QApplication.instance() or QApplication([])
    def test_name_keyboard_and_paste_cannot_insert_numbers(self):
        from PySide6.QtWidgets import QLineEdit
        from PySide6.QtTest import QTest
        from ui.validacion_campos import configurar_campo
        f=QLineEdit();configurar_campo(f,'nombres');f.show();f.setFocus()
        QTest.keyClicks(f,'Ana123');self.assertEqual(f.text(),'Ana')
        self.app.clipboard().setText('Pedro5');f.selectAll();f.paste();self.assertEqual(f.text(),'Ana')
        self.app.clipboard().setText('María José');f.selectAll();f.paste();self.assertEqual(f.text(),'María José');f.close()
    def test_id_auto_hyphens_uppercase_delete_and_invalid_date(self):
        from PySide6.QtWidgets import QLineEdit
        from PySide6.QtTest import QTest
        from PySide6.QtCore import Qt
        from ui.validacion_campos import configurar_campo
        f=QLineEdit();configurar_campo(f,'cedula');f.show();f.setFocus()
        QTest.keyClicks(f,'0011508900001a');self.assertEqual(f.text(),'001-150890-0001A');self.assertTrue(f.hasAcceptableInput())
        f.clear();QTest.keyClicks(f,'001');self.assertEqual(f.text(),'001-')
        QTest.keyClick(f,Qt.Key_Backspace);self.assertEqual(f.text(),'00')
        f.clear();QTest.keyClicks(f,'0013102900001b');self.assertFalse(f.hasAcceptableInput());f.close()
    def test_employee_and_client_dialogs_use_same_capture_helpers(self):
        from PySide6.QtWidgets import QDialog,QLineEdit
        from PySide6.QtCore import QTimer
        from crece.interfaz import PaginaClientes
        from ui.employees import EmployeesPage
        snapshots=[]
        def inspect():
            dialog=self.app.activeModalWidget();snapshots.append({k:dialog.findChild(QLineEdit,'dato_'+k).placeholderText() for k in ['cedula','nombres','apellidos','telefono']});dialog.reject()
        for page in [PaginaClientes(),EmployeesPage()]:
            QTimer.singleShot(30,inspect)
            if isinstance(page,EmployeesPage):page.editar()
            else:page.abrir_formulario_cliente()
            page.close()
        self.assertEqual(snapshots[0],snapshots[1])

if __name__=='__main__':unittest.main()
