#! /usr/bin/env python3

from datetime import datetime, timedelta
import ephem
import math
import pytz
import svgwrite

class SunEvents:
  date = None
  set = None
  rise = None
  antitransit = None
  civil_twilight_pm = None
  nautical_twilight_pm = None
  astro_twilight_pm = None
  civil_twilight_am = None
  nautical_twilight_am = None
  astro_twilight_am = None

def get_set_rise(observer, body, horizon='0', use_center=False):
  original_horizon = observer.horizon
  observer.horizon = horizon
  result = (observer.previous_setting(body, use_center=use_center),
      observer.next_rising(body, use_center=use_center))
  observer.horizon = original_horizon
  return result

def get_sun_events(observer, start_date, end_date):
  def localize(*dates):
    for d in dates:
      yield d.datetime().replace(tzinfo=pytz.utc).astimezone(tz)

  sun = ephem.Sun()
  tz = start_date.tzinfo
  current_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
  current_date = current_date.astimezone(pytz.utc)
  one_day = timedelta(days=1)
  result = []
  while current_date < end_date:
    observer.date = ephem.Date(current_date)
    events = SunEvents()
    events.date = current_date
    events.set, events.rise = localize(*get_set_rise(observer, sun))

    # We don't know in advance whether solar midnight will fall before or after
    # clock midnight, so calculate both and take the nearer one.
    events.antitransit = localize(min(
        observer.previous_antitransit(sun),
        observer.next_antitransit(sun),
        key = lambda x: abs((current_date -
          x.datetime().replace(tzinfo=pytz.utc)).total_seconds())))

    # PyEphem's trick for calculating the various twilights is to lower the
    # horizon to the required angle, and then calculate the rise/set time.
    # The other quirk is that regular rise/set times measure from the sun's
    # upper limb, whereas twilight measures from the centre.
    events.civil_twilight_pm, events.civil_twilight_am = localize(
        *get_set_rise(observer, sun, horizon='-6', use_center=True))
    events.nautical_twilight_pm, events.nautical_twilight_am = localize(
        *get_set_rise(observer, sun, horizon='-12', use_center=True))
    events.astro_twilight_pm, events.astro_twilight_am = localize(
        *get_set_rise(observer, sun, horizon='-18', use_center=True))

    result.append(events)
    current_date += one_day
  return result

def main():
  drawing = svgwrite.Drawing('drawing.svg', profile='tiny', size=(100, 100))
  sydney = ephem.Observer()
  sydney.lat = '-33.865143'
  sydney.lon = '151.209900'
  sydney_tz = pytz.timezone('Australia/Sydney')

  sun_events_list = get_sun_events(sydney,
      sydney_tz.localize(datetime(2018, 1, 2)),
      sydney_tz.localize(datetime(2019, 1, 1, 12)))

  drawing.save()

if __name__ == '__main__':
  main()
