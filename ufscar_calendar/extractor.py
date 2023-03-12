import pdfplumber
import re
from datetime import datetime, timedelta
from typing import List, Union, Tuple
from typing_extensions import TypedDict

regex_date = r"(\d{1,2})(/(\d{1,2}))?"
regex_dates = rf"({regex_date})(\s(a|e)\s({regex_date}))?"
regex_dates_with_separator = rf"({regex_dates}) (-|\u2013)"
regex_indices = rf"(\n{regex_dates_with_separator}(\s|\n)[a-zA-Z])"

class RawDate(TypedDict):
    month: str
    year: str

class RawEvent(TypedDict):
    text: str
    _raw: str
    start: str
    connector: Union[str, None]
    end: str

class MonthData(TypedDict):
    month: str
    year: str
    holidays: List[RawEvent]
    students: List[RawEvent]
    teachers: List[RawEvent]

class Extractor:
    @classmethod
    def extract(cls, path:str) -> List[MonthData]:
        tables = cls._extract_raw_tables(path)
        output = cls._parse_tables(tables)
        return output

    @classmethod
    def _extract_raw_tables(cls, path: str) -> List[List[List[Union[str,None]]]]:
        tables = []
        with pdfplumber.open(path) as pdf:
            pages = pdf.pages
            for page in pages:
                table = page.extract_table()
                tables.append(table)
        
        return tables
    
    @classmethod
    def _get_columns(cls, row: List[Union[str,None]]) -> Tuple[str,str,str]:
        length = len(row)
        if length == 18:
            return row[9] or '', row[12] or '', row[15] or ''
        elif length == 19:
            return row[10] or '', row[13] or '', row[16] or ''
        elif length == 12:
            return row[9] or '', row[10] or '', row[11] or ''
        elif length == 16:
            return row[9] or '', row[10] or '', row[13] or ''
        else:
            raise Exception("Invalid row length")
    
    @classmethod
    def _translate_month(cls, month: str) -> str:
        month = month.upper()
        if month == "JANEIRO":
            return "January"
        elif month == "FEVEREIRO":
            return "February"
        elif month == "MARÇO":
            return "March"
        elif month == "ABRIL":
            return "April"
        elif month == "MAIO":
            return "May"
        elif month == "JUNHO":
            return "June"
        elif month == "JULHO":
            return "July"
        elif month == "AGOSTO":
            return "August"
        elif month == "SETEMBRO":
            return "September"
        elif month == "OUTUBRO":
            return "October"
        elif month == "NOVEMBRO":
            return "November"
        elif month == "DEZEMBRO":
            return "December"
        else:
            raise Exception("Invalid month")

    @classmethod
    def _get_date(cls, text:str) -> Union[RawDate, None]:
        regex = r"(JANEIRO|FEVEREIRO|MARÇO|MAIO|ABRIL|JUNHO|JULHO|AGOSTO|SETEMBRO|OUTUBRO|NOVEMBRO|DEZEMBRO)\s(\d{4})"
        match = re.match(regex, text, re.RegexFlag.IGNORECASE)
        if match is None:
            return None
        
        raw_month = match.group(1)
        month = cls._translate_month(raw_month)
        year = match.group(2)
        return {
            "month": month,
            "year": year
        }

    @classmethod
    def _split_by_indices(cls, text: str, indices: List[int]) -> List[str]:
        return [text[i:j] for i,j in zip(indices, indices[1:]+[None])]

    @classmethod
    def _get_indices(cls, text: str) -> List[int]:
        matches = re.finditer(regex_indices, text, re.MULTILINE)
        indices = [match.start() for match in matches]
        indices.insert(0, 0)
        return indices
    
    @classmethod
    def _format_item(cls, item:str)-> str:
        return item.replace("\n", " ").strip().replace(r"\s{2}", " ").replace("\u2013","-")

    @classmethod
    def _parse_date(cls, date:Union[str, None], default_month:str, default_year:str) -> Union[str, None]:
        if date == None:
            return None
        
        match = re.match(regex_date, date, re.RegexFlag.IGNORECASE)
        if match is None:
            raise Exception("Invalid date")
        
        day = match.group(1)
        raw_month = match.group(3)
        has_month = raw_month is not None

        date_str = f"{day}/{raw_month}/{default_year}" if has_month else f"{day} {default_month} {default_year}"
        parsed_date = datetime.strptime(date_str, "%d/%m/%Y" if has_month else "%d %B %Y")

        return parsed_date.strftime("%Y-%m-%d")

        

    @classmethod
    def _parse_item(cls, item:str, date: RawDate) -> RawEvent:
        match = re.match(regex_dates, item, re.RegexFlag.IGNORECASE)
        if match is None:
            raise Exception("Invalid item")

        raw_start = match.group(1)
        raw_connector = match.group(6)
        raw_end = match.group(7)
        start_date = cls._parse_date(raw_start, date["month"], date["year"])
        end_date = cls._parse_date(raw_end, date["month"], date["year"])

        has_connector = raw_connector is not None
        connector = None
        if has_connector:
            parsed_connector = raw_connector.strip().lower()
            if parsed_connector == "a":
                connector = "to"
            elif parsed_connector == "e":
                connector = "and"
            else:
                raise Exception("Invalid connector")


        if start_date is None:
            raise Exception("Invalid start date")
        
        if end_date is None:
            # If there is no end date, the event is only one day
            end_date = start_date

        parsed_text = re.sub(regex_dates_with_separator, "", item, 0, re.RegexFlag.IGNORECASE).strip()
        event: RawEvent = {
            "start": start_date,
            "connector": connector,
            "end": end_date,
            "text": parsed_text,
            "_raw": item
        }
        
        return event
        
    @classmethod
    def _parse_items(cls, text: Union[str, None], date: RawDate) -> List[RawEvent]:
        if text == None:
            return []
        indices = cls._get_indices(text)
        items = cls._split_by_indices(text,indices)
        
        mapped_items = list(filter(lambda x: len(x) > 0, map(cls._format_item, items)))


        parsed_items = [cls._parse_item(item, date) for item in mapped_items]

        return parsed_items
    
    @classmethod
    def _parse_tables(cls, tables: List[List[List[Union[str,None]]]]) -> List[MonthData]:
        parsed_data: List[MonthData] = []

        for table in tables:
            for row in table:
                if row is None:
                    continue

                text = "".join(map(str,filter(lambda x: x != None, row)))
                date = cls._get_date(text)
                if date:
                    raw_feriados, raw_estudantes, raw_professores = cls._get_columns(row)
                    
                    feriados = cls._parse_items(raw_feriados, date)
                    estudantes = cls._parse_items(raw_estudantes, date)
                    professores = cls._parse_items(raw_professores, date)

                    item: MonthData = {
                        "month": date['month'],
                        "year": date['year'],
                        "holidays": feriados,
                        "students": estudantes,
                        "teachers": professores
                    }
                    parsed_data.append(item)

        return parsed_data



