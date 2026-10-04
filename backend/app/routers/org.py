from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Department, SiwesBatch, Unit
from ..schemas import BatchIn, BatchOut, DepartmentIn, DepartmentOut, UnitIn, UnitOut

admin = Depends(require_roles("admin"))
dep_router = APIRouter(prefix="/api/departments", tags=["departments"])
unit_router = APIRouter(prefix="/api/units", tags=["units"])
batch_router = APIRouter(prefix="/api/batches", tags=["batches"])


def _commit(db: Session, msg: str):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, msg)


@dep_router.get("", response_model=list[DepartmentOut], dependencies=[Depends(get_current_user)])
def list_departments(db: Session = Depends(get_db)):
    return db.scalars(select(Department).order_by(Department.name)).all()


@dep_router.post("", response_model=DepartmentOut, status_code=201, dependencies=[admin])
def create_department(body: DepartmentIn, db: Session = Depends(get_db)):
    d = Department(**body.model_dump())
    db.add(d)
    _commit(db, "A department with that name already exists")
    return d


@dep_router.delete("/{dep_id}", status_code=204, dependencies=[admin])
def delete_department(dep_id: int, db: Session = Depends(get_db)):
    d = db.get(Department, dep_id)
    if not d:
        raise HTTPException(404, "Department not found")
    db.delete(d)
    db.commit()


@unit_router.get("", response_model=list[UnitOut], dependencies=[Depends(get_current_user)])
def list_units(department_id: int | None = None, db: Session = Depends(get_db)):
    q = select(Unit).order_by(Unit.name)
    if department_id:
        q = q.where(Unit.department_id == department_id)
    return db.scalars(q).all()


@unit_router.post("", response_model=UnitOut, status_code=201, dependencies=[admin])
def create_unit(body: UnitIn, db: Session = Depends(get_db)):
    if not db.get(Department, body.department_id):
        raise HTTPException(404, "Department not found")
    u = Unit(**body.model_dump())
    db.add(u)
    _commit(db, "That unit already exists in the department")
    return u


@unit_router.delete("/{unit_id}", status_code=204, dependencies=[admin])
def delete_unit(unit_id: int, db: Session = Depends(get_db)):
    u = db.get(Unit, unit_id)
    if not u:
        raise HTTPException(404, "Unit not found")
    db.delete(u)
    db.commit()


@batch_router.get("", response_model=list[BatchOut], dependencies=[Depends(get_current_user)])
def list_batches(db: Session = Depends(get_db)):
    return db.scalars(select(SiwesBatch).order_by(SiwesBatch.year.desc())).all()


@batch_router.post("", response_model=BatchOut, status_code=201, dependencies=[admin])
def create_batch(body: BatchIn, db: Session = Depends(get_db)):
    b = SiwesBatch(**body.model_dump())
    db.add(b)
    _commit(db, "A batch with that name already exists")
    return b


@batch_router.patch("/{batch_id}", response_model=BatchOut, dependencies=[admin])
def update_batch(batch_id: int, body: BatchIn, db: Session = Depends(get_db)):
    b = db.get(SiwesBatch, batch_id)
    if not b:
        raise HTTPException(404, "Batch not found")
    for k, v in body.model_dump().items():
        setattr(b, k, v)
    _commit(db, "A batch with that name already exists")
    return b
