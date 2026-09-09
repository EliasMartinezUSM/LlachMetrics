from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    full_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    password: Mapped["PasswordHash"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class PasswordHash(Base):
    __tablename__ = "pwd_hash"

    id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    hash: Mapped[str] = mapped_column(Text)
    user: Mapped[User] = relationship(back_populates="password")
