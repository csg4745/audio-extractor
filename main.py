#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频提取器 v1.1 - Android APP
基于Kivy框架，参照模板UI设计
深色主题，内置FFmpeg，功能完善的视频音频提取工具
"""

import os
import sys
import re
import subprocess
import threading
import time
import math
import shutil
import stat
from pathlib import Path

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.modalview import ModalView
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.metrics import dp, sp
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Ellipse, Line, Rectangle
from kivy.properties import (
    ListProperty, StringProperty, NumericProperty,
    BooleanProperty, ObjectProperty, DictProperty
)
from kivy.utils import platform
from kivy.animation import Animation

# ============ Android 专用导入 ============
try:
    from android.storage import primary_external_storage_path
    HAS_ANDROID_API = True
except ImportError:
    HAS_ANDROID_API = False

try:
    from android.permissions import request_permissions, Permission
    HAS_PERMISSION_API = True
except ImportError:
    HAS_PERMISSION_API = False


# ============================================================
#                    颜色 / 尺寸 常量
# ============================================================
C_BG        = (0.078, 0.090, 0.165, 1)     # #141724 全局背景
C_CARD      = (0.141, 0.157, 0.216, 1)     # #242837 卡片背景
C_TAB_BG    = (0.110, 0.118, 0.165, 1)     # #1C1E2A 底栏背景
C_ACCENT    = (0.153, 0.839, 0.561, 1)     # #27D68F 选中绿色
C_WHITE     = (1.000, 1.000, 1.000, 1)     # 白色主文字
C_GRAY      = (0.561, 0.573, 0.620, 1)     # #8F929E 未选灰
C_ICON_BG   = (0.561, 0.573, 0.620, 0.18)  # 圆形图标底
C_DIVIDER   = (0.200, 0.220, 0.300, 1)     # 分隔线
C_RED       = (0.950, 0.300, 0.300, 1)     # 错误/删除
C_BANNER_1  = (0.920, 0.400, 0.580, 1)     # 粉
C_BANNER_2  = (0.980, 0.850, 0.200, 1)     # 黄
C_BANNER_3  = (0.300, 0.600, 0.950, 1)     # 蓝
C_BANNER_4  = (0.980, 0.600, 0.200, 1)     # 橙
C_PROGRESS_BG = (0.18, 0.20, 0.31, 1)      # 进度条底色
C_INACTIVE  = (0.250, 0.280, 0.400, 1)     # 未激活按钮
C_FILE_BG   = (0.110, 0.130, 0.210, 1)     # 文件项背景

MARGIN      = dp(16)
CARD_R      = dp(12)
BANNER_R    = dp(14)
ICON_SIZE   = dp(42)
TAB_H       = dp(60)
NAV_H       = dp(50)
SPACING     = dp(12)

# ============ 音频格式配置 ============
FORMATS = {
    "mp3":  {"codec": "libmp3lame",  "ext": ".mp3",  "bitrate": "192k"},
    "wav":  {"codec": "pcm_s16le",   "ext": ".wav",  "bitrate": None},
    "flac": {"codec": "flac",        "ext": ".flac", "bitrate": None},
    "aac":  {"codec": "aac",         "ext": ".aac",  "bitrate": "192k"},
    "m4a":  {"codec": "aac",         "ext": ".m4a",  "bitrate": "192k"},
    "ogg":  {"codec": "libvorbis",   "ext": ".ogg",  "bitrate": "192k"},
}

VIDEO_EXTS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.3gp', '.ts', '.mpeg'}


# ============================================================
#                     KV 样式定义
# ============================================================
KV = '''
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

<RoundedCard@BoxLayout>:
    canvas.before:
        Color:
            rgba: root.bg_color if hasattr(root, 'bg_color') else (0.141, 0.157, 0.216, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: root.radius if hasattr(root, 'radius') else [dp(12)]
    orientation: 'vertical'

<FunctionCard>:
    canvas.before:
        Color:
            rgba: self.card_bg
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(12)]
    orientation: 'vertical'
    padding: dp(6), dp(10), dp(6), dp(6)
    spacing: dp(4)

    FloatLayout:
        size_hint: 1, 0.62
        Widget:
            id: _circle
            size_hint: None, None
            size: dp(42), dp(42)
            pos_hint: {'center_x': 0.5, 'center_y': 0.55}
            canvas.before:
                Color:
                    rgba: 0.561, 0.573, 0.620, 0.18
                Ellipse:
                    pos: self.pos
                    size: self.size
        Label:
            text: root.icon_char
            font_size: sp(20)
            color: 1, 1, 1, 1
            pos_hint: {'center_x': 0.5, 'center_y': 0.55}
            size_hint: None, None
            halign: 'center'
            valign: 'middle'

    Label:
        text: root.card_text
        font_size: sp(12)
        color: 1, 1, 1, 1
        size_hint: 1, 0.38
        halign: 'center'
        valign: 'top'
        text_size: self.width, None

<TabButton>:
    canvas.before:
        Color:
            rgba: 0.110, 0.118, 0.165, 1
        Rectangle:
            pos: self.pos
            size: self.size
    orientation: 'vertical'
    spacing: dp(2)
    padding: dp(4), dp(6)

    Label:
        id: _tab_icon
        text: root.tab_icon
        font_size: sp(20)
        color: root.tab_color
        size_hint: 1, 0.55
        halign: 'center'
        valign: 'bottom'
    Label:
        id: _tab_text
        text: root.tab_label
        font_size: sp(10)
        color: root.tab_color
        size_hint: 1, 0.45
        halign: 'center'
        valign: 'top'

<FileItem>:
    canvas.before:
        Color:
            rgba: 0.110, 0.130, 0.210, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]
    orientation: 'horizontal'
    padding: dp(10), dp(8)
    spacing: dp(10)
    size_hint_y: None
    height: dp(56)

    Label:
        text: '♫'
        font_size: sp(22)
        color: 0.153, 0.839, 0.561, 1
        size_hint: None, 1
        width: dp(30)
        halign: 'center'
        valign: 'middle'
    BoxLayout:
        orientation: 'vertical'
        spacing: dp(2)
        Label:
            text: root.file_name
            font_size: sp(13)
            color: 1, 1, 1, 1
            halign: 'left'
            valign: 'middle'
            text_size: self.width, None
            shorten: True
            shorten_from: 'right'
        Label:
            text: root.file_info
            font_size: sp(10)
            color: 0.561, 0.573, 0.620, 1
            halign: 'left'
            valign: 'top'
            text_size: self.width, None
    Button:
        text: '✕'
        font_size: sp(14)
        color: 0.950, 0.300, 0.300, 1
        size_hint: None, 1
        width: dp(32)
        background_normal: ''
        background_color: 0, 0, 0, 0
        on_press: root.on_remove()

<ExtractedFileItem>:
    canvas.before:
        Color:
            rgba: 0.110, 0.130, 0.210, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]
    orientation: 'horizontal'
    padding: dp(10), dp(8)
    spacing: dp(10)
    size_hint_y: None
    height: dp(56)

    Label:
        text: '♪'
        font_size: sp(22)
        color: 0.153, 0.839, 0.561, 1
        size_hint: None, 1
        width: dp(30)
        halign: 'center'
        valign: 'middle'
    BoxLayout:
        orientation: 'vertical'
        spacing: dp(2)
        Label:
            text: root.file_name
            font_size: sp(13)
            color: 1, 1, 1, 1
            halign: 'left'
            valign: 'middle'
            text_size: self.width, None
            shorten: True
            shorten_from: 'right'
        Label:
            text: root.file_info
            font_size: sp(10)
            color: 0.561, 0.573, 0.620, 1
            halign: 'left'
            valign: 'top'
            text_size: self.width, None
    Button:
        text: '🗑'
        font_size: sp(14)
        color: 0.950, 0.300, 0.300, 1
        size_hint: None, 1
        width: dp(32)
        background_normal: ''
        background_color: 0, 0, 0, 0
        on_press: root.on_delete()
'''


# ============================================================
#                     工具函数
# ============================================================
def hex_to_rgba(hex_str):
    """16进制色值转RGBA元组(0-1)"""
    h = hex_str.lstrip('#')
    return tuple(int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)) + (1.0,)


def format_size(size_bytes):
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024*1024):.1f} MB"
    else:
        return f"{size_bytes / (1024*1024*1024):.1f} GB"


def get_external_storage():
    """获取外部存储根路径"""
    if HAS_ANDROID_API:
        try:
            return primary_external_storage_path()
        except Exception:
            pass
    if platform == 'android':
        return '/storage/emulated/0'
    # 桌面测试用
    return os.path.expanduser('~')


def get_output_dir():
    """获取默认输出目录"""
    base = get_external_storage()
    out = os.path.join(base, '音频提取器')
    os.makedirs(out, exist_ok=True)
    return out


def request_android_permissions():
    """请求Android存储权限"""
    if HAS_PERMISSION_API and platform == 'android':
        try:
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.WRITE_EXTERNAL_STORAGE,
            ])
        except Exception:
            pass


# ============================================================
#               音频提取引擎 (ffmpeg)
# ============================================================
class FFmpegInstaller:
    """内置 FFmpeg 安装器 - 首次启动自动解压到私有目录"""

    ASSET_NAMES = {
        'arm64-v8a': 'ffmpeg-arm64',
        'armeabi-v7a': 'ffmpeg-armv7',
    }

    @staticmethod
    def get_arch():
        """获取CPU架构"""
        if platform == 'android':
            try:
                import platform as _plat
                machine = _plat.machine().lower()
                if 'aarch64' in machine or 'arm64' in machine:
                    return 'arm64-v8a'
                elif 'arm' in machine or 'armv7' in machine:
                    return 'armeabi-v7a'
            except Exception:
                pass
            return 'arm64-v8a'
        return None

    @staticmethod
    def get_installed_path():
        """获取已安装的ffmpeg路径"""
        if platform != 'android':
            return None
        try:
            app = App.get_running_app()
            if app:
                ffmpeg_path = os.path.join(app.user_data_dir, 'ffmpeg')
                if os.path.isfile(ffmpeg_path) and os.access(ffmpeg_path, os.X_OK):
                    return ffmpeg_path
        except Exception:
            pass
        return None

    @staticmethod
    def install_from_assets():
        """从APK assets中解压ffmpeg到私有目录"""
        if platform != 'android':
            return False, "非Android平台"
        try:
            from android import activity
            context = activity.getApplicationContext()
            assets = context.getAssets()

            arch = FFmpegInstaller.get_arch()
            asset_name = FFmpegInstaller.ASSET_NAMES.get(arch, 'ffmpeg-arm64')

            app = App.get_running_app()
            dest_dir = app.user_data_dir
            dest_path = os.path.join(dest_dir, 'ffmpeg')

            # 尝试从assets读取
            try:
                ff_bytes = assets.open(f'assets/bin/{asset_name}').read()
                with open(dest_path, 'wb') as f:
                    f.write(ff_bytes)
                os.chmod(dest_path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
                if os.path.isfile(dest_path) and os.path.getsize(dest_path) > 100000:
                    return True, "FFmpeg 初始化成功"
                else:
                    return False, "解压的文件不完整"
            except Exception as e:
                # 备用：从app private files目录复制
                alt_paths = [
                    os.path.join(dest_dir, 'files', 'bin', asset_name),
                    os.path.join(dest_dir, 'files', asset_name),
                ]
                for alt in alt_paths:
                    if os.path.isfile(alt):
                        shutil.copy2(alt, dest_path)
                        os.chmod(dest_path, stat.S_IRWXU)
                        return True, "FFmpeg 初始化成功"
                return False, f"无法读取内置FFmpeg: {e}"

        except Exception as e:
            return False, f"FFmpeg安装失败: {e}"

    @staticmethod
    def ensure_ffmpeg_ready():
        """确保ffmpeg可用（检查 -> 安装 -> 再检查）"""
        # 1. 检查系统ffmpeg
        for path in ['/system/bin/ffmpeg', '/system/xbin/ffmpeg']:
            if os.path.isfile(path):
                try:
                    r = subprocess.run([path, '-version'], capture_output=True, timeout=3)
                    if r.returncode == 0:
                        return True, path
                except Exception:
                    pass

        # 2. 检查已安装的
        installed = FFmpegInstaller.get_installed_path()
        if installed:
            return True, installed

        # 3. 尝试从assets安装
        ok, msg = FFmpegInstaller.install_from_assets()
        if ok:
            installed = FFmpegInstaller.get_installed_path()
            if installed:
                return True, installed
            return False, "安装成功但路径异常"

        return False, msg


class AudioEngine:
    """使用 ffmpeg 提取视频中的音频"""

    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.process = None
        self.cancel_flag = False
        self._duration = 0

    def _find_ffmpeg(self):
        """查找 ffmpeg 可执行文件"""
        # Android: 从 app 私有目录找
        if platform == 'android':
            installed = FFmpegInstaller.get_installed_path()
            if installed:
                return installed
            app_dir = App.get_running_app().user_data_dir if App.get_running_app() else '/data/data'
            ffmpeg_path = os.path.join(app_dir, 'ffmpeg')
            if os.path.isfile(ffmpeg_path) and os.access(ffmpeg_path, os.X_OK):
                return ffmpeg_path
            for p in ['/system/bin/ffmpeg', '/system/xbin/ffmpeg',
                       os.path.join(app_dir, 'files', 'ffmpeg')]:
                if os.path.isfile(p):
                    return p
            return ffmpeg_path
        # 桌面: 使用系统 ffmpeg
        return 'ffmpeg'

    def refresh_path(self):
        """刷新ffmpeg路径（安装后调用）"""
        self.ffmpeg_path = self._find_ffmpeg()

    def ensure_ffmpeg(self):
        """确保 ffmpeg 可用，返回 (可用, 消息)"""
        # 先尝试刷新
        self.refresh_path()
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return True, "ffmpeg 就绪"
        except FileNotFoundError:
            pass
        except Exception as e:
            return False, f"ffmpeg 检测失败: {e}"

        # 尝试自动安装
        ok, msg = FFmpegInstaller.ensure_ffmpeg_ready()
        if ok:
            self.refresh_path()
            return True, "ffmpeg 已自动就绪"

        return False, f"未找到 ffmpeg: {msg}，请通过Termux安装: pkg install ffmpeg"

    def extract(self, input_file, output_file, fmt, progress_cb=None):
        """
        从视频中提取音频
        返回 (成功, 消息)
        """
        if fmt not in FORMATS:
            return False, f"不支持的格式: {fmt}"

        codec = FORMATS[fmt]['codec']
        bitrate = FORMATS[fmt].get('bitrate')

        cmd = [self.ffmpeg_path, '-i', input_file, '-vn']
        cmd += ['-acodec', codec]
        if bitrate:
            cmd += ['-ab', bitrate]
        cmd += ['-y', output_file]

        self.cancel_flag = False
        self._duration = 0

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )

            for line in self.process.stderr:
                if self.cancel_flag:
                    self.process.kill()
                    self.process.wait()
                    return False, "已取消"

                # 解析总时长
                if self._duration == 0:
                    m = re.search(r'Duration:\s*(\d+):(\d+):(\d+)\.(\d+)', line)
                    if m:
                        h, mi, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                        self._duration = h * 3600 + mi * 60 + s + ms / 100.0

                # 解析当前进度
                if self._duration > 0 and 'time=' in line:
                    m = re.search(r'time=\s*(\d+):(\d+):(\d+)\.(\d+)', line)
                    if m and progress_cb:
                        h, mi, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                        cur = h * 3600 + mi * 60 + s + ms / 100.0
                        pct = min(int(cur / self._duration * 100), 99)
                        progress_cb(pct)

            self.process.wait()

            if self.cancel_flag:
                return False, "已取消"

            if self.process.returncode == 0:
                if progress_cb:
                    progress_cb(100)
                return True, "提取成功"
            else:
                return False, f"ffmpeg 返回错误码 {self.process.returncode}"

        except FileNotFoundError:
            return False, "未找到 ffmpeg，请确认已安装"
        except Exception as e:
            return False, f"提取失败: {e}"
        finally:
            self.process = None

    def cancel(self):
        """取消当前任务"""
        self.cancel_flag = True
        if self.process:
            try:
                self.process.kill()
            except Exception:
                pass

    def get_video_info(self, filepath):
        """获取视频信息(时长、大小)"""
        info = {'duration': 0, 'size': 0}
        try:
            info['size'] = os.path.getsize(filepath)
        except Exception:
            pass
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-i', filepath],
                capture_output=True, text=True, timeout=10
            )
            m = re.search(r'Duration:\s*(\d+):(\d+):(\d+)\.(\d+)', result.stderr)
            if m:
                h, mi, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                info['duration'] = h * 3600 + mi * 60 + s + ms / 100.0
        except Exception:
            pass
        return info


# ============================================================
#                    自定义控件
# ============================================================
class FunctionCard(ButtonBehavior, BoxLayout):
    """功能卡片 - 灰色圆底+白色图标字符+文字"""
    icon_char = StringProperty('')
    card_text = StringProperty('')
    card_bg = ListProperty(list(C_CARD))

    def __init__(self, icon_char='', card_text='', on_press=None, **kwargs):
        super().__init__(**kwargs)
        self.icon_char = icon_char
        self.card_text = card_text
        self._on_press_cb = on_press

    def on_press(self, *args):
        pass

    def on_release(self, *args):
        if self._on_press_cb:
            self._on_press_cb()

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.card_bg = list((0.18, 0.20, 0.32, 1))
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self.card_bg = list(C_CARD)
        return super().on_touch_up(touch)


class TabButton(ButtonBehavior, BoxLayout):
    """底部导航标签按钮"""
    tab_icon = StringProperty('')
    tab_label = StringProperty('')
    tab_color = ListProperty(list(C_GRAY))
    tab_index = NumericProperty(0)

    def __init__(self, tab_icon='', tab_label='', tab_index=0, **kwargs):
        super().__init__(**kwargs)
        self.tab_icon = tab_icon
        self.tab_label = tab_label
        self.tab_index = tab_index

    def set_active(self, active):
        self.tab_color = list(C_ACCENT) if active else list(C_GRAY)

    def on_release(self):
        app = App.get_running_app()
        if app and hasattr(app, 'switch_tab'):
            app.switch_tab(self.tab_index)


class FileItem(BoxLayout):
    """已选视频文件条目"""
    file_name = StringProperty('')
    file_info = StringProperty('')
    file_path = StringProperty('')

    def __init__(self, file_path='', on_remove=None, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self._on_remove_cb = on_remove
        try:
            size = os.path.getsize(file_path)
            self.file_info = format_size(size)
        except Exception:
            self.file_info = ''

    def on_remove(self):
        if self._on_remove_cb:
            self._on_remove_cb(self.file_path)


class ExtractedFileItem(BoxLayout):
    """已提取音频文件条目"""
    file_name = StringProperty('')
    file_info = StringProperty('')
    file_path = StringProperty('')

    def __init__(self, file_path='', on_delete=None, **kwargs):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self._on_delete_cb = on_delete
        try:
            size = os.path.getsize(file_path)
            mtime = os.path.getmtime(file_path)
            t_str = time.strftime('%Y-%m-%d %H:%M', time.localtime(mtime))
            self.file_info = f"{format_size(size)}  |  {t_str}"
        except Exception:
            self.file_info = ''

    def on_delete(self):
        if self._on_delete_cb:
            self._on_delete_cb(self.file_path)


# ============================================================
#                   首页 (HomeScreen)
# ============================================================
class HomeScreen(Screen):
    """首页 - 参照模板设计"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'home'
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', padding=[0, 0, 0, 0],
                         spacing=0)

        # ---- 顶部导航栏 ----
        nav = BoxLayout(size_hint=(1, None), height=NAV_H,
                        padding=[MARGIN, 0, MARGIN, 0])
        # 头像
        avatar = Label(text='◉', font_size=sp(20), color=C_WHITE,
                       size_hint=(None, 1), width=dp(36))
        # 标题
        title = Label(text='首页', font_size=sp(20), bold=True,
                      color=C_WHITE, size_hint=(1, 1))
        # 帮助
        help_btn = Button(text='?', font_size=sp(16), bold=True,
                          color=C_WHITE, size_hint=(None, 1), width=dp(36),
                          background_normal='', background_color=(0, 0, 0, 0))
        help_btn.bind(on_press=self._show_about)
        nav.add_widget(avatar)
        nav.add_widget(title)
        nav.add_widget(help_btn)
        root.add_widget(nav)

        # ---- 可滚动内容区 ----
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        content = BoxLayout(orientation='vertical', size_hint_y=None,
                            spacing=dp(8), padding=[MARGIN, dp(4), MARGIN, dp(16)])
        content.bind(minimum_height=content.setter('height'))

        # ---- Banner ----
        banner = self._make_banner()
        content.add_widget(banner)

        # ---- 热门功能 ----
        content.add_widget(self._section_title('热门功能'))
        grid1 = self._make_function_grid([
            ('♫', '音频提取',   self._goto_extract),
            ('✂', '音频剪辑',   self._toast_coming),
            ('⇄', '音频转换',   self._toast_coming),
            ('♪', '提取伴奏\n&人声', self._toast_coming),
            ('⊞', '音频合并',   self._toast_coming),
            ('◉', '音量调整',   self._toast_coming),
        ], cols=3, rows=2)
        content.add_widget(grid1)

        # ---- 常用功能 ----
        content.add_widget(self._section_title('常用功能'))
        grid2 = self._make_function_grid([
            ('●', '录音机',   self._toast_coming),
            ('≋', '音频降噪', self._toast_coming),
            ('⚡', '音频加速', self._toast_coming),
        ], cols=3, rows=1)
        content.add_widget(grid2)

        scroll.add_widget(content)
        root.add_widget(scroll)

        # ---- 底部导航 ----
        self._bottom_nav = self._make_bottom_nav(active=0)
        root.add_widget(self._bottom_nav)

        self.add_widget(root)

    # ---- UI 构建辅助 ----
    def _make_banner(self):
        banner = FloatLayout(size_hint=(1, None), height=dp(120))
        with banner.canvas.before:
            Color(*C_CARD)
            banner._bg_rect = RoundedRectangle(
                pos=banner.pos, size=banner.size, radius=[BANNER_R])
        banner.bind(pos=lambda w, v: setattr(w._bg_rect, 'pos', v),
                    size=lambda w, v: setattr(w._bg_rect, 'size', v))

        # 彩色装饰条
        deco = BoxLayout(size_hint=(1, 1), padding=[dp(12), dp(10)],
                         spacing=dp(6))
        colors = [C_BANNER_1, C_BANNER_2, C_BANNER_3, C_BANNER_4]
        labels = ['音', '频', '提', '取']
        for i in range(4):
            block = BoxLayout(size_hint=(1, 1), padding=[dp(2)])
            bl = BoxLayout()
            with bl.canvas.before:
                Color(*colors[i])
                bl._r = RoundedRectangle(pos=bl.pos, size=bl.size, radius=[dp(8)])
            bl.bind(pos=lambda w, v, _r=bl._r: setattr(_r, 'pos', v),
                    size=lambda w, v, _r=bl._r: setattr(_r, 'size', v))
            ll = Label(text=labels[i], font_size=sp(28), bold=True,
                       color=C_WHITE, size_hint=(1, 0.6))
            bl.add_widget(ll)
            block.add_widget(bl)
            deco.add_widget(block)

        # 副标题
        sub_box = BoxLayout(size_hint=(1, None), height=dp(28),
                            padding=[dp(20), dp(2)])
        sub = Label(text='免费提取视频中的音频', font_size=sp(12),
                    color=(0.8, 0.85, 0.9, 1), halign='center')
        sub_box.add_widget(sub)

        inner = BoxLayout(orientation='vertical', size_hint=(1, 1))
        inner.add_widget(deco)
        inner.add_widget(sub_box)
        banner.add_widget(inner)
        return banner

    def _section_title(self, text):
        lbl = Label(text=text, font_size=sp(16), bold=True,
                    color=C_WHITE, size_hint=(1, None), height=dp(30),
                    halign='left', valign='middle')
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def _make_function_grid(self, items, cols=3, rows=2):
        grid = GridLayout(cols=cols, rows=rows,
                          size_hint=(1, None),
                          height=dp(90) * rows,
                          spacing=SPACING,
                          row_default_height=dp(90),
                          row_force_default=True,
                          col_default_height=dp(90))
        for icon, text, cb in items:
            card = FunctionCard(icon_char=icon, card_text=text, on_press=cb)
            grid.add_widget(card)
        return grid

    def _make_bottom_nav(self, active=0):
        nav = BoxLayout(size_hint=(1, None), height=TAB_H,
                        orientation='horizontal', spacing=0)
        tabs = [
            ('♫', '首页', 0),
            ('♪', '音频列表', 1),
            ('⚙', '设置', 2),
        ]
        self._tab_buttons = []
        for icon, label, idx in tabs:
            tb = TabButton(tab_icon=icon, tab_label=label, tab_index=idx,
                           size_hint=(1, 1))
            tb.set_active(idx == active)
            self._tab_buttons.append(tb)
            nav.add_widget(tb)
        return nav

    # ---- 交互逻辑 ----
    def _goto_extract(self):
        App.get_running_app().switch_tab(0, sub='extract')

    def _toast_coming(self):
        self._show_popup('提示', '该功能即将上线，敬请期待！')

    def _show_about(self, *args):
        self._show_popup('关于', '音频提取器 v1.0\n\n从视频中提取音频\n支持 MP3/WAV/FLAC/AAC/OGG 格式')

    def _show_popup(self, title, msg):
        popup = ModalView(size_hint=(0.85, 0.35),
                          background_color=(0, 0, 0, 0.6))
        box = BoxLayout(orientation='vertical', padding=[dp(20)], spacing=dp(12))

        with box.canvas.before:
            Color(*C_CARD)
            box._bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(12)])
        box.bind(pos=lambda w, v: setattr(w._bg, 'pos', v),
                 size=lambda w, v: setattr(w._bg, 'size', v))

        t = Label(text=title, font_size=sp(18), bold=True, color=C_ACCENT,
                  size_hint=(1, None), height=dp(30))
        m = Label(text=msg, font_size=sp(13), color=C_WHITE,
                  size_hint=(1, 1), halign='left', valign='top')
        m.bind(size=m.setter('text_size'))
        btn = Button(text='确定', font_size=sp(14),
                     size_hint=(None, None), size=(dp(100), dp(36)),
                     pos_hint={'center_x': 0.5},
                     background_normal='',
                     background_color=list(C_ACCENT[:3]) + [1],
                     color=C_WHITE)

        box.add_widget(t)
        box.add_widget(m)
        box.add_widget(btn)
        popup.add_widget(box)
        btn.bind(on_press=lambda x: popup.dismiss())
        popup.open()


