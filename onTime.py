import os.path
import datetime as dt
from datetime import timedelta
from dateutil import parser

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import string
import googlemaps
import twilio
from datetime import datetime, timedelta
from twilio.rest import Client
import time
import datetime

#parameters for calendar
CLIENT_FILE = r"path to client json file"
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_CLIENT_ADDRESS = "google dev email with shared access to calendar"
CALENDAR_KEY = "google calendar API use key"
API_NAME = 'calendar'
API_VERSION = 'v3'
recipients_list = ["user phone number verified on twilio website"]  #my phone number

import os
import datetime as dt
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

def string_to_datetime(string):
    # Converts an iso8601 date string into a datetime.datetime data type
    date_format = "%Y-%m-%d %H:%M:%S"
    try:
        string_datetime = datetime.datetime.strptime(string, date_format)
        return string_datetime
    except ValueError:
        print("Invalid date format. Please use the format YYYY-MM-DD HH:MM:SS.")
        return None

def get_daily_events():
    #reads all events from user google calendar
    creds = None
    locations = []
    datetimes = []

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
    try:
        service = build('calendar', 'v3', credentials=creds)
        now = dt.datetime.now().isoformat() + 'Z'
        tmo_temp = dt.datetime.now() + dt.timedelta(days=1)
        tmo = tmo_temp.isoformat() + "Z"
        event_result = service.events().list(calendarId='primary', timeMin=now, singleEvents=True, orderBy='startTime').execute()
        events = event_result.get("items", [])
        if not events:
            print("No events today")
            return
        for event in events:
            start = event['start'].get('dateTime', event["start"].get("date"))
            summary = event["summary"]
            location = event.get("location", "No location provided")
            # print(f"{start} - {summary} - Location: {location}")
            locations.append(location)
            datetimes.append(start)
        return locations, datetimes


    except HttpError as error:
        print('An error occurred:', error)


def split_date(class_datetime):
    # splits a datetime.datetime data type into a #"YYYY-MM-DD" string
    class_datetime = str(class_datetime)
    class_date = class_datetime[:10]
    return class_date


def split_time(class_datetime):
    # splits a datetime.datetime data type into a "HH:MM" string
    class_datetime = str(class_datetime)
    class_time = (((class_datetime.split())[1])[:-3])
    return class_time


def remove_colon(input):
    # removes punctuation from a string
    translator = str.maketrans("", "", string.punctuation)
    result = input.translate(translator)
    return result


def commute_duration(start, destination, ):  # add transport method
    API_KEY = 'google maps API key'
    maps_client = googlemaps.Client(API_KEY)
    route = maps_client.directions(start, destination, )
    # calculates best route, can add any method of transport in parameters, drive by default
    leg = route[0]['legs'][0]  # multiple legs with different transport methods soon in directions method and # of legs
    duration = leg['duration']['text']
    duration = duration.strip(' mins')
    duration = int(duration)
    # returns an integer for # of mins commute
    return duration


def get_tod_datetime(class_datetime, start, destination):
    # subtracts duration from event start time and returns as a datetime.datetime
    duration = commute_duration(start, destination)
    tod_datetime = class_datetime - timedelta(minutes=duration)
    return tod_datetime


def get_message_datetime(class_datetime, tod_datetime):
    '''subtracts time of departure and a 30min advance to send message at a reasonable time, returns a datetime'''
    difference_datetime = class_datetime - tod_datetime
    message_datetime = class_datetime - difference_datetime - timedelta(minutes=30)
    return message_datetime


def create_message(class_datetime, tod_datetime):
    # creates a message that will be sent to the user notifying them of what time they should leave for their event
    tod = split_time(tod_datetime)
    class_time = split_time(class_datetime)
    sms_message = (
        f"\nHello!\n"
        f"Just to make sure you are onTime today, \n"
        f"you will need to leave by {tod} to attend your {class_time} event on time."
    )
    return sms_message


def send_message(message, user_phone_num):
    # sends message to user via phone
    # twilio recovery code: TQE6W6QJGQ76BPQKYVV64E6K
    twilio_account_sid = "twilio account sid"
    twilio_account_token = "twilio account token"
    twilio_phone_number = "a verified phone number from twilio website"
    client = Client(twilio_account_sid, twilio_account_token)
    client.messages.create(
        from_=twilio_phone_number,
        to=user_phone_num,
        body=message)


def send_message_at_time(class_datetime, tod_datetime, start, destination, user_phone_num):
    # sends the message at the designated message time
    message_datetime = get_message_datetime(class_datetime, tod_datetime)
    while True:
        if datetime.datetime.now() >= message_datetime:
            tod = get_tod_datetime(class_datetime, start, destination)
            message = create_message(class_datetime, tod)
            send_message(message, user_phone_num)
            print("message sent!")
            break
        else:
            tod = get_tod_datetime(class_datetime, start, destination)
            message_datetime = get_message_datetime(class_datetime, tod)
            print("updated message datetime: ", message_datetime)
            time.sleep(60)


def main():
    user_phone_num = recipients_list[0]
    start_location = input("Enter your home address: ")
    locations, datetimes = get_daily_events()

    #for every event in the calendar organized by time, wait until tod-30mins to send message
    #then move to next element
    for event in range(len(datetimes)):
        #change format of datetimes
        tobesplit = datetimes[event]
        date_str, time_str = tobesplit.split("T")
        datetime_str = date_str + ' ' + time_str[:-6]
        start = string_to_datetime(datetime_str)
        now = datetime.datetime.now()
        #create condition to send messages
        message_sent = False
        while not message_sent:
            if get_tod_datetime(start, start_location, locations[event]) < datetime.datetime.now():
                tod_datetime = get_tod_datetime(start, start_location, locations[event])
                send_message_at_time(start, tod_datetime, start_location, locations[event], user_phone_num)
                message_sent = True


if __name__ == '__main__':
    main()