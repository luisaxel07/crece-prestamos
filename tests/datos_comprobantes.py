"""Comprobante de prueba sintético; no corresponde a una transferencia real."""
from functools import lru_cache
from io import BytesIO
from PIL import Image,ImageDraw
@lru_cache(maxsize=1)
def imagen_prueba():
    image=Image.new('RGB',(480,240),'white');draw=ImageDraw.Draw(image)
    draw.text((20,20),'COMPROBANTE FICTICIO - PRUEBAS',fill='black');draw.text((20,70),'Referencia: PRUEBA-001',fill='black');draw.text((20,110),'Importe: C$ 100.00',fill='black')
    buffer=BytesIO();image.save(buffer,format='PNG');image.close();return buffer.getvalue()
