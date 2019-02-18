import sys
import smtplib

from pprint import pprint
from bs4 import BeautifulSoup
from urllib.request import urlopen
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from AutoDelayRepay.AutoDelayRepay.stations import STATIONS
from AutoDelayRepay.AutoDelayRepay.recipients import RECIPIANTS
from AutoDelayRepay.AutoDelayRepay.passwords import PASSWORD
from jinja2 import Environment, select_autoescape, FileSystemLoader

"""
TODO - 2018-03-02
National Rail API

https://github.com/DanteLore/national-rail
https://github.com/prabhu/pynationalrail


TODO - 2018-05-27 
    Email should send once for both route. CHM-LST and LST-CHM
    When a train is cancelled we need to find the next one that will arrive.
    
"""

env = Environment(
    # loader=PackageLoader('AutoDelayRepay', 'templates'), # this does not seem to work from command line
    loader=FileSystemLoader('H:\\Code\\PycharmProjects\\AutoDelayRepay\\AutoDelayRepay\\Templates'),
    autoescape=select_autoescape(['html']),
)
DELAY_TEMPLATE = env.get_template('delayed_trains_email.html')
# URL = 'http://recenttraintimes.co.uk/Home/Search?Op=Srch&Fr={0}To={1}TimTyp=D&TimDay=A&Days=Al&TimPer=7d&dtFr={2}&dtTo={3}&ShwTim=AvAr&TOC=All&ArrSta=5&MetAvg=Mea&MetSpr=RT&MxScDu=&MxSvAg=35&MnScCt=&MxArCl=5'
# URL2 = 'http://www.recenttraintimes.co.uk/Home/Search?Op=Srch&Fr=Chelmsford+%28CHM%29&To=London+Liverpool+Street+%28LST%29&TimTyp=A&TimDay=A&Days=Wk&TimPer=7d&dtFr=&dtTo=&ShwTim=AvAr&TOC=All&ArrSta=5&MetAvg=Mea&MetSpr=RT&MxScDu=&MxSvAg=&MnScCt=&MxArCl=5'
URL ='http://recenttraintimes.co.uk/Home/Search?Op=Srch&Fr={0}To={1}TimTyp=A&TimDay=A&Days=Wk&TimPer=Cu&dtFr={2}&dtTo={3}&ShwTim=AvAr&TOC=All&ArrSta=5&MetAvg=Mea&MetSpr=RT&MxScDu=&MxSvAg=&MnScCt=&MxArCl=5'

_TESTING_DATES1 = '21 02 2018'
_TESTING_DATES2 = '28 02 2018'
_FROM = 'CHM'
_TO = 'CHM'


def get_station(code):
    return STATIONS[code]


def get_html(origin='CHM', destination='LST', dateTo=None, dateFrom=None):
    if not dateTo:
        dateTo = datetime.today().date()
    if not dateFrom:
        dateFrom = dateTo - timedelta(7)

    return urlopen(
        URL.format(
            get_station(origin),
            get_station(destination),
            datetime.strftime(dateFrom, '%d %m %Y').replace(' ', '%2F'),
            datetime.strftime(dateTo,  '%d %m %Y').replace(' ', '%2F'),
        )
    ).read()


def sanitize_text(string):
    return string.replace(u'\xa0', '').replace(u'\xbdL', '')


def extract_headers(soup):
    return [sanitize_text(th.text) for th in soup.find_all('th') if not (th.get('colspan') or 'Arrivals' in th.text or th.text == '')]


def extract_rows(soup):
    chunks = 11 # We need to split the data into chuncks of each train. There are 11 columns of data in this table. Given a full week.
    td = [sanitize_text(td.text) for td in soup.find_all('td')] # '*' filter out the midnight trains.
    return [td[x:x+chunks] for x in range(0, len(td), chunks) if not td[x:x+chunks][1].startswith('*')]


def format_table(soup):
    html_tbl = soup.find_all('table')[1] # Its the second table on this page.

    return extract_headers(html_tbl), extract_rows(html_tbl)


