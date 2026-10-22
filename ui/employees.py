"""Gestión de empleados y sus cuentas: disponible solo para administración."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QComboBox,QDialog,QScrollArea,QMessageBox,QTableWidgetItem
from ui.validacion_campos import configurar_campo, enfocar_error
from ui.workspace import label,button,DataTable,surface
from crece.servicios.gestion import listar_empleados,guardar_empleado,eliminar_empleado
from crece.infraestructura.base_datos import ErrorConexionBaseDatos

class EmployeesPage(QWidget):
    def __init__(self):
        super().__init__()
        self.records=[]
        box=QVBoxLayout(self)
        box.setContentsMargins(28,22,28,24)
        box.addWidget(label('Empleados y accesos','workspaceTitle'))
        box.addWidget(label('El administrador habilita las credenciales y el estado de cada empleado.',wrap=True))
        actions=QHBoxLayout()
        actions.addWidget(button('Añadir empleado',lambda:self.editar()))
        actions.addWidget(button('Editar / credenciales',self.editar_seleccionado,False))
        actions.addWidget(button('Eliminar / desactivar',self.eliminar,False))
        actions.addWidget(button('Actualizar',self.cargar_empleados,False))
        actions.addStretch()
        box.addLayout(actions)
        self.search=QLineEdit()
        self.search.setObjectName('workspaceSearch')
        self.search.setPlaceholderText('Buscar empleado, cédula, usuario o cargo…')
        self.search.setAccessibleName('Buscar empleados')
        self.search.textChanged.connect(self.filtrar)
        box.addWidget(self.search)
        card=surface()
        body=QVBoxLayout(card)
        self.table=DataTable(['CÉDULA','NOMBRE','CARGO','USUARIO','TELÉFONO','ESTADO'])
        self.table.cellDoubleClicked.connect(lambda *_:self.editar_seleccionado())
        body.addWidget(self.table)
        box.addWidget(card,1)

    def cargar_empleados(self):
        try: self.records=listar_empleados()
        except (ValueError,ErrorConexionBaseDatos) as error: QMessageBox.warning(self,'Empleados',str(error));return
        self.table.setRowCount(len(self.records))
        for row,e in enumerate(self.records):
            for col,value in enumerate([e['cedula'],e['nombre'],e['cargo'],e['nombre_usuario'],e['telefono'],'Activo' if e['activo'] else 'Inactivo']):
                self.table.setItem(row,col,QTableWidgetItem(str(value)))
            self.table.item(row,0).setData(Qt.UserRole,e)
        self.table.show_empty('Todavía no hay empleados registrados.' if not self.records else '')
        self.filtrar()

    def filtrar(self,*_):
        query=self.search.text().strip().casefold()
        for row in range(self.table.rowCount()):
            self.table.setRowHidden(row,not any(query in self.table.item(row,col).text().casefold() for col in range(self.table.columnCount())))

    def seleccionado(self):
        row=self.table.currentRow()
        if row<0: raise ValueError('Selecciona un empleado.')
        return self.table.item(row,0).data(Qt.UserRole)

    def editar_seleccionado(self):
        try:self.editar(self.seleccionado())
        except ValueError as error:QMessageBox.information(self,'Empleado',str(error))

    def editar(self,record=None):
        dialog=QDialog(self)
        dialog.setWindowTitle('Editar empleado' if record else 'Nuevo empleado')
        dialog.setMinimumWidth(480)
        box=QVBoxLayout(dialog)
        form=QFormLayout()
        fields={}
        for key,title in [('cedula','Cédula'),('nombres','Nombres'),('apellidos','Apellidos'),('telefono','Teléfono'),('correo','Correo'),('cargo','Cargo'),('nombre_usuario','Usuario de acceso'),('contrasena','Nueva contraseña' if record else 'Contraseña')]:
            field=QLineEdit(record.get(key,'') or '' if record else '')
            field.setAccessibleName(title)
            if key=='contrasena': field.setEchoMode(QLineEdit.Password);field.setPlaceholderText('Mínimo 10 caracteres; vacío conserva la actual' if record else 'Mínimo 10 caracteres')
            ayuda=configurar_campo(field,key,requerido=key not in ("correo","contrasena"))
            if key=="contrasena":field.setPlaceholderText("Vacía para conservar la actual" if record else "Mínimo 10 caracteres")
            form.addRow(title,field)
            form.addRow("",ayuda)
            fields[key]=field
        active=QComboBox()
        active.addItem('Activo',True)
        active.addItem('Inactivo',False)
        if record: active.setCurrentIndex(0 if record['activo'] else 1)
        form.addRow('Estado autorizado',active)
        contenido=QWidget();contenido.setLayout(form)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(contenido);box.addWidget(scroll)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollArea > QWidget > QWidget { background: transparent; }")
        scroll.verticalScrollBar().setStyleSheet("QScrollBar:vertical { width: 10px; margin: 0px; } QScrollBar::handle:vertical { background: #00A651; min-height: 28px; border-radius: 4px; } QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }")
        dialog.resize(570,min(740,dialog.screen().availableGeometry().height()-80))
        def save():
            try: guardar_empleado(**{k:f.text() for k,f in fields.items()},activo=active.currentData(),empleado_id=record['id'] if record else None)
            except (ValueError,ErrorConexionBaseDatos) as error: enfocar_error(dialog,error);QMessageBox.warning(dialog,'No se pudo guardar',str(error));return
            dialog.accept();self.cargar_empleados()
        box.addWidget(button('Guardar empleado',save))
        dialog.exec()

    def eliminar(self):
        try:
            record=self.seleccionado()
            if QMessageBox.question(self,'Eliminar empleado',f"¿Dar de baja a {record['nombre']}? Si tiene operaciones, se conserva el historial y se desactiva el acceso.")!=QMessageBox.Yes:return
            result=eliminar_empleado(record['id'])
            self.cargar_empleados()
            QMessageBox.information(self,'Empleado actualizado',result.capitalize())
        except (ValueError,ErrorConexionBaseDatos) as error:QMessageBox.warning(self,'Empleado',str(error))
