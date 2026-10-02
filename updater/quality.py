# -*- coding: utf-8 -*-
"""点検と指標。

入力は 1 通貨の日次系列（dates: 昇順の 'YYYY-MM-DD'、vals: 1 ドルあたりの現地通貨）。
「通貨の価値の変化」= 旧レート ÷ 新レート − 1（マイナスが通貨安）。
"""
import datetime as dt
import math
import statistics

SPIKE_DEV = 0.20      # 飛び: 直前の正常値から 20% 以上ずれ
SPIKE_AGREE = 0.05    # 飛び: 戻った値が直前の正常値と 5% 以内
SPIKE_MAXRUN = 5      # 飛び: 続く日数の上限（これより長く続けば段差として扱う）
STEP_LOG = math.log(1.2)   # 段差: 1 日でレートが 1.2 倍（または 1/1.2）以上動き、戻らない
PEG_RANGE = 0.01      # 固定相場: 1 年の高値 ÷ 安値 − 1 がこれ未満
PEG_MOVE = 0.005      # 固定相場が動いた: 7 日の変化の絶対値がこれ超
Z_MIN_SCALE = 0.0005  # 週次の振れ幅がこれ以下なら「普段の何倍」は出さない
Z_MIN_WEEKS = 12
Z_ALERT = 3.0         # 異変の線（仮）: 普段の 3 倍以上の下落
CHECK_1D = 0.20       # 要確認: 当日だけで 20% 以上動いた（翌日に飛びか段差かが分かる）
LOOKBACK_DAYS = 365


def value_change(old, new):
    return old / new - 1


def find_spikes(vals):
    """飛び（数日だけ別の値になって元に戻る点）の添字の集合。"""
    spikes = set()
    n = len(vals)
    base = 0  # 直前の正常値の添字
    i = 1
    while i < n:
        a = vals[base]
        if abs(vals[i] / a - 1) > SPIKE_DEV:
            back = None
            for j in range(i + 1, min(i + SPIKE_MAXRUN, n - 1) + 1):
                if abs(vals[j] / a - 1) < SPIKE_AGREE:
                    back = j
                    break
            if back is not None:
                spikes.update(range(i, back))
                base = back
                i = back + 1
                continue
        base = i
        i += 1
    return spikes


def clean(vals, spikes):
    """飛びの日を直前の正常値で埋めた系列。"""
    out = list(vals)
    for i in sorted(spikes):
        out[i] = out[i - 1]
    return out


def find_steps(dates, cvals):
    """段差（1 日で大きく動いて戻らない点）。[(date, 通貨の価値の変化 %)]"""
    steps = []
    for i in range(1, len(cvals)):
        a, b = cvals[i - 1], cvals[i]
        if abs(math.log(b / a)) > STEP_LOG:
            steps.append((dates[i], round(value_change(a, b) * 100, 1)))
    return steps


def _index_on_or_before(dates, day):
    lo, hi = 0, len(dates) - 1
    if dates[0] > day:
        return None
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if dates[mid] <= day:
            lo = mid
        else:
            hi = mid - 1
    return lo


def back_index(dates, days):
    end = dt.date.fromisoformat(dates[-1])
    return _index_on_or_before(dates, str(end - dt.timedelta(days=days)))


def weekly_points(dates, cvals, weeks=53):
    """最新日から 7 日おきに遡った点（古い順）。[(date, val)]"""
    end = dt.date.fromisoformat(dates[-1])
    pts = []
    for k in range(weeks):
        i = _index_on_or_before(dates, str(end - dt.timedelta(days=7 * k)))
        if i is None:
            break
        pts.append((dates[i], cvals[i]))
    return pts[::-1]


def z_score(wpts):
    """直近 1 週の動きが、いつもの動きからどれだけ外れたか（週ごとの振れ幅の何倍か）。

    (倍率, 下落側に外れたか) を返す。振れ幅が無い通貨は (None, False)。
    いつもの動き（中央値）からのずれで測るので、毎週少しずつ切り下げる通貨は
    いつもどおりの切り下げでは反応しない。
    """
    v = [x for _, x in wpts]
    lr = [math.log(v[i - 1] / v[i]) for i in range(1, len(v))]
    if len(lr) < Z_MIN_WEEKS + 1:
        return None, False
    last, prev = lr[-1], lr[:-1]
    med = statistics.median(prev)
    scale = statistics.median([abs(x - med) for x in prev]) * 1.4826
    if scale <= Z_MIN_SCALE:
        return None, False
    return round(abs(last - med) / scale, 1), last < med


