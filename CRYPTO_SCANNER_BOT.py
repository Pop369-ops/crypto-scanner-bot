"""
╔══════════════════════════════════════════════════════════════════╗
║           CRYPTO SCANNER BOT — AI Ensemble Edition             ║
║  محلل مالي عبقري 24/7 بذكاء اصطناعي                           ║
║                                                                  ║
║  3 وكلاء AI (كلهم Claude بـ system prompts مختلفة):            ║
║  🔴 الصقر (Hawk)   — رصد السيولة والأموال الذكية               ║
║  🔵 الحكيم (Sage)  — فحص الأمان والتوكنوميكس                  ║
║  🟢 العراف (Oracle)— الحكم النهائي Wall St / Harvard           ║
║                                                                  ║
║  المصادر المجانية:                                               ║
║  • GeckoTerminal — DEX Pools (Eth/BSC/Sol/Base/Arb)            ║
║  • DexScreener   — DEX New Pairs + Liquidity                    ║
║  • Binance       — CEX Volume Anomalies                         ║
║  • CoinGecko     — Tokenomics + Market Data                     ║
║  • GoPlus        — Smart Contract Security Audit                ║
║  • Alternative.me— Fear & Greed Index                           ║
║                                                                  ║
║  الـ Gatekeeper: سيولة > $250K + حجم 1h > $50K + عمر > 5min   ║
║  تقارير كل 4 ساعات + تنبيه فوري للحالات الاستثنائية            ║
╚══════════════════════════════════════════════════════════════════╝
"""

import os, asyncio, logging, re, time
from datetime import datetime, timedelta, timezone
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)

