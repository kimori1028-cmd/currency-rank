# -*- coding: utf-8 -*-
"""点検ロジックの受入テスト。 python updater/test_quality.py"""
import datetime as dt
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quality  # noqa: E402
import crosscheck  # noqa: E402


def days(n, start='2025-01-01'):
    d0 = dt.date.fromisoformat(start)
    return [str(d0 + dt.timedelta(days=i)) for i in range(n)]


def wobble(n, base=100.0, amp=0.01):
    """週ごとに ±amp ほど揺れる、普通の変動相場（揺れ幅は週によって違う）。"""
    return [base * (1 + amp * math.sin((i // 7) * 1.7)) for i in range(n)]


def flags(a):
    return {f['k'] for f in a['flags']}


results = []


def check(name, cond):
    results.append(cond)
    print(('○ ' if cond else '× ') + name)


N = 400
d = days(N)

# T1 価値の変化の向き: 1 ドル=100 → 125 は −20%
check('T1 レート 100→125 は −20%', abs(quality.value_change(100, 125) - (-0.2)) < 1e-9)

# T2 普通の変動相場には旗が立たない
a = quality.analyze(d, wobble(N))
check('T2 普通の相場は旗なし・異変なし', not a['flags'] and a['alert'] is None)

# T3 1 日だけの飛びは「値の飛び」になり、順位の計算に入らない
v = wobble(N); v[N - 20] = 4.0
a = quality.analyze(d, v)
check('T3 1 日だけの飛び → 値の飛び', flags(a) == {'spike'} and a['spikes'] == [d[N - 20]])
check('T3b 飛びは 30 日の変化に影響しない', abs(a['d30']) < 2)

# T4 3 日続いて戻る飛びも拾う
v = wobble(N); v[N - 40:N - 37] = [3.0, 3.0, 3.0]
a = quality.analyze(d, v)
check('T4 3 日続く飛び → 値の飛び', flags(a) == {'spike'} and len(a['spikes']) == 3)

# T5 戻らない大きな動きは「段差」になり、変化率に入る
v = wobble(N); v[N - 20:] = [x * 2 for x in v[N - 20:]]
a = quality.analyze(d, v)
check('T5 戻らない 2 倍 → 段差', flags(a) == {'step'} and a['steps'][0][0] == d[N - 20])
check('T5b 段差は 30 日の変化に入る（約 −50%）', -51 < a['d30'] < -49)

# T6 固定相場
a = quality.analyze(d, [3.6725] * N)
check('T6 動かない通貨 → 固定相場・普段の何倍は出さない', flags(a) == {'peg'} and a['z'] is None and a['alert'] is None)

# T7 固定相場が動いたら異変
v = [3.6725] * N; v[N - 3:] = [3.75] * 3
a = quality.analyze(d, v)
check('T7 固定相場が 2% 動く → 異変「固定相場が動いた」', a['alert'] == '固定相場が動いた' and 'peg' in flags(a))

# T8 普段の 3 倍以上の下落は異変、同じ大きさの上昇は異変にしない
v = wobble(N); v[N - 3:] = [x * 1.10 for x in v[N - 3:]]
a = quality.analyze(d, v)
check('T8 普段の何倍もの下落 → 異変', a['alert'] is not None and a['z'] >= quality.Z_ALERT and a['d7'] < 0)
v = wobble(N); v[N - 3:] = [x / 1.10 for x in v[N - 3:]]
a = quality.analyze(d, v)
check('T8b 同じ大きさの上昇 → 異変にしない', a['alert'] is None and a['d7'] > 0)

# T9 今日だけ 20% 以上動いた → 要確認（飛びか段差かはまだ分からない）
v = wobble(N); v[-1] = v[-1] * 1.5
a = quality.analyze(d, v)
check('T9 当日の急変 → 要確認', 'check' in flags(a))

# T10 公定→実勢の切り替え＋ 1 日だけ戻る（イランで実際にあった形）
v = [42000.0] * N
for i in range(N - 260, N):
    v[i] = 1070000.0 + 500 * (i % 5)
v[N - 232] = 42125.0
a = quality.analyze(d, v)
check('T10 イラン型 → 段差と値の飛びの両方', flags(a) >= {'step', 'spike'} and a['spikes'] == [d[N - 232]])

# T11 年初来の比較日は前年の 12/31
a = quality.analyze(days(400, '2025-06-01'), wobble(400))
check('T11 年初来は前年末と比べる', a['ref']['ytd'] == '2025-12-31')


# T12 毎週同じ幅で切り下げる通貨は、いつもどおりの切り下げでは異変にしない
v = [100.0 * (1.003 ** (i // 7)) * (1 + 0.0008 * math.sin(i // 7)) for i in range(N)]
a = quality.analyze(d, v)
check('T12 いつもどおりの切り下げ → 異変にしない', a['alert'] is None and a['d7'] < 0)

# T13 2 本目のデータ源との突き合わせ: 5% 以内は旗なし、超えたら旗、桁違いはデノミの疑い
check('T13 差 1% → 旗なし', crosscheck.flag('JPY', 150.0, {'JPY': 151.5}) is None)
f = crosscheck.flag('SDG', 600.0, {'SDG': 511.5})
check('T13b 差 15% → 食い違いの旗', f is not None and f['k'] == 'diff' and '実勢' in f['why'])
f = crosscheck.flag('SYP', 13000.0, {'SYP': 121.7})
check('T13c 桁が違う → デノミの疑いと書く', f is not None and 'デノミ' in f['why'])
check('T13d 2 本目に無い通貨・取得できない時 → 旗なし', crosscheck.flag('KPW', 900.0, {'JPY': 150}) is None and crosscheck.flag('JPY', 150.0, None) is None)

print()
print('○ 全 %d 項目通過' % len(results) if all(results) else '× 失敗あり')
sys.exit(0 if all(results) else 1)
