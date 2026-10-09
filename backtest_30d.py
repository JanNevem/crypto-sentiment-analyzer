"""Thirty-day non-lookahead backtest for corrected BTC indicator signals."""
from __future__ import annotations
import csv, json, math
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = "https://data-api.binance.vision/api/v3/klines"
OUT_CSV = Path("backtest_30d_results.csv")
OUT_MD = Path("backtest_30d_report.md")
USER_AGENT = "BTC-Sentiment-Analyzer-Backtest/1.0"


def fetch(interval: str, limit: int):
    q = urlencode({"symbol":"BTCUSDT", "interval":interval, "limit":limit})
    req = Request(f"{BASE}?{q}", headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=20) as r:
        payload = json.loads(r.read().decode())
    if not isinstance(payload, list) or any(not isinstance(row, list) or len(row) < 8 for row in payload):
        raise ValueError(f"Invalid {interval} payload")
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    rows=[]
    for row in payload:
        if int(row[6]) > now_ms: continue
        rows.append({"open_time":int(row[0]), "open":float(row[1]), "high":float(row[2]), "low":float(row[3]), "close":float(row[4]), "volume":float(row[7])})
    return rows


def ema(values, period):
    out=[]; alpha=2/(period+1); result=None
    for value in values:
        result=value if result is None else (value-result)*alpha+result
        out.append(result)
    return out


def rsi_values(closes, period=14):
    if len(closes)<period+1: return [50.0]*len(closes)
    deltas=[closes[i]-closes[i-1] for i in range(1,len(closes))]
    gains=[max(x,0) for x in deltas]; losses=[max(-x,0) for x in deltas]
    avg_gain=sum(gains[:period])/period; avg_loss=sum(losses[:period])/period
    out=[50.0]
    for i in range(period, len(deltas)+1):
        avg_gain=(avg_gain*(period-1)+gains[i-1])/period
        avg_loss=(avg_loss*(period-1)+losses[i-1])/period
        rs=avg_gain/avg_loss if avg_loss else 100
        out.append(100-(100/(1+rs)))
    return [out[0]]*(len(closes)-len(out))+out


def rsi_signal(closes):
    if len(closes)<40: return 0
    rsis=rsi_values(closes); lows=[i for i in range(2,len(closes)-2) if closes[i]<closes[i-1] and closes[i]<=closes[i+1] and closes[i]<closes[i-2] and closes[i]<=closes[i+2]]
    highs=[i for i in range(2,len(closes)-2) if closes[i]>closes[i-1] and closes[i]>=closes[i+1] and closes[i]>closes[i-2] and closes[i]>=closes[i+2]]
    lows=[i for i in lows if i>=len(closes)-45]; highs=[i for i in highs if i>=len(closes)-45]
    if len(lows)>=2:
        a,b=lows[-2:]
        if closes[b]<closes[a] and rsis[b]>rsis[a]+3: return 2
    if len(highs)>=2:
        a,b=highs[-2:]
        if closes[b]>closes[a] and rsis[b]<rsis[a]-3: return -2
    return 0


def trend_signal(rows):
    if len(rows)<35: return 0, None
    highs=[r['high'] for r in rows]; lows=[r['low'] for r in rows]; closes=[r['close'] for r in rows]
    prev=[closes[0]]+closes[:-1]
    tr=[max(h-l,abs(h-p),abs(l-p)) for h,l,p in zip(highs,lows,prev)]
    atr=ema(tr, 27)  # equivalent stable approximation for the analyzer's alpha=1/14
    up=[highs[i]-highs[i-1] if highs[i]-highs[i-1]>0 else 0 for i in range(len(rows))]
    down=[lows[i-1]-lows[i] if lows[i-1]-lows[i]>0 else 0 for i in range(len(rows))]
    plus=[100*a/max(b,1e-9) for a,b in zip(ema(up,27),atr)]
    minus=[100*a/max(b,1e-9) for a,b in zip(ema(down,27),atr)]
    dx=[100*abs(a-b)/max(a+b,1e-9) for a,b in zip(plus,minus)]
    adx=ema(dx,27)[-1]; momentum=(closes[-1]-closes[-6])/max(atr[-1],1e-9)
    direction='Up' if plus[-1]>minus[-1] and momentum>0 else 'Down' if minus[-1]>plus[-1] and momentum<0 else 'Neutral'
    strength=5
    if adx>=25: strength += 2 if direction!='Neutral' else 0
    elif adx>=18 and direction!='Neutral': strength += 1
    if abs(momentum)>=2: strength += 2 if direction!='Neutral' else 0
    elif abs(momentum)>=1: strength += 1 if direction!='Neutral' else 0
    if direction=='Down': strength=10-strength
    strength=max(1,min(10,strength))
    score=2 if strength>=8 else 1 if strength>=6 else -2 if strength<=2 else -1 if strength<=4 else 0
    return score, {'adx':adx,'plus_di':plus[-1],'minus_di':minus[-1],'momentum_5d_atr':momentum,'strength':strength,'direction':direction}


