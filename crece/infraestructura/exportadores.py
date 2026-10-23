"""Exportación local: ReportLab y openpyxl, como en las sesiones 34-36."""
from pathlib import Path
from html import escape
from decimal import Decimal
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4,landscape
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from openpyxl import Workbook
from openpyxl.styles import Font,PatternFill,Alignment,Border,Side
from openpyxl.drawing.image import Image as ExcelImage
from openpyxl.worksheet.page import PageMargins
from openpyxl.utils import get_column_letter

ROOT=Path(__file__).resolve().parents[2]
BLUE='#003366'
GREEN='#006633'
MONEY='"C$ "#,##0.00'

def moneda(value): return f'C$ {value:,.2f}'
def tasa(value):
    value=Decimal(str(value))
    if value==value.quantize(Decimal('0.01')):return f'{value:.2f} %'
    return format(value,'.6f').rstrip('0').rstrip('.')+' %'

def exportar_pdf(reporte,destino,progreso=None):
    path=Path(destino)
    if 'CreceBody' not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont('CreceBody',str(ROOT/'assets/fonts/OpenSans-Regular.ttf')))
        pdfmetrics.registerFont(TTFont('CreceHeading',str(ROOT/'assets/fonts/Montserrat-Bold.ttf')))
    styles=getSampleStyleSheet()
    for name in ('Normal','BodyText'):
        styles[name].fontName='CreceBody'
        styles[name].fontSize=9
        styles[name].leading=13
    styles.add(ParagraphStyle('Brand',fontName='CreceHeading',fontSize=20,leading=24,textColor=colors.HexColor(BLUE),spaceAfter=10))
    styles.add(ParagraphStyle('Section',fontName='CreceHeading',fontSize=12,leading=16,textColor=colors.HexColor(GREEN),spaceBefore=14,spaceAfter=8))
    header_style=ParagraphStyle('HeaderCell',parent=styles['BodyText'],textColor=colors.white,fontName='CreceBody',fontSize=8)
    def p(text): return Paragraph(escape(str(text)),styles['BodyText'])
    def table(headers,rows,widths=None):
        data=[[Paragraph(escape(str(h)),header_style) for h in headers]]+[[p(v) for v in row] for row in rows]
        t=Table(data,colWidths=widths,repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor(BLUE)),('TEXTCOLOR',(0,0),(-1,0),colors.white),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#EBF9F1')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),1,colors.HexColor(GREEN))]))
        return t
    story=[]
    logo=ROOT/'assets/logo_horizontal_crece.png'
    titulo=Paragraph(escape(reporte['titulo']),styles['Brand'])
    generado=p(f"Generado: {reporte['generado_en']:%d/%m/%Y %H:%M} · Responsable: {reporte['generado_por']}")
    if logo.exists():
        # Original asset, preserving its complete proportions and clear space.
        header=Table([[Image(str(logo),width=160,height=160*2550/4200,hAlign='LEFT'),[titulo,generado]]],colWidths=[184,576],hAlign='LEFT')
        header.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
        story.append(header)
    else:story.extend([titulo,generado])
    story.append(Spacer(1,10))
    if reporte['cliente']:
        c=reporte['cliente']
        story.extend([p('Cliente: '+c['nombre_completo']+' · Cédula: '+c['cedula']+' · Teléfono: '+c['telefono']),p('Correo: '+(c['correo'] or 'No registrado')+' · Dirección: '+(c['direccion'] or 'No registrada')),Spacer(1,12)])
    totals=reporte['totales']
    story.append(table(['Principal desembolsado','Interés programado','Total ordinario','Cobrado confirmado','Saldo pendiente total'],[[moneda(totals[k]) for k in ('principal','interes','programado','cobrado','saldo')]], [148]*5))
    story.append(p('Totales excluyen borradores y préstamos cancelados. Total programado: capital e interés ordinario. Saldo pendiente y cobrado incluyen recargos aplicables.'))
    story.append(p(f"Recargos únicos: {moneda(totals.get('recargos',0))} · Recargos cobrados: {moneda(totals.get('recargos_cobrados',0))} · Recargos pendientes: {moneda(totals.get('recargos_pendientes',0))}"))
    if not reporte['prestamos']: story.append(p('No hay préstamos para el alcance seleccionado.'))
    for index,loan in enumerate(reporte['prestamos']):
        if progreso: progreso(5+int(55*index/max(1,len(reporte['prestamos']))))
        story.append(Paragraph(escape(f"PR-{loan['id']:05d} · {loan['cliente']}"),styles['Section']))
        story.extend([p(f"Estado: {loan['estado']} · Emitido por: {loan['empleado']} · Desembolso: {loan['fecha_desembolso']:%d/%m/%Y}"),p(f"Principal: {moneda(loan['monto_principal'])} · Tasa mensual nominal: {tasa(loan['tasa_mensual'])} · Equivalente anual nominal: {tasa(loan['tasa_interes_anual'])} · Plazo: {loan['plazo_meses']} cuotas · Frecuencia: {loan.get('frecuencia_texto','Mensual')}"),p('Notas: '+(loan['notas'] or 'Sin observaciones')),Spacer(1,8)])
        rows=[[q['numero_cuota'],q['fecha_vencimiento'].strftime('%d/%m/%Y'),moneda(q['saldo_inicial']),tasa(q.get('tasa_periodica',q['tasa_mensual'])),moneda(q['interes']),moneda(q['abono_capital']),moneda(q['cuota_programada']),moneda(q['monto_pagado']),moneda(q['saldo']),q['estado']] for q in loan['cuotas']]
        story.append(table(['#','Vencimiento','Saldo capital inicial','Tasa del período','Interés','Capital','Cuota ordinaria','Pagado ordinario','Pendiente total','Estado'],rows,[28,75,90,70,75,75,80,80,85,82]))
        if loan.get('recargo_porcentaje',0):
            story.append(p(f"Mora: recargo único del {tasa(loan['recargo_porcentaje'])} sobre el capital de la cuota pendiente al terminar la gracia de {loan['gracia_horas']} horas desde el final del vencimiento. No se capitaliza. Horario de Nicaragua."))
            mora=[[q['numero_cuota'],q['limite_gracia'].strftime('%d/%m/%Y %H:%M'),moneda(q['capital_base_mora']),moneda(q['recargo']),moneda(q['recargo_pagado']),moneda(q['recargo_pendiente'])] for q in loan['cuotas']]
            story.append(table(['Cuota','Fin de gracia','Base del recargo','Recargo único','Recargo cobrado','Recargo pendiente'],mora,[50,150,140,140,140,140]))
        story.append(Spacer(1,12))
    def footer(canvas,doc):
        canvas.setFont('CreceBody',8)
        canvas.setFillColor(colors.HexColor(BLUE))
        canvas.drawString(32,20,'CRECE+ PRÉSTAMOS · Información de cartera')
        canvas.drawRightString(810,20,f'Página {doc.page}')
    class Documento(SimpleDocTemplate):
        def afterFlowable(self,flowable):
            if progreso: progreso(min(95,65+self.page))
    Documento(str(path),pagesize=landscape(A4),leftMargin=32,rightMargin=32,topMargin=28,bottomMargin=36,title=reporte['titulo'],author='CRECE+ PRÉSTAMOS').build(story,onFirstPage=footer,onLaterPages=footer)
    return path

