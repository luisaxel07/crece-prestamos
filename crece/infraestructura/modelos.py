"""Entidades SQLAlchemy 2.0 sobre las tablas existentes, sin recrear datos."""
from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey, JSON, UniqueConstraint, LargeBinary
from sqlalchemy.orm import DeclarativeBase, mapped_column, relationship, deferred
from sqlalchemy.dialects.mysql import BIGINT, MEDIUMBLOB

PK=BigInteger().with_variant(BIGINT(unsigned=True),'mysql')
DINERO=Numeric(14,2)

class Base(DeclarativeBase): pass

class Usuario(Base):
    __tablename__='usuarios'
    id=mapped_column(PK,primary_key=True,autoincrement=True)
    nombre_usuario=mapped_column(String(60),unique=True,nullable=False)
    hash_contrasena=mapped_column(String(255),nullable=False)
    version_sesion=mapped_column(Integer,nullable=False,default=1,server_default='1')
    rol=mapped_column(String(20),nullable=False)
    activo=mapped_column(Boolean,nullable=False,default=True)
    requiere_cambio_contrasena=mapped_column(Boolean,nullable=False,default=False)
    ultimo_acceso_en=mapped_column(DateTime)
    creado_en=mapped_column(DateTime,default=datetime.now,nullable=False)
    actualizado_en=mapped_column(DateTime,default=datetime.now,onupdate=datetime.now)
    empleado=relationship('Empleado',back_populates='usuario',uselist=False)

class Empleado(Base):
    __tablename__='empleados'
    id=mapped_column(PK,primary_key=True,autoincrement=True)
    usuario_id=mapped_column(PK,ForeignKey('usuarios.id'),unique=True,nullable=False)
    cedula=mapped_column(String(30),unique=True,nullable=False)
    nombres=mapped_column(String(80),nullable=False)
    apellidos=mapped_column(String(80),nullable=False)
    telefono=mapped_column(String(25),nullable=False)
    correo=mapped_column(String(160))
    cargo=mapped_column(String(80),nullable=False,default='Asesor de crédito')
    creado_en=mapped_column(DateTime,default=datetime.now,nullable=False)
    usuario=relationship('Usuario',back_populates='empleado')

class Cliente(Base):
    __tablename__='clientes'
    id=mapped_column(PK,primary_key=True,autoincrement=True)
    usuario_id=mapped_column(PK,ForeignKey('usuarios.id'),unique=True)
    cedula=mapped_column(String(30),unique=True,nullable=False)
    nombres=mapped_column(String(80),nullable=False)
    apellidos=mapped_column(String(80),nullable=False)
    telefono=mapped_column(String(25),nullable=False)
    correo=mapped_column(String(160),unique=True)
    direccion=mapped_column(String(255))
    estado=mapped_column(String(20),nullable=False,default='ACTIVO')
    creado_en=mapped_column(DateTime,default=datetime.now,nullable=False)
    prestamos=relationship('Prestamo',back_populates='cliente')
    usuario=relationship('Usuario')
    @property
    def nombre(self): return f'{self.nombres} {self.apellidos}'

class Prestamo(Base):
    __tablename__='prestamos'
    id=mapped_column(PK,primary_key=True,autoincrement=True)
    cliente_id=mapped_column(PK,ForeignKey('clientes.id'),nullable=False)
    creado_por=mapped_column(PK,ForeignKey('usuarios.id'),nullable=False)
    monto_principal=mapped_column(DINERO,nullable=False)
    tasa_interes_anual=mapped_column(Numeric(7,4),nullable=False)
    plazo_meses=mapped_column(Integer,nullable=False)
    cuota_mensual=mapped_column(DINERO,nullable=False)
    frecuencia=mapped_column(String(12),nullable=False,default='MENSUAL',server_default='MENSUAL')
    tipo_credito=mapped_column(String(20),nullable=False,default='GENERAL',server_default='GENERAL')
    metodo_interes=mapped_column(String(12),nullable=False,default='FRANCES',server_default='FRANCES')
    recargo_porcentaje=mapped_column(Numeric(5,2),nullable=False,default=Decimal('0'),server_default='0')
    gracia_horas=mapped_column(Integer,nullable=False,default=72,server_default='72')
    fecha_desembolso=mapped_column(Date,nullable=False)
    fecha_primera_cuota=mapped_column(Date,nullable=False)
    estado=mapped_column(String(20),nullable=False,default='ACTIVO')
    notas=mapped_column(String(500))
    creado_en=mapped_column(DateTime,default=datetime.now,nullable=False)
    cliente=relationship('Cliente',back_populates='prestamos')
    creador=relationship('Usuario')
    cuotas=relationship('CuotaModel',back_populates='prestamo',order_by='CuotaModel.numero_cuota')
    @property
    def tasa_mensual(self): return self.tasa_interes_anual/Decimal('12')
    @property
    def tasa_periodica(self):
        from crece.nucleo.amortizacion import tasa_por_periodo
        return tasa_por_periodo(self.tasa_mensual,self.frecuencia)
    @property
    def numero_cuotas(self):return self.plazo_meses

