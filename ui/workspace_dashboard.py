from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QProgressBar
from ui.workspace import label, button, surface, Metric


class Dashboard(QWidget):
    def __init__(self, open_loans, open_clients, open_simulator):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28,22,28,24)
        layout.setSpacing(18)
        heading = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(5)
        titles.addWidget(label('VISIÓN GENERAL','workspaceEyebrow'))
        titles.addWidget(label('Tu cartera, en perspectiva.','workspaceTitle'))
        titles.addWidget(label('La información que necesitas para decidir tu próximo paso.'))
        heading.addLayout(titles)
        heading.addStretch()
        heading.addWidget(button('Ir a préstamos',open_loans,icon='arrow'))
        layout.addLayout(heading)
        hero = QFrame()
        hero.setObjectName('workspaceHero')
        hero.setFixedHeight(112)
        hero_row = QHBoxLayout(hero)
        hero_row.setContentsMargins(24,18,24,18)
        message = QVBoxLayout()
        caption = label('CRECE+ PRÉSTAMOS  /  GESTIÓN FINANCIERA')
        caption.setStyleSheet('color: rgba(255,255,255,180); font-size: 10px; letter-spacing: 1px;')
        headline = label('Cada decisión, con respaldo.')
        headline.setStyleSheet('color: #FFFFFF; font-family: Montserrat; font-size: 23px; font-weight: 700;')
        detail = label('Crecemos contigo, con claridad en cada operación.')
        detail.setStyleSheet('color: rgba(255,255,255,200); font-size: 12px;')
        message.addWidget(caption)
        message.addWidget(headline)
        message.addWidget(detail)
        hero_row.addLayout(message)
        hero_row.addStretch()
        accent = label('CRECE+')
        accent.setStyleSheet('color: rgba(255,255,255,22); font-family: Montserrat; font-size: 46px; font-weight: 700;')
        hero_row.addWidget(accent)
        layout.addWidget(hero)
        metrics = QHBoxLayout()
        metrics.setSpacing(14)
        self.tarjetas_metricas = []
        for title,description,icon in [
            ('CARTERA ACTIVA','Saldo pendiente por recuperar','coins'),
            ('CUOTAS POR COBRAR','Cuotas activas o en mora','document'),
            ('PAGOS POR VERIFICAR','Solicitudes de clientes','shield'),
            ('ÍNDICE DE MORA','Proporción de cuotas vencidas','chart')]:
            metric = Metric(title,description=description,icon=icon)
            self.tarjetas_metricas.append(metric)
            metrics.addWidget(metric)
        layout.addLayout(metrics)
        bottom = QHBoxLayout()
        bottom.setSpacing(18)
        activity = surface()
        self.activity_layout = QVBoxLayout(activity)
        self.activity_layout.setContentsMargins(21,19,21,19)
        self.activity_layout.setSpacing(14)
        self.activity_layout.addWidget(label('Actividad reciente','surfaceTitle'))
        self.activity_layout.addWidget(label('Últimos movimientos de la operación.'))
        self.activity_rows = QVBoxLayout()
        self.activity_rows.setSpacing(0)
        self.activity_layout.addLayout(self.activity_rows)
        self.activity_layout.addStretch()
        self.activity_empty = label('No hay movimientos registrados para mostrar.',wrap=True)
        self.activity_rows.addWidget(self.activity_empty)
        bottom.addWidget(activity,3)
        health = surface()
        health_box = QVBoxLayout(health)
        health_box.setContentsMargins(21,19,21,19)
        health_box.setSpacing(15)
        health_box.addWidget(label('Estado de tu cartera','surfaceTitle'))
        self.health_rate = label('—','metricValue')
        health_box.addWidget(self.health_rate)
        health_box.addWidget(label('Cuotas en mora sobre cuotas pendientes',wrap=True))
        self.health_bar = QProgressBar()
        self.health_bar.setObjectName('workspaceHealth')
        self.health_bar.setRange(0,100)
        self.health_bar.setValue(0)
        self.health_bar.setTextVisible(False)
        health_box.addWidget(self.health_bar)
        self.health_note = label('La información se actualiza con las operaciones registradas.',wrap=True)
        health_box.addWidget(self.health_note)
        health_box.addStretch()
        health_box.addWidget(label('PRÓXIMO PASO','workspaceEyebrow'))
        health_box.addWidget(button('Registrar cliente',open_clients,False,'users'))
        health_box.addWidget(button('Simular un préstamo',open_simulator,False,'calculator'))
        bottom.addWidget(health,2)
        layout.addLayout(bottom,1)

    def load(self, summary_loader, activity_loader):
        from crece.servicios.clientes import ErrorConexionBaseDatos
        try:
            summary = summary_loader()
        except (ValueError, ErrorConexionBaseDatos):
            self.health_note.setText('No se pudo actualizar la cartera. Revisa la conexión e intenta nuevamente.')
            return
        values = [f"C$ {summary['cartera_activa']:,.2f}",str(summary['cuotas_pendientes']),str(summary['pagos_por_verificar']),f"{summary['indice_mora']:,.2f} %"]
        for widget,value in zip(self.tarjetas_metricas,values):
            widget.actualizar(value)
        self.health_rate.setText(values[-1])
        self.health_bar.setValue(round(float(summary['indice_mora'])))
        self.health_note.setText(f"{summary['cuotas_pendientes']} cuotas pendientes · {summary['pagos_por_verificar']} pagos por verificar.")
        try:
            records = activity_loader()
        except (ValueError, ErrorConexionBaseDatos):
            records = None
        while self.activity_rows.count():
            item = self.activity_rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not records:
            self.activity_rows.addWidget(label('No se pudo actualizar la actividad.' if records is None else 'Aún no hay movimientos registrados.',wrap=True))
        else:
            for record in records[:5]:
                row = QFrame()
                row.setStyleSheet('QFrame { border: none; border-bottom: 1px solid rgba(0,51,102,18); }')
                line = QHBoxLayout(row)
                line.setContentsMargins(0,13,0,13)
                line.setSpacing(14)
                dot = label('')
                dot.setFixedSize(8,8)
                dot.setStyleSheet('background: #00A651; border-radius: 4px;')
                line.addWidget(dot)
                texts = QVBoxLayout()
                texts.setSpacing(4)
                title = label(str(record['tipo']),'activityTitle')
                texts.addWidget(title)
                detail = label(str(record['detalle']),'activityDetail',wrap=True)
                texts.addWidget(detail)
                line.addLayout(texts,1)
                date = record.get('fecha')
                if date:
                    line.addWidget(label(date.strftime('%d %b · %H:%M'),'workspaceCount'))
                self.activity_rows.addWidget(row)
