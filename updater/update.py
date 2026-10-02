# -*- coding: utf-8 -*-
"""毎日の更新: 取る → 確かめる → 並べる → サイト用の JSON を書く。

  python updater/update.py            足りない日だけ取得して作り直す
  python updater/update.py --no-fetch 取得せず、手元の履歴から作り直す

履歴は data/history/YYYY.csv（1 行 1 日・列は通貨コード・値は 1 ドルあたりの現地通貨）。
出力は site/data/latest.json（ランキング）と site/data/series/<コード>.json（国別の画面）。
"""
import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import glob
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from currencies import CUR, CODES  # noqa: E402
import quality  # noqa: E402
import market  # noqa: E402

HIST = os.path.join(ROOT, 'data', 'history')
OUT = os.path.join(ROOT, 'site', 'data')
START = dt.date(2024, 3, 2)   # このデータ源で遡れる最初の日
URLS = ('https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@%s/v1/currencies/usd.min.json',
        'https://%s.currency-api.pages.dev/v1/currencies/usd.min.json')
PERIODS = ('d1', 'd7', 'd30', 'ytd')


def fetch(tag):
    """tag は 'latest' か 'YYYY-MM-DD'。(date, {CODE: rate}) を返す。取れなければ None。"""
    for url in URLS:
        try:
            req = urllib.request.Request(url % tag, headers={'User-Agent': 'currency-rank/1.0'})
            j = json.loads(urllib.request.urlopen(req, timeout=40).read())
            usd = j['usd']
            return j['date'], {c: usd[c.lower()] for c in CODES if usd.get(c.lower())}
        except Exception:
            continue
    return None