logging.basicConfig(level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")

BOT_TOKEN     = os.environ.get("BOT_TOKEN",        "YOUR_BOT_TOKEN_HERE")
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
OPENAI_KEY    = os.environ.get("OPENAI_API_KEY",    "")
GEMINI_KEY    = os.environ.get("GEMINI_API_KEY",    "")

OPENAI_API  = "https://api.openai.com/v1/chat/completions"
GEMINI_API  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
CLAUDE_API  = "https://api.anthropic.com/v1/messages"

COINGECKO  = "https://api.coingecko.com/api/v3"
GECKOT     = "https://api.geckoterminal.com/api/v2"
DEXSCREEN  = "https://api.dexscreener.com/latest/dex"
BINANCE    = "https://api.binance.com/api/v3"
ALTME      = "https://api.alternative.me"
GOPLUS     = "https://api.gopluslabs.io/api/v1"
ANTHROPIC  = "https://api.anthropic.com/v1/messages"

_TZ3 = timezone(timedelta(hours=3))

scan_results  = {}
watching      = {}
user_settings = {}

sess = requests.Session()
sess.headers.update({"User-Agent":"CryptoScannerBot/3.0","Accept":"application/json"})

def safe_get(url, params=None, timeout=(6,20)):
    try:
        r = sess.get(url, params=params, timeout=timeout)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        logging.warning(f"[HTTP] {url[:50]}: {e}")
        return None

def fmt_usd(v):
    if v is None: return "—"
    v = float(v)
    if v >= 1e9: return f"${v/1e9:.2f}B"
    if v >= 1e6: return f"${v/1e6:.2f}M"
    if v >= 1e3: return f"${v/1e3:.1f}K"
    if v >= 1:   return f"${v:,.2f}"
    return f"${v:.6f}"

def now_sa():
    return datetime.now(_TZ3).strftime("%H:%M:%S %d/%m/%Y")

# ══════════════════════════════════════════════════════════════════
# HAWK — رصد السيولة
# ══════════════════════════════════════════════════════════════════

def hawk_dex_scan(min_liq=250_000, min_vol=50_000):
    chains = ["ethereum","bsc","solana","base","arbitrum"]
    results = []
    for chain in chains:
        data = safe_get(f"{GECKOT}/networks/{chain}/new_pools", timeout=(8,20))
        if data and data.get("data"):
            for pool in data["data"][:15]:
                try:
                    attr  = pool.get("attributes",{})
                    liq   = float(attr.get("reserve_in_usd","0") or 0)
                    vol1h = float(attr.get("volume_usd",{}).get("h1","0") or 0)
                    vol24 = float(attr.get("volume_usd",{}).get("h24","0") or 0)
                    age_s = attr.get("pool_created_at","")
                    age_min = 9999
                    if age_s:
                        try:
                            from datetime import datetime as dt
                            created = dt.fromisoformat(age_s.replace("Z","+00:00"))
                            age_min = (dt.now(timezone.utc)-created).total_seconds()/60
                        except: pass
                    if liq < min_liq or vol1h < min_vol or age_min < 5: continue
                    chg1h = float(attr.get("price_change_percentage",{}).get("h1","0") or 0)
                    chg24 = float(attr.get("price_change_percentage",{}).get("h24","0") or 0)
                    tx24  = attr.get("transactions",{}).get("h24",{})
                    buys  = int(tx24.get("buys",0) or 0)
                    sells = int(tx24.get("sells",0) or 0)
                    bp    = buys/(buys+sells)*100 if (buys+sells)>0 else 50
                    rel   = pool.get("relationships",{})
                    base_addr = rel.get("base_token",{}).get("data",{}).get("id","").split("_")[-1]
                    results.append({
                        "pool_id":   pool.get("id","").split("_")[-1],
                        "name":      attr.get("name",""),
                        "chain":     chain,
                        "dex":       attr.get("dex_id",""),
                        "price_usd": float(attr.get("base_token_price_usd","0") or 0),
                        "liquidity": liq,
                        "vol_1h":    vol1h,
                        "vol_24h":   vol24,
                        "chg_1h":   chg1h,
                        "chg_24h":  chg24,
                        "age_min":  age_min,
                        "buy_pressure": bp,
                        "buys_24h": buys,
                        "sells_24h":sells,
                        "base_addr":base_addr,
                        "url":      f"https://www.geckoterminal.com/{chain}/pools/{pool.get('id','').split('_')[-1]}",
                    })
                except: pass
        else:
            # DexScreener fallback
            ds = safe_get(f"{DEXSCREEN}/search/?q=new", timeout=(8,20))
            if ds and ds.get("pairs"):
                for p in ds["pairs"][:8]:
                    try:
                        if p.get("chainId","") != chain: continue
                        liq  = float(p.get("liquidity",{}).get("usd",0) or 0)
                        vol1 = float(p.get("volume",{}).get("h1",0) or 0)
                        if liq < min_liq or vol1 < min_vol: continue
                        age_ms = p.get("pairCreatedAt",0) or 0
                        age_m  = (time.time()*1000-age_ms)/60000 if age_ms else 9999
                        if age_m < 5: continue
                        results.append({
                            "pool_id":      p.get("pairAddress",""),
                            "name":         f"{p.get('baseToken',{}).get('symbol','?')}/{p.get('quoteToken',{}).get('symbol','?')}",
                            "chain":        chain,
                            "dex":          p.get("dexId",""),
                            "price_usd":    float(p.get("priceUsd","0") or 0),
                            "liquidity":    liq,
                            "vol_1h":       vol1,
                            "vol_24h":      float(p.get("volume",{}).get("h24",0) or 0),
                            "chg_1h":       float(p.get("priceChange",{}).get("h1",0) or 0),
                            "chg_24h":      float(p.get("priceChange",{}).get("h24",0) or 0),
                            "age_min":      age_m,
                            "buy_pressure": 55.0,
                            "buys_24h":     0,
                            "sells_24h":    0,
                            "base_addr":    p.get("baseToken",{}).get("address",""),
                            "url":          p.get("url",""),
                        })
                    except: pass
    results.sort(key=lambda x: x["liquidity"]*(x["buy_pressure"]/100)*max(x["chg_1h"],0.1),reverse=True)
    return results[:20]


def hawk_cex_anomalies(min_chg=8.0, min_vol=2_000_000):
    data = safe_get(f"{BINANCE}/ticker/24hr", timeout=(10,25))
    if not data: return []
    results = []
    for t in data:
        try:
            if not t.get("symbol","").endswith("USDT"): continue
            vol = float(t.get("quoteVolume","0"))
            chg = float(t.get("priceChangePercent","0"))
            if vol >= min_vol and chg >= min_chg:
                results.append({
                    "symbol":  t["symbol"],
                    "price":   float(t.get("lastPrice","0")),
                    "chg_24h": chg,
                    "vol_24h": vol,
                    "source":  "Binance_CEX",
                })
        except: continue
    results.sort(key=lambda x: x["vol_24h"]*x["chg_24h"],reverse=True)
    return results[:10]


# ══════════════════════════════════════════════════════════════════
# SAGE — الأمان والتوكنوميكس
# ══════════════════════════════════════════════════════════════════

def sage_audit(address, chain="ethereum"):
    chain_ids = {"ethereum":"1","bsc":"56","polygon":"137","arbitrum":"42161","base":"8453","solana":"sol"}
    cid = chain_ids.get(chain.lower(),"1")
    if not address: return {"status":"unknown","score":50,"flags":[],"risks":["⚠️ عنوان غير متاح"]}
    data = safe_get(f"{GOPLUS}/token_security/{cid}", params={"contract_addresses":address}, timeout=(8,20))
    if not data or data.get("code") != 1:
        return {"status":"unknown","score":50,"flags":[],"risks":["⚠️ فحص الأمان غير متاح"]}
    result = data.get("result",{})
    td = result.get(address.lower(), next(iter(result.values())) if result else {})
    if not td: return {"status":"unknown","score":50,"flags":[],"risks":["⚠️ بيانات غير كافية"]}
    flags=[]; risks=[]; score=100
    if str(td.get("is_honeypot","0"))=="1": risks.append("🚨 HONEYPOT!"); score-=50
    if str(td.get("is_mintable","0"))=="1": risks.append("⚠️ Mintable"); score-=20
    if str(td.get("is_proxy","0"))=="1": risks.append("⚠️ Proxy"); score-=10
    bt=float(td.get("buy_tax","0") or 0); st=float(td.get("sell_tax","0") or 0)
    if bt>10 or st>10: risks.append(f"⚠️ ضريبة عالية: شراء {bt:.0f}% بيع {st:.0f}%"); score-=15
    elif bt>0: flags.append(f"ℹ️ ضريبة: {bt:.0f}%/{st:.0f}%")
    cp=float(td.get("creator_percent","0") or 0)*100
    if cp>30: risks.append(f"⚠️ المطور يمتلك {cp:.0f}%"); score-=20
    elif cp<5: flags.append(f"✅ المطور {cp:.1f}%")
    if str(td.get("is_open_source","0"))=="1": flags.append("✅ كود مفتوح")
    else: risks.append("⚠️ كود مغلق"); score-=5
    score=max(0,min(100,score))
    return {"status":"safe" if score>=70 else ("warning" if score>=40 else "danger"),
            "score":score,"buy_tax":bt,"sell_tax":st,"creator_pct":cp,"flags":flags,"risks":risks}


def sage_tokenomics(coin_id):
    data = safe_get(f"{COINGECKO}/coins/{coin_id}",{
        "localization":"false","tickers":"false","market_data":"true",
        "developer_data":"true","sparkline":"false"})
    if not data: return {}
    md=data.get("market_data",{}); dd=data.get("developer_data",{})
    circ=md.get("circulating_supply",0) or 0; total=md.get("total_supply",0) or 0
    maxx=md.get("max_supply",0); mcap=md.get("market_cap",{}).get("usd",0) or 0
    fdv=md.get("fully_diluted_valuation",{}).get("usd",0) or 0
    vol24=md.get("total_volume",{}).get("usd",0) or 0
    price=md.get("current_price",{}).get("usd",0) or 0
    ath_drop=md.get("ath_change_percentage",{}).get("usd",0) or 0
    commits=dd.get("commit_count_4_weeks",0) or 0
    stars=dd.get("stars",0) or 0
    prs=dd.get("pull_request_contributors",0) or 0
    tok_flags=[]; tok_risks=[]; tok_score=0
    cr=circ/total if total>0 else 0
    if cr>0.6: tok_score+=20; tok_flags.append(f"✅ {cr*100:.0f}% متداول")
    elif cr>0.3: tok_score+=10
    else: tok_risks.append(f"⚠️ {cr*100:.0f}% فقط متداول")
    fm=fdv/mcap if mcap>0 else 0
    if fm<2: tok_score+=20; tok_flags.append("✅ FDV/MCap منطقي")
    elif fm<5: tok_score+=10
    else: tok_risks.append(f"⚠️ FDV أكبر {fm:.1f}x")
    vm=vol24/mcap if mcap>0 else 0
    if vm>0.1: tok_score+=20; tok_flags.append(f"✅ Vol/MCap={vm*100:.1f}%")
    elif vm>0.05: tok_score+=10
    else: tok_risks.append("⚠️ حجم منخفض نسبياً")
    if commits>50: tok_score+=20; tok_flags.append(f"✅ {commits} commit")
    elif commits>10: tok_score+=10
    elif commits==0: tok_risks.append("⚠️ لا نشاط تطوير")
    if maxx: tok_flags.append(f"✅ حد أقصى: {maxx:,.0f}")
    else: tok_risks.append("⚠️ لا حد أقصى للعرض")
    return {"coin_id":coin_id,"name":data.get("name",""),"symbol":data.get("symbol","").upper(),
            "desc":data.get("description",{}).get("en","")[:400],
            "categories":data.get("categories",[])[:3],
            "homepage":(data.get("links",{}).get("homepage",[""])[0] or ""),
            "github":data.get("links",{}).get("repos_url",{}).get("github",[]),
            "twitter":data.get("links",{}).get("twitter_screen_name",""),
            "price":price,"mcap":mcap,"fdv":fdv,"vol_24h":vol24,
            "circ":circ,"total":total,"max_supply":maxx,
            "circ_ratio":cr,"vol_mcap":vm,"fdv_mcap":fm,
            "chg_24h":md.get("price_change_percentage_24h",0) or 0,
            "chg_7d":md.get("price_change_percentage_7d",0) or 0,
            "chg_30d":md.get("price_change_percentage_30d",0) or 0,
            "ath":md.get("ath",{}).get("usd",0) or 0,"ath_drop":ath_drop,
            "commits":commits,"stars":stars,"prs":prs,
            "tok_score":tok_score,"tok_flags":tok_flags,"tok_risks":tok_risks,
            "rank":data.get("market_cap_rank"),
            "tw_followers":data.get("community_data",{}).get("twitter_followers",0) or 0,
            "reddit_subs":data.get("community_data",{}).get("reddit_subscribers",0) or 0,
            }


# ══════════════════════════════════════════════════════════════════
# ORACLE — AI Ensemble (Claude × 3 Roles)
# ══════════════════════════════════════════════════════════════════

HAWK_SYS = """أنت "الصقر" — خبير سيولة DEX/CEX. حلل: هل الحركة حقيقية أم مصطنعة؟ هل هناك أموال ذكية؟
أجب بالعربية، 3 فقرات قصيرة، ركز على الأرقام."""

SAGE_SYS = """أنت "الحكيم" — خبير أمان العقود وTokenomics. هل المشروع حقيقي؟ هل التوكنوميكس مستدامة؟
أجب بالعربية، 3 فقرات، كل نقطة مدعومة برقم."""

ORACLE_SYS = """أنت "العراف" — كبير محللي Wall Street وHarvard Business School.
اقرأ تقارير الصقر والحكيم وأصدر حكماً استثمارياً للأفق 6-12 شهر.
ابدأ بـ "⚡ حكم العراف:" ثم: درجة الثقة (0-100)، التوصية، هدف السعر (نسبة نمو)، أهم محفز وأهم مخاطرة.
أجب بالعربية."""

def _call_gemini(sys_p, msg, max_tok=800):
    """الصقر — Gemini."""
    if not GEMINI_KEY: return "[Gemini: أضف GEMINI_API_KEY]"
    try:
        r = requests.post(f"{GEMINI_API}?key={GEMINI_KEY}",
            headers={"Content-Type":"application/json"},
            json={"contents":[{"parts":[{"text":f"{sys_p}\n\n{msg}"}]}],
                  "generationConfig":{"maxOutputTokens":max_tok,"temperature":0.3}},
            timeout=(10,60))
        if r.status_code==200: return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        return f"[Gemini {r.status_code}]"
    except Exception as e: return f"[Gemini: {str(e)[:50]}]"

def _call_claude(sys_p, msg, max_tok=800):
    """الحكيم — Claude."""
    if not ANTHROPIC_KEY: return "[Claude: أضف ANTHROPIC_API_KEY]"
    try:
        r = requests.post(CLAUDE_API,
            headers={"x-api-key":ANTHROPIC_KEY,"anthropic-version":"2023-06-01","anthropic-beta":"messages-2023-12-15","Content-Type":"application/json"},
            json={"model":"claude-haiku-4-5-20251001","max_tokens":max_tok,"system":sys_p,
                  "messages":[{"role":"user","content":msg}]},
            timeout=(10,60))
        if r.status_code==200: return r.json()["content"][0]["text"].strip()
        # طباعة تفاصيل الخطأ لمعرفة السبب
        err_detail = ""
        try: err_detail = r.json().get("error",{}).get("message","")[:100]
        except: err_detail = r.text[:100]
        return f"[Claude {r.status_code}: {err_detail}]"
    except Exception as e: return f"[Claude: {str(e)[:50]}]"

def _call_gpt(sys_p, msg, max_tok=900):
    """العراف — GPT-4o."""
    if not OPENAI_KEY: return "[GPT: أضف OPENAI_API_KEY]"
    try:
        r = requests.post(OPENAI_API,
            headers={"Authorization":f"Bearer {OPENAI_KEY}","Content-Type":"application/json"},
            json={"model":"gpt-4o-mini","max_tokens":max_tok,"temperature":0.3,
                  "messages":[{"role":"system","content":sys_p},{"role":"user","content":msg}]},
            timeout=(10,60))
        if r.status_code==200: return r.json()["choices"][0]["message"]["content"].strip()
        return f"[GPT {r.status_code}]"
    except Exception as e: return f"[GPT: {str(e)[:50]}]"

def call_claude(system, user_msg, max_tok=800):
    """Fallback — يجرب المتاح."""
    for fn in [_call_claude, _call_gemini, _call_gpt]:
        r = fn(system, user_msg, max_tok)
        if not any(x in r for x in ["أضف","خطأ","Error",": 4","]: 5"]): return r
    return r



def oracle_ensemble(pair, security, tokenomics, fg, gm):
    pair_txt = f"""
العملة: {pair.get('name','')} | {pair.get('chain','')} | {pair.get('dex','')}
السيولة: {fmt_usd(pair.get('liquidity',0))} | حجم 1h: {fmt_usd(pair.get('vol_1h',0))}
ضغط الشراء: {pair.get('buy_pressure',50):.0f}%
تغيير 1h: {pair.get('chg_1h',0):+.2f}% | 24h: {pair.get('chg_24h',0):+.2f}%
عمر: {pair.get('age_min',0):.0f} دقيقة"""

    sec_txt = f"""
درجة الأمان: {security.get('score',0)}/100
Honeypot: {'🚨' if security.get('status')=='danger' else '✅'}
المخاطر: {' | '.join(security.get('risks',[])[:3])}"""

    tok_txt = ""
    if tokenomics:
        tok_txt = f"""
MCap: {fmt_usd(tokenomics.get('mcap',0))} | FDV: {fmt_usd(tokenomics.get('fdv',0))}
FDV/MCap: {tokenomics.get('fdv_mcap',0):.1f}x | متداول: {tokenomics.get('circ_ratio',0)*100:.0f}%
30d: {tokenomics.get('chg_30d',0):+.1f}% | ATH Drop: {tokenomics.get('ath_drop',0):.0f}%
Commits: {tokenomics.get('commits',0)}/4أسابيع"""

    mkt_txt = f"FG={fg.get('value',50)}/100 | BTC={gm.get('btc_dominance',0):.1f}% | السوق 24h={gm.get('chg_24h',0):+.1f}%"

    # 🔴 الصقر — Gemini (سيولة + أموال ذكية)
    hawk = _call_gemini(HAWK_SYS, f"حلل السيولة:\n{pair_txt}\nالسوق: {mkt_txt}", 600)
    if any(x in hawk for x in ['أضف','خطأ']): hawk = _call_claude(HAWK_SYS, f"حلل السيولة:\n{pair_txt}", 600)
    # 🔵 الحكيم — Claude (أمان + tokenomics)
    sage = _call_claude(SAGE_SYS, f"حلل الأمان والتوكنوميكس:\n{sec_txt}\n{tok_txt}", 600)
    if any(x in sage for x in ['أضف','خطأ']): sage = _call_gemini(SAGE_SYS, f"حلل التوكنوميكس:\n{tok_txt}", 600)
    # 🟢 العراف — GPT-4o (حكم نهائي موحّد)
    _oracle_inp = f"تقرير الصقر (Gemini):\n{hawk}\n\nتقرير الحكيم (Claude):\n{sage}\n\nالبيانات:\n{pair_txt}\n{sec_txt}\n{tok_txt}\n{mkt_txt}\n\nأصدر الحكم الموحّد 6-12 شهر مع التوافق بين الوكيلين."
    oracle = _call_gpt(ORACLE_SYS, _oracle_inp, 900)
    if any(x in oracle for x in ['أضف','خطأ']): oracle = _call_claude(ORACLE_SYS, _oracle_inp, 900)
    if any(x in oracle for x in ['أضف','خطأ']): oracle = _call_gemini(ORACLE_SYS, _oracle_inp, 900)
    conf = 50
    m = re.search(r'(\d{1,3})\s*(?:/100|٪|%)', oracle)
    if m: conf = min(100, int(m.group(1)))
    return {"hawk":hawk,"hawk_model":"Gemini 1.5 Flash","sage":sage,"sage_model":"Claude Sonnet","oracle":oracle,"oracle_model":"GPT-4o","confidence":conf}


# ══════════════════════════════════════════════════════════════════
# Market Data
# ══════════════════════════════════════════════════════════════════

def get_fg():
    d = safe_get(f"{ALTME}/fng/?limit=1")
    if d and d.get("data"):
        v = int(d["data"][0].get("value",50))
        c = d["data"][0].get("value_classification","")
        icon = "😱" if v<=20 else ("😰" if v<=40 else ("😐" if v<=60 else ("🤑" if v<=80 else "🚀")))
        return {"value":v,"class":c,"icon":icon}
    return {"value":50,"class":"Neutral","icon":"😐"}

def get_gm():
    d = safe_get(f"{COINGECKO}/global")
    if not d: return {}
    g = d.get("data",{})
    return {"total_mcap":g.get("total_market_cap",{}).get("usd",0),
            "btc_dominance":g.get("market_cap_percentage",{}).get("btc",0),
            "eth_dominance":g.get("market_cap_percentage",{}).get("eth",0),
            "chg_24h":g.get("market_cap_change_percentage_24h_usd",0),
            "active_coins":g.get("active_cryptocurrencies",0),
            "total_vol":g.get("total_volume",{}).get("usd",0)}


# ══════════════════════════════════════════════════════════════════
# رسائل
# ══════════════════════════════════════════════════════════════════

def msg_scan(pairs, cex, fg, gm, auto=False):
    ts = now_sa()
    fgv=fg.get("value",50); fgi=fg.get("icon","😐")
    btcd=gm.get("btc_dominance",0); gchg=gm.get("chg_24h",0)
    pfx = "🔔 *تقرير تلقائي*\n" if auto else "🔭 *مسح شامل*\n"
    m = f"{pfx}🕐 {ts}\n━━━━━━━━━━━━━━━━━━━━\n\n"
    m += f"🌍 {fgi} FG=`{fgv}` | BTC=`{btcd:.1f}%` | 24h=`{gchg:+.1f}%`\n\n"
    if pairs:
        m += f"🔥 *DEX — عبر الـ Gatekeeper ({len(pairs)} فرصة):*\n\n"
        for i,p in enumerate(pairs[:6],1):
            bp=p.get("buy_pressure",50)
            bpi="🟢" if bp>60 else("🔴" if bp<40 else "⚪")
            age_h=p.get("age_min",0)/60
            m += (f"*{i}. {p.get('name','')}* | `{p.get('chain','')}` | `{p.get('dex','')}`\n"
                  f"   💧 `{fmt_usd(p.get('liquidity',0))}` 📊 `{fmt_usd(p.get('vol_1h',0))}/h`\n"
                  f"   {bpi} `{bp:.0f}%` 📈 `{p.get('chg_1h',0):+.1f}%` ⏱ `{age_h:.1f}h`\n"
                  f"   `/analyze {p.get('name','').split('/')[0].strip()}`\n\n")
    if cex:
        m += f"⚡ *Binance — تحركات استثنائية:*\n"
        for cc in cex[:4]:
            m += f"   • `{cc.get('symbol','')}` `{cc.get('chg_24h',0):+.1f}%` | {fmt_usd(cc.get('vol_24h',0))}\n"
        m += "\n"
    m += "━━━━━━━━━━━━━━━━━━━━\n"
    m += "`/analyze X` تحليل AI | `/watch X` متابعة | `/settings` الإعدادات\n"
    m += "⚠️ _للأغراض التعليمية فقط_"
    return m


def msg_analysis(pair, sec, tok, ens, fg, gm):
    ts=now_sa(); name=pair.get("name",""); conf=ens.get("confidence",50)
    bar="█"*int(conf/10)+"░"*(10-int(conf/10))
    sec_icon="🟢" if sec.get("status")=="safe" else("🟡" if sec.get("status")=="warning" else "🔴")
    m = f"🔬 *تحليل شامل: {name}*\n🕐 {ts}\n━━━━━━━━━━━━━━━━━━━━\n\n"
    m += f"📊 *نظرة عامة:*\n"
    m += f"⛓ `{pair.get('chain','')}` 🔄 `{pair.get('dex','')}` 💰 `{fmt_usd(pair.get('price_usd',0))}`\n"
    m += f"💧 `{fmt_usd(pair.get('liquidity',0))}` 📊 `{fmt_usd(pair.get('vol_1h',0))}/h`\n"
    m += f"📈 `{pair.get('chg_1h',0):+.1f}%` (1h) `{pair.get('chg_24h',0):+.1f}%` (24h)\n"
    m += f"🎯 ضغط الشراء: `{pair.get('buy_pressure',50):.0f}%`\n\n"
    m += f"🛡 *الأمان: {sec_icon} {sec.get('score',0)}/100*\n"
    for r in sec.get("risks",[])[:3]: m += f"  {r}\n"
    for f in sec.get("flags",[])[:2]: m += f"  {f}\n"
    m += "\n"
    if tok and tok.get("mcap"):
        m += f"📦 *Tokenomics:*\n"
        m += f"MCap: `{fmt_usd(tok.get('mcap',0))}` FDV: `{fmt_usd(tok.get('fdv',0))}`\n"
        m += f"FDV/MCap: `{tok.get('fdv_mcap',0):.1f}x` عرض: `{tok.get('circ_ratio',0)*100:.0f}%`\n"
        m += f"Commits: `{tok.get('commits',0)}` | الرتبة: `#{tok.get('rank','?')}`\n"
        for tf in tok.get("tok_flags",[])[:2]: m += f"  {tf}\n"
        for tr in tok.get("tok_risks",[])[:2]: m += f"  {tr}\n"
        if tok.get("desc"): m += f"\n📖 _{tok['desc'][:200]}_\n"
        m += "\n"
    m += "━━━━━━━━━━━━━━━━━━━━\n"
    m += "🤖 *مجلس المستشارين:*\n\n"
    m += f"🔴 *الصقر ({ens.get('hawk_model','Gemini')}):*\n_{ens.get('hawk','')[:300]}_\n\n"
    m += f"🔵 *الحكيم ({ens.get('sage_model','Claude')}):*\n_{ens.get('sage','')[:300]}_\n\n"
    m += f"🟢 *العراف ({ens.get('oracle_model','GPT-4o')}):*\n_{ens.get('oracle','')[:400]}_\n\n"
    m += f"━━━━━━━━━━━━━━━━━━━━\n"
    m += f"📊 *مؤشر الثقة:* `{conf}/100`\n`{bar}`\n\n"
    m += "⚠️ _للأغراض التعليمية فقط — ليس توصية استثمارية_"
    return m


def msg_watch_alert(coin_id, detail, sec_score, oracle_mini):
    m = f"🔔 *تنبيه متابعة: {detail.get('name','')} ({detail.get('symbol','')})*\n"
    m += f"🕐 {now_sa()}\n━━━━━━━━━━━━━━━━━━━━\n"
    icon="📈" if detail.get('chg_24h',0)>0 else "📉"
    m += f"💰 `{fmt_usd(detail.get('price',0))}` {icon} `{detail.get('chg_24h',0):+.2f}%`\n"
    m += f"📊 7d: `{detail.get('chg_7d',0):+.1f}%` MCap: `{fmt_usd(detail.get('mcap',0))}`\n"
    m += f"🛡 أمان: `{sec_score}/100` 💻 Commits: `{detail.get('commits',0)}`\n"
    m += f"👥 Twitter: `{detail.get('tw_followers',0):,}`\n\n"
    m += f"🟢 *العراف:*\n_{oracle_mini[:300]}_\n\n"
    m += f"`/analyze {detail.get('symbol','')}`"
    return m


# ══════════════════════════════════════════════════════════════════
# Handlers
# ══════════════════════════════════════════════════════════════════

async def cmd_start(u: Update, c: ContextTypes.DEFAULT_TYPE):
    ai_status = "✅ مفعّل" if ANTHROPIC_KEY else "❌ أضف ANTHROPIC_API_KEY في Railway"
    await u.message.reply_text(
        f"🔭 *CRYPTO SCANNER — AI Ensemble*\n"
        f"AI Ensemble:\n🔴 Gemini (الصقر) | 🔵 Claude (الحكيم) | 🟢 GPT-4o (العراف)\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 *وكلاء AI:*\n"
        "🔴 الصقر — سيولة + أموال ذكية\n"
        "🔵 الحكيم — أمان + توكنوميكس\n"
        "🟢 العراف — Wall St / Harvard\n\n"
        "📊 *الأوامر:*\n"
        "`/scan`        — مسح DEX+CEX الآن\n"
        "`/analyze X`   — تحليل AI عميق\n"
        "`/watch X`     — متابعة ساعية\n"
        "`/watchlist`   — قائمة متابعتك\n"
        "`/market`      — السوق الكلي\n"
        "`/dex`         — إدراجات DEX\n"
        "`/settings`    — ضبط الفلتر\n\n"
        "🔁 `تفعيل` — مسح تلقائي كل 4 ساعات\n\n"
        "🎯 *Gatekeeper الافتراضي:*\n"
        "سيولة > $250K | حجم 1h > $50K | عمر > 5 دقائق\n\n"
        "⚠️ _للأغراض التعليمية فقط_",
        parse_mode="Markdown")


async def cmd_scan(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid = u.effective_chat.id
    s = user_settings.get(cid,{})
    ml = s.get("min_liquidity",250_000); mv = s.get("min_volume",50_000)
    wait = await u.message.reply_text(
        f"🔭 الصقر يمسح 5 سلاسل...\n💧 سيولة > {fmt_usd(ml)} | 📊 حجم > {fmt_usd(mv)}/h\n⏳ 30-60 ثانية...",
        parse_mode="Markdown")
    try:
        loop = asyncio.get_event_loop()
        def do():
            fg=get_fg(); gm=get_gm()
            pairs=hawk_dex_scan(ml,mv); cex=hawk_cex_anomalies()
            return fg,gm,pairs,cex
        fg,gm,pairs,cex = await asyncio.wait_for(loop.run_in_executor(None,do),timeout=90)
        scan_results[cid]={"pairs":pairs,"cex":cex,"fg":fg,"gm":gm,"ts":now_sa()}
        msg = msg_scan(pairs,cex,fg,gm)
        await wait.delete()
        for chunk in [msg[i:i+3800] for i in range(0,len(msg),3800)]:
            try: await u.message.reply_text(chunk,parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تحديث",callback_data="rescan")]]))
            except: await u.message.reply_text(chunk)
    except asyncio.TimeoutError:
        await wait.edit_text("❌ انتهى الوقت — حاول لاحقاً")
    except Exception as e:
        await wait.edit_text(f"❌ {str(e)[:100]}")


async def cmd_analyze(u: Update, c: ContextTypes.DEFAULT_TYPE):
    parts = u.message.text.strip().split(maxsplit=1)
    if len(parts)<2:
        await u.message.reply_text("مثال: `/analyze PEPE` أو `/analyze ethereum`",parse_mode="Markdown"); return
    raw = parts[1].strip()
    wait = await u.message.reply_text(
        f"🤖 *مجلس المستشارين يحلل {raw.upper()}...*\n🔴+🔵+🟢\n⏳ 60-90 ثانية...",
        parse_mode="Markdown")
    try:
        loop = asyncio.get_event_loop()
        def do():
            fg=get_fg(); gm=get_gm()
            # بحث في DexScreener
            ds = safe_get(f"{DEXSCREEN}/search/?q={raw}",timeout=(8,20))
            pair={}
            if ds and ds.get("pairs"):
                best = sorted(ds["pairs"],key=lambda p:float(p.get("liquidity",{}).get("usd",0) or 0),reverse=True)[0]
                bp_raw = best
                liq = float(bp_raw.get("liquidity",{}).get("usd",0) or 0)
                vol1 = float(bp_raw.get("volume",{}).get("h1",0) or 0)
                vol24 = float(bp_raw.get("volume",{}).get("h24",0) or 0)
                chg1h = float(bp_raw.get("priceChange",{}).get("h1",0) or 0)
                chg24 = float(bp_raw.get("priceChange",{}).get("h24",0) or 0)
                age_ms = bp_raw.get("pairCreatedAt",0) or 0
                age_m = (time.time()*1000-age_ms)/60000 if age_ms else 9999
                pair = {
                    "pool_id":    bp_raw.get("pairAddress",""),
                    "name":       f"{bp_raw.get('baseToken',{}).get('name','?')} ({bp_raw.get('baseToken',{}).get('symbol','?')})",
                    "chain":      bp_raw.get("chainId",""),
                    "dex":        bp_raw.get("dexId",""),
                    "price_usd":  float(bp_raw.get("priceUsd","0") or 0),
                    "liquidity":  liq,
                    "vol_1h":     vol1,
                    "vol_24h":    vol24,
                    "chg_1h":    chg1h,
                    "chg_24h":   chg24,
                    "age_min":    age_m,
                    "buy_pressure":55.0,
                    "base_addr":  bp_raw.get("baseToken",{}).get("address",""),
                    "url":        bp_raw.get("url",""),
                }
            # CoinGecko
            tok={}
            search = safe_get(f"{COINGECKO}/search",{"query":raw})
            if search and search.get("coins"):
                tok = sage_tokenomics(search["coins"][0]["id"])
                if not pair:
                    pair = {
                        "name": tok.get("name",""),
                        "chain":"multi","dex":"CEX/DEX",
                        "price_usd":tok.get("price",0),
                        "liquidity":tok.get("vol_24h",0),
                        "vol_1h":tok.get("vol_24h",0)/24 if tok.get("vol_24h") else 0,
                        "vol_24h":tok.get("vol_24h",0),
                        "chg_1h":0,"chg_24h":tok.get("chg_24h",0),
                        "buy_pressure":55,"age_min":99999,
                        "base_addr":"","url":tok.get("homepage",""),
                    }
            if not pair: return None,None,None,None,fg,gm
            # Audit
            addr  = pair.get("base_addr","")
            chain = pair.get("chain","ethereum") if pair.get("chain") not in ("multi","") else "ethereum"
            sec = sage_audit(addr, chain) if addr else {"status":"unknown","score":50,"flags":[],"risks":["⚠️ عنوان غير متاح"]}
            # AI Ensemble
            ens = oracle_ensemble(pair,sec,tok,fg,gm)
            return pair,sec,tok,ens,fg,gm
        result = await asyncio.wait_for(loop.run_in_executor(None,do),timeout=120)
        pair,sec,tok,ens,fg,gm = result
        if not pair:
            await wait.edit_text(f"❌ لم يتم العثور على '{raw}'"); return
        msg = msg_analysis(pair,sec,tok,ens,fg,gm)
        await wait.delete()
        for i,chunk in enumerate([msg[j:j+3800] for j in range(0,len(msg),3800)]):
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("👁 تابع",callback_data=f"watchadd:{raw}"),
                InlineKeyboardButton("🔄 تحديث",callback_data=f"reanalyze:{raw}"),
            ]]) if i==0 else None
            try: await u.message.reply_text(chunk,parse_mode="Markdown",reply_markup=kb,disable_web_page_preview=True)
            except: await u.message.reply_text(chunk,reply_markup=kb)
    except asyncio.TimeoutError:
        await wait.edit_text("❌ انتهى الوقت")
    except Exception as e:
        await wait.edit_text(f"❌ {str(e)[:100]}")