def _texto(cell,value):
    cell.value=value
    if isinstance(value,str): cell.data_type='s'

def exportar_excel(reporte,destino,progreso=None):
    """Reporte de marca con encabezado, logo y cuadrícula visible en cada hoja."""
    book=Workbook()
    summary=book.active
    summary.title='Resumen'
    header_row=9
    first_row=header_row+1
    line=Side(style='thin',color='B7CDC3')
    grid=Border(left=line,right=line,top=line,bottom=line)
    logo=ROOT/'assets/logo_horizontal_crece.png'
    scope=reporte['cliente']['nombre_completo'] if reporte['cliente'] else 'Toda la cartera seleccionada'

    def encabezado(sheet,last,title):
        end=get_column_letter(last)
        sheet.sheet_view.showGridLines=False
        sheet.sheet_view.zoomScale=85 if last>8 else 100
        sheet.sheet_properties.tabColor='00A651'
        for row in range(1,5): sheet.row_dimensions[row].height=22
        sheet.row_dimensions[5].height=5
        sheet.row_dimensions[6].height=24
        sheet.row_dimensions[7].height=28
        sheet.row_dimensions[8].height=8
        if logo.exists():
            mark=ExcelImage(str(logo))
            mark.width=160
            mark.height=160*2550/4200
            sheet.add_image(mark,'A1')
        title_col='C' if last==8 else 'D'
        sheet.merge_cells(f'{title_col}1:{end}2')
        cell=sheet[f'{title_col}1']
        _texto(cell,'CRECE+ PRÉSTAMOS · '+title)
        cell.font=Font(name='Montserrat',size=16,color=BLUE[1:],bold=True)
        cell.alignment=Alignment(vertical='center',wrap_text=True)
        for row,text in [(3,f"Generado: {reporte['generado_en']:%d/%m/%Y %H:%M}"),(4,'Responsable: '+reporte['generado_por'])]:
            sheet.merge_cells(f'{title_col}{row}:{end}{row}')
            cell=sheet[f'{title_col}{row}'];_texto(cell,text)
            cell.font=Font(name='Open Sans',size=10,color=BLUE[1:])
            cell.alignment=Alignment(vertical='center',wrap_text=True)
        for col in range(1,last+1): sheet.cell(5,col).fill=PatternFill('solid',fgColor='00A651')
        for row,text in [(6,'Alcance: '+scope),(7,'Importes en C$. Tasas nominales por período. Saldo total = ordinario pendiente + recargo pendiente. Pagos y recargos separados.')]:
            sheet.merge_cells(f'A{row}:{end}{row}')
            cell=sheet.cell(row,1);_texto(cell,text)
            cell.font=Font(name='Open Sans',size=10,color=BLUE[1:],bold=row==6)
            cell.alignment=Alignment(vertical='center',wrap_text=True)
            cell.fill=PatternFill('solid',fgColor='EBF9F1')
        sheet.freeze_panes=f'C{first_row}' if last>8 else f'A{first_row}'
        sheet.sheet_properties.pageSetUpPr.fitToPage=True
        sheet.page_setup.orientation='landscape'
        sheet.page_setup.paperSize=sheet.PAPERSIZE_A4
        sheet.page_setup.fitToWidth=1
        sheet.page_setup.fitToHeight=0
        sheet.page_margins=PageMargins(left=.25,right=.25,top=.35,bottom=.35,header=.15,footer=.15)
        sheet.print_title_rows=f'1:{header_row}'
        sheet.oddFooter.center.text='CRECE+ PRÉSTAMOS · Información de cartera'
        sheet.oddFooter.right.text='Página &P de &N'
        sheet.oddFooter.center.size=9
        sheet.oddFooter.right.size=9

    def formato(sheet,last,monies=(),rates=(),dates=()):
        sheet.row_dimensions[header_row].height=34
        for row in sheet.iter_rows(min_row=header_row,max_col=last):
            for cell in row:
                if isinstance(cell.value,str): cell.data_type='s'
                cell.border=grid
                cell.font=Font(name='Open Sans',size=11,color=BLUE[1:])
                cell.alignment=Alignment(vertical='center',wrap_text=True)
                if cell.row==header_row:
                    cell.fill=PatternFill('solid',fgColor=BLUE[1:])
                    cell.font=Font(name='Open Sans',size=10,color='FFFFFF',bold=True)
                    cell.alignment=Alignment(vertical='center',horizontal='center',wrap_text=True)
                else:
                    cell.fill=PatternFill('solid',fgColor='EBF9F1' if (cell.row-first_row)%2 else 'FFFFFF')
                    if cell.column in monies:
                        cell.number_format=MONEY
                        cell.alignment=Alignment(horizontal='right',vertical='center')
                    elif cell.column in rates:
                        cell.number_format='0.000000%'
                        cell.alignment=Alignment(horizontal='center',vertical='center')
                    elif cell.column in dates:
                        cell.number_format='dd/mm/yyyy'
                        cell.alignment=Alignment(horizontal='center',vertical='center')
            if row[0].row>=first_row: sheet.row_dimensions[row[0].row].height=36
        sheet.print_area=f'A1:{get_column_letter(last)}{sheet.max_row}'

    encabezado(summary,8,reporte['titulo'])
    for col in range(1,9): summary.column_dimensions[get_column_letter(col)].width=15
    summary.merge_cells('A9:C9');summary['A9']='Indicador'
    summary.merge_cells('D9:H9');summary['D9']='Importe (C$)'
    for row,(name,key) in enumerate([('Principal desembolsado','principal'),('Interés programado','interes'),('Total ordinario','programado'),('Cobrado confirmado','cobrado'),('Saldo pendiente total','saldo')],first_row):
        summary.merge_cells(start_row=row,start_column=1,end_row=row,end_column=3)
        summary.merge_cells(start_row=row,start_column=4,end_row=row,end_column=8)
        summary.cell(row,1,name)
        summary.cell(row,4,float(reporte['totales'][key]))
    formato(summary,8,monies=(4,))
    summary.merge_cells('A16:H17')
    summary['A16']='Totales sin borradores ni préstamos cancelados. Consulta Préstamos y Cuotas para revisar el detalle de cada operación.'
    summary['A16'].alignment=Alignment(wrap_text=True,vertical='center')
    summary['A16'].font=Font(name='Open Sans',size=10,color=GREEN[1:])
    summary.print_area='A1:H17'
    loans=book.create_sheet('Préstamos')
    quotas=book.create_sheet('Cuotas')
    for sheet,headers,widths in [
        (loans,['Código','Cliente','Cédula','Responsable','Desembolso','Principal','Tasa mensual','Tasa nominal anual','Número cuotas','Cuota periódica','Saldo total','Estado','Notas','Frecuencia','Tasa del período','Recargo único','Gracia (horas)'],[15,32,23,24,15,19,15,18,14,19,19,17,34,22,18,17,16]),
        (quotas,['Préstamo','Cliente','Cuota','Vencimiento','Capital inicial','Tasa del período','Interés','Capital','Cuota ordinaria','Pagado ordinario','Saldo total','Estado','Frecuencia','Recargo único','Recargo pagado','Recargo pendiente','Fin de gracia'],[15,32,9,15,19,19,16,16,19,19,19,17,22,19,19,19,24])]:
        encabezado(sheet,len(headers),sheet.title)
        for col,(header,width) in enumerate(zip(headers,widths),1):
            sheet.cell(header_row,col,header)
            sheet.column_dimensions[get_column_letter(col)].width=width
    for index,loan in enumerate(reporte['prestamos']):
        if progreso: progreso(5+int(55*index/max(1,len(reporte['prestamos']))))
        loans.append([f"PR-{loan['id']:05d}",loan['cliente'],loan['cedula'],loan['empleado'],loan['fecha_desembolso'],float(loan['monto_principal']),float(loan['tasa_mensual']/100),float(loan['tasa_interes_anual']/100),loan['plazo_meses'],float(loan['cuota_mensual']),float(loan['saldo_pendiente']),loan['estado'],loan['notas'] or '',loan.get('frecuencia','MENSUAL'),float(loan.get('tasa_periodica',loan['tasa_mensual'])/100),float(loan.get('recargo_porcentaje',0)/100),loan.get('gracia_horas',72)])
        for q in loan['cuotas']:
            quotas.append([f"PR-{loan['id']:05d}",loan['cliente'],q['numero_cuota'],q['fecha_vencimiento'],float(q['saldo_inicial']),float(q.get('tasa_periodica',q['tasa_mensual'])/100),float(q['interes']),float(q['abono_capital']),float(q['cuota_programada']),float(q['monto_pagado']),float(q['saldo']),q['estado'],loan.get('frecuencia','MENSUAL'),float(q.get('recargo',0)),float(q.get('recargo_pagado',0)),float(q.get('recargo_pendiente',0)),q.get('limite_gracia') if loan.get('recargo_porcentaje',0) else None])
    for sheet,monies,rates,dates in [(loans,[6,10,11],[7,8,15,16],[5]),(quotas,[5,7,8,9,10,11,14,15,16],[6],[4])]:
        if progreso: progreso(70)
        formato(sheet,sheet.max_column,monies,rates,dates)
        sheet.auto_filter.ref=f'A{header_row}:{get_column_letter(sheet.max_column)}{sheet.max_row}'
    for row in range(first_row,quotas.max_row+1):quotas.cell(row,17).number_format='dd/mm/yyyy hh:mm'
    for row,(titulo,clave) in enumerate([('Recargos únicos','recargos'),('Recargos cobrados','recargos_cobrados'),('Recargos pendientes','recargos_pendientes')],19):
        summary.merge_cells(start_row=row,start_column=1,end_row=row,end_column=3)
        summary.merge_cells(start_row=row,start_column=4,end_row=row,end_column=8)
        summary.cell(row,1,titulo);summary.cell(row,4,float(reporte['totales'].get(clave,0)))
        for col in range(1,9):
            cell=summary.cell(row,col);cell.border=grid;cell.font=Font(name='Open Sans',size=11,color=BLUE[1:]);cell.fill=PatternFill('solid',fgColor='EBF9F1')
        summary.cell(row,4).number_format=MONEY
    summary.print_area='A1:H21'
    if progreso: progreso(90)
    book.save(destino)
    return Path(destino)