def load_history():
    """{date: {CODE: rate}}"""
    hist = {}
    for fn in sorted(glob.glob(os.path.join(HIST, '*.csv'))):
        with open(fn, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                d = row.pop('date')
                hist[d] = {c: float(v) for c, v in row.items() if v}
    return hist


def save_history(hist):
    os.makedirs(HIST, exist_ok=True)
    by_year = {}
    for d in sorted(hist):
        by_year.setdefault(d[:4], []).append(d)
    for year, days in by_year.items():
        tmp = os.path.join(HIST, year + '.csv.tmp')
        with open(tmp, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['date'] + CODES)
            for d in days:
                w.writerow([d] + [repr(hist[d][c]) if c in hist[d] else '' for c in CODES])
        os.replace(tmp, os.path.join(HIST, year + '.csv'))


def update_history(hist):
    """今日（UTC）までの足りない日を日付指定で取る。

    その日のファイルは毎日 UTC 4〜5 時台に出る。jsDelivr の「latest」は半日ほど古いことがあるので、
    日付指定で取り、latest は当日分がまだ無い時の保険にだけ使う。
    """
    today = dt.datetime.now(dt.timezone.utc).date()
    want = [str(START + dt.timedelta(days=i)) for i in range((today - START).days + 1)]
    missing = [d for d in want if d not in hist]
    failed, got_n = [], 0
    with cf.ThreadPoolExecutor(6) as ex:
        for d, res in zip(missing, ex.map(fetch, missing)):
            if res and res[0] == d:
                hist[d] = res[1]
                got_n += 1
            elif d != str(today):       # 当日分がまだ出ていないのは普通
                failed.append(d)
    if str(today) not in hist:
        res = fetch('latest')
        if res and res[0] not in hist:
            hist[res[0]] = res[1]
            got_n += 1
    print('最新日 %s・新たに取得 %d 日・取得できず %d 日' % (max(hist) if hist else '-', got_n, len(failed)))
    return failed


def build(hist, mkt):
    """mkt = {CODE: {date: rate}}（市中レートのある通貨だけ）。あればそちらで順位を付ける。"""
    days = sorted(hist)
    end = days[-1]
    rows, alerts = [], []
    os.makedirs(os.path.join(OUT, 'series'), exist_ok=True)
    for c in CODES:
        pairs = [(d, hist[d][c]) for d in days if c in hist[d]]
        if len(pairs) < 30 or pairs[-1][0] != end:
            continue
        dates = [d for d, _ in pairs]
        vals = [v for _, v in pairs]
        a = quality.analyze(dates, vals)
        name, region = CUR[c]
        official = None
        mk = {d: v for d, v in mkt.get(c, {}).items() if d <= end}
        if len(mk) >= 30 and max(mk) >= days[-8]:
            # 市中レートで順位を付け、配信の値は「配信レート」として国別の画面に残す
            official = {'dates': dates, 'vals': [float('%.7g' % v) for v in vals], 'rate': a['rate'],
                        'spikes': a['spikes'], 'steps': a['steps'], 'flags': a['flags']}
            dates = sorted(mk)
            vals = [mk[d] for d in dates]
            a = quality.analyze(dates, vals)
        row = {'c': c, 'n': name, 'g': region, 'rate': a['rate'], 'z': a['z'], 'alert': a['alert'],
               'f': [{'k': f['k'], 't': f['t']} for f in a['flags']], 'w': a['w']}
        if official:
            row['m'] = market.SOURCES[c]['label']
        for p in PERIODS:
            row[p] = a[p]
        rows.append(row)
        if a['alert']:
            alerts.append({'c': c, 'n': name, 'why': a['alert'], 'd7': a['d7']})
        series = {'c': c, 'n': name, 'g': region, 'end': end, 'dates': dates,
                  'vals': [float('%.7g' % v) for v in vals],
                  'spikes': a['spikes'], 'steps': a['steps'], 'flags': a['flags'],
                  'rate': a['rate'], 'z': a['z'], 'alert': a['alert'], 'ref': a['ref']}
        for p in PERIODS:
            series[p] = a[p]
        if official:
            series['market'] = {'label': market.SOURCES[c]['label'], 'src': market.SOURCES[c]['src'], 'asof': dates[-1]}
            series['official'] = official
            series['gap'] = round((a['rate'] / official['rate'] - 1) * 100, 1)   # 市中が配信より何 % ドル高か
        with open(os.path.join(OUT, 'series', c + '.json'), 'w', encoding='utf-8') as f:
            json.dump(series, f, ensure_ascii=False, separators=(',', ':'))
    # 期間ごとの比較日（多くの通貨で共通の日付）
    ref = {}
    sample = quality.analyze(days, [1.0] * len(days))['ref']
    for p in PERIODS:
        ref[p] = sample[p]
    latest = {'end': end, 'ref': ref, 'count': len(rows), 'alerts': sorted(alerts, key=lambda x: x['d7'] or 0),
              'generated': dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M') + ' 日本時間', 'rows': rows}
    tmp = os.path.join(OUT, 'latest.json.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(latest, f, ensure_ascii=False, separators=(',', ':'))
    os.replace(tmp, os.path.join(OUT, 'latest.json'))
    print('%s 時点・%d 通貨・異変 %d 件 → site/data/' % (end, len(rows), len(alerts)))
    return latest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-fetch', action='store_true')
    a = ap.parse_args()
    hist = load_history()
    if not a.no_fetch:
        failed = update_history(hist)
        save_history(hist)
        if failed:
            print('取得できなかった日（次回また試す）:', ', '.join(failed[:10]), '…' if len(failed) > 10 else '')
    if not hist:
        sys.exit('履歴がありません')
    mkt = {}
    for code in market.SOURCES:
        if a.no_fetch:
            mkt[code] = market.load(code)
        else:
            mkt[code], ok = market.update(code, str(START))
            print('%s の市中レート: %s・%d 日分' % (code, '取得' if ok else '取得できず（手元の控えを使用）', len(mkt[code])))
    build(hist, mkt)


if __name__ == '__main__':
    main()