async def cmd_watch(u: Update, c: ContextTypes.DEFAULT_TYPE):
    parts = u.message.text.strip().split(maxsplit=1)
    if len(parts)<2: await u.message.reply_text("مثال: `/watch PEPE`",parse_mode="Markdown"); return
    raw = parts[1].strip().lower(); cid = u.effective_chat.id
    wait = await u.message.reply_text(f"🔍 جاري البحث عن {raw.upper()}...")
    loop = asyncio.get_event_loop()
    search = await loop.run_in_executor(None,lambda:safe_get(f"{COINGECKO}/search",{"query":raw}))
    coin_id=raw; coin_name=raw.upper()
    if search and search.get("coins"):
        coin_id=search["coins"][0]["id"]; coin_name=search["coins"][0].get("name",raw.upper())
    watching.setdefault(cid,{})[coin_id]={"name":coin_name,"raw":raw,"added":now_sa()}
    jn=f"watch_{cid}_{coin_id}"
    for j in c.job_queue.get_jobs_by_name(jn): j.schedule_removal()
    c.job_queue.run_repeating(watch_job,interval=3600,first=300,
        data={"chat_id":cid,"coin_id":coin_id,"coin_name":coin_name},name=jn)
    await wait.edit_text(f"👁 *تمت إضافة {coin_name}*\nتنبيه ساعي: سعر + أمان + رأي العراف\nإيقاف: `/unwatch {raw}`",parse_mode="Markdown")