# ============================================================
#                 音频提取页 (ExtractScreen)
# ============================================================
class ExtractScreen(Screen):
    """音频提取操作页"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'extract'
        self.selected_files = []
        self.output_format = 'mp3'
        self.output_dir = get_output_dir()
        self.engine = AudioEngine()
        self._extracting = False
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', spacing=0)

        # ---- 顶部栏 ----
        nav = BoxLayout(size_hint=(1, None), height=NAV_H,
                        padding=[MARGIN, 0, MARGIN, 0], spacing=dp(8))
        back_btn = Button(text='←', font_size=sp(22), color=C_ACCENT,
                          size_hint=(None, 1), width=dp(40),
                          background_normal='', background_color=(0, 0, 0, 0))
        back_btn.bind(on_press=lambda x: self._go_back())
        title = Label(text='音频提取', font_size=sp(20), bold=True,
                      color=C_WHITE, size_hint=(1, 1))
        nav.add_widget(back_btn)
        nav.add_widget(title)
        root.add_widget(nav)

        # ---- 可滚动内容 ----
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        content = BoxLayout(orientation='vertical', size_hint_y=None,
                            spacing=dp(10), padding=[MARGIN, dp(8), MARGIN, MARGIN])
        content.bind(minimum_height=content.setter('height'))

        # 已选文件区域
        content.add_widget(self._label('已选视频文件'))
        self._file_list_box = BoxLayout(orientation='vertical',
                                        size_hint=(1, None),
                                        spacing=dp(6))
        self._file_list_box.bind(minimum_height=self._file_list_box.setter('height'))
        self._file_list_placeholder = Label(
            text='尚未选择视频文件', font_size=sp(13),
            color=C_GRAY, size_hint=(1, None), height=dp(40))
        self._file_list_box.add_widget(self._file_list_placeholder)
        content.add_widget(self._file_list_box)

        # 添加文件按钮
        add_btn = Button(text='＋ 添加视频文件', font_size=sp(14),
                         size_hint=(1, None), height=dp(42),
                         background_normal='',
                         background_color=list(C_ACCENT[:3]) + [1],
                         color=C_WHITE)
        add_btn.bind(on_press=lambda x: self._pick_files())
        content.add_widget(add_btn)

        # 分隔
        content.add_widget(Widget(size_hint=(1, None), height=dp(8)))

        # 输出格式
        content.add_widget(self._label('输出音频格式'))
        self._format_box = self._make_format_selector()
        content.add_widget(self._format_box)

        # 输出目录
        content.add_widget(self._label('输出目录'))
        self._dir_label = Label(text=self.output_dir, font_size=sp(12),
                                color=C_GRAY, size_hint=(1, None), height=dp(24),
                                halign='left', valign='middle',
                                shorten=True, shorten_from='right')
        self._dir_label.bind(size=self._dir_label.setter('text_size'))
        content.add_widget(self._dir_label)

        dir_btn = Button(text='选择输出目录', font_size=sp(13),
                         size_hint=(1, None), height=dp(38),
                         background_normal='',
                         background_color=list(C_INACTIVE[:3]) + [1],
                         color=C_WHITE)
        dir_btn.bind(on_press=lambda x: self._pick_output_dir())
        content.add_widget(dir_btn)

        # 分隔
        content.add_widget(Widget(size_hint=(1, None), height=dp(8)))

        # 进度
        content.add_widget(self._label('提取进度'))
        self._progress = ProgressBar(max=100, value=0,
                                     size_hint=(1, None), height=dp(16))
        content.add_widget(self._progress)

        self._status_label = Label(text='就绪', font_size=sp(12),
                                   color=C_GRAY, size_hint=(1, None),
                                   height=dp(24), halign='left',
                                   valign='middle')
        self._status_label.bind(size=self._status_label.setter('text_size'))
        content.add_widget(self._status_label)

        # 操作按钮
        btn_row = BoxLayout(size_hint=(1, None), height=dp(44),
                            spacing=dp(12))
        self._start_btn = Button(text='开始提取', font_size=sp(15),
                                 size_hint=(1, 1),
                                 background_normal='',
                                 background_color=list(C_ACCENT[:3]) + [1],
                                 color=C_WHITE)
        self._start_btn.bind(on_press=lambda x: self._start_extraction())

        self._cancel_btn = Button(text='取消', font_size=sp(15),
                                  size_hint=(0.5, 1),
                                  background_normal='',
                                  background_color=list(C_RED[:3]) + [1],
                                  color=C_WHITE, disabled=True,
                                  opacity=0.5)
        self._cancel_btn.bind(on_press=lambda x: self._cancel_extraction())

        btn_row.add_widget(self._start_btn)
        btn_row.add_widget(self._cancel_btn)
        content.add_widget(btn_row)

        # 底部留白
        content.add_widget(Widget(size_hint=(1, None), height=dp(20)))

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def _label(self, text):
        lbl = Label(text=text, font_size=sp(14), bold=True,
                    color=C_WHITE, size_hint=(1, None), height=dp(26),
                    halign='left', valign='middle')
        lbl.bind(size=lbl.setter('text_size'))
        return lbl

    def _make_format_selector(self):
        box = BoxLayout(orientation='horizontal', size_hint=(1, None),
                        height=dp(40), spacing=dp(8))
        self._fmt_buttons = {}
        for fmt in FORMATS:
            btn = Button(text=fmt.upper(), font_size=sp(13),
                         size_hint=(1, 1),
                         background_normal='',
                         background_color=list(C_ACCENT[:3]) + [1] if fmt == self.output_format else list(C_INACTIVE[:3]) + [1],
                         color=C_WHITE)
            btn.bind(on_press=lambda x, f=fmt: self._select_format(f))
            box.add_widget(btn)
            self._fmt_buttons[fmt] = btn
        return box

    def _select_format(self, fmt):
        self.output_format = fmt
        for f, btn in self._fmt_buttons.items():
            if f == fmt:
                btn.background_color = list(C_ACCENT[:3]) + [1]
            else:
                btn.background_color = list(C_INACTIVE[:3]) + [1]

    def _pick_files(self):
        """选择视频文件 - 使用内置文件浏览器"""
        app = App.get_running_app()
        if app and hasattr(app, 'open_file_browser'):
            app.open_file_browser(callback=self._on_files_selected)

    def _on_files_selected(self, files):
        """文件选择回调"""
        for f in files:
            if f not in self.selected_files:
                self.selected_files.append(f)
        self._refresh_file_list()

    def _refresh_file_list(self):
        """刷新文件列表"""
        self._file_list_box.clear_widgets()
        if not self.selected_files:
            self._file_list_placeholder = Label(
                text='尚未选择视频文件', font_size=sp(13),
                color=C_GRAY, size_hint=(1, None), height=dp(40))
            self._file_list_box.add_widget(self._file_list_placeholder)
            return
        for fp in self.selected_files:
            item = FileItem(file_path=fp, on_remove=self._remove_file)
            self._file_list_box.add_widget(item)

    def _remove_file(self, filepath):
        """移除选中的文件"""
        if filepath in self.selected_files:
            self.selected_files.remove(filepath)
            self._refresh_file_list()

    def _pick_output_dir(self):
        """选择输出目录"""
        app = App.get_running_app()
        if app and hasattr(app, 'open_dir_browser'):
            app.open_dir_browser(callback=self._on_dir_selected)

    def _on_dir_selected(self, dirpath):
        self.output_dir = dirpath
        self._dir_label.text = dirpath

    def _start_extraction(self):
        """开始提取"""
        if self._extracting:
            return
        if not self.selected_files:
            self._show_toast('请先添加视频文件')
            return

        # 检查 ffmpeg
        ok, msg = self.engine.ensure_ffmpeg()
        if not ok:
            self._show_toast(msg)
            return

        self._extracting = True
        self._start_btn.disabled = True
        self._start_btn.opacity = 0.5
        self._cancel_btn.disabled = False
        self._cancel_btn.opacity = 1.0
        self._progress.value = 0
        self._status_label.text = '准备提取...'

        threading.Thread(target=self._run_extraction, daemon=True).start()

    def _run_extraction(self):
        """后台提取线程"""
        total = len(self.selected_files)
        success = 0
        errors = []

        for i, fp in enumerate(self.selected_files):
            if self.engine.cancel_flag:
                break

            base = os.path.splitext(os.path.basename(fp))[0]
            ext = FORMATS[self.output_format]['ext']
            out_path = os.path.join(self.output_dir, f"{base}{ext}")

            # 更新状态
            Clock.schedule_once(lambda dt, f=fp, n=i+1, t=total:
                self._update_status(f'正在提取 {os.path.basename(f)} ({n}/{t})'))
            Clock.schedule_once(lambda dt, n=i, t=total:
                self._update_progress(int(n / t * 100)))

            def progress_cb(pct, _i=i, _t=total):
                overall = int((_i + pct / 100.0) / _t * 100)
                Clock.schedule_once(lambda dt, v=overall: self._update_progress(v))

            ok, msg = self.engine.extract(fp, out_path, self.output_format,
                                          progress_cb=progress_cb)
            if ok:
                success += 1
            else:
                errors.append(f"{os.path.basename(fp)}: {msg}")

        # 完成
        Clock.schedule_once(lambda dt: self._on_extraction_done(success, total, errors))

    def _on_extraction_done(self, success, total, errors):
        self._extracting = False
        self._start_btn.disabled = False
        self._start_btn.opacity = 1.0
        self._cancel_btn.disabled = True
        self._cancel_btn.opacity = 0.5

        if success == total:
            self._status_label.text = f'提取完成！成功 {success}/{total} 个文件'
            self._progress.value = 100
            self._show_toast(f'成功提取 {success} 个音频文件')
        elif success > 0:
            self._status_label.text = f'部分完成：{success}/{total}'
            self._show_toast(f'完成 {success}/{total}，{len(errors)} 个失败')
        else:
            self._status_label.text = '提取失败'
            if errors:
                self._show_toast(errors[0])

    def _cancel_extraction(self):
        self.engine.cancel()
        self._status_label.text = '正在取消...'

    def _update_status(self, text):
        self._status_label.text = text

    def _update_progress(self, value):
        self._progress.value = value

    def _go_back(self):
        app = App.get_running_app()
        if app and hasattr(app, 'switch_tab'):
            app.switch_tab(0)

    def _show_toast(self, msg):
        popup = ModalView(size_hint=(0.8, 0.18),
                          background_color=(0, 0, 0, 0.5),
                          auto_dismiss=True)
        box = BoxLayout(padding=[dp(16)])
        with box.canvas.before:
            Color(0.12, 0.14, 0.22, 0.95)
            box._bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(10)])
        box.bind(pos=lambda w, v: setattr(w._bg, 'pos', v),
                 size=lambda w, v: setattr(w._bg, 'size', v))
        lbl = Label(text=msg, font_size=sp(13), color=C_WHITE)
        box.add_widget(lbl)
        popup.add_widget(box)
        popup.open()
        Clock.schedule_once(lambda dt: popup.dismiss(), 2.5)


# ============================================================
#              文件浏览器 (FileBrowserScreen)
# ============================================================
class FileBrowserScreen(Screen):
    """内置视频文件浏览器"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'file_browser'
        self._current_dir = get_external_storage()
        self._selected_files = []
        self._callback = None
        self._mode = 'file'  # 'file' or 'dir'
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', spacing=0)

        # 顶部栏
        nav = BoxLayout(size_hint=(1, None), height=NAV_H,
                        padding=[MARGIN, 0, MARGIN, 0], spacing=dp(8))
        back_btn = Button(text='←', font_size=sp(22), color=C_ACCENT,
                          size_hint=(None, 1), width=dp(40),
                          background_normal='', background_color=(0, 0, 0, 0))
        back_btn.bind(on_press=lambda x: self._go_back())
        title = Label(text='选择视频文件', font_size=sp(18), bold=True,
                      color=C_WHITE, size_hint=(1, 1))
        nav.add_widget(back_btn)
        nav.add_widget(title)
        root.add_widget(nav)

        # 当前路径
        self._path_label = Label(text=self._current_dir, font_size=sp(11),
                                 color=C_GRAY, size_hint=(1, None), height=dp(22),
                                 halign='left', valign='middle',
                                 shorten=True, shorten_from='right',
                                 padding_x=[MARGIN, MARGIN])
        self._path_label.bind(size=self._path_label.setter('text_size'))
        root.add_widget(self._path_label)

        # 文件列表
        self._file_scroll = ScrollView(do_scroll_x=False, bar_width=0)
        self._file_container = BoxLayout(orientation='vertical',
                                         size_hint_y=None, spacing=dp(4),
                                         padding=[MARGIN, dp(4), MARGIN, dp(4)])
        self._file_container.bind(minimum_height=self._file_container.setter('height'))
        self._file_scroll.add_widget(self._file_container)
        root.add_widget(self._file_scroll)

        # 底部操作栏
        bottom = BoxLayout(size_hint=(1, None), height=dp(50),
                           padding=[MARGIN, dp(4), MARGIN, dp(4)],
                           spacing=dp(10))
        self._sel_label = Label(text='已选: 0 个文件', font_size=sp(12),
                                color=C_ACCENT, size_hint=(1, 1))
        confirm_btn = Button(text='确认选择', font_size=sp(14),
                             size_hint=(None, 1), width=dp(110),
                             background_normal='',
                             background_color=list(C_ACCENT[:3]) + [1],
                             color=C_WHITE)
        confirm_btn.bind(on_press=lambda x: self._confirm())
        bottom.add_widget(self._sel_label)
        bottom.add_widget(confirm_btn)
        root.add_widget(bottom)

        self.add_widget(root)

    def open(self, callback=None, mode='file'):
        """打开浏览器"""
        self._callback = callback
        self._mode = mode
        self._selected_files = []
        self._current_dir = get_external_storage()
        self._refresh_list()
        self._sel_label.text = '已选: 0 个文件'
        if mode == 'dir':
            # dir 模式下导航栏标题修改
            self._go_back = self._go_back_dir

        app = App.get_running_app()
        if app and hasattr(app, 'show_screen'):
            app.show_screen('file_browser')

    def _refresh_list(self):
        self._file_container.clear_widgets()
        self._path_label.text = self._current_dir

        try:
            entries = os.listdir(self._current_dir)
        except PermissionError:
            lbl = Label(text='无权限访问该目录', font_size=sp(13),
                        color=C_RED, size_hint=(1, None), height=dp(50))
            self._file_container.add_widget(lbl)
            return
        except Exception as e:
            lbl = Label(text=f'读取失败: {e}', font_size=sp(13),
                        color=C_RED, size_hint=(1, None), height=dp(50))
            self._file_container.add_widget(lbl)
            return

        # 返回上级
        parent = os.path.dirname(self._current_dir)
        if parent and parent != self._current_dir:
            up_btn = self._make_dir_item('..', parent)
            self._file_container.add_widget(up_btn)

        # 快捷目录
        quick_dirs = []
        base = get_external_storage()
        for d in ['Download', 'Movies', 'DCIM', 'Music', 'Pictures', 'Documents']:
            full = os.path.join(base, d)
            if os.path.isdir(full) and full != self._current_dir:
                quick_dirs.append((d, full))

        # 分离文件夹和文件
        dirs = []
        files = []
        for e in sorted(entries):
            full = os.path.join(self._current_dir, e)
            if os.path.isdir(full):
                dirs.append((e, full))
            elif self._mode == 'file':
                ext = os.path.splitext(e)[1].lower()
                if ext in VIDEO_EXTS:
                    files.append((e, full))

        # 添加文件夹
        for name, path in dirs:
            self._file_container.add_widget(self._make_dir_item(f'📁 {name}', path))

        # 添加视频文件
        for name, path in files:
            self._file_container.add_widget(self._make_file_item(name, path))

        if not dirs and not files:
            lbl = Label(text='当前目录没有视频文件', font_size=sp(13),
                        color=C_GRAY, size_hint=(1, None), height=dp(50))
            self._file_container.add_widget(lbl)

    def _make_dir_item(self, name, path):
        item = Button(text=f'  {name}', font_size=sp(14), color=C_WHITE,
                      size_hint=(1, None), height=dp(44), halign='left',
                      valign='middle', background_normal='',
                      background_color=C_FILE_BG)
        item.bind(size=item.setter('text_size'))
        item.bind(on_press=lambda x, p=path: self._enter_dir(p))
        return item

    def _make_file_item(self, name, path):
        is_selected = path in self._selected_files
        bg = list(C_ACCENT[:3]) + [0.2] if is_selected else list(C_FILE_BG)
        item = Button(text=f'  ♫ {name}', font_size=sp(13),
                      color=C_ACCENT if is_selected else C_WHITE,
                      size_hint=(1, None), height=dp(40), halign='left',
                      valign='middle', background_normal='',
                      background_color=bg)
        item.bind(size=item.setter('text_size'))
        item.bind(on_press=lambda x, p=path: self._toggle_file(p))
        return item

    def _enter_dir(self, path):
        self._current_dir = path
        self._refresh_list()

    def _toggle_file(self, path):
        if path in self._selected_files:
            self._selected_files.remove(path)
        else:
            self._selected_files.append(path)
        self._sel_label.text = f'已选: {len(self._selected_files)} 个文件'
        self._refresh_list()

    def _confirm(self):
        if self._mode == 'dir':
            if self._callback:
                self._callback(self._current_dir)
        else:
            if self._callback:
                self._callback(self._selected_files)
        self._go_back()

    def _go_back(self):
        app = App.get_running_app()
        if app and hasattr(app, 'show_screen'):
            app.show_screen('extract')

    def _go_back_dir(self):
        """目录选择模式的返回"""
        self._go_back()


