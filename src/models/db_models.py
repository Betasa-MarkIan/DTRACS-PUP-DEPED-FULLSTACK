from sqlalchemy import event, text, Column, String, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
import re

class AdminAccount(Base):
    __tablename__ = "admin"

    user_id = Column(CHAR(36), primary_key=True, index=True)
    office = Column(CHAR(36), nullable=False)
    office_description = Column(String(200), nullable=False)
    last_name = Column(String(50), nullable=False)
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    failed_login_attempt = Column(Integer, default=0)
    lock_until = Column(DateTime, nullable=True)


class FocalAccountsRequest(Base):
    __tablename__ = "focal_request"

    user_id = Column(CHAR(36), primary_key=True, index=True)
    last_name = Column(String(50), nullable=False)
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    full_name = Column(String(150), nullable=False)
    office = Column(String(100), nullable=False)
    section_designation = Column(String(100), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    contact_number = Column(String(20), nullable=True)
    password = Column(String(255), nullable=False)
    registration_date = Column(DateTime, default=datetime.now)
    avatar = Column(String(500), nullable=True)


class FocalAccountsVerified(Base):
    __tablename__ = "focal_verified"

    user_id = Column(CHAR(36), primary_key=True, index=True)
    last_name = Column(String(50), nullable=False)
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    full_name = Column(String(150), nullable=False)
    office = Column(String(100), nullable=False)
    section_designation = Column(String(100), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    contact_number = Column(String(20), nullable=True)
    password = Column(String(255), nullable=False)
    registration_date = Column(DateTime, default=datetime.now)
    avatar = Column(String(500), nullable=True)
    
    task_creator = relationship("Tasks", back_populates="creator", cascade="all, delete-orphan")


class SchoolAccountsRequest(Base):
    __tablename__ = "school_request"

    user_id = Column(CHAR(36), primary_key=True, index=True)
    last_name = Column(String(50), nullable=False)
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    full_name = Column(String(150), nullable=False)
    school_name = Column(String(200), nullable=False)
    school_address = Column(String(300), nullable=False)
    position = Column(String(100), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    contact_number = Column(String(20), nullable=True)
    password = Column(String(255), nullable=False)
    registration_date = Column(DateTime, default=datetime.now)
    avatar = Column(String(500), nullable=True)


class SchoolAccountsVerified(Base):
    __tablename__ = "school_verified"

    user_id = Column(CHAR(36), primary_key=True, index=True)
    last_name = Column(String(50), nullable=False)
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50), nullable=True)
    full_name = Column(String(150), nullable=False)
    school_name = Column(String(200), nullable=False)
    school_address = Column(String(300), nullable=False)
    position = Column(String(100), nullable=True)
    email = Column(String(150), unique=True, index=True, nullable=False)
    contact_number = Column(String(20), nullable=True)
    password = Column(String(255), nullable=False)
    registration_date = Column(DateTime, default=datetime.now)
    avatar = Column(String(500), nullable=True)

    assignments = relationship("TaskAssignment", back_populates="account", cascade="all, delete-orphan")


class Tasks(Base):
    __tablename__ = "tasks"

    task_id = Column(CHAR(36), primary_key=True, index=True)
    creator_id = Column(CHAR(36), ForeignKey("focal_verified.user_id"),nullable=False)
    creator_name = Column(String(100), nullable=False)
    office = Column(String(150), nullable=False)
    section = Column(String(150), nullable=False)
    creation_date = Column(DateTime, default=datetime.now, nullable=False)
    modified_date = Column(DateTime, default=None, nullable=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=False)
    task_status = Column(String(100), nullable=False)
    status_updated_at = Column(DateTime, default=None)
    links = Column(JSON, default=list, nullable=True)

    creator = relationship("FocalAccountsVerified", back_populates="task_creator")

    assignments = relationship("TaskAssignment", back_populates="task", cascade="all")


class TaskAssignment(Base):
    __tablename__ = "task_assignment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(CHAR(36), ForeignKey("tasks.task_id"), nullable=False)
    school_id = Column(CHAR(36), ForeignKey("school_verified.user_id"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.now())
    status = Column(String(100), default="INCOMPLETE", nullable=False)
    status_updated_at = Column(DateTime, default=None)
    remarks = Column(String(150), default="PENDING", nullable=True)
    links = Column(JSON, default=list, nullable=True)

    task = relationship("Tasks", back_populates="assignments")
    account = relationship("SchoolAccountsVerified", back_populates="assignments")



# *id_gen
@event.listens_for(FocalAccountsRequest, 'before_insert')
def generate_focal_request_id(mapper, connection, target):
    if target.user_id is None:
        result = connection.execute(text(
            'SELECT user_id FROM focal_request ORDER BY user_id DESC LIMIT 1'
        ))
        last_id = result.scalar()

        if last_id:
            match = re.search(r'FREQ-(\d+)', str(last_id))
            if match:
                next_number = int(match.group(1)) + 1
            else:
                next_number = 1
        else: 
            next_number = 1

        target.user_id = f"FREQ-{next_number:04d}"

@event.listens_for(SchoolAccountsRequest, 'before_insert')
def generate_school_request_id(mapper, connection, target):
    if target.user_id is None:
        result = connection.execute(text(
            'SELECT user_id FROM school_request ORDER BY user_id DESC LIMIT 1'
        ))
        last_id = result.scalar()

        if last_id:
            match = re.search(r'SREQ-(\d+)', str(last_id))
            if match:
                next_number = int(match.group(1)) + 1
            else:
                next_number = 1
        else: 
            next_number = 1

        target.user_id = f"SREQ-{next_number:04d}"

@event.listens_for(FocalAccountsVerified, 'before_insert')
def generate_focal_verified_id(mapper, connection, target):
    if target.user_id is None:
        result = connection.execute(text(
            'SELECT user_id FROM focal_verified ORDER BY user_id DESC LIMIT 1'
        ))
        last_id = result.scalar()

        if last_id:
            match = re.search(r'FOCAL-(\d+)', str(last_id))
            if match:
                next_number = int(match.group(1)) + 1
            else:
                next_number = 1
        else: 
            next_number = 1

        target.user_id = f"FOCAL-{next_number:04d}"

@event.listens_for(SchoolAccountsVerified, 'before_insert')
def generate_school_verified_id(mapper, connection, target):
    if target.user_id is None:
        result = connection.execute(text(
            'SELECT user_id FROM school_verified ORDER BY user_id DESC LIMIT 1'
        ))
        last_id = result.scalar()

        if last_id:
            match = re.search(r'SCHOOL-(\d+)', str(last_id))
            if match:
                next_number = int(match.group(1)) + 1
            else:
                next_number = 1
        else: 
            next_number = 1

        target.user_id = f"SCHOOL-{next_number:04d}"
