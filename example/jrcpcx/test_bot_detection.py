#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浏览器反检测测试脚本
打开 https://www.browserscan.net/zh/bot-detection 模拟真人操作
- 随机滚动
- 随机鼠标移动
- 随机点击
- 不自动退出，保持浏览器窗口打开
"""

import random
import time
from playwright.sync_api import sync_playwright


def simulate_human_scroll(page, num_scrolls=5):
    """
    模拟真人滚动操作
    
    策略：
    1. 随机滚动距离（300-800px）
    2. 随机方向（向下为主，偶尔向上）
    3. 随机速度（使用平滑滚动）
    4. 滚动后随机停顿
    """
    print(f"\n[滚动] 开始模拟滚动，共 {num_scrolls} 次")
    
    for i in range(num_scrolls):
        direction = random.choice(["down", "down", "down", "up"])
        distance = random.randint(300, 800)
        
        if direction == "down":
            scroll_amount = distance
            print(f"  第 {i+1}/{num_scrolls} 次: 向下滚动 {scroll_amount}px")
        else:
            scroll_amount = -int(distance * 0.6)
            print(f"  第 {i+1}/{num_scrolls} 次: 向上滚动 {abs(scroll_amount)}px")
        
        page.evaluate(f"window.scrollBy({{ top: {scroll_amount}, behavior: 'smooth' }})")
        
        time.sleep(random.uniform(0.8, 2.0))


def simulate_human_mouse_move(page):
    """
    模拟真人鼠标移动操作
    
    策略：
    1. 移动到随机位置
    2. 多次小幅度移动
    3. 随机速度
    """
    print("\n[鼠标移动] 开始模拟鼠标移动")
    
    viewport = page.viewport_size
    if viewport:
        width = viewport["width"]
        height = viewport["height"]
    else:
        width = 1200
        height = 800
    
    for i in range(random.randint(5, 10)):
        x = random.randint(50, width - 50)
        y = random.randint(100, height - 100)
        
        page.mouse.move(x, y)
        print(f"  移动到: ({x}, {y})")
        time.sleep(random.uniform(0.3, 1.0))


def simulate_human_click(page):
    """
    模拟真人点击操作
    
    策略：
    1. 点击可见的、安全的元素（不会触发跳转）
    2. 随机停顿
    3. 优先点击按钮、链接等交互元素
    """
    print("\n[点击] 开始模拟随机点击")
    
    safe_selectors = [
        "button:not([type='submit'])",
        "a[href='#']",
        "div[role='button']",
        "span",
        "p"
    ]
    
    for selector in safe_selectors:
        try:
            elements = page.query_selector_all(selector)
            if elements:
                element = random.choice(elements)
                
                if element.is_visible():
                    box = element.bounding_box()
                    if box:
                        x = box["x"] + box["width"] / 2
                        y = box["y"] + box["height"] / 2
                        
                        print(f"  点击元素: {selector} 位置: ({int(x)}, {int(y)})")
                        
                        page.mouse.move(x, y)
                        time.sleep(random.uniform(0.2, 0.5))
                        page.mouse.click(x, y)
                        time.sleep(random.uniform(1.0, 2.0))
                        
                        return
        except Exception as e:
            continue
    
    print("  未找到合适的点击元素，使用随机位置模拟点击")
    viewport = page.viewport_size
    if viewport:
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        page.mouse.move(x, y)
        time.sleep(random.uniform(0.2, 0.5))
        page.mouse.down()
        time.sleep(random.uniform(0.1, 0.3))
        page.mouse.up()
        print(f"  模拟点击位置: ({x}, {y})")


def simulate_keyboard_input(page):
    """
    模拟键盘输入（输入到隐藏的 textarea）
    避免触发实际功能
    """
    print("\n[键盘] 模拟随机键盘输入")
    
    try:
        page.evaluate("""
            const textarea = document.createElement('textarea');
            textarea.style.position = 'fixed';
            textarea.style.opacity = '0';
            textarea.id = 'simulated-input';
            document.body.appendChild(textarea);
            textarea.focus();
        """)
        
        test_texts = ["test", "hello", "abc123", "test123"]
        text = random.choice(test_texts)
        
        for char in text:
            page.keyboard.press(char)
            time.sleep(random.uniform(0.1, 0.3))
        
        print(f"  输入文本: '{text}'")
        
        page.evaluate("""
            const textarea = document.getElementById('simulated-input');
            if (textarea) textarea.remove();
        """)
        
    except Exception as e:
        print(f"  键盘模拟异常: {e}")


def test_bot_detection(url="https://www.browserscan.net/zh/bot-detection",
                        headless=False,
                        slow_mo=100):
    """
    打开浏览器检测页面并模拟真人操作
    
    参数:
        url: 目标页面 URL
        headless: 是否无头模式（默认 False，显示浏览器）
        slow_mo: 操作延迟（毫秒），使操作更自然
    """
    print("=" * 60)
    print("浏览器反检测测试")
    print("=" * 60)
    print(f"目标页面: {url}")
    print(f"无头模式: {headless}")
    print(f"操作延迟: {slow_mo}ms")
    print("=" * 60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless,
            slow_mo=slow_mo,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ]
        )
        
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        
        page = context.new_page()
        
        try:
            print(f"\n[导航] 正在访问: {url}")
            page.goto(url, wait_until="networkidle", timeout=60000)
            print("[导航] 页面加载完成")
            
            time.sleep(random.uniform(2.0, 4.0))
            
            print("\n" + "-" * 60)
            print("开始模拟真人行为")
            print("-" * 60)
            
            simulate_human_mouse_move(page)
            time.sleep(random.uniform(1.0, 2.0))
            
            simulate_human_scroll(page, num_scrolls=random.randint(4, 7))
            time.sleep(random.uniform(1.0, 2.0))
            
            simulate_human_click(page)
            time.sleep(random.uniform(1.0, 2.0))
            
            simulate_human_mouse_move(page)
            time.sleep(random.uniform(1.0, 2.0))
            
            simulate_human_scroll(page, num_scrolls=random.randint(2, 4))
            time.sleep(random.uniform(1.0, 2.0))
            
            print("\n" + "-" * 60)
            print("模拟操作完成！浏览器窗口保持打开状态")
            print("-" * 60)
            print("请查看浏览器中的检测结果")
            print("按 Ctrl+C 或关闭终端来结束程序")
            print("-" * 60)
            
            while True:
                try:
                    time.sleep(5)
                except KeyboardInterrupt:
                    print("\n[退出] 收到中断信号，准备关闭浏览器...")
                    break
                    
        except KeyboardInterrupt:
            print("\n[退出] 收到中断信号")
        except Exception as e:
            print(f"[错误] {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\n[清理] 关闭浏览器...")
            browser.close()
            print("[完成] 程序结束")


if __name__ == "__main__":
    test_bot_detection()
