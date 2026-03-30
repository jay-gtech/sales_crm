from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base_class import Base

VALID_ROLES = ("admin", "manager", "sales_rep")

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name       = Column(String, nullable=True)
    is_active       = Column(Boolean, default=True)

    # Role: "admin" | "manager" | "sales_rep"
    role       = Column(String, nullable=False, default="sales_rep", server_default="sales_rep")
    # Self-referential: who this user reports to
    manager_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Self-referential hierarchy
    manager = relationship(
        "User",
        remote_side="User.id",
        foreign_keys=[manager_id],
        back_populates="reports",
    )
    reports = relationship(
        "User",
        foreign_keys=[manager_id],
        back_populates="manager",
    )

    # Existing relationships — untouched
    deals = relationship("Deal", back_populates="owner")
    leads = relationship("Lead", back_populates="owner")

    # ── helpers ───────────────────────────────────────────────────────────────
    @property
    def display_name(self) -> str:
        return self.full_name or self.email.split("@")[0]

    @property
    def role_label(self) -> str:
        return {"admin": "Admin", "manager": "Manager", "sales_rep": "Sales Rep"}.get(
            self.role or "sales_rep", self.role or "sales_rep"
        )

    @property
    def is_admin(self) -> bool:
        return (self.role or "") == "admin"
