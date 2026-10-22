"""Vista del mismo reporte que se guarda o imprime; no confirma una impresión automáticamente."""
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFileDialog,QMessageBox,QTableWidgetItem,QProgressDialog,QHeaderView
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
        heading.addStretch()
        box.addLayout(heading)
        client=reporte['cliente']
        box.addWidget(label((client['nombre_completo']+' · '+client['cedula']) if client else 'Todos los clientes incluidos en el alcance seleccionado','surfaceTitle'))
        totals=reporte['totales']
        box.addWidget(label(f"Principal: C$ {totals['principal']:,.2f}  ·  Cobrado: C$ {totals['cobrado']:,.2f}  ·  Saldo programado: C$ {totals['saldo']:,.2f}",wrap=True))
        box.addWidget(label('Saldo programado = capital e interés pendientes. Las condiciones de préstamos emitidos se conservan.',wrap=True))
        self.table=DataTable(['PRÉSTAMO','#','VENCE','CAPITAL INICIAL','TASA MENSUAL','INTERÉS','CAPITAL','CUOTA','PAGADO','PENDIENTE','ESTADO'])
        rows=[(loan,q) for loan in reporte['prestamos'] for q in loan['cuotas']]
        self.table.setRowCount(len(rows))
        self.table.setMinimumWidth(0)
        for row,(loan,q) in enumerate(rows):
            values=[f"PR-{loan['id']:05d}",q['numero_cuota'],q['fecha_vencimiento'].strftime('%d/%m/%Y'),f"C$ {q['saldo_inicial']:,.2f}",f"{q['tasa_mensual']:.4f} %",f"C$ {q['interes']:,.2f}",f"C$ {q['abono_capital']:,.2f}",f"C$ {q['cuota_programada']:,.2f}",f"C$ {q['monto_pagado']:,.2f}",f"C$ {q['saldo']:,.2f}",q['estado']]
            for col,value in enumerate(values): self.table.setItem(row,col,QTableWidgetItem(str(value)))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        if not rows: self.table.show_empty('No hay cuotas para el alcance seleccionado.')
        box.addWidget(self.table,1)
        close=button('Cerrar',self.accept,False)
        box.addWidget(close,alignment=Qt.AlignRight)

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
