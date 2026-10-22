"""Controles de captura Qt que comparten reglas con los servicios y la web."""
import re
import unicodedata
from PySide6.QtCore import QRegularExpression,Qt,QEvent,QObject
from PySide6.QtGui import QValidator,QRegularExpressionValidator
from PySide6.QtWidgets import QLabel
from crece.nucleo.validaciones import (REGLAS,ErrorValidacion,normalizar_nombre,normalizar_cedula,normalizar_telefono,normalizar_correo)

class ValidadorNombre(QValidator):
    def __init__(self,limite,parent=None):super().__init__(parent);self.limite=limite
    def validate(self,value,pos):
        value=unicodedata.normalize('NFC',value)
        if len(value)>self.limite or any(not (c.isalpha() or c==' ') for c in value):return QValidator.State.Invalid,value,pos
        return (QValidator.State.Acceptable if value.strip() else QValidator.State.Intermediate),value,min(pos,len(value))

class EdicionCedula(QObject):
    def eventFilter(self,field,event):
        if event.type()==QEvent.KeyPress and not field.hasSelectedText():
            pos=field.cursorPosition()
            if event.key()==Qt.Key_Backspace and pos>0 and field.text()[pos-1]=='-':field.setCursorPosition(pos-1)
            elif event.key()==Qt.Key_Delete and pos<len(field.text()) and field.text()[pos]=='-':field.setCursorPosition(pos+1)
        return False

class ValidadorCedula(QValidator):
    def validate(self,value,pos):
        if not re.fullmatch(r'[0-9A-Za-z-]*',value):return QValidator.State.Invalid,value,pos
        compacto=value.replace('-','')
        if not re.fullmatch(r'[0-9]{0,13}|[0-9]{13}[A-Za-z]',compacto):return QValidator.State.Invalid,value,pos
        left=len(value[:pos].replace('-',''))
        compacto=compacto.upper()
        formatted=compacto[:3]+('-' if len(compacto)>=3 else '')+compacto[3:9]+('-' if len(compacto)>=9 else '')+compacto[9:]
        cursor=left+(1 if left>=3 else 0)+(1 if left>=9 else 0)
        try:normalizar_cedula(formatted);state=QValidator.State.Acceptable
        except ValueError:state=QValidator.State.Intermediate
        return state,formatted,min(cursor,len(formatted))

def mensaje_campo(key,texto,requerido=True):
    if not texto and not requerido:return ''
    try:
        if key in ('nombres','apellidos','name','cargo'):normalizar_nombre(texto,key,REGLAS[key]['maxlength'])
        elif key=='cedula':normalizar_cedula(texto)
        elif key=='telefono':normalizar_telefono(texto)
        elif key=='correo':normalizar_correo(texto,requerido)
    except ValueError as error:return str(error)
    return ''

def configurar_campo(field,key,requerido=True):
    regla=REGLAS[key]
    if field.objectName()!='authField':field.setObjectName('dato_'+key)
    field.setProperty('validationKey',key)
    field.setMaxLength(regla['maxlength'])
    field.setPlaceholderText(regla['placeholder'])
    field.setToolTip(regla['ayuda'])
    field.setAccessibleDescription(regla['ayuda'])
    if key in ('nombres','apellidos','name','cargo'):field.setValidator(ValidadorNombre(regla['maxlength'],field))
    elif key=='cedula':
        field.setValidator(ValidadorCedula(field));field._edicion_cedula=EdicionCedula(field);field.installEventFilter(field._edicion_cedula)
    elif key=='telefono':field.setValidator(QRegularExpressionValidator(QRegularExpression('[0-9]{0,15}'),field));field.setInputMethodHints(Qt.ImhDigitsOnly)
    if key=='correo':field.setInputMethodHints(Qt.ImhEmailCharactersOnly)
    ayuda=QLabel(regla['ayuda']);ayuda.setWordWrap(True);ayuda.setTextFormat(Qt.PlainText)
    ayuda.setStyleSheet('font-size:11px;');field._ayuda_validacion=ayuda
    def mostrar(*_):
        error=mensaje_campo(key,field.text(),requerido)
        ayuda.setText(error or regla['ayuda']);field.setAccessibleDescription(error or regla['ayuda'])
    field.editingFinished.connect(mostrar)
    field.inputRejected.connect(lambda:ayuda.setText('Entrada no permitida. '+regla['ayuda']))
    field.textEdited.connect(lambda *_:mostrar() if key=='cedula' and len(field.text())==16 else ayuda.setText(regla['ayuda']))
    return ayuda

def enfocar_error(dialog,error):
    from PySide6.QtWidgets import QLineEdit
    if isinstance(error,ErrorValidacion):
        field=dialog.findChild(QLineEdit,'dato_'+error.campo)
        if field:
            field.setFocus();field.selectAll()
            if hasattr(field,'_ayuda_validacion'):field._ayuda_validacion.setText(str(error))

def configurar_numero(field,tipo):
    patrones={'monto':r'[0-9]{0,12}(?:\.[0-9]{0,2})?','tasa':r'[0-9]{0,2}(?:\.[0-9]{0,4})?','meses':r'[0-9]{0,3}'}
    field.setValidator(QRegularExpressionValidator(QRegularExpression(patrones[tipo]),field))
    field.setPlaceholderText(REGLAS[tipo]['placeholder']);field.setMaxLength(REGLAS[tipo]['maxlength'])
    field.setToolTip(REGLAS[tipo]['ayuda']);field.setAccessibleDescription(REGLAS[tipo]['ayuda'])
    field.setInputMethodHints(Qt.ImhDigitsOnly if tipo=='meses' else Qt.ImhFormattedNumbersOnly)



def leer_numero(field,tipo):
    from decimal import Decimal
    from crece.nucleo.validaciones import validar_numero_texto
    return Decimal(validar_numero_texto(field.text(),tipo))

def leer_plazo(field):
    from crece.nucleo.validaciones import validar_plazo
    return validar_plazo(field.text())
