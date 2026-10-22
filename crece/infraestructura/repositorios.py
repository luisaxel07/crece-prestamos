"""Patrón repositorio: consultas y ciclo de vida ORM separados de PySide6."""
from sqlalchemy import select
from sqlalchemy.orm import joinedload,selectinload
from .modelos import Prestamo

class Repositorio:
    def __init__(self,session,model): self.session,self.model=session,model
    def obtener(self,id,bloquear=False): return self.session.get(self.model,int(id),with_for_update=bloquear)
    def listar(self,*conditions): return list(self.session.scalars(select(self.model).where(*conditions).order_by(self.model.id.desc())))
    def agregar(self,**values):
        entity=self.model(**values)
        self.session.add(entity)
        self.session.flush()
        return entity
    def eliminar(self,entity): self.session.delete(entity)

class PrestamosRepositorio(Repositorio):
    def __init__(self,session): super().__init__(session,Prestamo)
    def cartera(self,cliente_id=None,prestamo_id=None):
        query=select(Prestamo).options(joinedload(Prestamo.cliente),joinedload(Prestamo.creador),selectinload(Prestamo.cuotas)).order_by(Prestamo.id.desc())
        if cliente_id is not None: query=query.where(Prestamo.cliente_id==int(cliente_id))
        if prestamo_id is not None: query=query.where(Prestamo.id==int(prestamo_id))
        return list(self.session.scalars(query))