def volume_signal(rows):
    if len(rows)<5: return 0
    closes=[r['close'] for r in rows]; vols=[r['volume'] for r in rows]
    avg=sum(vols[-20:])/min(20,len(vols)); spike=vols[-1]>avg*1.5; increasing=vols[-1]>avg
    obv=0; values=[]
    for i in range(len(rows)):
        if i: obv += vols[i] if closes[i]>closes[i-1] else -vols[i] if closes[i]<closes[i-1] else 0
        values.append(obv)
    obv_up=values[-1]-values[-5]>0 if len(values)>=5 else False
    obv_down=values[-1]-values[-5]<0 if len(values)>=5 else False
    if spike and increasing: return 2 if closes[-1]>closes[-2] else -2
    if increasing: return 1 if closes[-1]>closes[-2] else -1
    return 1 if obv_up else -1 if obv_down else 0


def bollinger_signal(closes):
    if len(closes)<20: return 0
    window=closes[-20:]; mean=sum(window)/20; std=(sum((x-mean)**2 for x in window)/20)**0.5
    return 2 if closes[-1]>mean+2*std else -2 if closes[-1]<mean-2*std else 0


def structure_signal(rows):
    if len(rows)<10: return 0
    recent=rows[-10:]; prior=recent[:-1]; highs=[r['high'] for r in prior]; lows=[r['low'] for r in prior]; closes=[r['close'] for r in recent]
    hh=highs[-1] if False else (rows[-1]['high']>rows[-3]['high']>rows[-5]['high'])
    hl=rows[-1]['low']>rows[-3]['low']>rows[-5]['low']
    lh=rows[-1]['high']<rows[-3]['high']<rows[-5]['high']
    ll=rows[-1]['low']<rows[-3]['low']<rows[-5]['low']
    bos_up=closes[-1]>max(highs) and highs.index(max(highs))<5
    bos_down=closes[-1]<min(lows) and lows.index(min(lows))<5
    return 2 if hh and hl and bos_up else 1 if hh and hl else -2 if lh and ll and bos_down else -1 if lh and ll else 0


def structure_signal_4h(rows):
    """Replicate StructureAnalyzer on the last 50 completed 4H candles."""
    if len(rows) < 10: return 0
    recent=rows[-10:]; prior=recent[:-1]; highs=[r['high'] for r in prior]; lows=[r['low'] for r in prior]; closes=[r['close'] for r in recent]
    hh=recent[-1]['high']>recent[-3]['high']>recent[-5]['high']; hl=recent[-1]['low']>recent[-3]['low']>recent[-5]['low']
    lh=recent[-1]['high']<recent[-3]['high']<recent[-5]['high']; ll=recent[-1]['low']<recent[-3]['low']<recent[-5]['low']
    bos_up=closes[-1]>max(highs) and highs.index(max(highs))<5
    bos_down=closes[-1]<min(lows) and lows.index(min(lows))<5
    return 2 if hh and hl and bos_up else 1 if hh and hl else -2 if lh and ll and bos_down else -1 if lh and ll else 0


