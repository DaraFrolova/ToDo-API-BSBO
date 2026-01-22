from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship, mapped_column
from sqlalchemy.sql import func
from database import Base

class Task(Base):
    __tablename__ = "tasks"
    
    id = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title = mapped_column(Text, nullable=False)
    description = mapped_column(Text, nullable=True)
    is_important = mapped_column(Boolean, nullable=False, default=False)
    is_urgent = mapped_column(Boolean, nullable=False, default=False)
    quadrant = mapped_column(String(2), nullable=False, default='Q4')
    completed = mapped_column(Boolean, nullable=False, default=False)
    created_at = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at = mapped_column(DateTime(timezone=True), nullable=True)
    
    user_id = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="tasks")
    
    # Конструктор не нужен при использовании mapped_column с default
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', quadrant='{self.quadrant}')>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "is_important": self.is_important,
            "is_urgent": self.is_urgent,
            "quadrant": self.quadrant,
            "completed": self.completed,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "deadline_at": self.deadline_at,
            "user_id": self.user_id
        }