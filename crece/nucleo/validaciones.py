"""Validación común de datos personales, independiente de web, Qt y base de datos."""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

REGLAS=json.loads((Path(__file__).resolve().parents[2]/'portal_web/static/reglas-formularios.json').read_text(encoding='utf-8-sig'))

class ErrorValidacion(ValueError):
    def __init__(self,campo,mensaje):
        self.campo=campo
        super().__init__(mensaje)

def normalizar_nombre(value,campo='nombres',limite=80):
    nombre=unicodedata.normalize('NFC',str(value)).strip(' ')
    if not nombre or len(nombre)>limite or any(not (c.isalpha() or c==' ') for c in nombre):
        raise ErrorValidacion(campo,f'{"Apellidos" if campo=="apellidos" else "Cargo" if campo=="cargo" else "Nombres"}: usa solo letras y espacios (máximo {limite} caracteres).')
    return re.sub(' +',' ',nombre)

def normalizar_cedula(value):
    value=str(value).strip()
    if not re.fullmatch(r'(?:[0-9]{13}[A-Za-z]|[0-9]{3}-[0-9]{6}-[0-9]{4}[A-Za-z])',value):
        raise ErrorValidacion('cedula','Cédula: usa 000-000000-0000A, con 13 dígitos y una letra final de A a Z.')
    compact=value.replace('-','').upper()
    try:
        # El documento solo indica dos cifras del año. Se comprueba el calendario,
        # sin inventar una edad ni certificar que el número fue emitido por el CSE.
        date(2000+int(compact[7:9]),int(compact[5:7]),int(compact[3:5]))
    except ValueError:
        raise ErrorValidacion('cedula','Cédula: los seis dígitos centrales deben ser una fecha de nacimiento válida (DDMMAA).') from None
    return compact[:3]+'-'+compact[3:9]+'-'+compact[9:]

def normalizar_telefono(value):
    value=str(value).strip()
    if not re.fullmatch(r'[0-9]{8,15}',value):
        raise ErrorValidacion('telefono','Teléfono: ingresa de 8 a 15 dígitos, sin letras, espacios ni signos.')
    return value

def normalizar_correo(value,requerido=False):
    value=str(value or '').strip().lower()
    patron=r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+@[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+"
    if not value and not requerido:return ''
    if len(value)>160 or not re.fullmatch(patron,value) or '..' in value or value.startswith('.') or '.@' in value:
        raise ErrorValidacion('correo','Correo: ingresa una dirección válida, por ejemplo nombre@correo.com.')
    return value

def normalizar_persona(cedula,nombres,apellidos,telefono,correo=''):
    return dict(cedula=normalizar_cedula(cedula),nombres=normalizar_nombre(nombres),apellidos=normalizar_nombre(apellidos,'apellidos'),telefono=normalizar_telefono(telefono),correo=normalizar_correo(correo))


def validar_numero_texto(value,campo):
    texto=str(value).strip()
    regla=REGLAS[campo]
    if not re.fullmatch(regla['pattern'],texto):raise ErrorValidacion(campo,regla['ayuda'])
    return texto

def validar_plazo(value):
    plazo=int(validar_numero_texto(value,'meses'))
    if not 1<=plazo<=600:raise ErrorValidacion('meses',REGLAS['meses']['ayuda'])
    return plazo
