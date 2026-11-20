from sqlalchemy import Column,Integer,String,Float,JSON,Text,UniqueConstraint
from src.config.database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(100),unique=True);password=Column(String(200));role=Column(String(20))
class Shipment(Base):
 __tablename__='shipments'
 id=Column(Integer,primary_key=True);code=Column(String(60),unique=True);route=Column(String(60));zone=Column(String(20));driver=Column(String(60))
class Sample(Base):
 __tablename__='samples'
 id=Column(Integer,primary_key=True);shipment_id=Column(Integer,index=True);code=Column(String(60),unique=True);exposure=Column(Float,nullable=True);excursions=Column(Integer,nullable=True);loss=Column(Float,nullable=True)
class Study(Base):
 __tablename__='studies'
 id=Column(Integer,primary_key=True);name=Column(String(100));zone=Column(String(20));feature=Column(String(30));state=Column(String(20),default='queued');result=Column(JSON,nullable=True);error=Column(Text,default='')
class Recommendation(Base):
 __tablename__='recommendations'
 id=Column(Integer,primary_key=True);study_id=Column(Integer);note=Column(Text);owner=Column(String(60));status=Column(String(20),default='draft')
class Audit(Base):
 __tablename__='audits'
 id=Column(Integer,primary_key=True);actor=Column(String(100));action=Column(String(200));created=Column(String(40))
class Survey(Base):
 __tablename__='surveys'
 id=Column(Integer,primary_key=True);name=Column(String(100));request_key=Column(String(64),unique=True,nullable=True);zone=Column(String(20),default='冷藏');seed=Column(String(32));frame=Column(JSON);key_routes=Column(JSON,nullable=True);n=Column(Integer);n1=Column(Integer);n2_quota=Column(Integer,default=0);n2=Column(Integer,default=0);pool=Column(Integer,default=0);state=Column(String(20),default='inspecting');result=Column(JSON,nullable=True)
class Inspection(Base):
 __tablename__='inspections'
 __table_args__=(UniqueConstraint('survey_id','shipment_id'),)
 id=Column(Integer,primary_key=True);survey_id=Column(Integer,index=True);shipment_id=Column(Integer);code=Column(String(60));route=Column(String(60));phase=Column(Integer);probability=Column(Float);loss=Column(Float,nullable=True);state=Column(String(20),default='pending')
