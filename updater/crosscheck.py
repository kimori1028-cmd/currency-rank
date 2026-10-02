# -*- coding: utf-8 -*-
"""2 本目のデータ源との突き合わせ。最新日の値だけを比べ、大きく食い違う通貨に旗を立てる。

出どころ: open.er-api.com（無料・キー不要・1 日 1 回更新・表示義務あり = サイトの下に出どころを書く）。
"""
import json
import urllib.request

URL = 'https://open.er-api.com/v6/latest/USD'
NAME = 'ExchangeRate-API'
TOLERANCE = 0.05   # 5% を超えて食い違えば旗（更新時刻の違いによる普通のずれは 1% 前後まで）


def fetch():
    """{CODE: 1 ドルあたりの値}。取れなければ None。"""
    try:
        req = urllib.request.Request(URL, headers={'User-Agent': 'currency-rank/1.0'})
        j = json.loads(urllib.request.urlopen(req, timeout=40).read())
        if j.get('result') == 'success' and j.get('rates'):
            return {c: float(v) for c, v in j['rates'].items() if v}
    except Exception:
        pass
    return None


def flag(code, rate, second):
    """食い違いの旗（無ければ None）。"""
    if not second or code not in second:
        return None
    other = second[code]
    diff = other / rate - 1
    if abs(diff) <= TOLERANCE:
        return None
    if abs(diff) > 0.9 or abs(rate / other - 1) > 0.9:
        hint = '桁が違うので、通貨の単位の切り替え（デノミ）をどちらかが反映していない可能性'
    else:
        hint = '公定レートと実勢レートの違い、またはどちらかの更新遅れの可能性'
    fmt = (lambda v: '{:,.0f}'.format(v) if v >= 1000 else '{:.2f}'.format(v) if v >= 10 else '{:.4f}'.format(v))
    return {'k': 'diff', 't': '出どころで食い違い',
            'why': '2 本目のデータ源（%s）は 1 ドル＝%s で、%+.1f%% の差。%s' % (NAME, fmt(other), diff * 100, hint)}
