#! /usr/bin/env python3

from datetime import datetime, timedelta
import ephem
import math
import pytz
import svgwrite

params = {
  'vscale': 30,   # Height of an hour
  'hscale': 2.5,    # Width of a day
  'day-fill': 'rgb(250, 250, 255)',
  'civil-fill': 'rgb(128, 128, 255)',
  'nautical-fill': 'rgb(0, 0, 255)',
  'astro-fill': 'rgb(0, 0, 128)',
  'night-fill': 'rgb(0, 0, 64)',
  'padding-top': 30,
  'padding-left': 30,
  'padding-bottom': 30,
  'padding-right': 30,
  'start-date': datetime(2018, 1, 2),
  'end-date': datetime(2019, 1, 1, 12),
  'latitude': '-33.865143',
  'longitude': '151.209900',
  'timezone': 'Australia/Sydney',
  'use-dst': True,
  'filename': 'drawing.svg',
}

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
    return [d.datetime().replace(tzinfo=pytz.utc).astimezone(tz) for d in dates]

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
    events.antitransit, = localize(min(
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

calc_params = {}

def hours_since_midnight(date):
  return date.hour + date.minute/60 + date.second/3600

def date_to_point(date):
  day_diff = (date - params['start-date']).days
  time_diff = calc_params['latest-rise'] - hours_since_midnight(date)
  if date.hour >= 12:
    day_diff += 1
    time_diff += 24
  x = day_diff * params['hscale'] + params['padding-left']
  y = time_diff * params['vscale'] + params['padding-top']
  return x, y

def get_sun_event_path(events, key1, key2):
  path = svgwrite.path.Path()
  path.push('M ')
  for e in events:
    path.push('%.2f %.2f ' % date_to_point(key1(e)))
  for e in reversed(events):
    path.push('%.2f %.2f ' % date_to_point(key2(e)))
  path.push('z')
  return path

def main():
  observer = ephem.Observer()
  observer.lat = params['latitude']
  observer.lon = params['longitude']
  timezone = pytz.timezone(params['timezone'])
  params['start-date'] = params['start-date'].replace(tzinfo=timezone)
  params['end-date'] = params['end-date'].replace(tzinfo=timezone)

  sun_events = get_sun_events(observer,
      params['start-date'], params['end-date'])

  # Calculate data-dependent layout parameters
  temp = min(sun_events, key = lambda x: x.set.time()).set
  calc_params['earliest-set'] = 24 - hours_since_midnight(temp)
  temp = max(sun_events, key = lambda x: x.rise.time()).rise
  calc_params['latest-rise'] = hours_since_midnight(temp)
  calc_params['canvas-width'] = \
      (params['end-date'] - params['start-date']).days * params['hscale'] \
      + params['padding-left'] + params['padding-right']
  calc_params['canvas-height'] = (calc_params['earliest-set'] 
      + calc_params['latest-rise']) * params['vscale'] \
      + params['padding-top'] + params['padding-bottom']

  drawing = svgwrite.Drawing(params['filename'], profile='tiny',
      size=(calc_params['canvas-width'], calc_params['canvas-height']))

  # Add a border and background for debug purposes
  border = svgwrite.path.Path()
  border.push('M 0 0 %d 0 %d %d 0 %d Z' % (calc_params['canvas-width'],
    calc_params['canvas-width'], calc_params['canvas-height'],
    calc_params['canvas-height']))
  border.attribs['fill'] = params['day-fill']
  border.attribs['stroke'] = 'black'
  border.attribs['stroke-width'] = '4'
  drawing.add(border)

  # Draw civil twilight path
  civil_twilight_path = get_sun_event_path(sun_events,
      lambda x: x.rise, lambda x: x.set)
  civil_twilight_path.attribs['fill'] = params['civil-fill']
  drawing.add(civil_twilight_path)

  # Draw nautical twilight path
  nautical_twilight_path = get_sun_event_path(sun_events,
      lambda x: x.civil_twilight_am, lambda x: x.civil_twilight_pm)
  nautical_twilight_path.attribs['fill'] = params['nautical-fill']
  drawing.add(nautical_twilight_path)

  # Draw astronomical twilight path
  astro_twilight_path = get_sun_event_path(sun_events,
      lambda x: x.nautical_twilight_am, lambda x: x.nautical_twilight_pm)
  astro_twilight_path.attribs['fill'] = params['astro-fill']
  drawing.add(astro_twilight_path)

  # Draw night path
  night_path = get_sun_event_path(sun_events,
      lambda x: x.astro_twilight_am, lambda x: x.astro_twilight_pm)
  night_path.attribs['fill'] = params['night-fill']
  drawing.add(night_path)

  drawing.save()

if __name__ == '__main__':
  main()