def html_impresion(reporte):
    """La misma instantánea, paginada por QTextDocument/QPrinter en vista previa."""
    e=lambda v:escape(str(v))
    logo=(ROOT/'assets/logo_horizontal_crece.png').as_uri()
    body=[f'<img src="{e(logo)}" width="160" alt="CRECE+ PRÉSTAMOS"><h1>{e(reporte["titulo"])}</h1><p>CRECE+ PRÉSTAMOS · {reporte["generado_en"]:%d/%m/%Y %H:%M}</p>']
    if reporte['cliente']:
        c=reporte['cliente']
        body.append(f'<p><b>{e(c["nombre_completo"])}</b> · Cédula {e(c["cedula"])} · Tel. {e(c["telefono"])}<br>Correo: {e(c["correo"] or "No registrado")}<br>{e(c["direccion"] or "")}</p>')
    body.append('<p>Saldo programado: '+moneda(reporte['totales']['saldo'])+'</p>')
    for p in reporte['prestamos']:
        body.append(f'<h2>PR-{p["id"]:05d} · {e(p["cliente"])}</h2><p>Principal: {moneda(p["monto_principal"])} · Tasa mensual: {tasa(p["tasa_mensual"])} · {p["plazo_meses"]} cuotas · {e(p.get("frecuencia_texto","Mensual"))} · {e(p["estado"])}</p>')
        body.append(f'<p>Cédula: {e(p["cedula"])} · Emitido por: {e(p["empleado"])} · Desembolso: {p["fecha_desembolso"]:%d/%m/%Y}<br>Equivalente nominal anual: {tasa(p["tasa_interes_anual"])} · Observaciones: {e(p["notas"] or "Sin observaciones")}</p>')
        body.append('<table border="1" cellspacing="0" cellpadding="5"><thead><tr>'+''.join('<th>'+h+'</th>' for h in ['Cuota','Vence','Tasa del período','Capital inicial','Interés','Capital','Programada','Pagado ordinario','Recargo pendiente','Pendiente total','Estado'])+'</tr></thead>')
        for q in p['cuotas']:
            values=[q['numero_cuota'],q['fecha_vencimiento'].strftime('%d/%m/%Y'),tasa(q.get('tasa_periodica',q['tasa_mensual'])),moneda(q['saldo_inicial']),moneda(q['interes']),moneda(q['abono_capital']),moneda(q['cuota_programada']),moneda(q['monto_pagado']),moneda(q.get('recargo_pendiente',0)),moneda(q['saldo']),q['estado']]
            body.append('<tr>'+''.join('<td>'+e(v)+'</td>' for v in values)+'</tr>')
        body.append('</table>')
    return '<html><head><style>body{font-family:Arial;font-size:9pt;color:#003366}h1{font-size:20pt}h2{font-size:12pt;color:#006633}th{background:#003366;color:white}table{font-size:8pt;width:100%}</style></head><body>'+''.join(body)+'</body></html>'