def main():
    daily=fetch('1d',400); fourh=fetch('4h',1000)
    # Use the last 30 completed daily closes as signal dates; trade next day.
    start=max(60,len(daily)-31); rows=[]; equity=1.0; buyhold=1.0; peak=1.0; maxdd=0.0; wins=0; active=0; costs=0.001
    prev_pos=0
    for i in range(start, len(daily)-1):
        history=daily[:i+1]; closes=[r['close'] for r in history]; nxt=daily[i+1]
        macd=ema(closes,12); macd26=ema(closes,26); signal_line=ema([a-b for a,b in zip(macd,macd26)],9)
        hist_now=(macd[-1]-macd26[-1])-signal_line[-1]; hist_prev=(macd[-2]-macd26[-2])-signal_line[-2]
        macd_score=2 if macd[-1]-macd26[-1]>0 and hist_now>hist_prev and hist_now>0 else 1 if macd[-1]-macd26[-1]>0 and hist_now>hist_prev else -2 if macd[-1]-macd26[-1]<0 and hist_now<hist_prev and hist_now<0 else -1 if macd[-1]-macd26[-1]<0 and hist_now<hist_prev else 0
        rsi=rsi_signal(closes); trend,tm=trend_signal(history); vol=volume_signal(history); bb=bollinger_signal(closes)
        cutoff=nxt['open_time']
        structure_rows=[row for row in fourh if row['open_time'] < cutoff][-50:]
        struct=structure_signal_4h(structure_rows)
        score=rsi+macd_score+trend+vol+bb+struct
        position=1 if score>=3 else -1 if score<=-3 else 0
        ret=nxt['close']/nxt['open']-1
        gross=position*ret; turnover=abs(position-prev_pos); net=gross-turnover*costs
        equity*=1+net; buyhold*=nxt['close']/nxt['open']; peak=max(peak,equity); maxdd=max(maxdd,(peak-equity)/peak)
        if position: active+=1; wins += 1 if gross>0 else 0
        rows.append({'signal_date':datetime.fromtimestamp(history[-1]['open_time']/1000,timezone.utc).date().isoformat(),'trade_date':datetime.fromtimestamp(nxt['open_time']/1000,timezone.utc).date().isoformat(),'score':score,'position':position,'next_day_return':ret,'strategy_return':net,'rsi':rsi,'macd':macd_score,'structure':struct,'trend':trend,'volume':vol,'bollinger':bb,'adx':tm['adx'] if tm else None,'plus_di':tm['plus_di'] if tm else None,'minus_di':tm['minus_di'] if tm else None,'momentum_5d_atr':tm['momentum_5d_atr'] if tm else None})
        prev_pos=position
    total=len(rows); active_rows=[r for r in rows if r['position']]
    strat_ret=equity-1; bh_ret=buyhold-1; avg=sum(r['strategy_return'] for r in rows)/total; stdev=(sum((r['strategy_return']-avg)**2 for r in rows)/max(1,total-1))**0.5; sharpe=(avg/stdev*math.sqrt(365)) if stdev else 0
    directional=[r for r in active_rows if r['next_day_return']!=0]; directional_acc=sum(1 for r in directional if (r['position']>0)==(r['next_day_return']>0))/len(directional) if directional else 0
    with OUT_CSV.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    last=rows[-1]
    md=f'''# BTC Corrected Indicator Backtest — 30 Days\n\n## Method\n\nThis is a non-lookahead daily backtest on real BTCUSDT candles from Binance public market data. Each signal uses only data through the signal day close; the position is applied to the following day’s open-to-close return. Long exposure is used for composite score >= +3, short exposure for <= -3, and flat otherwise. A 0.10% transaction cost is charged on position changes.\n\nThe tested available historical feeds are RSI divergence, MACD momentum, the corrected 4-hour market-structure signal, ATR/ADX trend strength, volume profile, and Bollinger Bands. Whale activity, Fear & Greed, open interest, funding, and dollar strength are excluded because reliable historical values are not persisted by the current analyzer; they are not fabricated.\n\n## Results\n\n| Metric | Result |\n|---|---:|\n| Signal/trading days | {total} |\n| Active long/short days | {active} |\n| Strategy return after costs | {strat_ret*100:.2f}% |\n| Buy-and-hold open-to-close benchmark | {bh_ret*100:.2f}% |\n| Max drawdown | {maxdd*100:.2f}% |\n| Annualized daily Sharpe (descriptive only) | {sharpe:.2f} |\n| Directional accuracy on active days | {directional_acc*100:.1f}% |\n| Active-day win rate | {wins/active*100 if active else 0:.1f}% |\n| Long / short / flat days | {sum(r['position']==1 for r in rows)} / {sum(r['position']==-1 for r in rows)} / {sum(r['position']==0 for r in rows)} |\n\n## Latest backtest observation\n\nThe final signal date was **{last['signal_date']}** with composite score **{last['score']}** and position **{last['position']}** for the following session. Its trend metrics were ADX **{last['adx']:.2f}**, +DI **{last['plus_di']:.2f}**, −DI **{last['minus_di']:.2f}**, and ATR-normalized 5-day momentum **{last['momentum_5d_atr']:.2f}**.\n\n## Interpretation\n\nThis is a diagnostic sample, not evidence of a deployable trading edge. Thirty days is too short for robust validation, and the strategy intentionally omits several live feeds because their historical series are unavailable. The most important follow-up is to persist historical indicator outputs and test multiple market regimes with walk-forward splits, costs, and slippage.\n\nRaw daily results are in `backtest_30d_results.csv`.\n'''
    OUT_MD.write_text(md)
    print(md)
    print(json.dumps({'strategy_return':strat_ret,'buy_hold':bh_ret,'max_drawdown':maxdd,'sharpe':sharpe,'accuracy':directional_acc},indent=2))

if __name__=='__main__': main()
