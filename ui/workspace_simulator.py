from datetime import date
from decimal import Decimal, InvalidOperation
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QDateEdit, QComboBox, QTableWidgetItem, QMessageBox,QHeaderView
from crece.nucleo.amortizacion import calcular_tabla_credito,tasa_por_periodo,FRECUENCIAS
from ui.validacion_campos import configurar_numero,leer_numero,leer_plazo
from ui.workspace import label, button, surface, Metric, DataTable
from ui.widgets.premium import ASSETS


class PremiumSimulator(QWidget):
    def __init__(self, calculator):
        super().__init__()
        self.calculator = calculator
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,22,28,24)
        layout.setSpacing(18)
        layout.addWidget(label('PLANIFICACIÓN / CRÉDITO','workspaceEyebrow'))
        layout.addWidget(label('Simulador de préstamo','workspaceTitle'))
        layout.addWidget(label('Explora la cuota y el costo de un crédito antes de emitirlo.'))
        body = QHBoxLayout()
        body.setSpacing(18)
        form_card = surface()
        form_card.setFixedWidth(285)
        form = QVBoxLayout(form_card)
        form.setContentsMargins(21,21,21,21)
        form.setSpacing(12)
        form.addWidget(label('Configura tu escenario','surfaceTitle'))
        form.addWidget(label('Método de amortización francés',wrap=True))
        form.addSpacing(8)
        self.monto_principal = QLineEdit('10000')
        self.tasa_mensual = QLineEdit('2')
        self.tasa_anual = self.tasa_mensual  # Compatibility alias for integrations.
        self.plazo_meses = QLineEdit('12')
        self.frecuencia=QComboBox()
        for codigo,nombre in FRECUENCIAS.items():self.frecuencia.addItem(nombre,codigo)
        for field,tipo in [(self.monto_principal,'monto'),(self.tasa_mensual,'tasa'),(self.plazo_meses,'meses')]:configurar_numero(field,tipo)
        self.fecha_primera_cuota = QDateEdit()
        self.fecha_primera_cuota.setDate(date.today())
        self.fecha_primera_cuota.setCalendarPopup(True)
        self.fecha_primera_cuota.setDisplayFormat('dd/MM/yyyy')
        for title,control in [('Monto del préstamo (C$)',self.monto_principal),('Tasa mensual (%)',self.tasa_mensual),('Frecuencia de pago',self.frecuencia),('Número de cuotas',self.plazo_meses),('Primera cuota',self.fecha_primera_cuota)]:
            caption = label(title)
            caption.setBuddy(control)
            form.addWidget(caption)
            control.setAccessibleName(title)
            control.setObjectName('simulationInput')
            form.addWidget(control)
        form.addSpacing(4)
        self.calculate = button('Calcular plan',self.calcular_plan,True,'calculator')
        form.addWidget(self.calculate)
        form.addWidget(label('Esta simulación es orientativa. El crédito se registra únicamente al emitir el préstamo.',wrap=True))
        body.addWidget(form_card,0,Qt.AlignTop)
        results = QVBoxLayout()
        results.setSpacing(16)
        metrics = QHBoxLayout()
        metrics.setSpacing(12)
        self.payment_metric = Metric('CUOTA PERIÓDICA',description='Pago periódico estimado',icon='coins',compact=True)
        self.interest_metric = Metric('INTERÉS TOTAL',description='Costo financiero del plan',icon='chart',compact=True)
        self.total_metric = Metric('TOTAL A PAGAR',description='Capital más intereses',icon='document',compact=True)
        for metric in (self.payment_metric,self.interest_metric,self.total_metric): metrics.addWidget(metric)
        results.addLayout(metrics)
        table_card = surface()
        table = QVBoxLayout(table_card)
        table.setContentsMargins(1,1,1,1)
        table.setSpacing(0)
        header = QVBoxLayout()
        header.setContentsMargins(18,16,18,16)
        header.setSpacing(5)
        header.addWidget(label('Plan de pagos','surfaceTitle'))
        self.resumen = label('Completa los datos y calcula para obtener tu calendario.',wrap=True)
        header.addWidget(self.resumen)
        table.addLayout(header)
        self.tabla_cuotas = DataTable(['#','VENCIMIENTO','CUOTA','INTERÉS','CAPITAL','SALDO','TASA PERÍODO'])
        self.tabla_cuotas.horizontalHeader().setSectionResizeMode(6,QHeaderView.ResizeToContents)
        self.tabla_cuotas.show_empty('Tu plan de pagos aparecerá aquí después de calcular.')
        table.addWidget(self.tabla_cuotas,1)
        results.addWidget(table_card,1)
        body.addLayout(results,1)
        layout.addLayout(body,1)
        for field in (self.monto_principal,self.tasa_anual,self.plazo_meses):
            field.textChanged.connect(self.mark_stale)
            field.returnPressed.connect(self.calcular_plan)
        self.fecha_primera_cuota.dateChanged.connect(self.mark_stale)
        self.frecuencia.currentIndexChanged.connect(self.mark_stale)

    def mark_stale(self,*_):
        if self.tabla_cuotas.rowCount():
            self.resumen.setText('Cambiaste los datos. Vuelve a calcular para actualizar este plan.')

    def calcular_plan(self):
        try:
            principal = leer_numero(self.monto_principal,'monto')
            rows = calcular_tabla_credito(principal,leer_numero(self.tasa_anual,'tasa'),leer_plazo(self.plazo_meses),self.fecha_primera_cuota.date().toPython(),self.frecuencia.currentData())
        except (ValueError,InvalidOperation):
            QMessageBox.warning(self,'Datos inválidos','Verifica el monto, la tasa, el plazo y la fecha.')
            return
        total = sum(row.pago for row in rows)
        self.payment_metric.actualizar(f'C$ {rows[0].pago:,.2f}')
        self.interest_metric.actualizar(f'C$ {total-principal:,.2f}')
        self.total_metric.actualizar(f'C$ {total:,.2f}')
        self.resumen.setText(f'{self.frecuencia.currentText()} · {len(rows)} cuotas · Primera: {rows[0].fecha_vencimiento:%d/%m/%Y} · Última: {rows[-1].fecha_vencimiento:%d/%m/%Y}. Sin recargos por mora.')
        self.tabla_cuotas.setRowCount(len(rows))
        for row,quota in enumerate(rows):
            values = [str(quota.numero),quota.fecha_vencimiento.strftime('%d/%m/%Y'),f'C$ {quota.pago:,.2f}',f'C$ {quota.interes:,.2f}',f'C$ {quota.abono_capital:,.2f}',f'C$ {quota.saldo_final:,.2f}',f'{tasa_por_periodo(Decimal(self.tasa_mensual.text()),self.frecuencia.currentData()):.6f} %']
            for column,value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment((Qt.AlignRight if column>1 else Qt.AlignCenter)|Qt.AlignVCenter)
                self.tabla_cuotas.setItem(row,column,item)
        self.tabla_cuotas.show_empty('')
