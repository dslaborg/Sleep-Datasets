import datetime
import re
import time
import xml.etree.ElementTree as ET

from psg_utils.io.hypnogram.dhedreader import BaseEDFReader


def extract_from_xml(file_path: str):
    # example event:
    # <ScoredEvent>
    # <EventType/>
    # <EventConcept>Recording Start Time</EventConcept>
    # <Start>0</Start>
    # <Duration>30815.0</Duration>
    # <ClockTime>01.01.85 22.00.48</ClockTime>
    # </ScoredEvent>
    events = ET.parse(file_path).findall('ScoredEvents')
    assert len(events) == 1
    for event in events[0]:
        if not event[1].text == "Recording Start Time":
            continue
        clock_time = event[4].text
        if clock_time.startswith("00.00.00"):
            clock_time = datetime.datetime.strptime(clock_time, "00.00.00 %H.%M.%S")
        elif re.match(r"^\d{2}\.\d{2}\.\d{2}$", clock_time):
            clock_time = datetime.datetime.strptime(clock_time, "%H.%M.%S")
        else:
            clock_time = datetime.datetime.strptime(clock_time, "%d.%m.%y %H.%M.%S")
        # parse to universal time string
        clock_time = time.mktime(clock_time.timetuple())
        return clock_time


def extract_from_edf(file_path: str):
    with open(file_path, "rb") as in_f:
        base_edf = BaseEDFReader(in_f)
        base_edf.read_header()
        start_date = base_edf.header["date_time"]
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        start_date = time.mktime(start_date.timetuple())

    return start_date


def extract_start_time(file_path: str):
    if file_path.endswith(".xml"):
        return extract_from_xml(file_path)
    elif file_path.endswith(".edf") or file_path.endswith(".EDF") or file_path.endswith(".rec"):
        return extract_from_edf(file_path)
    else:
        return None
