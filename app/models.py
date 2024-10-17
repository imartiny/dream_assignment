from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProcessData(Base):
    __tablename__ = 'process_data'

    id = Column(Integer, primary_key=True, index=True)
    command = Column(String, index=True)
    pid = Column(Integer, index=True)
    vsz = Column(Integer, index=True)
    rss = Column(Integer, index=True)
    cpu_usage = Column(Float, index=True)
    mem_usage = Column(Float, index=True)
    tty = Column(String, index=True)
    stat = Column(String, index=True)
    start_time = Column(String, index=True)
    duration = Column(String, index=True)
    user = Column(String)
    
    timestamp = Column(DateTime, index=True)
    machine_name = Column(String, index=True)
    machine_id = Column(String, index=True)
    os_type = Column(String)

    def to_dict(self):
        return {
            "id": self.id,
            "command": self.command,
            "pid": self.pid,
            "vsz": self.vsz,
            "rss": self.rss,
            "cpu_usage": self.cpu_usage,
            "mem_usage": self.mem_usage,
            "tty": self.tty,
            "stat": self.stat,
            "start_time": self.start_time,
            "user": self.user,
            "timestamp": self.timestamp,
            "machine_name": self.machine_name,
            "machine_id": self.machine_id,
            "os_type": self.os_type
        }