async def cmd_unwatch(u: Update, c: ContextTypes.DEFAULT_TYPE):
    parts=u.message.text.strip().split(maxsplit=1)
    if len(parts)<2: await u.message.reply_text("مثال: `/unwatch PEPE`",parse_mode="Markdown"); return
    raw=parts[1].strip().lower(); cid=u.effective_chat.id
    search=safe_get(f"{COINGECKO}/search",{"query":raw})
    coin_id=search["coins"][0]["id"] if search and search.get("coins") else raw
    jn=f"watch_{cid}_{coin_id}"
    for j in c.job_queue.get_jobs_by_name(jn): j.schedule_removal()
    watching.get(cid,{}).pop(coin_id,None)
    await u.message.reply_text(f"⛔ توقفت متابعة {raw.upper()}")


async def cmd_watchlist(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid=u.effective_chat.id; coins=watching.get(cid,{})
    if not coins: await u.message.reply_text("قائمتك فارغة\n`/watch PEPE`",parse_mode="Markdown"); return
    m="👁 *قائمة متابعتك:*\n\n"
    for coin_id,info in coins.items():
        m+=f"• *{info.get('name',coin_id)}* — {info.get('added','')}\n"
        m+=f"  `/analyze {info.get('raw',coin_id)}` | `/unwatch {info.get('raw',coin_id)}`\n\n"
    await u.message.reply_text(m,parse_mode="Markdown")


async def cmd_market(u: Update, c: ContextTypes.DEFAULT_TYPE):
    wait=await u.message.reply_text("⏳ جاري جلب بيانات السوق والتحليل AI...")
    loop=asyncio.get_event_loop()
    try:
        def do():
            fg=get_fg(); gm=get_gm()
            mkt_txt=f"FG={fg.get('value',50)}/100 ({fg.get('class','')}), BTC={gm.get('btc_dominance',0):.1f}%, MCap={fmt_usd(gm.get('total_mcap',0))}, 24h={gm.get('chg_24h',0):+.1f}%"
            oracle_mkt=call_claude(ORACLE_SYS,f"حلل حالة السوق الكلي وأعطِ توصية عامة:\n{mkt_txt}",500)
            return fg,gm,oracle_mkt
        fg,gm,oracle_mkt = await asyncio.wait_for(loop.run_in_executor(None,do),timeout=60)
        fgv=fg.get("value",50); fgi=fg.get("icon","😐"); fgc=fg.get("class","")
        m=f"🌍 *السوق الكلي*\n🕐 {now_sa()}\n━━━━━━━━━━━━━━━━━━━━\n\n"
        m+=f"{fgi} FG: `{fgv}/100` — {fgc}\n"
        m+=f"💰 MCap: `{fmt_usd(gm.get('total_mcap',0))}`\n"
        m+=f"📊 Vol: `{fmt_usd(gm.get('total_vol',0))}`\n"
        m+=f"{'📈' if gm.get('chg_24h',0)>0 else '📉'} 24h: `{gm.get('chg_24h',0):+.2f}%`\n"
        m+=f"₿ BTC: `{gm.get('btc_dominance',0):.1f}%` Ξ ETH: `{gm.get('eth_dominance',0):.1f}%`\n\n"
        m+=f"━━━━━━━━━━━━━━━━━━━━\n🟢 *العراف:*\n_{oracle_mkt[:500]}_\n\n"
        m+="⚠️ _للأغراض التعليمية فقط_"
        await wait.edit_text(m,parse_mode="Markdown")
    except Exception as e:
        await wait.edit_text(f"❌ {str(e)[:80]}")


async def cmd_dex(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid=u.effective_chat.id; s=user_settings.get(cid,{})
    ml=s.get("min_liquidity",250_000); mv=s.get("min_volume",50_000)
    wait=await u.message.reply_text(f"🔍 الصقر يمسح DEX...\n💧 > {fmt_usd(ml)}",parse_mode="Markdown")
    loop=asyncio.get_event_loop()
    try:
        pairs=await asyncio.wait_for(loop.run_in_executor(None,hawk_dex_scan,ml,mv),timeout=60)
        m=f"🆕 *إدراجات DEX*\n🕐 {now_sa()}\n\n"
        for i,p in enumerate(pairs[:8],1):
            bp=p.get("buy_pressure",50); bpi="🟢" if bp>60 else("🔴" if bp<40 else "⚪")
            m+=(f"*{i}. {p.get('name','')}*\n"
                f"   ⛓ `{p.get('chain','')}` 🔄 `{p.get('dex','')}`\n"
                f"   💧 `{fmt_usd(p.get('liquidity',0))}` 📊 `{fmt_usd(p.get('vol_1h',0))}/h`\n"
                f"   {bpi} `{bp:.0f}%` 📈 `{p.get('chg_1h',0):+.1f}%` ⏱ `{p.get('age_min',0)/60:.1f}h`\n"
                f"   `/analyze {p.get('name','').split('/')[0].strip()}`\n\n")
        if not pairs: m+="_لا توجد نتائج تجاوزت الـ Gatekeeper_\n"
        m+="⚠️ _العملات الجديدة مخاطرها عالية جداً_"
        await wait.edit_text(m,parse_mode="Markdown")
    except Exception as e:
        await wait.edit_text(f"❌ {str(e)[:80]}")


async def cmd_settings(u: Update, c: ContextTypes.DEFAULT_TYPE):
    cid=u.effective_chat.id; s=user_settings.get(cid,{})
    ml=s.get("min_liquidity",250_000); mv=s.get("min_volume",50_000)
    m=f"⚙️ *الإعدادات الحالية:*\n\n"
    m+=f"💧 حد السيولة: `{fmt_usd(ml)}`\n📊 حد الحجم 1h: `{fmt_usd(mv)}`\n"
    await u.message.reply_text(m,parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💧 $100K",callback_data="sl:100000"),
             InlineKeyboardButton("💧 $250K",callback_data="sl:250000"),
             InlineKeyboardButton("💧 $500K",callback_data="sl:500000")],
            [InlineKeyboardButton("📊 $10K",callback_data="sv:10000"),
             InlineKeyboardButton("📊 $50K",callback_data="sv:50000"),
             InlineKeyboardButton("📊 $100K",callback_data="sv:100000")],
        ]))


