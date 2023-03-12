import json
from extractor import Extractor
from parser import Parser

files = [
    "2021-suplementar",
    "2022",
    "2022-ferias",
    "2023",
]

for file in files:
    output = Extractor.extract(f"input/{file}.pdf")
    calendar = Parser.generate_calendar(output)
    with open(f"output/ics/{file}.ics", "wb") as f:
        f.write(calendar.to_ical())
    with open(f"output/json/{file}.json", "w") as f:
        f.write(json.dumps(output, indent=2, ensure_ascii=False))