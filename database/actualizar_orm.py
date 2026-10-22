"""Migración aditiva: crea empleados, comprobantes y recuperación asistida; nunca modifica préstamos ni cuotas existentes."""
import sys
import json
from hashlib import sha256
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect,text
from crece.infraestructura.base_datos import obtener_motor
from crece.infraestructura.modelos import Empleado,ComprobantePago,RecuperacionContrasena

def instantanea(engine):
    resultado={}
    with engine.connect() as connection:
        for tabla in ('clientes','prestamos','cuotas','pagos'):
            rows=[dict(row) for row in connection.execute(text('SELECT * FROM '+tabla+' ORDER BY id')).mappings()]
            contenido=json.dumps(rows,sort_keys=True,ensure_ascii=False,default=str).encode('utf-8')
            resultado[tabla]=dict(registros=len(rows),sha256=sha256(contenido).hexdigest())
    return resultado

def verificar(aplicar=False):
    engine=obtener_motor()
    inspector=inspect(engine)
    tables=set(inspector.get_table_names())
    required={'usuarios','clientes','prestamos','cuotas','pagos','bitacora_auditoria'}
    if not required<=tables: raise ValueError('Faltan tablas del esquema base. Aplica schema.sql antes de esta migración.')
    columns={col['name'] for col in inspector.get_columns('usuarios')}
    if not {'requiere_cambio_contrasena','actualizado_en'}<=columns:
        raise ValueError('Primero debe aplicarse la migración de seguridad existente.')
    if aplicar:
        antes=instantanea(engine)
        Empleado.__table__.create(engine,checkfirst=True)
        ComprobantePago.__table__.create(engine,checkfirst=True)
        RecuperacionContrasena.__table__.create(engine,checkfirst=True)
        if 'version_sesion' not in columns:
            with engine.begin() as connection:connection.execute(text('ALTER TABLE usuarios ADD COLUMN version_sesion INT NOT NULL DEFAULT 1'))
        despues=instantanea(engine)
        resultado=dict(migracion='RECUPERACION_ASISTIDA',historial_sin_cambios=antes==despues,antes=antes,despues=despues)
        (Path(__file__).parent/'verificacion_migracion_recuperacion.json').write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding='utf-8')
        if antes!=despues:raise ValueError('La instantánea cambió durante la operación; revisa si hubo operaciones concurrentes.')
        print('Migración aditiva lista. Clientes, préstamos, cuotas y pagos existentes no se modificaron.')
    else:
        for tabla in ('empleados','comprobantes_pago','recuperaciones_contrasena'):
            print('Tabla '+tabla+': '+('existente' if tabla in tables else 'pendiente; ejecutar con --aplicar'))

if __name__=='__main__':
    try: verificar('--aplicar' in sys.argv)
    except Exception:
        print('No se pudo verificar/aplicar la migración. Comprueba MySQL y los permisos; no se alteraron préstamos ni cuotas.')
        raise SystemExit(1)
