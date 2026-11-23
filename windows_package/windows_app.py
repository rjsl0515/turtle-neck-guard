import datetime
import json
import os
import subprocess
import sys
import traceback
import time
import winsound

# WebView2에서 웹캠 권한 자동 허용 및 오토플레이 허용 (webview import 전에 설정 필수)
os.environ.setdefault(
    "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
    "--use-fake-ui-for-media-stream --autoplay-policy=no-user-gesture-required",
)

import webview


def resource_path(relative_path: str) -> str:
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def get_app_dir() -> str:
    app_data = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    save_dir = os.path.join(app_data, "TurtleNeckGuard")
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


APP_DIR = get_app_dir()
STATS_PATH = os.path.join(APP_DIR, "stats.json")
LOG_PATH = os.path.join(APP_DIR, "app.log")
HTML_PATH = resource_path("index.html")


def log_error(msg: str):
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass


def today_str() -> str:
    return datetime.date.today().isoformat()


def load_stats() -> dict:
    today = today_str()
    default = {
        "date": today,
        "today_count": 0,
        "today_duration_sec": 0.0,
        "today_good_sec": 0.0,
        "today_score_sum": 0.0,
        "today_score_samples": 0,
        "total_count": 0,
        "total_duration_sec": 0.0,
        "total_good_sec": 0.0,
        "total_score_sum": 0.0,
        "total_score_samples": 0,
        "recent_events": [],
        "daily_history": {},
        "trigger_sec": 6.0,
        "bad_threshold": 45,
        "manner_mode_enabled": True,
        "language": "ko",
        "alarm_threshold": 3,
    }
    try:
        if os.path.exists(STATS_PATH):
            with open(STATS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in default.items():
                data.setdefault(k, v)
            if data.get("date") != today:
                prev_mon = data["today_good_sec"] + data["today_duration_sec"]
                prev_pct = round((data["today_good_sec"] / prev_mon) * 100) if prev_mon > 0 else 100
                data.setdefault("daily_history", {})[data["date"]] = {
                    "good_pct": prev_pct,
                    "count": data["today_count"],
                    "duration_sec": int(data["today_duration_sec"]),
                }
                data.update({
                    "date": today,
                    "today_count": 0,
                    "today_duration_sec": 0.0,
                    "today_good_sec": 0.0,
                    "today_score_sum": 0.0,
                    "today_score_samples": 0,
                    "recent_events": [],
                })
            return data
    except Exception:
        pass
    return default


def save_stats(stats: dict):
    mon = stats["today_good_sec"] + stats["today_duration_sec"]
    pct = round((stats["today_good_sec"] / mon) * 100) if mon > 0 else 100
    hist = stats.setdefault("daily_history", {})
    hist[stats["date"]] = {
        "good_pct": pct,
        "count": stats["today_count"],
        "duration_sec": int(stats["today_duration_sec"]),
    }
    keys = sorted(hist.keys())
    if len(keys) > 7:
        for old_k in keys[:-7]:
            hist.pop(old_k, None)
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def detect_active_meeting_app() -> str:
    targets = {
        "zoom.exe": "Zoom",
        "discord.exe": "Discord",
        "teams.exe": "Teams",
        "ms-teams.exe": "Teams",
        "webexmta.exe": "Webex",
        "ptoneclk.exe": "Webex",
    }
    try:
        output = subprocess.check_output(
            ["tasklist", "/FO", "CSV", "/NH"],
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=True,
            errors="ignore",
        ).lower()
        for proc_name, label in targets.items():
            if f'"{proc_name}"' in output:
                return label
    except Exception:
        pass
    return ""


class TurtleApi:
    def __init__(self):
        self.stats = load_stats()
        self.enabled = True
        self.prev_warning = False
        self.prev_calibrated = False
        self.last_tick = time.time()
        self.last_save = time.time()
        self.last_meeting_check = 0.0
        self.active_meeting_app = ""
        self.window = None
        self.is_fullscreen = False

    def get_state(self):
        return self._payload()

    def toggle(self):
        self.enabled = not self.enabled
        if not self.enabled and self.prev_warning:
            self.prev_warning = False
            self._exit_warning_mode()
        return self._payload()

    def test_alarm(self):
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass
        return True

    def update_settings(
        self,
        trigger_sec=6.0,
        bad_threshold=45,
        manner_mode_enabled=True,
        language="ko",
        alarm_threshold=3,
    ):
        self.stats["trigger_sec"] = max(3.0, min(15.0, float(trigger_sec)))
        self.stats["bad_threshold"] = max(25, min(70, int(bad_threshold)))
        self.stats["manner_mode_enabled"] = bool(manner_mode_enabled)
        self.stats["language"] = str(language or "ko")
        self.stats["alarm_threshold"] = max(0, min(20, int(alarm_threshold)))
        if not self.stats["manner_mode_enabled"]:
            self.active_meeting_app = ""
        save_stats(self.stats)
        return self._payload()

    def reset_stats(self):
        kept = {
            "trigger_sec": self.stats["trigger_sec"],
            "bad_threshold": self.stats["bad_threshold"],
            "manner_mode_enabled": self.stats["manner_mode_enabled"],
            "language": self.stats["language"],
            "alarm_threshold": self.stats["alarm_threshold"],
        }
        self.stats = {
            "date": today_str(),
            "today_count": 0,
            "today_duration_sec": 0.0,
            "today_good_sec": 0.0,
            "today_score_sum": 0.0,
            "today_score_samples": 0,
            "total_count": 0,
            "total_duration_sec": 0.0,
            "total_good_sec": 0.0,
            "total_score_sum": 0.0,
            "total_score_samples": 0,
            "recent_events": [],
            "daily_history": {},
            **kept,
        }
        save_stats(self.stats)
        return self._payload()

    def _enter_warning_mode(self):
        if not self.window:
            return
        try:
            self.window.restore()
        except Exception:
            pass
        try:
            self.window.on_top = True
        except Exception:
            pass
        try:
            if not self.is_fullscreen:
                self.window.toggle_fullscreen()
                self.is_fullscreen = True
        except Exception:
            pass

    def _exit_warning_mode(self):
        if not self.window:
            return
        try:
            if self.is_fullscreen:
                self.window.toggle_fullscreen()
                self.is_fullscreen = False
        except Exception:
            pass
        try:
            self.window.on_top = False
        except Exception:
            pass
        try:
            self.window.minimize()
        except Exception:
            pass

    def send_status(self, score, warning, calibrated):
        now = time.time()
        dt = max(0.0, min(1.0, now - self.last_tick))
        self.last_tick = now

        if self.stats.get("manner_mode_enabled", True):
            if now - self.last_meeting_check >= 3.0:
                self.last_meeting_check = now
                self.active_meeting_app = detect_active_meeting_app()
        else:
            self.active_meeting_app = ""

        score = int(score)
        calibrated = bool(calibrated)
        raw_warn = bool(warning)
        warn = (self.enabled and not self.active_meeting_app) and raw_warn

        if warn and not self.prev_warning:
            self.stats["today_count"] += 1
            self.stats["total_count"] += 1
            self.stats["recent_events"] = (
                self.stats["recent_events"]
                + [{"time": datetime.datetime.now().strftime("%H:%M"), "score": score}]
            )[-10:]
            save_stats(self.stats)
            alarm_th = int(self.stats.get("alarm_threshold", 3))
            if alarm_th > 0 and self.stats["today_count"] >= alarm_th:
                self.test_alarm()

        if self.enabled and calibrated:
            self.stats["today_score_sum"] += score
            self.stats["today_score_samples"] += 1
            self.stats["total_score_sum"] += score
            self.stats["total_score_samples"] += 1
            if warn:
                self.stats["today_duration_sec"] += dt
                self.stats["total_duration_sec"] += dt
            elif score < self.stats["bad_threshold"]:
                self.stats["today_good_sec"] += dt
                self.stats["total_good_sec"] += dt

            if now - self.last_save >= 5.0:
                save_stats(self.stats)
                self.last_save = now

        if calibrated and not self.prev_calibrated and self.window and not warn:
            try:
                self.window.minimize()
            except Exception:
                pass

        if warn and not self.prev_warning:
            self._enter_warning_mode()
        elif not warn and self.prev_warning:
            self._exit_warning_mode()

        self.prev_calibrated = calibrated
        self.prev_warning = warn
        return self._payload()

    def _build_last_7_days(self):
        today = datetime.date.today()
        items = []
        hist = self.stats.get("daily_history", {})
        for offset in range(-6, 1):
            d = today + datetime.timedelta(days=offset)
            key = d.isoformat()
            label = "오늘" if offset == 0 else f"{d.month}/{d.day}"
            if key in hist:
                items.append({
                    "date": key,
                    "label": label,
                    "good_pct": hist[key].get("good_pct", 100),
                    "count": hist[key].get("count", 0),
                    "has_data": True,
                })
            else:
                items.append({
                    "date": key,
                    "label": label,
                    "good_pct": 0,
                    "count": 0,
                    "has_data": False,
                })
        return items

    def _payload(self):
        ts = self.stats["today_score_samples"]
        alls = self.stats["total_score_samples"]
        tm = self.stats["today_good_sec"] + self.stats["today_duration_sec"]
        am = self.stats["total_good_sec"] + self.stats["total_duration_sec"]
        return {
            "enabled": self.enabled,
            "today_count": self.stats["today_count"],
            "today_duration_sec": int(self.stats["today_duration_sec"]),
            "today_avg_score": round(self.stats["today_score_sum"] / ts, 1) if ts > 0 else 0.0,
            "today_good_pct": round((self.stats["today_good_sec"] / tm) * 100) if tm > 0 else 100,
            "total_count": self.stats["total_count"],
            "total_duration_sec": int(self.stats["total_duration_sec"]),
            "total_avg_score": round(self.stats["total_score_sum"] / alls, 1) if alls > 0 else 0.0,
            "total_good_pct": round((self.stats["total_good_sec"] / am) * 100) if am > 0 else 100,
            "recent_events": self.stats["recent_events"],
            "weekly_history": self._build_last_7_days(),
            "trigger_sec": self.stats["trigger_sec"],
            "bad_threshold": self.stats["bad_threshold"],
            "manner_mode_enabled": self.stats.get("manner_mode_enabled", True),
            "active_meeting_app": self.active_meeting_app,
            "language": self.stats.get("language", "ko"),
            "alarm_threshold": self.stats.get("alarm_threshold", 3),
        }


def main():
    api = TurtleApi()
    win = webview.create_window(
        "거북목 화면 교정기",
        HTML_PATH,
        js_api=api,
        width=1040,
        height=780,
    )
    api.window = win
    # http_server=True: file:// 대신 http://127.0.0.1 로컬 서버로 열어 웹캠(getUserMedia) 및 MediaPipe WASM이 정상 동작하게 함
    webview.start(http_server=True)
    save_stats(api.stats)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_error(traceback.format_exc())
        raise
