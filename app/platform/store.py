from sqlalchemy import JSON, String, Text, create_engine
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


class Store:
    def __init__(self, settings: Settings):
        self._engine = create_engine(settings.mysql_url, pool_pre_ping=True)

    def create_tables(self) -> None:
        Base.metadata.create_all(self._engine)

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
            rows = session.query(JobRow).limit(limit).all()
            return [
                Job(
                    id=row.id,
                    url=row.url,
                    keyword=row.keyword,
                    capability=row.capability,  # type: ignore[arg-type]
                    platform=row.platform,
                    status=row.status,
                    error=row.error,
                )
                for row in rows
            ]
