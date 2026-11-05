"""Regresiones de impresión y archivos de marca, con datos MySQL de prueba y sin imprimir papel."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
import tempfile
import time
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch
from openpyxl import load_workbook
from PySide6.QtGui import QPageLayout, QPageSize
from PySide6.QtWidgets import QApplication, QDialog
from PySide6.QtTest import QTest
from PySide6.QtPdf import QPdfDocument
from PySide6.QtPdfWidgets import QPdfView
from PySide6.QtPrintSupport import QPrinter
import test_orm_management as orm_tests
from crece.servicios.reportes import obtener_reporte
from crece.infraestructura.exportadores import exportar_excel,exportar_pdf
from ui.print_preview import PrintPreviewDialog,imprimir_pdf,paginas_de_impresion


class PrintExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])
        fixture=orm_tests.OrmManagementTests();fixture.setUp()
        loan=fixture.loan();cls.report=obtener_reporte(prestamo_id=loan)
        fixture.tearDown()

    def setUp(self):
        self.folder=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.root=Path(self.folder.name)

    def tearDown(self): self.folder.cleanup()

    def test_excel_has_logo_grid_and_typed_values_on_all_sheets(self):
        target=self.root/'reporte.xlsx'
        before=deepcopy(self.report)
        exportar_excel(self.report,target)
        book=load_workbook(target)
        self.assertEqual(book.sheetnames,['Resumen','Préstamos','Cuotas'])
        for sheet in book:
            self.assertEqual(len(sheet._images),1)
            self.assertEqual(sheet.cell(10,1).border.left.style,'thin')
            self.assertEqual(sheet.cell(10,1).border.bottom.style,'thin')
            self.assertEqual(sheet['A9'].fill.fgColor.rgb,'00003366')
            self.assertTrue(sheet.print_title_rows)
        quotas=book['Cuotas']
        self.assertEqual(quotas['F10'].value,float(self.report['prestamos'][0]['cuotas'][0]['interes']))
        self.assertTrue(quotas['D10'].is_date)
        self.assertEqual(quotas['E10'].value,10000)
        self.assertEqual(quotas.max_row,21)
        self.assertEqual(quotas.auto_filter.ref,'A9:P21')
        self.assertEqual(quotas.freeze_panes,'C10')
        self.assertEqual(book['Resumen']['D14'].value,float(self.report['totales']['saldo']))
        self.assertEqual(self.report,before)
        book.close()

    def test_excel_keeps_formula_like_names_as_text(self):
        report=deepcopy(self.report)
        report['prestamos'][0]['cliente']='=1+1'
        report['prestamos'][0]['notas']='+SUM(1,1)'
        target=self.root/'texto.xlsx';exportar_excel(report,target)
        book=load_workbook(target)
        self.assertEqual(book['Préstamos']['B10'].data_type,'s')
        self.assertEqual(book['Préstamos']['B10'].value,'=1+1')
        self.assertEqual(book['Préstamos']['M10'].data_type,'s')
        book.close()

    def test_preview_uses_horizontal_official_pdf_and_clear_navigation(self):
        # Todo el material de prueba permanece en la carpeta aislada del proyecto.
        with patch('ui.print_preview.TemporaryDirectory',side_effect=lambda **kwargs:tempfile.TemporaryDirectory(dir=self.root,**kwargs)):
            dialog=PrintPreviewDialog(self.report)
        dialog.show()
        limite=time.monotonic()+60
        while time.monotonic()<limite:
            QTest.qWait(50)
            if dialog.worker is None and dialog.documento.pageCount():break
        try:
            self.assertGreater(dialog.documento.pageCount(),0)
            size=dialog.documento.pagePointSize(0)
            self.assertGreater(size.width(),size.height())
            self.assertEqual(dialog.vista.zoomMode(),QPdfView.ZoomMode.FitToWidth)
            self.assertTrue(dialog.imprimir_button.isEnabled())
            self.assertIn('horizontal',dialog.estado.text())
            if dialog.documento.pageCount()>1:
                dialog.ir_pagina(2);QTest.qWait(20)
                self.assertEqual(dialog.pagina.value(),2)
                self.assertTrue(dialog.anterior.isEnabled())
            dialog.zoom.setCurrentIndex(dialog.zoom.findText('150 %'))
            self.assertEqual(dialog.vista.zoomFactor(),1.5)
            with patch('ui.print_preview.QPrintDialog') as chooser,patch('ui.print_preview.imprimir_pdf') as send:
                chooser.return_value.exec.return_value=QDialog.Rejected
                dialog.imprimir()
                send.assert_not_called()
        finally:
            dialog.close()
            if dialog.worker:
                dialog.worker.wait();QTest.qWait(20)

    def test_print_pipeline_preserves_landscape_pages_and_page_selection(self):
        source=self.root/'source.pdf';exportar_pdf(self.report,source)
        document=QPdfDocument();document.load(str(source))
        printer=QPrinter(QPrinter.HighResolution)
        printer.setResolution(300)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setPageOrientation(QPageLayout.Landscape)
        target=self.root/'impreso.pdf';printer.setOutputFileName(str(target))
        self.assertTrue(imprimir_pdf(document,printer))
        result=QPdfDocument();result.load(str(target))
        self.assertEqual(result.pageCount(),document.pageCount())
        self.assertTrue(all(result.pagePointSize(i).width()>result.pagePointSize(i).height() for i in range(result.pageCount())))
        result.close()
        printer.setPrintRange(QPrinter.CurrentPage)
        self.assertEqual(paginas_de_impresion(printer,document.pageCount(),1),[1])
        printer.setPrintRange(QPrinter.PageRange);printer.setFromTo(2,2)
        self.assertEqual(paginas_de_impresion(printer,document.pageCount()),[1])
        document.close()


if __name__=='__main__':unittest.main()
