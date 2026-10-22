"""Comprobantes privados, compartidos entre web y escritorio mediante el ORM."""
from io import BytesIO
from hashlib import sha256
from PIL import Image,ImageOps,UnidentifiedImageError
from sqlalchemy import select
from crece.infraestructura.base_datos import transaccion
from crece.infraestructura.modelos import ComprobantePago,Pago,CuotaModel,Prestamo
from crece.servicios.permisos import exigir_personal

MAX_COMPROBANTE=5*1024*1024
MAX_PIXELES=24_000_000
FORMATOS=('JPEG','PNG','WEBP')

class ErrorComprobante(ValueError):pass

def preparar_comprobante(contenido):
    if not isinstance(contenido,bytes) or not contenido:
        raise ErrorComprobante('Adjunta una foto del comprobante de pago.')
    if len(contenido)>MAX_COMPROBANTE:
        raise ErrorComprobante('El comprobante no debe superar 5 MB.')
    try:
        with Image.open(BytesIO(contenido)) as imagen:
            if imagen.format not in FORMATOS or getattr(imagen,'n_frames',1)!=1:
                raise ErrorComprobante('Adjunta una imagen JPG, PNG o WebP sin animación.')
            if max(imagen.size)>10000 or imagen.width*imagen.height>MAX_PIXELES:
                raise ErrorComprobante('La imagen es demasiado grande. Usa una foto de hasta 24 megapíxeles.')
            imagen.verify()
        with Image.open(BytesIO(contenido)) as original:
            orientada=ImageOps.exif_transpose(original)
            orientada.thumbnail((6000,6000),Image.Resampling.LANCZOS)
            # Una imagen nueva conserva solo los píxeles, sin GPS, EXIF, comentarios
            # ni datos adicionales enviados junto al archivo original.
            rgba=orientada.convert('RGBA')
            limpia=Image.new('RGB',rgba.size,'white')
            limpia.paste(rgba,mask=rgba.getchannel('A'))
            destino=BytesIO();limpia.save(destino,format='JPEG',quality=92,exif=b'',icc_profile=None)
            salida=destino.getvalue()
            rgba.close();limpia.close();orientada.close()
        if len(salida)>MAX_COMPROBANTE:
            raise ErrorComprobante('La imagen procesada supera 5 MB. Reduce el tamaño de la foto.')
        return salida
    except ErrorComprobante:raise
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError) as error:
        raise ErrorComprobante('No se pudo leer la imagen. Adjunta una foto JPG, PNG o WebP válida.') from error

def guardar_comprobante(session,pago_id,contenido):
    session.add(ComprobantePago(pago_id=pago_id,tipo_mime='image/jpeg',contenido=contenido,sha256=sha256(contenido).hexdigest()))

def obtener_comprobante_pago(pago_id,usuario_cliente_id=None):
    with transaccion() as session:
        if usuario_cliente_id is None:exigir_personal(session)
        else:
            from crece.servicios.portal_orm import _cliente
            cliente=_cliente(session,usuario_cliente_id)
            propio=session.scalar(select(Pago.id).join(CuotaModel).join(Prestamo).where(Pago.id==int(pago_id),Prestamo.cliente_id==cliente.id))
            if not propio:raise ErrorComprobante('Comprobante no disponible.')
        comprobante=session.scalar(select(ComprobantePago).where(ComprobantePago.pago_id==int(pago_id)))
        if not comprobante:raise ErrorComprobante('Esta solicitud no tiene un comprobante adjunto.')
        return dict(contenido=bytes(comprobante.contenido),tipo_mime=comprobante.tipo_mime,nombre=f'comprobante_pago_{int(pago_id)}.jpg')
