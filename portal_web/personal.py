"""Área web del personal. Los casos de uso y sus transacciones son los de escritorio."""
from datetime import date
from decimal import Decimal, DecimalException, InvalidOperation
from io import BytesIO
from tempfile import TemporaryDirectory
from pathlib import Path
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file, url_for
from crece.servicios.comprobantes import obtener_comprobante_pago,ErrorComprobante
from crece.servicios import gestion as servicios, cuentas_orm as cuentas
from crece.servicios.reportes import obtener_reporte, limitar_reporte
from crece.infraestructura.exportadores import exportar_pdf, exportar_excel
from crece.infraestructura.base_datos import ErrorConexionBaseDatos
from crece.nucleo.validaciones import REGLAS, ErrorValidacion, validar_numero_texto, validar_plazo
from crece.nucleo.amortizacion import calcular_tabla_mensual
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
COL_PRESTAMOS=[('codigo','Préstamo','texto'),('cliente','Cliente','texto'),('monto_principal','Capital','moneda'),('tasa_mensual','Tasa mensual','porcentaje'),('saldo_pendiente','Saldo','moneda'),('estado','Estado','estado')]
def codigos(rows): return [dict(d,codigo=f"PR-{d['id']:05d}") for d in rows]

@personal.route('/')
@requiere_personal()
def inicio():
    return render_template('personal/inicio.html',resumen=servicios.obtener_resumen(),actividad=servicios.obtener_actividad_reciente())

@personal.route('/clientes')
@requiere_personal()
def clientes():
    return tabla('Clientes',[('cedula','Cédula','texto'),('nombre','Cliente','texto'),('telefono','Teléfono','texto'),('correo','Correo','texto'),('estado','Estado','estado')],servicios.listar_clientes(),lambda d:[enlace('Ver ficha','cliente',id=d['id']),enlace('Editar','cliente_form',id=d['id'])]+([enlace('Eliminar cliente','baja',tipo='cliente',id=d['id'])] if g.usuario_actual['rol']=='ADMINISTRADOR' else []),enlace('Nuevo cliente','cliente_form'))

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

def campos_plan():
    return [campo('monto','Capital (C$)','number',min='0.01',step='0.01'),campo('tasa','Tasa mensual (%)','number',min='0',step='0.0001'),campo('meses','Plazo en meses','number',min=1,max=600,step=1),campo('fecha_primera_cuota','Primera cuota','date')]

@personal.route('/prestamos/nuevo',methods=['GET','POST'])
@requiere_personal()
def prestamo_form():
    clientes=servicios.listar_clientes_para_prestamo()
    campos=[campo('cliente_id','Cliente','select',[(c['id'],c['nombre']+' · '+c['cedula']) for c in clientes])]+campos_plan()+[campo('fecha_desembolso','Desembolso','date')]
    def guardar():
        id=servicios.registrar_prestamo_mensual(int(texto('cliente_id')),numero('monto'),numero('tasa'),validar_plazo(texto('meses')),date.fromisoformat(texto('fecha_desembolso')),date.fromisoformat(texto('fecha_primera_cuota')))
        return url_for('personal.prestamo',id=id)
    return formulario('Emitir préstamo',campos,guardar,dict(cliente_id=request.args.get('cliente_id',''),fecha_desembolso=date.today().isoformat()),url_for('personal.prestamos'),nota='La tasa se expresa por mes. Antes de emitir puedes revisar el plan en el simulador. Se conservarán las condiciones y cuotas del contrato emitido.')

