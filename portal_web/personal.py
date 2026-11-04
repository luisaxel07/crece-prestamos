"""Área web del personal. Los casos de uso y sus transacciones son los de escritorio."""
from datetime import date, timedelta
from decimal import Decimal, DecimalException, InvalidOperation
from io import BytesIO
from tempfile import TemporaryDirectory
from pathlib import Path
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file, url_for
from crece.servicios.comprobantes import obtener_comprobante_pago,ErrorComprobante
from crece.servicios import gestion as servicios, cuentas_orm as cuentas
from crece.servicios.reportes import obtener_reporte, limitar_reporte
from crece.servicios import reportes as servicios_reportes
from crece.infraestructura.exportadores import exportar_pdf, exportar_excel
from crece.infraestructura.base_datos import ErrorConexionBaseDatos
from crece.nucleo.validaciones import REGLAS, ErrorValidacion, validar_numero_texto, validar_plazo
from crece.nucleo.amortizacion import calcular_tabla_credito,tasa_por_periodo,FRECUENCIAS,TASAS_TIPO_CREDITO,TIPOS_CREDITO
from portal_web.seguridad_web import requiere_personal

from crece.servicios.permisos import ErrorPermiso

personal=Blueprint('personal',__name__,url_prefix='/gestion')

@personal.errorhandler(ErrorConexionBaseDatos)
def sin_conexion(error):
    return render_template('error.html',codigo=503,mensaje='No se pudo completar la operación. Comprueba la conexión e inténtalo nuevamente.'),503

@personal.errorhandler(ErrorPermiso)
def permiso_revocado(error):
    abort(403,str(error))

@personal.errorhandler(ValueError)
def dato_invalido(error):
    return render_template('error.html',codigo=400,mensaje=str(error)),400

def enlace(texto,endpoint,**params): return dict(texto=texto,url=url_for('personal.'+endpoint,**params))
def campo(nombre,etiqueta,tipo='text',opciones=None,requerido=True,**attrs):
    regla=REGLAS.get(nombre,{})
    attrs={**attrs,**{k:regla[k] for k in ('placeholder','maxlength','pattern') if k in regla}}
    if nombre=='telefono':attrs['inputmode']='numeric'
    return dict(nombre=nombre,etiqueta=etiqueta,tipo=tipo,opciones=opciones or [],requerido=requerido,attrs=attrs,ayuda=regla.get('ayuda',''))
def texto(name): return request.form.get(name,'').strip()
def numero(name):
    try: value=Decimal(validar_numero_texto(texto(name),name))
    except InvalidOperation: raise ValueError('Ingresa un número válido.')
    if not value.is_finite() or abs(value)>Decimal('999999999999.99'): raise ValueError('El importe o la tasa exceden el rango permitido.')
    return value

