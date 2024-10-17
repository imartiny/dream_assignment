from app.parsers.unix_parser import UnixParser
from app.parsers.windows_parser import WindowsParser


class ParserFactory:
    @staticmethod
    def get_parser(os_type: str):
        if os_type.lower() in ['linux', 'unix', 'mac']:
            return UnixParser()
        elif os_type.lower() == 'windows':
            return WindowsParser()
        else:
            raise ValueError(f"Unsupported OS type: {os_type}")