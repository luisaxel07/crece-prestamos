"""Vista del mismo reporte que se guarda o imprime; no confirma una impresión automáticamente."""
from pathlib import Path
from datetime import date
from PySide6.QtCore import QDate
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFileDialog,QMessageBox,QTableWidgetItem,QProgressDialog,QHeaderView,QDateEdit,QFormLayout
from ui.workspace import label,button,DataTable
from ui.export_worker import ExportWorker

class ReportDialog(QDialog):
    def __init__(self,reporte,parent=None):
        super().__init__(parent)
        self.reporte=reporte
        self.worker=None
        self.cierre_pendiente=False
        if parent: self.setProperty('appearance',parent.window().property('appearance'))
        self.setWindowTitle(reporte['titulo']+' | CRECE+ PRÉSTAMOS')
        self.setWindowFlags(self.windowFlags()|Qt.WindowMinMaxButtonsHint)
        self.resize(1180,760)
        self.setMinimumSize(900,560)
        box=QVBoxLayout(self)
        box.setContentsMargins(24,24,24,24)
        box.addWidget(label(reporte['titulo'],'workspaceTitle',wrap=True))
        heading=QHBoxLayout()
        heading.addWidget(button('Guardar PDF',lambda:self.guardar('pdf')))
        heading.addWidget(button('Guardar Excel',lambda:self.guardar('xlsx'),False))
        heading.addWidget(button('Vista previa / imprimir',self.imprimir,False))
        if len(reporte['prestamos'])==1:
            heading.addWidget(button('Cotizar liquidacion',self.cotizar_liquidacion,False))
        heading.addStretch()
        box.addLayout(heading)
        client=reporte['cliente']
        box.addWidget(label((client['nombre_completo']+' · '+client['cedula']) if client else 'Todos los clientes incluidos en el alcance seleccionado','surfaceTitle'))
        if len(reporte['prestamos'])==1:
            loan=reporte['prestamos'][0]
            tipo={'ASALARIADO':'Asalariado','COMERCIAL':'Credito comercial'}.get(loan.get('tipo_credito','GENERAL'),'General')
            metodo='Interes plano sobre capital inicial' if loan.get('metodo_interes')=='PLANO' else 'Metodo frances sobre saldo'
            box.addWidget(label(f"{tipo} | {loan.get('tasa_mensual',0):.2f}% mensual | {metodo}",wrap=True))
        totals=reporte['totales']
        box.addWidget(label(f"Principal: C$ {totals['principal']:,.2f}  ·  Cobrado: C$ {totals['cobrado']:,.2f}  ·  Saldo programado: C$ {totals['saldo']:,.2f}",wrap=True))
        box.addWidget(label('Saldo pendiente = capital, interés y recargos pendientes aplicables. Las condiciones de préstamos emitidos se conservan.',wrap=True))
        tasa_unica=len(reporte['prestamos'])==1
        tasa_periodo=reporte['prestamos'][0].get('tasa_periodica',reporte['prestamos'][0].get('tasa_mensual',0)) if tasa_unica else None
        columnas=['PRESTAMO','#','VENCE','CAPITAL INICIAL',f'TASA DEL PERIODO ({tasa_periodo:.6f} %) / INTERES EQUIVALENTE (C$)','CAPITAL','CUOTA','PAGADO ORDINARIO','RECARGO','RECARGO PAGADO','PENDIENTE TOTAL','ESTADO'] if tasa_unica else ['PRESTAMO','#','VENCE','CAPITAL INICIAL','TASA DEL PERIODO EQUIVALENTE (C$)','CAPITAL','CUOTA','PAGADO ORDINARIO','RECARGO','RECARGO PAGADO','PENDIENTE TOTAL','ESTADO']
        self.table=DataTable(columnas)
        rows=[(loan,q) for loan in reporte['prestamos'] for q in loan['cuotas']]
        self.table.setRowCount(len(rows))
        self.table.setMinimumWidth(0)
        for row,(loan,q) in enumerate(rows):
            if tasa_unica:
                values=[f"PR-{loan['id']:05d}",q['numero_cuota'],q['fecha_vencimiento'].strftime('%d/%m/%Y'),f"C$ {q['saldo_inicial']:,.2f}",f"C$ {q['interes']:,.2f}",f"C$ {q['abono_capital']:,.2f}",f"C$ {q['cuota_programada']:,.2f}",f"C$ {q['monto_pagado']:,.2f}",f"C$ {q.get('recargo',0):,.2f}",f"C$ {q.get('recargo_pagado',0):,.2f}",f"C$ {q['saldo']:,.2f}",q['estado']]
            else:
                values=[f"PR-{loan['id']:05d}",q['numero_cuota'],q['fecha_vencimiento'].strftime('%d/%m/%Y'),f"C$ {q['saldo_inicial']:,.2f}",f"C$ {q['interes']:,.2f}",f"C$ {q['abono_capital']:,.2f}",f"C$ {q['cuota_programada']:,.2f}",f"C$ {q['monto_pagado']:,.2f}",f"C$ {q.get('recargo',0):,.2f}",f"C$ {q.get('recargo_pagado',0):,.2f}",f"C$ {q['saldo']:,.2f}",q['estado']]
            for col,value in enumerate(values): self.table.setItem(row,col,QTableWidgetItem(str(value)))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        if not rows: self.table.show_empty('No hay cuotas para el alcance seleccionado.')
        box.addWidget(self.table,1)
        close=button('Cerrar',self.accept,False)
        box.addWidget(close,alignment=Qt.AlignRight)

    def cotizar_liquidacion(self):
        from crece.servicios.reportes import cotizar_liquidacion
        from crece.infraestructura.base_datos import ErrorConexionBaseDatos
        from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QLabel,QMessageBox
        dialog=QDialog(self);dialog.setWindowTitle('Cotizar liquidacion anticipada')
        layout=QVBoxLayout(dialog);layout.addWidget(QLabel('Fecha en que el cliente desea liquidar:'))
        fecha=QDateEdit();fecha.setCalendarPopup(True);fecha.setDate(QDate.currentDate());layout.addWidget(fecha)
        actions=QHBoxLayout();ok=button('Calcular',dialog.accept);cancel=button('Cancelar',dialog.reject,False)
        actions.addWidget(cancel);actions.addWidget(ok);layout.addLayout(actions)
        if dialog.exec()!=QDialog.Accepted:return
        try:
            q=cotizar_liquidacion(self.reporte['prestamos'][0]['id'],fecha.date().toPython())
            QMessageBox.information(self,'Cotizacion de liquidacion',
                f"PR-{q['prestamo_id']:05d} - {q['cliente']}\nFecha: {q['fecha']:%d/%m/%Y}\n\n"
                f"Cuotas vencidas pendientes: C$ {q['cuotas_vencidas_pendientes']:,.2f}\n"
                f"Recargos pendientes: C$ {q['recargos_pendientes']:,.2f}\n"
                f"Capital futuro: C$ {q['capital_futuro']:,.2f}\n"
                f"Interes devengado hasta la fecha: C$ {q['interes_devengado']:,.2f}\n\n"
                f"TOTAL ESTIMADO: C$ {q['total']:,.2f}\n\nCotizacion informativa; no registra ningun pago.",self)
        except (ValueError,ErrorConexionBaseDatos) as error:
            QMessageBox.warning(self,'No se pudo cotizar',str(error))

    def guardar(self,formato):
        if self.worker and self.worker.isRunning(): return
        name='reporte_crece'
        if self.reporte['cliente']: name+=f"_cliente_{self.reporte['cliente']['id']}"
        path,_=QFileDialog.getSaveFileName(self,'Guardar reporte',str(Path.home()/f'{name}.{formato}'),'PDF (*.pdf)' if formato=='pdf' else 'Excel (*.xlsx)')
        if not path: return
        if not path.lower().endswith('.'+formato): path+='.'+formato
        self.progress=QProgressDialog('Preparando reporte…','Cancelar',0,100,self)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setMinimumDuration(0)
        self.progress.setAutoClose(False)
        self.worker=ExportWorker(self.reporte,path,formato,self)
        self.progress.canceled.connect(self.worker.requestInterruption)
        self.worker.progreso.connect(self.progress.setValue)
        self.worker.completado.connect(lambda result:QMessageBox.information(self,'Reporte guardado',f'Archivo guardado en:\n{result}'))
        self.worker.fallo.connect(lambda error:QMessageBox.warning(self,'No se pudo guardar',error))
        self.worker.finished.connect(self.exportacion_terminada)
        self.worker.start()

    def exportacion_terminada(self):
        self.progress.close()
        self.worker.deleteLater()
        self.worker=None
        if self.cierre_pendiente: super().reject()

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.cierre_pendiente=True
            self.worker.requestInterruption()
            return
        super().reject()

    def done(self,result):
        if self.worker and self.worker.isRunning():
            self.cierre_pendiente=True
            self.worker.requestInterruption()
            return
        super().done(result)

    def imprimir(self):
        from ui.print_preview import PrintPreviewDialog
        PrintPreviewDialog(self.reporte,self).exec()
