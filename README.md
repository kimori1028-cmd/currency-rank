# 世界の通貨安ランキング

153 の法定通貨を、米ドルに対してどれだけ価値が減ったかで毎日並べる静的サイト。

## 置き場所

| パス | 中身 |
|---|---|
| `updater/update.py` | 毎日の更新（取る → 確かめる → 並べる → サイト用 JSON を書く） |
| `updater/quality.py` | 点検（固定相場・段差・値の飛び・要確認）と指標（価値の変化・普段の何倍・異変） |
| `updater/market.py` | 市中レート（いまはイランだけ）。国を足す時はここの `SOURCES` に足す |
| `updater/currencies.py` | 対象の 153 通貨（コード・国名・地域） |
| `updater/test_quality.py` | 点検の受入テスト |
| `data/history/YYYY.csv` | 配信レートの履歴（1 行 1 日・2024-03-02 から） |
| `data/market/IRR.csv` | イランの市中レートの控え |
| `site/` | サイト本体。`site/data/` は update.py が作る（Git には入れない） |

## 使い方

```
python updater/test_quality.py        点検のテスト（15 項目）
python updater/update.py              足りない日を取得して作り直す
python updater/update.py --no-fetch   取得せず、手元の履歴から作り直す
python -m http.server 8765 -d site    http://localhost:8765 で見る
```

`run_update.bat` は テスト → 更新 を続けて行う。

## 数え方

- **通貨の価値の変化** = 旧レート ÷ 新レート − 1。マイナスが通貨安（1 ドル＝100 → 125 は −20%）。
- **普段の何倍** = 直近 1 週の動きが「いつもの週の動き」からどれだけ外れたか ÷ 過去 1 年の週ごとの振れ幅。毎週少しずつ切り下げる通貨は、いつもどおりの切り下げでは反応しない。
- **異変（仮の線）** = 普段の 3 倍以上の下落、または固定相場が 7 日で 0.5% 超動いた。線は `quality.py` の先頭の定数。
- **旗** = 固定相場（1 年の高値と安値の差が 1% 未満）／段差（1 日で 1.2 倍以上動いて戻らない）／値の飛び（5 日以内に元の値へ戻る）／要確認（当日だけで 20% 以上動いた）。値の飛びの日は、順位の計算では直前の値で埋める。

## データの出どころ

- 配信レート: currency-api（無料・キー不要）。`https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@<latest|日付>/v1/currencies/usd.min.json`
- イランの市中レート: bonbast.com の両替相場の公開アーカイブ（MIT）。`https://raw.githubusercontent.com/SamadiPour/rial-exchange-rates-archive/data/gregorian_imp.min.json`（単位はトマン。10 倍してリアルにする）

イランは市中レートで順位を付け、配信レート（公定に近い値）は国別の画面に 2 本目の線として残す。

## まだ無いもの

- 世界の一覧（地域別のタイル）
- 2 本目のデータ源との突き合わせ
- 異変の日のメール
- イラン以外の市中レート
