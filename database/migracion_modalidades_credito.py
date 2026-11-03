"""Adds loan product and interest method columns without rewriting existing schedules."""
import sys
from hashlib import sha256
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sqlalchemy import inspect,text
from crece.infraestructura.base_datos import obtener_motor


def digest(engine,table,columns):
    names=','.join(f'`{name}`' for name in columns)
    with engine.connect() as conn:
        rows=[tuple(row) for row in conn.execute(text(f'SELECT {names} FROM `{table}` ORDER BY `id`')).all()]
    return sha256(repr(rows).encode('utf-8')).hexdigest()


def aplicar():
    engine=obtener_motor()
    inspector=inspect(engine)
    columns=[c['name'] for c in inspector.get_columns('prestamos')]
    cuotas_columns=[c['name'] for c in inspector.get_columns('cuotas')]
    before=(digest(engine,'prestamos',columns),digest(engine,'cuotas',cuotas_columns))
    changes={
        'tipo_credito':"VARCHAR(20) NOT NULL DEFAULT 'GENERAL'",
        'metodo_interes':"VARCHAR(12) NOT NULL DEFAULT 'FRANCES'",
    }
    for name,definition in changes.items():
        if name not in {c['name'] for c in inspect(engine).get_columns('prestamos')}:
            with engine.begin() as conn:
                conn.execute(text(f'ALTER TABLE `prestamos` ADD COLUMN `{name}` {definition}'))
    if (digest(engine,'prestamos',columns),digest(engine,'cuotas',cuotas_columns))!=before:
        raise RuntimeError('Existing loan data changed during migration; stop and inspect the database.')
    print('Migration verified: existing loans and installment schedules were preserved.')


if __name__=='__main__':
    if '--aplicar' not in sys.argv:
        print('Review the project backup, then run with --aplicar to add the two loan columns.')
    else:
        try:
            aplicar()
        except Exception as error:
            print(f'Migration failed: {error}')
            raise SystemExit(1)
