from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, case, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.platform.config import Settings
from app.platform.models import Job, VideoItem


class Base(DeclarativeBase):
    pass


class JobRow(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    keyword: Mapped[str] = mapped_column(String(512), default="")
    capability: Mapped[str] = mapped_column(String(16))
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(32))
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class VideoRow(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), index=True)
    platform: Mapped[str] = mapped_column(String(32))
    source_url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text, default="")
    video_url: Mapped[str] = mapped_column(Text, default="")
    cover_url: Mapped[str] = mapped_column(Text, default="")
    raw: Mapped[dict] = mapped_column(JSON)


class LogRow(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    job_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    level: Mapped[str] = mapped_column(String(16), default="info")
    message: Mapped[str] = mapped_column(Text)


class Store:
    def __init__(self, settings: Settings):
        self._engine = create_engine(settings.mysql_url, pool_pre_ping=True)

    def create_tables(self) -> None:
        try:
            Base.metadata.create_all(self._engine)
        except Exception as exc:
            if "already exists" not in str(exc):
                raise
        columns = {column["name"] for column in inspect(self._engine).get_columns("jobs")}
        if "created_at" not in columns:
            with self._engine.begin() as connection:
                connection.execute(text("ALTER TABLE jobs ADD COLUMN created_at DATETIME NULL"))

    def save_job(self, job: Job) -> None:
        with Session(self._engine) as session:
            row = session.get(JobRow, job.id)
            if row is None:
                row = JobRow(id=job.id, url=job.url, capability=job.capability, status=job.status)
                session.add(row)
            row.url = job.url
            row.keyword = job.keyword
            row.capability = job.capability
            row.platform = job.platform
            row.status = job.status
            row.error = job.error
            session.commit()

    def save_video(self, item: VideoItem) -> None:
        with Session(self._engine) as session:
            session.add(VideoRow(**item.model_dump()))
            session.commit()

    def list_jobs(self, limit: int = 50) -> list[Job]:
        with Session(self._engine) as session:
            rows = (
                session.query(JobRow)
                .order_by(case((JobRow.created_at.is_(None), 1), else_=0), JobRow.created_at.desc())
                .limit(limit)
                .all()
            )
            return [self._job(row) for row in rows]

    def get_job(self, job_id: str) -> Job | None:
        with Session(self._engine) as session:
            row = session.get(JobRow, job_id)
            if row is None:
                return None
            return self._job(row)

    def delete_job(self, job_id: str) -> None:
        with Session(self._engine) as session:
            session.query(VideoRow).filter(VideoRow.job_id == job_id).delete()
            row = session.get(JobRow, job_id)
            if row is not None:
                session.delete(row)
            session.commit()

    def list_videos(self, limit: int = 50) -> list[VideoItem]:
        with Session(self._engine) as session:
            rows = session.query(VideoRow).order_by(VideoRow.id.desc()).limit(limit).all()
            return [
                VideoItem(
                    job_id=row.job_id,
                    platform=row.platform,
                    source_url=row.source_url,
                    title=row.title,
                    video_url=row.video_url,
                    cover_url=row.cover_url,
                    raw={"id": row.id, **(row.raw or {})},
                )
                for row in rows
            ]

    def delete_video(self, video_id: int) -> None:
        with Session(self._engine) as session:
            row = session.get(VideoRow, video_id)
            if row is not None:
                session.delete(row)
                session.commit()

    def add_log(self, job_id: str, level: str, message: str) -> None:
        with Session(self._engine) as session:
            session.add(LogRow(job_id=job_id, level=level, message=message[:4000]))
            session.commit()

    def list_logs(self, limit: int = 200) -> list[dict]:
        with Session(self._engine) as session:
            rows = session.query(LogRow).order_by(LogRow.id.desc()).limit(limit).all()
            return [
                {
                    "id": row.id,
                    "created_at": row.created_at.isoformat(sep=" ", timespec="seconds") if row.created_at else "",
                    "job_id": row.job_id,
                    "level": row.level,
                    "message": row.message,
                }
                for row in reversed(rows)
            ]

    @staticmethod
    def _job(row: JobRow) -> Job:
        return Job(
            id=row.id,
            url=row.url,
            keyword=row.keyword,
            capability=row.capability,  # type: ignore[arg-type]
            platform=row.platform,
            status=row.status,
            error=row.error,
        )
