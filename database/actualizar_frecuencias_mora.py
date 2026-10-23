"""Migración aditiva; conserva y verifica cada columna previa de la cartera."""
import sys,json
from pathlib import Path
from hashlib import sha256
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect,text
from crece.infraestructura.base_datos import obtener_motor

CAMBIOS={
 'prestamos':{'frecuencia':"VARCHAR(12) NOT NULL DEFAULT 'MENSUAL'",'recargo_porcentaje':'DECIMAL(5,2) NOT NULL DEFAULT 0','gracia_horas':'INT NOT NULL DEFAULT 72'},
 'cuotas':{'recargo_pagado':'DECIMAL(14,2) NOT NULL DEFAULT 0'},
 'pagos':{'monto_recargo':'DECIMAL(14,2) NOT NULL DEFAULT 0'}}

def instantanea(engine,columnas):
    resultado={}
    with engine.connect() as conn:
        for tabla,cols in columnas.items():
            consulta='SELECT '+','.join('`'+c+'`' for c in cols)+' FROM `'+tabla+'` ORDER BY id'
            rows=[dict(row) for row in conn.execute(text(consulta)).mappings()]
            contenido=json.dumps(rows,sort_keys=True,ensure_ascii=False,default=str).encode('utf-8')
            resultado[tabla]=dict(registros=len(rows),sha256=sha256(contenido).hexdigest())
    return resultado

def aplicar():
    engine=obtener_motor();inspector=inspect(engine)
    columnas={t:[c['name'] for c in inspector.get_columns(t)] for t in ('clientes','prestamos','cuotas','pagos')}
    antes=instantanea(engine,columnas)
    for tabla,cambios in CAMBIOS.items():
        existentes={c['name'] for c in inspect(engine).get_columns(tabla)}
        for nombre,tipo in cambios.items():
            if nombre not in existentes:
                with engine.begin() as conn:conn.execute(text(f'ALTER TABLE `{tabla}` ADD COLUMN `{nombre}` {tipo}'))
    despues=instantanea(engine,columnas)
    resultado=dict(migracion='FRECUENCIAS_MORA',columnas_verificadas=columnas,historial_sin_cambios=antes==despues,antes=antes,despues=despues)
    (Path(__file__).parent/'verificacion_migracion_frecuencias.json').write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding='utf-8')
    if antes!=despues:raise ValueError('Cambió la cartera durante la migración. Revisa operaciones concurrentes.')
    print('Migración verificada: contratos y pagos anteriores conservados; sin recargos retroactivos.')

if __name__=='__main__':
    if '--aplicar' not in sys.argv:print('Ejecuta con --aplicar para añadir las columnas de frecuencias y mora.')
    else:
        try:aplicar()
        except Exception:
            print('No se pudo completar o verificar la migración. Revisa MySQL y los permisos.');raise SystemExit(1)
