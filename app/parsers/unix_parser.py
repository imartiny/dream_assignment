from enum import Enum
import re

from fastapi import HTTPException
from app.models import ProcessData
from app.parsers.base import Parser
from typing import List, Dict, Any

class UnixPsFields(Enum):
    USER = 0
    PID = 1
    CPU = 2
    MEM = 3
    VSZ = 4
    RSS = 5
    TTY = 6
    STAT = 7
    START = 8
    TIME = 9
    COMMAND = 10


class UnixParser(Parser):
    def parse(self, content: str) -> List[Dict[str, Any]]:
        """
        Parse the output of 'ps auxww' command and create ProcessRecord objects.

        Args:
            output (str): The output of 'ps auxww' command.
            metadata (Dict): Metadata about the command execution.

        Returns:
            List[ProcessRecord]: A list of ProcessRecord objects.
        """
        lines = content.strip().split('\n')[1:]  # Skip the header
        process_datas = []

        if not lines:
            raise HTTPException(status_code=400, detail="psaux Content is invalid.")

        header = lines[0]
        if not header.startswith("USER"):
            raise HTTPException(status_code=400, detail="psaux Content is invalid.")

        for line in lines:
            fields = re.split(r'\s+', line.strip())
            if len(fields) != len(UnixPsFields.__members__):
                raise HTTPException(status_code=400, detail="psaux Content is invalid.")

            try:
                process_data = ProcessData(
                    user=fields[UnixPsFields.USER.value],
                    pid=int(fields[UnixPsFields.PID.value]),
                    cpu_usage=float(fields[UnixPsFields.CPU.value]),
                    mem_usage=float(fields[UnixPsFields.MEM.value]),
                    vsz=int(fields[UnixPsFields.VSZ.value]),
                    rss=int(fields[UnixPsFields.RSS.value]),
                    tty=fields[UnixPsFields.TTY.value],
                    stat=fields[UnixPsFields.STAT.value],
                    start_time=fields[UnixPsFields.START.value],
                    duration=fields[UnixPsFields.TIME.value],
                    command=' '.join(fields[UnixPsFields.COMMAND.value:])
                )
                process_datas.append(process_data)  # Collect ProcessRecord instances
            except Exception:
                raise HTTPException(status_code=400, detail="psaux Content is invalid.")

        return process_datas