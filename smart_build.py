#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频提取器 APK 打包工具 - WSL Ubuntu 完整优化版
解决: openssl慢 / skcms不可达 / sed语法错误
用法: cd ~/audio_app && python3 smart_build.py
"""

import os
import subprocess
import shutil
from pathlib import Path

HOME = Path.home()
APP_DIR = HOME / "audio_app"
SRC_DIR = Path("/mnt/e/Users/Y/Desktop/桌面资料/我的息壤智能体空间/音频提取器APP")
P4A_DIR = APP_DIR / ".buildozer/android/platform/python-for-android"
RECIPES = P4A_DIR / "pythonforandroid/recipes"
PLATFORM = APP_DIR / ".buildozer/android/platform"

G, R, Y = "\033[92m", "\033[91m", "\033[93m"
B, N = "\033[1m", "\033[0m"


def run(cmd, cwd=None, timeout=3600):
    print(f"  {Y}$ {cmd}{N}")
    try:
        r = subprocess.run(cmd, shell=True, cwd=str(cwd) if cwd else None,
                           text=True, timeout=timeout,
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # 只打印最后20行
        lines = (r.stdout or "").strip().split('\n')
        for l in lines[-20:]:
            print(f"    {l}")
        return r
    except subprocess.TimeoutExpired:
        print(f"  {R}[超时]{N}")
        return None


def safe_patch(filepath, old, new, label=""):
    """用Python精确替换文件内容，不用sed"""
    p = Path(filepath)
    if not p.exists():
        print(f"  {Y}[跳过]{N} {label or p.name} 文件不存在")
        return False
    text = p.read_text()
    if new in text:
        print(f"  {G}[已是最新]{N} {label or p.name}")
        return False
    if old not in text:
        print(f"  {Y}[无需修补]{N} {label or p.name} (目标文本不存在)")
        return False
    text = text.replace(old, new)
    p.write_text(text)
    print(f"  {G}[已修补]{N} {label or p.name}")
    return True


def step1_sync():
    """同步源码"""
    print(f"\n{B}[1/6] 同步源码{N}")
    for f in ["main.py", "buildozer.spec"]:
        src, dst = SRC_DIR / f, APP_DIR / f
        if src.exists():
            shutil.copy2(src, dst)
            print(f"  {G}OK{N} {f}")


def step2_git():
    """Git代理"""
    print(f"\n{B}[2/6] Git镜像加速{N}")
    run('git config --global url."https://ghfast.top/https://github.com/".insteadOf "https://github.com/"')
    run('git config --global http.postBuffer 524288000')
    run('git config --global http.lowSpeedLimit 0')
    run('git config --global http.lowSpeedTime 999999')
    print(f"  {G}OK{N} Git代理已配置")


def step3_download_p4a():
    """确保p4a已下载"""
    print(f"\n{B}[3/6] 检查 python-for-android{N}")
    marker = P4A_DIR / "pythonforandroid/toolchain.py"
    if marker.exists():
        print(f"  {G}OK{N} p4a 已存在")
        return True
    print(f"  首次运行buildozer下载p4a (约3-5分钟)...")
    os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
    run("buildozer android debug", cwd=APP_DIR, timeout=1800)
    if marker.exists():
        print(f"  {G}OK{N} p4a 下载完成")
        return True
    print(f"  {R}失败{N} p4a 未下载成功")
    return False


def step4_patch():
    """修补配方"""
    print(f"\n{B}[4/6] 修补配方{N}")

    # ---- openssl: 换清华镜像 ----
    safe_patch(
        RECIPES / "openssl/__init__.py",
        "https://www.openssl.org/source/",
        "https://mirrors.tuna.tsinghua.edu.cn/openssl/source/",
        "openssl -> 清华镜像"
    )

    # ---- sdl2_image: 去掉 --recursive ----
    img_file = RECIPES / "sdl2_image/__init__.py"
    if img_file.exists():
        text = img_file.read_text()
        changed = False

        # 1) 去掉 --recursive
        if "--recursive" in text:
            text = text.replace("--recursive", "")
            changed = True
            print(f"  {G}[已修补]{N} sdl2_image -> 去掉 --recursive")

        # 2) 添加 skcms 占位代码（在 def build_arch 之前插入）
        if "skcms_patch_marker" not in text:
            placeholder = (
                "\n"
                "    # skcms_patch_marker: create placeholder for China network\n"
                "    import os as _os\n"
                "    from os.path import join as _join, exists as _exists\n"
                "    _skcms = _join(self.ctx.bootstrap.build_dir, 'jni', 'SDL2_image', 'external', 'libjxl', 'third_party', 'skcms')\n"
                "    if not _exists(_skcms):\n"
                "        _os.makedirs(_skcms, exist_ok=True)\n"
                "        with open(_join(_skcms, 'skcms.h'), 'w') as _f:\n"
                "            _f.write('// placeholder\\n')\n"
            )
            idx = text.find("\n    def build_arch")
            if idx > 0:
                text = text[:idx] + placeholder + text[idx:]
                changed = True
                print(f"  {G}[已修补]{N} sdl2_image -> 添加 skcms 占位")

        if changed:
            img_file.write_text(text)
    else:
        print(f"  {Y}[跳过]{N} sdl2_image 配方不存在")

    # ---- libffi: 换镜像 ----
    safe_patch(
        RECIPES / "libffi/__init__.py",
        "https://github.com/libffi/libffi/",
        "https://ghfast.top/https://github.com/libffi/libffi/",
        "libffi -> ghfast镜像"
    )

    # ---- pyjnius: 换镜像 ----
    safe_patch(
        RECIPES / "pyjnius/__init__.py",
        "https://github.com/kivy/pyjnius/",
        "https://ghfast.top/https://github.com/kivy/pyjnius/",
        "pyjnius -> ghfast镜像"
    )

    # ---- kivy: 换镜像 ----
    safe_patch(
        RECIPES / "kivy/__init__.py",
        "https://github.com/kivy/kivy/",
        "https://ghfast.top/https://github.com/kivy/kivy/",
        "kivy -> ghfast镜像"
    )


def step5_clean():
    """清理构建缓存（保留p4a和packages）"""
    print(f"\n{B}[5/6] 清理构建缓存{N}")
    if PLATFORM.exists():
        for d in os.listdir(PLATFORM):
            full = PLATFORM / d
            if d.startswith("build-") and full.is_dir():
                shutil.rmtree(full, ignore_errors=True)
                print(f"  {G}清理{N} {d}")


def step6_build():
    """打包APK"""
    print(f"\n{B}[6/6] 打包 APK (约15-25分钟)...{N}\n")
    os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-17-openjdk-amd64"
    r = run("buildozer android debug", cwd=APP_DIR, timeout=3600)

    bin_dir = APP_DIR / "bin"
    apks = list(bin_dir.glob("*.apk")) if bin_dir.exists() else []

    if apks:
        print(f"\n{G}{'='*50}")
        print(f"  APK 打包成功！")
        print(f"{'='*50}{N}")
        for a in apks:
            mb = a.stat().st_size / 1024 / 1024
            print(f"  {G}{a.name}{N} ({mb:.1f} MB)")
        print(f"\n  Windows路径:")
        print(f"  \\\\wsl.localhost\\Ubuntu\\home\\csg\\audio_app\\bin")
        return True

    print(f"\n  {R}首次构建失败，修补后重试...{N}")
    step4_patch()  # 重新修补
    step5_clean()  # 清理缓存

    r2 = run("buildozer android debug", cwd=APP_DIR, timeout=3600)
    apks2 = list(bin_dir.glob("*.apk")) if bin_dir.exists() else []

    if apks2:
        print(f"\n{G}{'='*50}")
        print(f"  APK 打包成功！")
        print(f"{'='*50}{N}")
        for a in apks2:
            mb = a.stat().st_size / 1024 / 1024
            print(f"  {G}{a.name}{N} ({mb:.1f} MB)")
        return True

    print(f"\n  {R}打包仍然失败{N}")

    # 提取关键错误
    if r2 and r2.stdout:
        print(f"\n  {R}关键错误信息：{N}")
        for line in r2.stdout.split('\n'):
            l = line.lower()
            if any(k in l for k in ['error:', 'fatal:', 'failed']):
                clean = line.strip()[:200]
                if clean:
                    print(f"    {R}{clean}{N}")

    print(f"\n  建议: 使用 GitHub Actions 云端打包")
    print(f"  已更新workflow文件，push到GitHub即可自动构建")
    return False


def main():
    print(f"\n{G}{'='*50}")
    print(f"  音频提取器 APK 打包工具")
    print(f"  WSL Ubuntu 完整优化版")
    print(f"{'='*50}{N}")

    try:
        step1_sync()
        step2_git()
        if not step3_download_p4a():
            return
        step4_patch()
        step5_clean()
        step6_build()
    except KeyboardInterrupt:
        print(f"\n\n  {R}用户中断{N}")


if __name__ == "__main__":
    main()
