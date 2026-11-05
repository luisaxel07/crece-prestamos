"""Verifica listas reales de widgets con servicios aislados de la base de datos."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from decimal import Decimal
from datetime import date
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidgetItem, QLineEdit, QPushButton, QMessageBox
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from crece.interfaz import PaginaClientes, PaginaPrestamos, SimuladorPrestamo, ESTILO_APLICACION
from ui.workspace import workspace_styles
from ui.widgets.premium import load_fonts


class WorkspaceDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        load_fonts()
        cls.app.setStyleSheet(ESTILO_APLICACION)

    def test_search_filter_and_empty_state_follow_actual_records(self):
        page = PaginaClientes()
        page.setStyleSheet(workspace_styles())
        page.resize(1050,800)
        page.show()
        records = [
            dict(id=1,cedula='001',nombre_completo='Ana Pérez',telefono='88881111',correo='ana@example.test',estado='ACTIVO'),
            dict(id=2,cedula='002',nombre_completo='Luis Ruiz',telefono='88882222',correo='luis@example.test',estado='INACTIVO')]
        with patch('crece.interfaz.listar_clientes',return_value=records):
            page.cargar_clientes()
        QTest.qWait(60)
        self.assertTrue(page.tabla.empty.isHidden())
        self.assertEqual(page.total_metric.value.text(),'2')
        self.assertEqual(page.active_metric.value.text(),'1')
        self.assertEqual(page.amount_metric.value.text(),'2')
        page.buscar.setText('perez')
        self.assertFalse(page.tabla.isRowHidden(0))
        self.assertTrue(page.tabla.isRowHidden(1))
        self.assertEqual(page.contador.text(),'1 de 2 registros')
        self.assertEqual(page.amount_metric.value.text(),'2')
        page.filtro_estado.setCurrentText('Inactivo')
        self.assertFalse(page.tabla.empty.isHidden())
        self.assertIn('coincidencias',page.tabla.empty.text())
        page.limpiar_filtros()
        self.assertTrue(page.tabla.empty.isHidden())
        with patch('crece.interfaz.listar_clientes',return_value=[]):
            page.cargar_clientes()
        QTest.qWait(60)
        self.assertFalse(page.tabla.empty.isHidden())
        self.assertEqual(page.total_metric.value.text(),'0')
        page.close()

    def test_employee_client_form_saves_under_authenticated_actor(self):
        from crece.servicios.permisos import _actor
        previous_actor=_actor.get()
        page=PaginaClientes(actor_id=73,version_sesion=4)
        observed=[]
        def fill_and_save():
            dialog=QApplication.activeModalWidget()
            values={'cedula':'001-150890-0001A','nombres':'Ana','apellidos':'Prueba','telefono':'88881111','correo':'','direccion':''}
            for key,value in values.items():
                dialog.findChild(QLineEdit,'dato_'+key).setText(value)
            next(button for button in dialog.findChildren(QPushButton) if button.text()=='Guardar cliente').click()
        with patch('crece.interfaz.registrar_cliente',side_effect=lambda *_:observed.append(_actor.get()) or 31), \
             patch.object(page,'cargar_clientes'), patch.object(QMessageBox,'information'):
            QTimer.singleShot(30,fill_and_save)
            page.abrir_formulario_cliente()
        self.assertEqual(observed,[73])
        self.assertEqual(_actor.get(),previous_actor)
        page.close()

    def test_financial_totals_are_computed_from_loaded_rows(self):
        page = PaginaPrestamos()
        records = [dict(id=1,cliente='Cliente de prueba',monto_principal=Decimal('10000'),cuota_mensual=Decimal('945.60'),plazo_meses=12,estado='ACTIVO')]
        with patch('crece.interfaz.listar_prestamos',return_value=records):
            page.cargar_prestamos()
        QTest.qWait(50)
        self.assertEqual(page.amount_metric.value.text(),'C$ 10,000.00')
        self.assertEqual(page.tabla.item(0,2).textAlignment(),Qt.AlignRight|Qt.AlignVCenter)
        self.assertTrue(page.tabla.empty.isHidden())
        self.assertEqual(page.tabla.item(0,2).toolTip(),'C$10,000.00')
        page.close()

    def test_simulator_keeps_the_financial_engine_and_marks_stale_results(self):
        page = SimuladorPrestamo()
        page.calcular_plan()
        self.assertEqual(page.tabla_cuotas.rowCount(),12)
        self.assertEqual(page.tabla_cuotas.item(11,4).text(),'C$ 0.00')
        self.assertEqual(page.payment_metric.value.text(),'C$ 2,033.33')
        self.assertTrue(page.tabla_cuotas.empty.isHidden())
        page.monto_principal.setText('20000')
        self.assertIn('Vuelve a calcular',page.resumen.text())
        page.close()

    def test_simulator_frequency_changes_calendar_and_period_interest(self):
        page=SimuladorPrestamo()
        page.plazo_meses.setText('4')
        page.frecuencia.setCurrentIndex(page.frecuencia.findData('DIARIO'))
        page.calcular_plan()
        self.assertEqual(page.tabla_cuotas.rowCount(),4)
        self.assertEqual(page.tabla_cuotas.item(0,3).text(),'C$ 2,500.00')
        self.assertIn('0.400000',page.tabla_cuotas.horizontalHeaderItem(5).text())
        self.assertEqual(page.tabla_cuotas.item(0,5).text(),'C$ 40.00')
        self.assertIn('Diario',page.resumen.text())
        page.frecuencia.setCurrentIndex(page.frecuencia.findData('QUINCENAL'))
        self.assertIn('Vuelve a calcular',page.resumen.text())
        page.calcular_plan()
        self.assertEqual(page.tabla_cuotas.item(0,3).text(),'C$ 2,500.00')
        self.assertEqual(page.tabla_cuotas.item(0,5).text(),'C$ 600.00')
        page.close()


if __name__=='__main__':
    unittest.main()