# ══════════════════════════════════════════════════════════════════
# Jobs
# ══════════════════════════════════════════════════════════════════

async def auto_scan_job(ctx):
    cid=ctx.job.data["chat_id"]; s=user_settings.get(cid,{})
    ml=s.get("min_liquidity",250_000); mv=s.get("min_volume",50_000)
    try:
        loop=asyncio.get_event_loop()
        def do():
            fg=get_fg(); gm=get_gm()
            pairs=hawk_dex_scan(ml,mv); cex=hawk_cex_anomalies()
            return fg,gm,pairs,cex
        fg,gm,pairs,cex=await asyncio.wait_for(loop.run_in_executor(None,do),timeout=120)
        scan_results[cid]={"pairs":pairs,"cex":cex,"fg":fg,"gm":gm,"ts":now_sa()}
        if pairs or cex:
            msg=msg_scan(pairs,cex,fg,gm,auto=True)
            for chunk in [msg[i:i+3800] for i in range(0,len(msg),3800)]:
                try: await ctx.bot.send_message(cid,chunk,parse_mode="Markdown")
                except: await ctx.bot.send_message(cid,chunk)
    except Exception as e:
        logging.warning(f"[AUTO_SCAN] {cid}: {e}")


async def watch_job(ctx):
    cid=ctx.job.data["chat_id"]; coin_id=ctx.job.data["coin_id"]
    try:
        loop=asyncio.get_event_loop()
        def do():
            det=sage_tokenomics(coin_id)
            if not det: return None,None,None
            sec=sage_audit(det.get("github",[""])[0] if det.get("github") else "","ethereum")
            mini=f"{det.get('name','')} | MCap:{fmt_usd(det.get('mcap',0))} | 24h:{det.get('chg_24h',0):+.1f}% | ATH:{det.get('ath_drop',0):.0f}% | commits:{det.get('commits',0)}"
            ov=call_claude(ORACLE_SYS,f"ملخص استثماري مختصر (3 أسطر):\n{mini}",300)
            return det,sec,ov
        det,sec,ov=await asyncio.wait_for(loop.run_in_executor(None,do),timeout=60)
        if not det: return
        msg=msg_watch_alert(coin_id,det,sec.get("score",50) if sec else 50,ov)
        await ctx.bot.send_message(cid,msg,parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔬 تحليل كامل",callback_data=f"reanalyze:{det.get('symbol',coin_id).lower()}"),
                InlineKeyboardButton("⛔ إيقاف",callback_data=f"uw:{coin_id}"),
            ]]))
    except Exception as e:
        logging.warning(f"[WATCH_JOB] {coin_id}: {e}")