@personal.route('/prestamos/<int:id>')
@requiere_personal()
def prestamo(id):
    p=obtener_reporte(prestamo_id=id)['prestamos'][0]
    columnas=[('numero_cuota','Cuota','texto'),('fecha_vencimiento','Vence','fecha'),('tasa_mensual','Tasa mensual','porcentaje'),('saldo_inicial','Capital inicial','moneda'),('interes','Interés','moneda'),('abono_capital','Capital','moneda'),('cuota_programada','Programada','moneda'),('monto_pagado','Pagado','moneda'),('saldo','Pendiente','moneda'),('estado','Estado','estado')]
    acciones=lambda d: [enlace('Cobrar','cobro',cuota_id=d['id'])] if d['saldo']>0 and p['estado'] not in ('CANCELADO','BORRADOR') else []
    enlaces=[enlace('Editar notas','notas',id=id),enlace('PDF / Imprimir','exportar',formato='pdf',prestamo_id=id,vista=1),enlace('Excel','exportar',formato='xlsx',prestamo_id=id)]
    if g.usuario_actual['rol']=='ADMINISTRADOR': enlaces.append(enlace('Anular préstamo','baja',tipo='prestamo',id=id))
    return tabla(f'PR-{id:05d} · {p["cliente"]}',columnas,p['cuotas'],acciones,filtrar=False,detalles=[('Capital',f'C$ {p["monto_principal"]:,.2f}'),('Tasa mensual',f'{p["tasa_mensual"]:.4f} %'),('Plazo',f'{p["plazo_meses"]} meses'),('Estado',p['estado']),('Emitido por',p['empleado']),('Notas',p['notas'])],enlaces=enlaces)

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
    return tabla('Cuotas por cobrar',[('cliente','Cliente','texto'),('prestamo_id','Préstamo','texto'),('numero_cuota','Cuota','texto'),('fecha_vencimiento','Vence','fecha'),('tasa_mensual','Tasa mensual','porcentaje'),('saldo','Pendiente','moneda'),('estado','Estado','estado')],servicios.listar_cuotas_cobro(),lambda d:[enlace('Registrar cobro','cobro',cuota_id=d['id'])],enlaces=[enlace('Pagos y solicitudes','pagos')])

@personal.route('/cobros/<int:cuota_id>',methods=['GET','POST'])
@requiere_personal()
def cobro(cuota_id):
    q=next((q for q in servicios.listar_cuotas_cobro() if q['id']==cuota_id),None)
    if not q: abort(404)
    def guardar():
        servicios.registrar_cobro(cuota_id,numero('monto'),texto('metodo'),texto('referencia'))
        return url_for('personal.prestamo',id=q['prestamo_id'])
    return formulario('Registrar cobro',[campo('monto','Importe recibido (C$)','number',step='0.01',min='0.01',max=str(q['saldo'])),campo('metodo','Método','select',[(s,s.capitalize()) for s in ('EFECTIVO','TRANSFERENCIA','TARJETA')]),campo('referencia','Referencia','text',requerido=False,maxlength=100)],guardar,dict(monto=q['saldo']),url_for('personal.cobros'),nota=f"{q['cliente']} · Cuota {q['numero_cuota']} · Pendiente C$ {q['saldo']:,.2f}. Registra únicamente un pago recibido y verificado.")

@personal.route('/pagos')
@requiere_personal()
def pagos():
    return tabla('Pagos y solicitudes',[('cliente','Cliente','texto'),('numero_cuota','Cuota','texto'),('fecha_pago','Fecha','fecha'),('monto','Importe','moneda'),('metodo','Método','texto'),('referencia','Referencia','texto'),('tiene_comprobante','Comprobante','comprobante'),('estado','Estado','estado')],servicios.listar_pagos(),lambda d:[enlace('Revisar','pago',id=d['id'])])

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
        try: plan=calcular_tabla_mensual(numero('monto'),numero('tasa'),validar_plazo(texto('meses')),date.fromisoformat(texto('fecha_primera_cuota')))
        except (ValueError,DecimalException,OverflowError) as exc: error=str(exc)
    return render_template('personal/formulario.html',titulo='Simulador de préstamo',campos=campos_plan(),valores=values,error=error,volver=url_for('personal.prestamos'),plan=plan,nota='Calcula una proyección sin emitir un préstamo ni guardar movimientos.',boton='Calcular plan'),400 if error else 200

def reporte_filtrado():
    def id_arg(k):
        value=request.args.get(k,'')
        return int(value) if value else None
    report=obtener_reporte(cliente_id=id_arg('cliente_id'),prestamo_id=id_arg('prestamo_id'))
    q=request.args.get('q','').strip().casefold()[:160];estado=request.args.get('estado','')
    ids={p['id'] for p in report['prestamos'] if (not q or q in f"{p['cliente']} {p['cedula']} PR-{p['id']:05d}".casefold()) and (not estado or p['estado']==estado)}
    return limitar_reporte(report,ids)

@personal.route('/reportes')
@requiere_personal()
def reportes():
    report=reporte_filtrado()
    params={k:request.args[k] for k in ('cliente_id','prestamo_id','q','estado') if request.args.get(k)}
    return render_template('personal/reportes.html',titulo=report['titulo'],reporte=report,clientes=servicios.listar_clientes(),params=params)

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
