from icalendar import Calendar, Event
from typing import List
from datetime import datetime, timedelta
from typing_extensions import TypedDict
import pytz

from extractor import MonthData

class EventData(TypedDict):
    text: str
    start: datetime
    end: datetime
    event_type: str

class Parser:
    @classmethod
    def _parse_date(cls, text:str) -> datetime:
        return datetime.strptime(text, "%Y-%m-%d").replace(tzinfo=pytz.timezone("America/Sao_Paulo"))
    

    @classmethod
    def _factory_event(cls,
        start_date:datetime,
        end_date:datetime, 
        summary:str,
        description:str,
        categories:List[str]
    ) -> Event:

        event = Event()
        event.add('summary', summary)
        event.add('dtstart', start_date)
        event.add('dtend', end_date)
        event.add('dtstamp', datetime.now())
        event.add('location', 'UFSCar - São Carlos')
        event.add('description', description)
        event.add('class', 'PUBLIC')
        event.add('categories', categories)
        return event

    @classmethod
    def _parse_events_by_type(cls, data:MonthData, type:str) -> List[Event]:
        events: List[Event] = []
        
        for month_data in data:
            for item in month_data[type]:
                start_date = cls._parse_date(item['start'])
                end_date = cls._parse_date(item['end'])

                summary = item['text']
                description = item['_raw']
                categories = [type]

                if item['connector'] == 'and':
                    events.append(cls._factory_event(
                        start_date,
                        start_date + timedelta(days=1),
                        summary,
                        description,
                        categories
                    ))
                    events.append(cls._factory_event(
                        end_date,
                        end_date+ timedelta(days=1),
                        summary,
                        description,
                        categories
                    ))
                else:
                    end_date = end_date + timedelta(days=1)
                    events.append(cls._factory_event(
                            start_date,
                            end_date,
                            summary,
                            description,
                            categories
                    ))

        return events
        
    @classmethod
    def _parse_events(cls, data:MonthData) -> List[Event]:
        holidays = cls._parse_events_by_type(data, "holidays")
        students = cls._parse_events_by_type(data, "students")
        teachers = cls._parse_events_by_type(data, "teachers")

        return holidays + students + teachers

    @classmethod
    def generate_calendar(cls, data:MonthData) -> Calendar:
        parsed_events = cls._parse_events(data)
        calendar = Calendar()
        # set timezone
        calendar.add('prodid', '-//UFSCar Calendar//UFSCar//')
        calendar.add('version', '2.0')
        calendar.add('X-WR-CALNAME', 'UFSCar Calendar')
        calendar.add('X-WR-TIMEZONE', 'America/Sao_Paulo')
        
        for event in parsed_events:
            calendar.add_component(event)

        return calendar