def tabla(titulo,columnas,datos,acciones=None,nuevo=None,filtrar=True,**extra):
    query=request.args.get('q','').strip()[:160]
    if filtrar and query:
        datos=[d for d in datos if query.casefold() in ' '.join(str(d.get(c[0],'')) for c in columnas).casefold()]
    total=len(datos)
    try: pagina=max(1,int(request.args.get('pagina',1)))
    except ValueError: pagina=1
    pagina=min(pagina,max(1,(total+39)//40))
    return render_template('personal/tabla.html',titulo=titulo,columnas=columnas,datos=datos[(pagina-1)*40:pagina*40],acciones=acciones or (lambda d:[]),nuevo=nuevo,q=query,total=total,pagina=pagina,paginas=max(1,(total+39)//40),filtrar=filtrar,**extra)

def formulario(titulo,campos,guardar,datos=None,volver=None,nota='',plan=None,adjunto=None,sin_comprobante=False):
    valores=datos or {}; error=None;campo_error=None
    if request.method=='POST':
        valores={c['nombre']:request.form.get(c['nombre'],'') for c in campos if c['tipo']!='password'}
        try:
            for c in campos:
                value=request.form.get(c['nombre'],'')
                if c['requerido'] and not value.strip(): raise ValueError('Completa los campos obligatorios.')
                if c['opciones'] and value not in [str(o[0]) for o in c['opciones']]: raise ValueError('Selecciona una opción válida.')
                if len(value)>int(c['attrs'].get('maxlength',500)): raise ValueError('El texto excede la longitud permitida.')
            destino=guardar()
            if destino:
                flash('Operación completada correctamente.','exito')
                return redirect(destino)
        except ErrorPermiso:
            raise
        except (ValueError,DecimalException,OverflowError) as exc:
            error=str(exc) or 'Revisa los datos ingresados.'
            campo_error=getattr(exc,'campo',None)
    return render_template('personal/formulario.html',titulo=titulo,campos=campos,valores=valores,error=error,volver=volver or url_for('personal.inicio'),nota=nota,plan=plan,campo_error=campo_error,adjunto=adjunto,sin_comprobante=sin_comprobante),400 if error else 200

PERSONA=[campo('cedula','Cédula',maxlength=30),campo('nombres','Nombres',maxlength=80),campo('apellidos','Apellidos',maxlength=80),campo('telefono','Teléfono','tel',maxlength=25),campo('correo','Correo electrónico','email',requerido=False,maxlength=160)]
COL_PRESTAMOS=[('codigo','Préstamo','texto'),('cliente','Cliente','texto'),('monto_principal','Capital','moneda'),('interes_cuota_inicial','Tasa del período equivalente (C$)','moneda'),('frecuencia','Frecuencia','texto'),('saldo_pendiente','Saldo','moneda'),('estado','Estado','estado')]
def codigos(rows): return [dict(d,codigo=f"PR-{d['id']:05d}") for d in rows]

@personal.route('/')
@requiere_personal()
def inicio():
    return render_template('personal/inicio.html',resumen=servicios.obtener_resumen(),actividad=servicios.obtener_actividad_reciente())

@personal.route('/clientes')
@requiere_personal()
def clientes():
    return tabla('Clientes',[('cedula','Cédula','texto'),('nombre','Cliente','texto'),('telefono','Teléfono','texto'),('correo','Correo','texto'),('estado','Estado','estado')],servicios.listar_clientes(),lambda d:[enlace('Ver ficha','cliente',id=d['id']),enlace('Editar','cliente_form',id=d['id'])]+([enlace('Eliminar cliente','baja',tipo='cliente',id=d['id'])] if g.usuario_actual['rol']=='ADMINISTRADOR' else []),enlace('Nuevo cliente','cliente_form'))

@personal.route('/historial-cuotas')
@requiere_personal()
def historial_cuotas():
    clientes=servicios.listar_clientes()
    def acciones(c):
        return [
            enlace('Ver historial','reportes',cliente_id=c['id']),
            enlace('Descargar PDF','exportar',formato='pdf',cliente_id=c['id']),
            enlace('Descargar Excel','exportar',formato='xlsx',cliente_id=c['id']),
        ]
    return tabla('Historial de cuotas por cliente',[('nombre','Cliente','texto'),('cedula','Cédula','texto'),('estado','Estado','estado')],clientes,acciones)
@personal.route('/clientes/nuevo',methods=['GET','POST'])
@personal.route('/clientes/<int:id>/editar',methods=['GET','POST'])
@requiere_personal()
def cliente_form(id=None):
    datos=servicios.obtener_cliente(id) if id else {}
    campos=PERSONA+[campo('direccion','Dirección','textarea',requerido=False,maxlength=255)]
    if id: campos=campos+[campo('estado','Estado','select',[(s,s.capitalize()) for s in ('ACTIVO','INACTIVO','BLOQUEADO')])]
    def guardar():
        data={k:texto(k) for k in ('cedula','nombres','apellidos','telefono','correo','direccion')}
        if id: servicios.actualizar_cliente(id,**data,estado=texto('estado'));nuevo=id
        else: nuevo=servicios.registrar_cliente(**data)
        return url_for('personal.cliente',id=nuevo)
    return formulario('Editar cliente' if id else 'Nuevo cliente',campos,guardar,datos,url_for('personal.clientes'))

@personal.route('/clientes/<int:id>')
@requiere_personal()
def cliente(id):
    c=servicios.obtener_cliente(id)
    return tabla(c['nombre'],COL_PRESTAMOS,codigos(obtener_reporte(cliente_id=id)['prestamos']),lambda d:[enlace('Ver préstamo','prestamo',id=d['id'])],enlace('Emitir préstamo','prestamo_form',cliente_id=id),filtrar=False,detalles=[('Cédula',c['cedula']),('Teléfono',c['telefono']),('Correo',c['correo']),('Dirección',c['direccion']),('Estado',c['estado']),('Acceso web','Cuenta vinculada' if c['usuario_id'] else 'Sin cuenta')],enlaces=[enlace('Editar datos','cliente_form',id=id),enlace('Reporte del cliente','reportes',cliente_id=id)]+([] if c['usuario_id'] else [enlace('Crear acceso del cliente','cuenta_cliente',id=id)])+([enlace('Eliminar / inactivar cliente','baja',tipo='cliente',id=id)] if g.usuario_actual['rol']=='ADMINISTRADOR' else []))

@personal.route('/clientes/<int:id>/cuenta',methods=['GET','POST'])
@requiere_personal()
def cuenta_cliente(id):
    c=servicios.obtener_cliente(id)
    def guardar():
        cuentas.crear_cuenta_cliente(id,texto('correo'),request.form.get('contrasena',''))
        return url_for('personal.cliente',id=id)
    return formulario('Crear acceso del cliente',[campo('correo','Correo electrónico','email',maxlength=160),campo('contrasena','Contraseña inicial','password',minlength=10,maxlength=128)],guardar,c,url_for('personal.cliente',id=id),nota='La cuenta tendrá acceso exclusivamente a los préstamos de este cliente. Entrega sus credenciales por un canal privado.')

@personal.route('/prestamos')
@requiere_personal()
def prestamos():
    return tabla('Préstamos',COL_PRESTAMOS,codigos(servicios.listar_prestamos()),lambda d:[enlace('Ver detalle','prestamo',id=d['id'])],enlace('Emitir préstamo','prestamo_form'))

def tasa_de_modalidad(tipo_credito):
    tipo=str(tipo_credito).strip().upper()
    if tipo not in TASAS_TIPO_CREDITO: raise ValueError('Selecciona Asalariado o Credito comercial.')
    return tipo,TASAS_TIPO_CREDITO[tipo]

def campos_plan():
    opciones=[(key,f"{label} - {TASAS_TIPO_CREDITO[key]}% mensual, interes plano") for key,label in TIPOS_CREDITO.items()]
    return [campo('tipo_credito','Modalidad','select',opciones),campo('monto','Capital (C$)','number',min='0.01',step='0.01'),campo('frecuencia','Frecuencia de pago','select',list(FRECUENCIAS.items())),campo('meses','Numero de cuotas','number',min=1,max=600,step=1),campo('fecha_primera_cuota','Primera cuota','date')]

@personal.route('/prestamos/nuevo',methods=['GET','POST'])
@requiere_personal()
def prestamo_form():
    clientes=servicios.listar_clientes_para_prestamo()
    campos=[campo('cliente_id','Cliente','select',[(c['id'],c['nombre']+' | '+c['cedula']) for c in clientes])]+campos_plan()+[campo('fecha_desembolso','Desembolso','date')]
    def guardar():
        tipo,tasa=tasa_de_modalidad(texto('tipo_credito'))
        id=servicios.registrar_prestamo_periodico(int(texto('cliente_id')),numero('monto'),tasa,validar_plazo(texto('meses')),date.fromisoformat(texto('fecha_desembolso')),date.fromisoformat(texto('fecha_primera_cuota')),texto('frecuencia'),tipo_credito=tipo,metodo_interes='PLANO')
        return url_for('personal.prestamo',id=id)
    defaults=dict(cliente_id=request.args.get('cliente_id',''),tipo_credito='ASALARIADO',frecuencia='MENSUAL',fecha_desembolso=date.today().isoformat())
    nota='Asalariado: 12% mensual. Credito comercial: 14% mensual. El interes plano se calcula en cada periodo sobre el capital inicial y se suma al abono de capital. El capital se divide entre las cuotas. Las frecuencias quincenal, semanal y diaria convierten la tasa mensual al periodo correspondiente. Los contratos ya emitidos conservan sus condiciones.'
    return formulario('Emitir prestamo',campos,guardar,defaults,url_for('personal.prestamos'),nota=nota)

@personal.route('/prestamos/<int:id>')
@requiere_personal()
def prestamo(id):
    p=obtener_reporte(prestamo_id=id)['prestamos'][0]
    columnas=[('numero_cuota','Cuota','texto'),('fecha_vencimiento','Vence','fecha'),('interes',f'Tasa del periodo ({p["tasa_periodica"]:.6f} %) · equivalente C$','moneda'),('frecuencia','Frecuencia','texto'),('saldo_inicial','Capital inicial','moneda'),('abono_capital','Capital','moneda'),('cuota_programada','Programada','moneda'),('monto_pagado','Pagado ordinario','moneda'),('recargo','Recargo total','moneda'),('recargo_pagado','Recargo pagado','moneda'),('recargo_pendiente','Mora pendiente','moneda'),('saldo','Pendiente total','moneda'),('estado','Estado','estado')]
    acciones=lambda d: [enlace('Cobrar','cobro',cuota_id=d['id'])] if d['saldo']>0 and p['estado'] not in ('CANCELADO','BORRADOR') else []
    enlaces=[enlace('Cotizar liquidacion anticipada','liquidacion',id=id),enlace('Editar notas','notas',id=id),enlace('PDF / Imprimir','exportar',formato='pdf',prestamo_id=id,vista=1),enlace('Excel','exportar',formato='xlsx',prestamo_id=id)]
    if g.usuario_actual['rol']=='ADMINISTRADOR': enlaces.append(enlace('Anular préstamo','baja',tipo='prestamo',id=id))
    return tabla(f'PR-{id:05d} · {p["cliente"]}',columnas,p['cuotas'],acciones,filtrar=False,detalles=[('Modalidad',TIPOS_CREDITO.get(p['tipo_credito'],p['tipo_credito'])),('Metodo de interes','Plano sobre capital inicial' if p['metodo_interes']=='PLANO' else 'Frances sobre saldo'),('Capital',f'C$ {p["monto_principal"]:,.2f}'),('Tasa mensual',f'{p["tasa_mensual"]:.4f} %'),('Frecuencia',p['frecuencia_texto']),('Tasa del período (%)',f'{p["tasa_periodica"]:.6f} %'),('Plazo',f'{p["numero_cuotas"]} cuotas'),('Condiciones de mora',f'{p["recargo_porcentaje"]} % único sobre capital pendiente por cuota, tras {p["gracia_horas"]} horas desde el final del vencimiento' if p['recargo_porcentaje'] else 'Sin recargo: contrato anterior'),('Estado',p['estado']),('Emitido por',p['empleado']),('Notas',p['notas'])],enlaces=enlaces)


@personal.route('/prestamos/<int:id>/liquidacion',methods=['GET','POST'])
@requiere_personal()
def liquidacion(id):
    fecha_texto=request.values.get('fecha',date.today().isoformat())
    cotizacion=None; error=None
    if request.method=='POST':
        try:
            fecha=date.fromisoformat(fecha_texto)
            cotizacion=servicios_reportes.cotizar_liquidacion(id,fecha)
        except (ValueError,DecimalException) as exc:
            error=str(exc)
    return render_template('personal/liquidacion.html',id=id,fecha=fecha_texto,cotizacion=cotizacion,error=error,volver=url_for('personal.prestamo',id=id))

@personal.route('/prestamos/<int:id>/notas',methods=['GET','POST'])
@requiere_personal()
def notas(id):
    p=obtener_reporte(prestamo_id=id)['prestamos'][0]
    def guardar():
        servicios.actualizar_prestamo(id,texto('notas'))
        return url_for('personal.prestamo',id=id)
    return formulario('Notas del préstamo',[campo('notas','Observaciones','textarea',requerido=False,maxlength=500)],guardar,p,url_for('personal.prestamo',id=id))

@personal.route('/cobros')
@requiere_personal()
def cobros():
    return tabla('Cuotas por cobrar',[('cliente','Cliente','texto'),('prestamo_id','Préstamo','texto'),('numero_cuota','Cuota','texto'),('fecha_vencimiento','Vence','fecha'),('interes','Tasa del período equivalente (C$)','moneda'),('frecuencia','Frecuencia','texto'),('recargo_pendiente','Mora pendiente','moneda'),('saldo','Pendiente total','moneda'),('estado','Estado','estado')],servicios.listar_cuotas_cobro(),lambda d:[enlace('Registrar cobro','cobro',cuota_id=d['id'])],enlaces=[enlace('Pagos y solicitudes','pagos')])

@personal.route('/cobros/<int:cuota_id>',methods=['GET','POST'])
@requiere_personal()
def cobro(cuota_id):
    cuotas=servicios.listar_cuotas_cobro()
    q=next((item for item in cuotas if item['id']==cuota_id),None)
    if not q: abort(404)
    siguientes=[item for item in cuotas if item['prestamo_id']==q['prestamo_id'] and item['numero_cuota']>=q['numero_cuota']]
    maximo=sum((item['saldo'] for item in siguientes),Decimal('0'))
    def guardar():
        servicios.registrar_cobro(cuota_id,numero('monto'),texto('metodo'),texto('referencia'))
        return url_for('personal.prestamo',id=q['prestamo_id'])
    nota=(f"{q['cliente']} | Cuota {q['numero_cuota']} | Pendiente C$ {q['saldo']:,.2f} (recargo pendiente: C$ {q['recargo_pendiente']:,.2f}). "
          f"Puedes recibir hasta C$ {maximo:,.2f}; el excedente se aplicara por orden a las cuotas siguientes del mismo prestamo.")
    return formulario('Registrar cobro',[campo('monto','Importe recibido (C$)','number',step='0.01',min='0.01',max=str(maximo)),campo('metodo','Metodo','select',[(s,s.capitalize()) for s in ('EFECTIVO','TRANSFERENCIA','TARJETA')]),campo('referencia','Referencia','text',requerido=False,maxlength=100)],guardar,dict(monto=q['saldo']),url_for('personal.cobros'),nota=nota)

@personal.route('/pagos')
@requiere_personal()
def pagos():
    return tabla('Pagos y solicitudes',[('cliente','Cliente','texto'),('numero_cuota','Cuota','texto'),('fecha_pago','Fecha','fecha'),('monto','Importe total','moneda'),('monto_recargo','Aplicado a recargo','moneda'),('metodo','Método','texto'),('referencia','Referencia','texto'),('tiene_comprobante','Comprobante','comprobante'),('estado','Estado','estado')],servicios.listar_pagos(),lambda d:[enlace('Revisar','pago',id=d['id'])])

@personal.route('/pagos/<int:id>',methods=['GET','POST'])
@requiere_personal()
def pago(id):
    p=next((p for p in servicios.listar_pagos() if p['id']==id),None)
    if not p: abort(404)
    opciones=[('EDITAR_REFERENCIA','Actualizar referencia')]
    if p['estado']=='PENDIENTE_VERIFICACION': opciones=[('CONFIRMAR','Confirmar pago recibido'),('RECHAZAR','Rechazar solicitud')]+opciones
    if p['estado']=='CONFIRMADO' and g.usuario_actual['rol']=='ADMINISTRADOR': opciones.append(('ANULAR','Anular pago (requiere motivo)'))
    def guardar():
        accion=texto('accion')
        if accion=='ANULAR' and g.usuario_actual['rol']!='ADMINISTRADOR': abort(403)
        servicios.resolver_pago(id,accion,texto('motivo'))
        return url_for('personal.pagos')
    return formulario('Revisar pago',[campo('accion','Operación','select',opciones),campo('motivo','Referencia nueva o motivo','textarea',requerido=False,maxlength=100)],guardar,volver=url_for('personal.pagos'),adjunto=enlace("Abrir comprobante","comprobante",id=id) if p["tiene_comprobante"] else None,sin_comprobante=p["metodo"]=="PAGO_CLIENTE" and not p["tiene_comprobante"],nota=f"{p['cliente']} · C$ {p['monto']:,.2f} · {p['estado']} · Referencia: {p['referencia'] or 'Sin referencia'}. Confirma solo después de comprobar el ingreso.")

@personal.route('/pagos/<int:id>/comprobante')
@requiere_personal()
def comprobante(id):
    try:datos=obtener_comprobante_pago(id)
    except ErrorComprobante:abort(404)
    return send_file(BytesIO(datos['contenido']),mimetype=datos['tipo_mime'],download_name=datos['nombre'],as_attachment=request.args.get('descargar')=='1')

@personal.route('/simulador',methods=['GET','POST'])
@requiere_personal()
def simulador():
    plan=[];error=None;values={}
    if request.method=='POST':
        values=request.form
        try:
            tipo,tasa=tasa_de_modalidad(texto('tipo_credito'))
            frecuencia=texto('frecuencia')
            plan=calcular_tabla_credito(numero('monto'),tasa,validar_plazo(texto('meses')),date.fromisoformat(texto('fecha_primera_cuota')),frecuencia,metodo_interes='PLANO')
        except (ValueError,DecimalException,OverflowError) as exc: error=str(exc)
    defaults=values or {'tipo_credito':'ASALARIADO','frecuencia':'MENSUAL'}
    tipo_default=defaults.get('tipo_credito','ASALARIADO')
    return render_template('personal/formulario.html',titulo='Simulador de prestamo',campos=campos_plan(),valores=defaults,error=error,volver=url_for('personal.prestamos'),plan=plan,tasa_periodica=tasa_por_periodo(tasa,defaults.get('frecuencia','MENSUAL')) if plan else None,nota='Interes plano: cada cuota calcula interes sobre el capital inicial. Asalariado 12% mensual; credito comercial 14% mensual. El capital se distribuye entre las cuotas. Sin recargos por mora.',boton='Calcular plan'),400 if error else 200

def reporte_filtrado():
    """Aplica los mismos filtros a la tabla web y a los archivos exportados.

    Los pr?stamos se filtran por fecha de desembolso; los cobros confirmados,
    por fecha de pago. Los filtros de cliente, estado y texto se aplican al
    pr?stamo relacionado con cada cobro.
    """
    def id_arg(nombre):
        valor=request.args.get(nombre, '').strip()
        if not valor:
            return None
        if not valor.isdecimal() or int(valor) < 1:
            abort(400)
        return int(valor)

    tipo_reporte=request.args.get('tipo_reporte', 'GENERAL').strip().upper()
    if tipo_reporte not in ('GENERAL', 'PRESTAMOS', 'COBROS'):
        tipo_reporte='GENERAL'

    periodo=request.args.get('periodo', '').strip().upper()
    if periodo not in ('DIARIO', 'SEMANAL', 'MENSUAL'):
        periodo=''
    fecha_texto=request.args.get('fecha', '').strip()
    # Una fecha elegida sin periodo equivale a filtrar ese d?a.
    if not periodo and fecha_texto:
        periodo='DIARIO'

    referencia=None
    desde=hasta=None
    if periodo:
        try:
            referencia=date.fromisoformat(fecha_texto) if fecha_texto else date.today()
        except ValueError:
            referencia=date.today()
        if periodo=='DIARIO':
            desde=hasta=referencia
        elif periodo=='SEMANAL':
            desde=referencia-timedelta(days=referencia.weekday())
            hasta=desde+timedelta(days=6)
        else:
            desde=date(referencia.year, referencia.month, 1)
            siguiente=date(referencia.year+(referencia.month==12), 1 if referencia.month==12 else referencia.month+1, 1)
            hasta=siguiente-timedelta(days=1)

    report=obtener_reporte(cliente_id=id_arg('cliente_id'), prestamo_id=id_arg('prestamo_id'))
    q=request.args.get('q', '').strip().casefold()[:160]
    estados_validos={'ACTIVO', 'MORA', 'FINALIZADO', 'CANCELADO', 'BORRADOR'}
    estado=request.args.get('estado', '').strip().upper()
    if estado not in estados_validos:
        estado=''

    def coincide_busqueda(prestamo):
        texto=f"{prestamo['cliente']} {prestamo['cedula']} PR-{prestamo['id']:05d}".casefold()
        return not q or q in texto

    # Primero se aplican los filtros comunes a pr?stamos y cobros.
    prestamos_coincidentes=[p for p in report['prestamos']
                            if coincide_busqueda(p) and (not estado or p['estado']==estado)]

    # El periodo de pr?stamos corresponde a la fecha de desembolso.
    prestamos_resultado=prestamos_coincidentes
    if periodo and tipo_reporte!='COBROS':
        prestamos_resultado=[p for p in prestamos_resultado if desde<=p['fecha_desembolso']<=hasta]
    if tipo_reporte=='COBROS':
        prestamos_resultado=[]
    report=limitar_reporte(report, {p['id'] for p in prestamos_resultado})

    # Los cobros se cuentan solo si est?n confirmados y el periodo coincide
    # con la fecha del pago, sin depender de la fecha en que se desembols?.
    pagos=[]
    if tipo_reporte in ('GENERAL', 'COBROS'):
        ids_prestamos={p['id'] for p in prestamos_coincidentes}
        for pago in servicios.listar_pagos():
            if pago['estado']!='CONFIRMADO' or pago['prestamo_id'] not in ids_prestamos:
                continue
            fecha_pago=pago['fecha_pago']
            fecha_pago=fecha_pago.date() if hasattr(fecha_pago, 'date') else fecha_pago
            if periodo and not (desde<=fecha_pago<=hasta):
                continue
            pagos.append(pago)

    if tipo_reporte in ('GENERAL', 'COBROS'):
        report['pagos_periodo']=pagos
    else:
        report.pop('pagos_periodo', None)
    report['tipo_reporte']=tipo_reporte
    report['titulo']={'GENERAL':'Reporte general de cartera',
                      'PRESTAMOS':'Reporte de pr?stamos',
                      'COBROS':'Reporte de cobros'}[tipo_reporte]
    if periodo:
        report['periodo']={'tipo':periodo, 'desde':desde, 'hasta':hasta, 'referencia':referencia}
    else:
        report.pop('periodo', None)

    validos=[p for p in report['prestamos'] if p['estado'] not in ('BORRADOR', 'CANCELADO')]
    report['resumen_periodo']={
        'prestamos':len(validos),
        'capital':sum((p['monto_principal'] for p in validos), Decimal('0')),
        'numero_pagos':len(pagos),
        'cobrado':sum((p['monto'] for p in pagos), Decimal('0')),
        'ordinario':sum((p['monto']-p['monto_recargo'] for p in pagos), Decimal('0')),
        'recargos':sum((p['monto_recargo'] for p in pagos), Decimal('0')),
    }
    return report

@personal.route('/reportes')
@requiere_personal()
def reportes():
    report=reporte_filtrado()
    params={k:request.args[k] for k in ('cliente_id','prestamo_id','q','estado','periodo','fecha','tipo_reporte') if request.args.get(k)}
    if report.get('periodo'):
        params['periodo']=report['periodo']['tipo']
        params['fecha']=report['periodo']['referencia'].isoformat()
    return render_template('personal/reportes.html',titulo=report['titulo'],reporte=report,clientes=servicios.listar_clientes(),params=params,fecha_reporte=params.get('fecha',''))

@personal.route('/reportes/<formato>')
@requiere_personal()
def exportar(formato):
    if formato not in ('pdf','xlsx'): abort(404)
    report=reporte_filtrado();stream=BytesIO()
    with TemporaryDirectory(dir=current_app.config.get('REPORT_TEMP_DIR')) as carpeta:
        file=Path(carpeta)/('reporte.'+formato)
        (exportar_excel if formato=='xlsx' else exportar_pdf)(report,file)
        stream.write(file.read_bytes())
    stream.seek(0)
    return send_file(stream,mimetype='application/pdf' if formato=='pdf' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',as_attachment=request.args.get('vista')!='1' or formato!='pdf',download_name='reporte_crece.'+formato)

@personal.route('/empleados')
@requiere_personal(administrador=True)
def empleados():
    rows=[dict(e,estado='ACTIVO' if e['activo'] else 'INACTIVO') for e in servicios.listar_empleados()]
    return tabla('Empleados',[('cedula','Cédula','texto'),('nombre','Empleado','texto'),('cargo','Cargo','texto'),('nombre_usuario','Usuario','texto'),('estado','Estado','estado')],rows,lambda e:[enlace('Editar','empleado_form',id=e['id']),enlace('Dar de baja','baja',tipo='empleado',id=e['id'])],enlace('Nuevo empleado','empleado_form'))

@personal.route('/empleados/nuevo',methods=['GET','POST'])
@personal.route('/empleados/<int:id>/editar',methods=['GET','POST'])
@requiere_personal(administrador=True)
def empleado_form(id=None):
    e=next((e for e in servicios.listar_empleados() if e['id']==id),None) if id else {}
    if e is None: abort(404)
    data=dict(e,activo='1' if e.get('activo',True) else '0')
    campos=PERSONA+[campo('cargo','Cargo',maxlength=80),campo('nombre_usuario','Usuario',minlength=4,maxlength=60),campo('contrasena','Contraseña (dejar vacía para conservar)' if id else 'Contraseña inicial','password',requerido=not id,minlength=10,maxlength=128),campo('activo','Estado','select',[('1','Activo'),('0','Inactivo')])]
    def guardar():
        servicios.guardar_empleado(**{k:texto(k) for k in ('cedula','nombres','apellidos','telefono','correo','cargo','nombre_usuario')},contrasena=request.form.get('contrasena',''),activo=texto('activo')=='1',empleado_id=id)
        return url_for('personal.empleados')
    return formulario('Editar empleado' if id else 'Nuevo empleado',campos,guardar,data,url_for('personal.empleados'),nota='Las credenciales sirven para web y escritorio. Solo las cuentas activas pueden operar.')

@personal.route('/usuarios')
@requiere_personal(administrador=True)
def usuarios():
    rows=[dict(u,estado='ACTIVO' if u['activo'] else 'INACTIVO') for u in cuentas.listar_usuarios()]
    return tabla('Cuentas y permisos',[('nombre_usuario','Usuario','texto'),('rol','Rol','texto'),('estado','Estado','estado'),('ultimo_acceso_en','Último acceso','fecha')],rows,lambda u:[enlace('Editar acceso','usuario_form',id=u['id']),enlace('Recuperar acceso','recuperar_usuario',id=u['id']),enlace('Cambiar estado','estado_usuario',id=u['id']),enlace('Dar de baja','baja',tipo='usuario',id=u['id'])],enlace('Nueva cuenta de personal','usuario_form'))

@personal.route('/usuarios/<int:id>/recuperar',methods=['GET','POST'])
@requiere_personal(administrador=True)
def recuperar_usuario(id):
    from crece.servicios.recuperacion import emitir_codigo
    cuenta=next((u for u in cuentas.listar_usuarios() if u['id']==id),None)
    if cuenta is None:abort(404)
    resultado=None;error=None
    if request.method=='POST':
        try:resultado=emitir_codigo(id,request.form.get('clave_admin',''),texto('motivo'),request.form.get('identidad')=='SI')
        except ValueError as exc:error=str(exc)
    respuesta=current_app.make_response((render_template('personal/recuperacion.html',titulo='Recuperar acceso',cuenta=cuenta,resultado=resultado,error=error),400 if error else 200))
    respuesta.headers['Referrer-Policy']='no-referrer'
    return respuesta

@personal.route('/usuarios/nuevo',methods=['GET','POST'])
@personal.route('/usuarios/<int:id>/editar',methods=['GET','POST'])
@requiere_personal(administrador=True)
def usuario_form(id=None):
    u=next((u for u in cuentas.listar_usuarios() if u['id']==id),None) if id else {}
    if u is None: abort(404)
    campos=[campo('nombre_usuario','Usuario',minlength=4,maxlength=60),campo('contrasena','Contraseña (vacía para conservar)' if id else 'Contraseña','password',requerido=not id,minlength=10,maxlength=128)]
    if not id: campos.append(campo('rol','Rol','select',[('EMPLEADO','Empleado'),('ADMINISTRADOR','Administrador')]))
    def guardar():
        if id: cuentas.actualizar_usuario(id,texto('nombre_usuario'),request.form.get('contrasena',''))
        else: cuentas.crear_usuario_personal(texto('nombre_usuario'),request.form.get('contrasena',''),texto('rol'))
        return url_for('personal.usuarios')
    return formulario('Editar acceso' if id else 'Nueva cuenta de personal',campos,guardar,u,url_for('personal.usuarios'),nota='Para registrar también los datos del trabajador utiliza Empleados. El rol de una cuenta existente se conserva.')

@personal.route('/usuarios/<int:id>/estado',methods=['GET','POST'])
@requiere_personal(administrador=True)
def estado_usuario(id):
    u=next((u for u in cuentas.listar_usuarios() if u['id']==id),None)
    if u is None: abort(404)
    def guardar():
        cuentas.cambiar_estado_usuario(id,texto('activo')=='1');return url_for('personal.usuarios')
    return formulario('Estado de '+u['nombre_usuario'],[campo('activo','Acceso','select',[('1','Activo'),('0','Inactivo')])],guardar,dict(activo='1' if u['activo'] else '0'),url_for('personal.usuarios'),nota='Al desactivar la cuenta, su siguiente solicitud web se bloqueará. Se conserva el historial de operaciones.')

@personal.route('/bajas/<tipo>/<int:id>',methods=['GET','POST'])
@requiere_personal(administrador=True)
def baja(tipo,id):
    opciones={'cliente':(servicios.eliminar_cliente,'clientes'),'empleado':(servicios.eliminar_empleado,'empleados'),'usuario':(cuentas.eliminar_usuario,'usuarios'),'prestamo':(servicios.eliminar_prestamo,'prestamos')}
    if tipo not in opciones: abort(404)
    action,dest=opciones[tipo]
    def guardar():
        result=action(id,texto('motivo')) if tipo=='prestamo' else action(id)
        flash('Resultado: '+result.lower().capitalize()+'.','exito');return url_for('personal.'+dest)
    return formulario(('Eliminar cliente' if tipo=='cliente' else 'Confirmar baja de '+tipo),[campo('confirmacion','Confirmación','select',[('SI','Confirmo la baja del registro #'+str(id))])]+([campo('motivo','Motivo','textarea',maxlength=500)] if tipo=='prestamo' else []),guardar,volver=url_for('personal.'+dest),nota='Se eliminará únicamente si no hay operaciones vinculadas. Si existe historial, se conserva y se desactiva o anula según las reglas del sistema. Los préstamos con pagos no se pueden anular.')