def is_peg(dates, cvals):
    """直近 7 日を除く過去 1 年がほぼ一定か。"""
    i_end = back_index(dates, 7)
    i_start = back_index(dates, LOOKBACK_DAYS + 7)
    if i_end is None:
        return False
    seg = cvals[(i_start or 0):i_end + 1]
    if len(seg) < 60:
        return False
    return max(seg) / min(seg) - 1 < PEG_RANGE


def analyze(dates, vals):
    """1 通貨の点検結果と指標をまとめて返す。"""
    spikes = find_spikes(vals)
    cv = clean(vals, spikes)
    last = len(vals) - 1
    out = {'rate': vals[last]}

    def chg(i):
        return None if i is None or i >= last else round(value_change(cv[i], cv[last]) * 100, 2)

    out['d1'] = chg(last - 1) if last >= 1 else None
    out['d7'] = chg(back_index(dates, 7))
    out['d30'] = chg(back_index(dates, 30))
    year0 = str(int(dates[-1][:4]) - 1) + '-12-31'
    out['ytd'] = chg(_index_on_or_before(dates, year0))
    out['ref'] = {
        'd1': dates[last - 1] if last >= 1 else None,
        'd7': dates[back_index(dates, 7)] if back_index(dates, 7) is not None else None,
        'd30': dates[back_index(dates, 30)] if back_index(dates, 30) is not None else None,
        'ytd': dates[_index_on_or_before(dates, year0)] if _index_on_or_before(dates, year0) is not None else None,
    }

    wpts = weekly_points(dates, cv)
    out['w'] = [float('%.6g' % x) for _, x in wpts]
    out['z'], weaker = z_score(wpts)

    since = str(dt.date.fromisoformat(dates[-1]) - dt.timedelta(days=LOOKBACK_DAYS))
    steps = find_steps(dates, cv)
    out['steps'] = steps                                   # 全期間（国別の画面用）
    out['spikes'] = [dates[i] for i in sorted(spikes)]     # 全期間
    recent_steps = [s for s in steps if s[0] >= since]
    recent_spikes = [d for d in out['spikes'] if d >= since]

    flags = []
    peg = is_peg(dates, cv)
    if peg:
        flags.append({'k': 'peg', 't': '固定相場', 'why': '直近 1 年の高値と安値の差が 1% 未満'})
    if recent_steps:
        why = '・'.join('%s に %+.1f%%' % (d, p) for d, p in recent_steps[-3:])
        flags.append({'k': 'step', 't': '段差あり', 'why': '1 日で大きく動いて戻らない日がある（%s）。切り下げ・公定レートの変更・単位の変更の可能性' % why})
    if recent_spikes:
        flags.append({'k': 'spike', 't': '値の飛び', 'why': '数日だけ別の値になって元に戻った日がある（%s）。順位の計算では直前の値で埋めている' % '・'.join(recent_spikes[-3:])})
    if out['d1'] is not None and abs(math.log(cv[last - 1] / cv[last])) > math.log(1 + CHECK_1D):
        flags.append({'k': 'check', 't': '要確認', 'why': '今日だけで 20% 以上動いた。値の飛びか本当の段差かは翌日以降に分かる'})
    out['flags'] = flags

    # 異変の線（仮）: 普段の 3 倍以上の下落、または固定相場が動いた
    alert = None
    if peg and out['d7'] is not None and abs(out['d7']) > PEG_MOVE * 100:
        alert = '固定相場が動いた'
    elif out['z'] is not None and out['z'] >= Z_ALERT and weaker and out['d7'] is not None and out['d7'] < 0:
        alert = '普段の 20 倍を超える下落' if out['z'] >= 20 else '普段の %s 倍の下落' % out['z']
    out['alert'] = alert
    return out