def train_durations(headers, trains_data, days, origin='CHM', destination='LST', date_format='%a %d'):
    delay_mapping = []
    days_format = [day.strftime(date_format) for day in days]
    days_format2 = ['%s %s/%s' % (_day[:2], _date.lstrip('0'), _month.lstrip('0')) for (_day, _date, _month) in [(dt.strftime('%a'), dt.strftime('%d'), dt.strftime('%m')) for dt in days]]

    for train_times in trains_data:
        train_data = dict(zip(headers, train_times))

        train_delays = dict(
            due=train_data['a %s' % destination],
            dept=train_data['d %s' % origin],
        )

        for i, day in enumerate(days_format):
            delay = None
            arrival_on_day = train_data.get(day, train_data.get(days_format2[i]))

            if 'L' in arrival_on_day:
                delay = int(arrival_on_day[5:].rstrip('L'))
            train_delays[day] = delay

        delay_mapping.append(train_delays)

    return delay_mapping


def filter_delays(delays, delay_limit=30):
    delayed_trains = []

    for train in delays:
        for day, delay in train.items():
            if day not in ['due', 'dept'] and delay and delay > delay_limit:
                print('%s was delayed by %s mins' % (train['due'], delay))

                delayed_trains.append(
                    {
                        'date': day,
                        'due': train['due'],
                        'dept': train['dept'],
                        'delay': delay,
                    }
                )

    return delayed_trains

def find_days(date):
    return [(date - timedelta(i)).date() for i in range(7) if (date - timedelta(i)).weekday() < 5]


def email_delayed_train(delayed_trains, origin='FROM', dest='TO', days=None):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = '%i Delayed Trains %s-%s for %s' % (len(delayed_trains), origin, dest, datetime.today().date())
    html = DELAY_TEMPLATE.render(
        date=datetime.today().date(), trains=delayed_trains, origin=origin, destination=dest, days=days
    )
    msg.attach(MIMEText(html, 'html'))

    # Send the message via my googlemail account.
    # Server and port below.
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.ehlo()
    s.starttls()
    s.login('haydn.murray1', PASSWORD)
    if RECIPIANTS != ['haydn.murray1@googlemail.com']:
        raise ValueError('Are you sure you want to send to all?')

    s.sendmail('haydn.murray1@googlemail.com', RECIPIANTS + ['haydn.murray1@yahoo.co.uk'], msg.as_string())
    print('Sent email to %s on %s regarding %i delayed trains.' % (RECIPIANTS, datetime.today().date(), len(delayed_trains)))
    s.quit()

def main(origin='CHM', destination='LST', date=None):

    date = date or datetime.today() # datetime(2018, 3, 2)
    days = find_days(date)
    print('Searching for the following days: \n', pprint(days))

    # 1 - Parse the Website data
    html = get_html(origin=origin, destination=destination, dateTo=date)
    soup = BeautifulSoup(html, 'html.parser')
    headers, rows = format_table(soup)

    # 2 - Work out train arrival times and delays
    delays = train_durations(headers, rows, days, origin=origin, destination=destination)
    delayed = filter_delays(delays, delay_limit=30)

    print('Delayed trains: \n', pprint(delayed))
    # 3 - Email Delays Out
    email_delayed_train(
        sorted(delayed, key=lambda k:k['delay'])[::-1],
        origin=origin,
        dest=destination,
        days=days,
    )


def _main(origin, dest, *args):
    def getDefaultDate():
        t = datetime.today()
        while t.weekday() != 4:
            t = t - timedelta(1)

        return t.strftime('%Y%m%d')

    kwargs = {}
    if args[0]:
        for arg in args[0]:
            kwargs[arg.split('=')[0]] = arg.split('=')[1]

    date = datetime.strptime(kwargs.get('date', getDefaultDate()), '%Y%m%d')
    main(origin=origin, destination=dest, date=date)

if __name__ == '__main__':
    DEBUG = False # TODO set this to false once finished

    if DEBUG:
        _main('LST', 'CHM', [])
    else:
        _main(sys.argv[1], sys.argv[2], sys.argv[3:])

    print('Finshed mofos')
