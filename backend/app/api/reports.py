from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.report import Report
from app.models.review import Review
from app.schemas.report import ReportCreate, ReportResponse, ReportStatusUpdate
from app.api.deps import get_current_user, get_current_admin_user

router = APIRouter(prefix="/reports", tags=["reports"])


# ---------- 1. Report oluştur (giriş yapmış herhangi bir kullanıcı) ----------

@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
def create_report(
    payload: ReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    review = db.query(Review).filter(Review.id == payload.review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Değerlendirme bulunamadı")

    report = Report(
        review_id=payload.review_id,
        reporter_id=current_user.id,
        reason=payload.reason,
    )
    db.add(report)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Bu değerlendirmeyi zaten şikayet ettiniz",
        )

    db.refresh(report)
    return report


# ---------- 2. Bekleyen report'ları listele (sadece admin) ----------

@router.get("/pending", response_model=list[ReportResponse])
def list_pending_reports(
    admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Report)
        .filter(Report.status == "pending")
        .order_by(Report.created_at.asc())
        .all()
    )


# ---------- 3. Report durumunu güncelle (sadece admin) ----------

@router.patch("/{report_id}/status", response_model=ReportResponse)
def update_report_status(
    report_id: int,
    payload: ReportStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report bulunamadı")

    report.status = payload.status
    db.commit()
    db.refresh(report)
    return report