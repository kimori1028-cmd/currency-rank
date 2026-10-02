# -*- coding: utf-8 -*-
"""市中レート（公定レートと実勢が離れる国の、街の両替相場）。

いまはイランだけ。国を足す時は SOURCES に取得関数を足す。
返り値は {date('YYYY-MM-DD'): 1 ドルあたりの現地通貨}。
"""
import csv
import json
import os
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, 'data', 'market')

# bonbast.com の日次の記録（MIT ライセンスの公開アーカイブ・毎日更新・単位はトマン = 10 リアル）
IRR_URLS = ('https://raw.githubusercontent.com/SamadiPour/rial-exchange-rates-archive/data/gregorian_imp.min.json',
            'https://cdn.jsdelivr.net/gh/SamadiPour/rial-exchange-rates-archive@data/gregorian_imp.min.json')


def fetch_irr():
    for url in IRR_URLS:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'currency-rank/1.0'})
            j = json.loads(urllib.request.urlopen(req, timeout=60).read())
            out = {}
            for day, cur in j.items():
                usd = cur.get('usd') or {}
                if usd.get('sell'):
                    out[day.replace('/', '-')] = usd['sell'] * 10.0   # トマン → リアル
            if out:
                return out
        except Exception:
            continue
    return None


SOURCES = {
    'IRR': {'fetch': fetch_irr, 'label': '市中レート', 'src': 'bonbast.com の両替相場（売値）'},
}


def _path(code):
    return os.path.join(STORE, code + '.csv')


def load(code):
    if not os.path.exists(_path(code)):
        return {}
    with open(_path(code), newline='', encoding='utf-8') as f:
        return {r['date']: float(r['rate']) for r in csv.DictReader(f)}


def update(code, since):
    """取得して手元の控えに足す。取得できなければ控えをそのまま返す。(系列, 取得できたか)"""
    stored = load(code)
    got = SOURCES[code]['fetch']()
    if got:
        stored.update({d: v for d, v in got.items() if d >= since})
        os.makedirs(STORE, exist_ok=True)
        tmp = _path(code) + '.tmp'
        with open(tmp, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['date', 'rate'])
            for d in sorted(stored):
                w.writerow([d, repr(stored[d])])
        os.replace(tmp, _path(code))
    return stored, bool(got)
