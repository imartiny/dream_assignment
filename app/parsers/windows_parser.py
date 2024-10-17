from app.models import ProcessData
from app.parsers.base import Parser
from typing import List
from enum import Enum


class WindowsTasklistFields(Enum):
    IMAGE_NAME = 0
    PID = 1
    SESSION_NAME = 2
    SESSION = 3
    MEM_USAGE = 4

class WindowsParser(Parser):
    def parse(self, content: str) -> List[ProcessData]:
        """
        Parse the content of 'tasklist' command and create ProcessRecord objects.

        Args:
            oucontenttput (str): The content of 'tasklist' command.
            meta_info (MetaInfo): Metadata about the command execution.

        Returns:
            List[ProcessRecord]: A list of ProcessRecord objects.
        """
        lines = content.splitlines()

        # Identify the header and separator lines
        separator_line_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('='):
                separator_line_index = i
                break

        # Extract the header and data lines
        separator = lines[separator_line_index]
        data_lines = lines[separator_line_index + 1:]

        # Dynamically identify the column positions based on the '=' separator line
        column_positions = []
        for i, char in enumerate(separator):
            if char == '=' and (i == 0 or separator[i - 1] != '='):
                column_positions.append(i)

        process_datas = []

        for line in data_lines:
            fields = [line[column_positions[i]:column_positions[i+1]].strip()
                      for i in range(len(column_positions) - 1)] + [line[column_positions[-1]:].split()[0]]
            mem_usage = fields[WindowsTasklistFields.MEM_USAGE.value]

            #  In tasklist mem_usage can be N/A
            try:
                mem_usage = float(mem_usage.replace(',', '').replace('K', ''))
            except Exception:
                mem_usage = float(0.0)

            process_data = ProcessData(
                user="N/A",  # Tasklist doesn't provide user information
                pid=int(fields[WindowsTasklistFields.PID.value]),
                cpu_usage=0.0,  # Tasklist doesn't provide CPU usage
                mem_usage=mem_usage,
                vsz=0,  # Tasklist doesn't provide VSZ
                rss=0,  # Tasklist doesn't provide RSS
                tty=fields[WindowsTasklistFields.SESSION_NAME.value],
                stat="N/A",  # Tasklist doesn't provide status
                start_time="N/A",  # Tasklist doesn't provide start time
                duration="N/A",  # Tasklist doesn't provide duration time
                command=fields[WindowsTasklistFields.IMAGE_NAME.value],
            )

            process_datas.append(process_data)  # Collect ProcessRecord instances

        return process_datas