# ============================================================
#                音频列表页 (AudioListScreen)
# ============================================================
class AudioListScreen(Screen):
    """已提取音频文件列表"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'audio_list'
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', spacing=0)

        # 顶部导航栏
        nav = BoxLayout(size_hint=(1, None), height=NAV_H,
                        padding=[MARGIN, 0, MARGIN, 0])
        avatar = Label(text='◉', font_size=sp(20), color=C_WHITE,
                       size_hint=(None, 1), width=dp(36))
        title = Label(text='音频列表', font_size=sp(20), bold=True,
                      color=C_WHITE, size_hint=(1, 1))
        nav.add_widget(avatar)
        nav.add_widget(title)
        root.add_widget(nav)

        # 音频文件列表
        self._scroll = ScrollView(do_scroll_x=False, bar_width=0)
        self._container = BoxLayout(orientation='vertical',
                                    size_hint_y=None, spacing=dp(6),
                                    padding=[MARGIN, dp(8), MARGIN, MARGIN])
        self._container.bind(minimum_height=self._container.setter('height'))
        self._scroll.add_widget(self._container)
        root.add_widget(self._scroll)

        # 底部导航
        self._bottom_nav = self._make_bottom_nav(active=1)
        root.add_widget(self._bottom_nav)

        self.add_widget(root)

    def _make_bottom_nav(self, active=1):
        nav = BoxLayout(size_hint=(1, None), height=TAB_H,
                        orientation='horizontal', spacing=0)
        tabs = [('♫', '首页', 0), ('♪', '音频列表', 1), ('⚙', '设置', 2)]
        self._tab_buttons = []
        for icon, label, idx in tabs:
            tb = TabButton(tab_icon=icon, tab_label=label, tab_index=idx)
            tb.set_active(idx == active)
            self._tab_buttons.append(tb)
            nav.add_widget(tb)
        return nav

    def on_enter(self, *args):
        """进入页面时刷新列表"""
        self._refresh_list()

    def _refresh_list(self):
        self._container.clear_widgets()
        output_dir = get_output_dir()

        if not os.path.isdir(output_dir):
            lbl = Label(text='还没有提取的音频文件', font_size=sp(14),
                        color=C_GRAY, size_hint=(1, None), height=dp(60))
            self._container.add_widget(lbl)
            return

        audio_exts = {'.mp3', '.wav', '.flac', '.aac', '.m4a', '.ogg'}
        found = False
        for f in sorted(os.listdir(output_dir)):
            ext = os.path.splitext(f)[1].lower()
            if ext in audio_exts:
                found = True
                fp = os.path.join(output_dir, f)
                item = ExtractedFileItem(file_path=fp, on_delete=self._delete_file)
                self._container.add_widget(item)

        if not found:
            lbl = Label(text='还没有提取的音频文件', font_size=sp(14),
                        color=C_GRAY, size_hint=(1, None), height=dp(60))
            self._container.add_widget(lbl)

    def _delete_file(self, filepath):
        """删除音频文件"""
        try:
            os.remove(filepath)
        except Exception:
            pass
        self._refresh_list()


# ============================================================
#                  设置页 (SettingsScreen)
# ============================================================
class SettingsScreen(Screen):
    """应用设置"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = 'settings'
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', spacing=0)

        # 顶部导航栏
        nav = BoxLayout(size_hint=(1, None), height=NAV_H,
                        padding=[MARGIN, 0, MARGIN, 0])
        avatar = Label(text='◉', font_size=sp(20), color=C_WHITE,
                       size_hint=(None, 1), width=dp(36))
        title = Label(text='设置', font_size=sp(20), bold=True,
                      color=C_WHITE, size_hint=(1, 1))
        nav.add_widget(avatar)
        nav.add_widget(title)
        root.add_widget(nav)

        # 设置列表
        scroll = ScrollView(do_scroll_x=False, bar_width=0)
        content = BoxLayout(orientation='vertical', size_hint_y=None,
                            spacing=dp(2), padding=[MARGIN, dp(8), MARGIN, MARGIN])
        content.bind(minimum_height=content.setter('height'))

        # 输出目录设置
        content.add_widget(self._setting_item(
            '默认输出目录', get_output_dir(),
            lambda: self._change_output_dir()
        ))

        # ffmpeg 检测
        engine = AudioEngine()
        ok, msg = engine.ensure_ffmpeg()
        status_text = '已安装 ✓' if ok else '未安装 ✕'
        status_color = C_ACCENT if ok else C_RED
        content.add_widget(self._setting_item(
            'FFmpeg 状态', status_text, None, status_color
        ))

        # 版本信息
        content.add_widget(self._setting_item(
            '应用版本', 'v1.0.0', None
        ))

        # 关于
        about_btn = Button(text='关于音频提取器', font_size=sp(14),
                           size_hint=(1, None), height=dp(48),
                           background_normal='',
                           background_color=list(C_CARD[:3]) + [1],
                           color=C_WHITE, halign='left', valign='middle',
                           padding_x=[dp(16), 0])
        about_btn.bind(size=about_btn.setter('text_size'))
        about_btn.bind(on_press=lambda x: self._show_about())

        content.add_widget(about_btn)

        scroll.add_widget(content)
        root.add_widget(scroll)

        # 底部导航
        self._bottom_nav = self._make_bottom_nav(active=2)
        root.add_widget(self._bottom_nav)

        self.add_widget(root)

    def _setting_item(self, title, value='', on_tap=None, value_color=None):
        item = BoxLayout(orientation='horizontal',
                         size_hint=(1, None), height=dp(52),
                         padding=[dp(16), dp(4)])

        with item.canvas.before:
            Color(*C_CARD)
            item._bg = RoundedRectangle(pos=item.pos, size=item.size,
                                        radius=[dp(8)])
        item.bind(pos=lambda w, v: setattr(w._bg, 'pos', v),
                  size=lambda w, v: setattr(w._bg, 'size', v))

        t = Label(text=title, font_size=sp(14), color=C_WHITE,
                  size_hint=(0.5, 1), halign='left', valign='middle')
        t.bind(size=t.setter('text_size'))

        vc = value_color if value_color else C_GRAY
        v = Label(text=value, font_size=sp(12), color=vc,
                  size_hint=(0.5, 1), halign='right', valign='middle')
        v.bind(size=v.setter('text_size'))

        item.add_widget(t)
        item.add_widget(v)

        if on_tap:
            item_btn = Button(background_normal='',
                              background_color=(0, 0, 0, 0),
                              size_hint=(1, 1),
                              pos_hint={'x': 0, 'y': 0})
            item_btn.bind(on_press=lambda x: on_tap())
            # Overlay button
            item.add_widget(item_btn)

        return item

    def _make_bottom_nav(self, active=2):
        nav = BoxLayout(size_hint=(1, None), height=TAB_H,
                        orientation='horizontal', spacing=0)
        tabs = [('♫', '首页', 0), ('♪', '音频列表', 1), ('⚙', '设置', 2)]
        self._tab_buttons = []
        for icon, label, idx in tabs:
            tb = TabButton(tab_icon=icon, tab_label=label, tab_index=idx)
            tb.set_active(idx == active)
            self._tab_buttons.append(tb)
            nav.add_widget(tb)
        return nav

    def _change_output_dir(self):
        app = App.get_running_app()
        if app and hasattr(app, 'open_dir_browser'):
            app.open_dir_browser(
                callback=lambda d: self._on_dir_changed(d))

    def _on_dir_changed(self, dirpath):
        # 可以保存到配置文件
        pass

    def _show_about(self):
        popup = ModalView(size_hint=(0.85, 0.4),
                          background_color=(0, 0, 0, 0.6))
        box = BoxLayout(orientation='vertical', padding=[dp(20)], spacing=dp(10))
        with box.canvas.before:
            Color(*C_CARD)
            box._bg = RoundedRectangle(pos=box.pos, size=box.size, radius=[dp(12)])
        box.bind(pos=lambda w, v: setattr(w._bg, 'pos', v),
                 size=lambda w, v: setattr(w._bg, 'size', v))

        t = Label(text='音频提取器', font_size=sp(22), bold=True,
                  color=C_ACCENT, size_hint=(1, None), height=dp(36))
        m = Label(text='版本 1.0.0\n\n从视频中提取音频\n支持 MP3 / WAV / FLAC / AAC / M4A / OGG\n\n使用 FFmpeg 引擎',
                  font_size=sp(13), color=C_WHITE,
                  size_hint=(1, 1), halign='left', valign='top')
        m.bind(size=m.setter('text_size'))
        btn = Button(text='确定', font_size=sp(14),
                     size_hint=(None, None), size=(dp(100), dp(36)),
                     pos_hint={'center_x': 0.5},
                     background_normal='',
                     background_color=list(C_ACCENT[:3]) + [1],
                     color=C_WHITE)

        box.add_widget(t)
        box.add_widget(m)
        box.add_widget(btn)
        popup.add_widget(box)
        btn.bind(on_press=lambda x: popup.dismiss())
        popup.open()


