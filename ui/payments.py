from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QTableWidgetItem,QMessageBox,QInputDialog,QHeaderView
from crece.servicios.comprobantes import obtener_comprobante_pago
from ui.comprobante_dialog import ComprobanteDialog
from ui.workspace import label,button,DataTable
from crece.servicios.gestion import listar_pagos,resolver_pago
from crece.infraestructura.base_datos import ErrorConexionBaseDatos

class PaymentsDialog(QDialog):
    def __init__(self,parent=None):
        super().__init__(parent)
        if parent: self.setProperty('appearance',parent.window().property('appearance'))
        self.setWindowTitle('Cobros y solicitudes de pago | CRECE+ PRÉSTAMOS')
        self.resize(1100,700)
        box=QVBoxLayout(self)
        box.addWidget(label('Historial y verificación de pagos','workspaceTitle'))
        actions=QHBoxLayout()
        for text,action in [('Confirmar solicitud','CONFIRMAR'),('Rechazar solicitud','RECHAZAR'),('Editar referencia','EDITAR_REFERENCIA'),('Anular cobro','ANULAR')]:
            actions.addWidget(button(text,lambda checked=False,a=action:self.resolver(a),False))
        actions.addWidget(button('Ver comprobante',self.ver_comprobante,False))
        box.addLayout(actions)
        self.table=DataTable(['CLIENTE','PRÉSTAMO','CUOTA','FECHA','MONTO','REFERENCIA','COMPROBANTE','ESTADO','APLICADO A RECARGO'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        box.addWidget(self.table,1)
        self.table.cellDoubleClicked.connect(lambda *_:self.ver_comprobante())
        self.cargar()

    def cargar(self):
        try: rows=listar_pagos()
        except (ValueError,ErrorConexionBaseDatos) as error:QMessageBox.warning(self,'Pagos',str(error));return
        self.table.setRowCount(len(rows))
        for row,p in enumerate(rows):
            values=[p['cliente'],f"PR-{p['prestamo_id']:05d}",p['numero_cuota'],p['fecha_pago'].strftime('%d/%m/%Y'),f"C$ {p['monto']:,.2f}",p['referencia'] or '—','Adjunto' if p.get('tiene_comprobante') else 'Sin adjunto',p['estado'],f"C$ {p.get('monto_recargo',0):,.2f}"]
            for col,v in enumerate(values):self.table.setItem(row,col,QTableWidgetItem(str(v)))
            self.table.item(row,0).setData(Qt.UserRole,p['id'])
        self.table.show_empty('No hay pagos registrados.' if not rows else '')

    def ver_comprobante(self):
        row=self.table.currentRow()
        if row<0:QMessageBox.information(self,'Comprobante','Selecciona una solicitud de pago.');return
        try:ComprobanteDialog(obtener_comprobante_pago(self.table.item(row,0).data(Qt.UserRole)),self).exec()
        except (ValueError,ErrorConexionBaseDatos) as error:QMessageBox.warning(self,'Comprobante',str(error))

    def resolver(self,action):
        row=self.table.currentRow()
        if row<0:QMessageBox.information(self,'Pago','Selecciona un pago.');return
        note=''
        if action in ('ANULAR','EDITAR_REFERENCIA'):
            note,ok=QInputDialog.getText(self,'Pago','Motivo de anulación:' if action=='ANULAR' else 'Referencia:')
            if not ok:return
        if action!='EDITAR_REFERENCIA' and QMessageBox.question(self,'Confirmar operación',f'¿{action.capitalize()} el pago seleccionado?')!=QMessageBox.Yes:return
        try:resolver_pago(self.table.item(row,0).data(Qt.UserRole),action,note)
        except (ValueError,ErrorConexionBaseDatos) as error:QMessageBox.warning(self,'Pago',str(error));return
        self.cargar()