async def handle_callback(u: Update, c: ContextTypes.DEFAULT_TYPE):
    q=u.callback_query; cid=q.message.chat_id; data=q.data
    await q.answer()
    if data=="rescan":
        s=user_settings.get(cid,{}); ml=s.get("min_liquidity",250_000); mv=s.get("min_volume",50_000)
        await q.edit_message_text("🔭 جاري التحديث...")
        loop=asyncio.get_event_loop()
        def do(): return get_fg(),get_gm(),hawk_dex_scan(ml,mv),hawk_cex_anomalies()
        try:
            fg,gm,pairs,cex=await asyncio.wait_for(loop.run_in_executor(None,do),timeout=90)
            msg=msg_scan(pairs,cex,fg,gm)
            await q.edit_message_text(msg[:3800],parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 تحديث",callback_data="rescan")]]))
        except Exception as e: await q.edit_message_text(f"❌ {str(e)[:80]}")
    elif data.startswith("sl:"):
        user_settings.setdefault(cid,{})["min_liquidity"]=int(data.split(":")[1])
        await q.answer(f"✅ حد السيولة: {fmt_usd(int(data.split(':')[1]))}",show_alert=True)
    elif data.startswith("sv:"):
        user_settings.setdefault(cid,{})["min_volume"]=int(data.split(":")[1])
        await q.answer(f"✅ حد الحجم: {fmt_usd(int(data.split(':')[1]))}",show_alert=True)
    elif data.startswith("watchadd:"):
        raw=data.split(":",1)[1]
        search=safe_get(f"{COINGECKO}/search",{"query":raw})
        coin_id=search["coins"][0]["id"] if search and search.get("coins") else raw
        coin_name=search["coins"][0].get("name",raw.upper()) if search and search.get("coins") else raw.upper()
        watching.setdefault(cid,{})[coin_id]={"name":coin_name,"raw":raw,"added":now_sa()}
        jn=f"watch_{cid}_{coin_id}"
        for j in c.job_queue.get_jobs_by_name(jn): j.schedule_removal()
        c.job_queue.run_repeating(watch_job,interval=3600,first=300,
            data={"chat_id":cid,"coin_id":coin_id,"coin_name":coin_name},name=jn)
        await q.answer(f"✅ تمت إضافة {coin_name}",show_alert=True)
    elif data.startswith("uw:"):
        coin_id=data.split(":",1)[1]
        jn=f"watch_{cid}_{coin_id}"
        for j in c.job_queue.get_jobs_by_name(jn): j.schedule_removal()
        watching.get(cid,{}).pop(coin_id,None)
        await q.answer("⛔ تم الإيقاف",show_alert=True)
    elif data.startswith("reanalyze:"):
        raw=data.split(":",1)[1]
        await q.edit_message_text(f"🤖 جاري إعادة تحليل {raw.upper()}...",parse_mode="Markdown")
        loop=asyncio.get_event_loop()
        def do2():
            fg=get_fg(); gm=get_gm()
            search=safe_get(f"{COINGECKO}/search",{"query":raw})
            if not search or not search.get("coins"): return None
            det=sage_tokenomics(search["coins"][0]["id"])
            if not det: return None
            pair={"name":det.get("name",""),"chain":"multi","dex":"CEX/DEX",
                  "price_usd":det.get("price",0),"liquidity":det.get("vol_24h",0),
                  "vol_1h":det.get("vol_24h",0)/24,"vol_24h":det.get("vol_24h",0),
                  "chg_1h":0,"chg_24h":det.get("chg_24h",0),"buy_pressure":55,"age_min":99999,"base_addr":""}
            sec={"status":"unknown","score":50,"flags":[],"risks":["⚠️ فحص سريع"]}
            ens=oracle_ensemble(pair,sec,det,fg,gm)
            return det,pair,sec,ens,fg,gm
        try:
            res=await asyncio.wait_for(loop.run_in_executor(None,do2),timeout=90)
            if not res: await q.edit_message_text(f"❌ لم يتم العثور على {raw}"); return
            det,pair,sec,ens,fg,gm=res
            msg=msg_analysis(pair,sec,det,ens,fg,gm)
            await q.edit_message_text(msg[:3800],parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 تحديث",callback_data=f"reanalyze:{raw}"),
                    InlineKeyboardButton("👁 تابع",callback_data=f"watchadd:{raw}"),
                ]]))
        except Exception as e: await q.edit_message_text(f"❌ {str(e)[:80]}")


