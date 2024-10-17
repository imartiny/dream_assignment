from pydantic import BaseModel
from datetime import datetime
from typing import Dict, List, Optional, Union

# API request and response schemas
class IngestDataRequest(BaseModel):
    os_type: str
    content: str
    meta_info: dict

class IngestDataResponse(BaseModel):
    message: str
    records_processed: int

class QueryParams(BaseModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    os_type: Optional[str] = None
    type: Optional[str] = None
    machine_id: Optional[str] = None
    command: Optional[str] = None
    cpu_usage_gt: Optional[float] = None
    memory_usage_gt: Optional[float] = None
    limit: Optional[int] = 100
    offset: Optional[int] = 0
    aggregations: Optional[List[str]] = None


class ProcessDataBase(BaseModel):
    command: str
    pid: int
    vsz: int
    rss: int
    cpu_usage: float
    mem_usage: float
    tty: str
    stat: str
    start_time: str
    user: str
    timestamp: datetime
    machine_name: str
    machine_id: str
    os_type: str

class ProcessData(ProcessDataBase):
    id: int

    class Config:
        from_attributes = True

class QueryResponse(BaseModel):
    total_count: int
    records: List[Union[ProcessData, Dict]]

class ProcessDataResponse(BaseModel):
    process: ProcessData