# ============================================================
#                    主应用类
# ============================================================
class AudioExtractorApp(App):
    """音频提取器主应用"""

    def build(self):
        Window.clearcolor = C_BG[:3]
        self.sm = ScreenManager(transition=SlideTransition(duration=0.25))

        # 加载 KV 样式
        from kivy.lang import Builder
        Builder.load_string(KV)

        # 创建所有页面
        self.home_screen = HomeScreen()
        self.extract_screen = ExtractScreen()
        self.file_browser = FileBrowserScreen()
        self.audio_list_screen = AudioListScreen()
        self.settings_screen = SettingsScreen()

        self.sm.add_widget(self.home_screen)
        self.sm.add_widget(self.extract_screen)
        self.sm.add_widget(self.file_browser)
        self.sm.add_widget(self.audio_list_screen)
        self.sm.add_widget(self.settings_screen)

        # 请求Android权限
        Clock.schedule_once(lambda dt: request_android_permissions(), 1)

        return self.sm

    def switch_tab(self, tab_index, sub=None):
        """切换底部导航标签"""
        if tab_index == 0:
            if sub == 'extract':
                self.sm.current = 'extract'
            else:
                self.sm.current = 'home'
        elif tab_index == 1:
            self.sm.current = 'audio_list'
        elif tab_index == 2:
            self.sm.current = 'settings'

        # 更新所有底部导航状态
        self._update_all_tabs(tab_index)

    def _update_all_tabs(self, active_index):
        """更新所有页面的底部导航高亮"""
        for screen in [self.home_screen, self.audio_list_screen,
                       self.settings_screen]:
            if hasattr(screen, '_tab_buttons'):
                for tb in screen._tab_buttons:
                    tb.set_active(tb.tab_index == active_index)

    def show_screen(self, name):
        """切换到指定页面"""
        self.sm.current = name

    def open_file_browser(self, callback=None):
        """打开文件浏览器选择视频"""
        self.file_browser._callback = callback
        self.file_browser._mode = 'file'
        self.file_browser._selected_files = []
        self.file_browser._current_dir = get_external_storage()
        self.file_browser._refresh_list()
        self.sm.current = 'file_browser'

    def open_dir_browser(self, callback=None):
        """打开目录浏览器选择输出目录"""
        self.file_browser._callback = callback
        self.file_browser._mode = 'dir'
        self.file_browser._selected_files = []
        self.file_browser._current_dir = get_external_storage()
        self.file_browser._refresh_list()
        self.sm.current = 'file_browser'

    def on_pause(self):
        """Android暂停时保存状态"""
        return True

    def on_resume(self):
        """Android恢复"""
        pass


# ============================================================
#                      启动入口
# ============================================================
if __name__ == '__main__':
    # 桌面端测试时设置窗口大小
    if platform != 'android':
        Window.size = (390, 844)
        Window.top = 50
        Window.left = 100

    AudioExtractorApp().run()