async def handle_msg(u: Update, c: ContextTypes.DEFAULT_TYPE):
    text=u.message.text.strip(); cid=u.effective_chat.id
    if text.lower() in ("تفعيل","start","auto","تلقائي"):
        jn=f"auto_{cid}"
        for j in c.job_queue.get_jobs_by_name(jn): j.schedule_removal()
        c.job_queue.run_repeating(auto_scan_job,interval=14400,first=60,
            data={"chat_id":cid},name=jn)
        await u.message.reply_text("✅ *تم تفعيل المسح التلقائي كل 4 ساعات*\nإيقاف: `إيقاف`",parse_mode="Markdown")
        return
    if text.lower() in ("إيقاف","stop","وقف"):
        jn=f"auto_{cid}"
        for j in c.job_queue.get_jobs_by_name(jn): j.schedule_removal()
        await u.message.reply_text("⛔ تم الإيقاف"); return
    if re.match(r'^[A-Za-z0-9\-]{2,20}$',text):
        await u.message.reply_text(
            f"🔬 `/analyze {text}` تحليل AI عميق\n👁 `/watch {text}` متابعة ساعية",
            parse_mode="Markdown"); return
    await u.message.reply_text(
        "`/scan` `/analyze X` `/watch X` `/market` `/dex` `/settings`\n`تفعيل` للمسح كل 4 ساعات",
        parse_mode="Markdown")


def main():
    if BOT_TOKEN in ("YOUR_BOT_TOKEN_HERE",""):
        print("❌ أضف BOT_TOKEN في Railway"); return
    if not ANTHROPIC_KEY:
        print("⚠️  ANTHROPIC_API_KEY غير موجود — وكلاء AI معطلون")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    for cmd,fn in [("start",cmd_start),("scan",cmd_scan),("analyze",cmd_analyze),
                   ("watch",cmd_watch),("unwatch",cmd_unwatch),("watchlist",cmd_watchlist),
                   ("market",cmd_market),("dex",cmd_dex),("settings",cmd_settings)]:
        app.add_handler(CommandHandler(cmd,fn))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND,handle_msg))
    print(f"🔭 CRYPTO SCANNER BOT — AI: {'✅' if ANTHROPIC_KEY else '❌ أضف ANTHROPIC_API_KEY'}")
    app.run_polling(drop_pending_updates=True)

if __name__=="__main__":
    main()