class CuotaModel(Base):
    __tablename__='cuotas'
    __table_args__=(UniqueConstraint('prestamo_id','numero_cuota',name='uq_cuotas_numero'),)
    id=mapped_column(PK,primary_key=True,autoincrement=True)
    prestamo_id=mapped_column(PK,ForeignKey('prestamos.id'),nullable=False)
    numero_cuota=mapped_column(Integer,nullable=False)
    fecha_vencimiento=mapped_column(Date,nullable=False)
    saldo_inicial=mapped_column(DINERO,nullable=False)
    cuota_programada=mapped_column(DINERO,nullable=False)
    abono_capital=mapped_column(DINERO,nullable=False)
    interes=mapped_column(DINERO,nullable=False)
    monto_pagado=mapped_column(DINERO,nullable=False,default=Decimal('0'))
    recargo_pagado=mapped_column(DINERO,nullable=False,default=Decimal('0'),server_default='0')
    pagado_en=mapped_column(DateTime)
    estado=mapped_column(String(20),nullable=False,default='PENDIENTE')
    prestamo=relationship('Prestamo',back_populates='cuotas')
    pagos=relationship('Pago',back_populates='cuota')
    @property
    def saldo(self):
        from crece.nucleo.mora import detalle_mora
        return detalle_mora(self)['saldo_total']

class Pago(Base):
    __tablename__='pagos'
    id=mapped_column(PK,primary_key=True,autoincrement=True)
    cuota_id=mapped_column(PK,ForeignKey('cuotas.id'),nullable=False)
    registrado_por=mapped_column(PK,ForeignKey('usuarios.id'))
    monto=mapped_column(DINERO,nullable=False)
    monto_recargo=mapped_column(DINERO,nullable=False,default=Decimal('0'),server_default='0')
    fecha_pago=mapped_column(DateTime,nullable=False,default=datetime.now)
    metodo=mapped_column(String(20),nullable=False)
    referencia=mapped_column(String(100))
    estado=mapped_column(String(30),nullable=False,default='CONFIRMADO')
    notas=mapped_column(String(500))
    creado_en=mapped_column(DateTime,default=datetime.now,nullable=False)
    cuota=relationship('CuotaModel',back_populates='pagos')
    comprobante=relationship('ComprobantePago',back_populates='pago',uselist=False,lazy='selectin',cascade='all, delete-orphan')

class ComprobantePago(Base):
    __tablename__='comprobantes_pago'
    id=mapped_column(PK,primary_key=True,autoincrement=True)
    pago_id=mapped_column(PK,ForeignKey('pagos.id'),nullable=False,unique=True)
    tipo_mime=mapped_column(String(40),nullable=False)
    contenido=deferred(mapped_column(LargeBinary().with_variant(MEDIUMBLOB(),'mysql'),nullable=False))
    sha256=mapped_column(String(64),nullable=False)
    creado_en=mapped_column(DateTime,default=datetime.now,nullable=False)
    pago=relationship('Pago',back_populates='comprobante')

class RecuperacionContrasena(Base):
    __tablename__='recuperaciones_contrasena'
    id=mapped_column(PK,primary_key=True,autoincrement=True)
    usuario_id=mapped_column(PK,ForeignKey('usuarios.id'),nullable=False,index=True)
    codigo_hash=mapped_column(String(255),nullable=False)
    vence_en=mapped_column(DateTime,nullable=False)
    usado_en=mapped_column(DateTime)
    creado_en=mapped_column(DateTime,default=datetime.now,nullable=False)

class Auditoria(Base):
    __tablename__='bitacora_auditoria'
    id=mapped_column(PK,primary_key=True,autoincrement=True)
    usuario_actor_id=mapped_column(PK,ForeignKey('usuarios.id'))
    tipo_entidad=mapped_column(String(40),nullable=False)
    entidad_id=mapped_column(PK,nullable=False)
    accion=mapped_column(String(60),nullable=False)
    detalle=mapped_column(JSON)
    creado_en=mapped_column(DateTime,default=datetime.now,nullable=False)
