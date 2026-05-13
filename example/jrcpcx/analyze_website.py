#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析 opennana.com 网站的技术栈和 SEO
"""

import requests
import re
from bs4 import BeautifulSoup
import json
from urllib.parse import urlparse

url = "https://opennana.com/awesome-prompt-gallery"
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
}

print("=" * 70)
print("网站技术栈与 SEO 分析")
print("目标: https://opennana.com/awesome-prompt-gallery")
print("=" * 70)

try:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    print(f"\n✅ HTTP 状态码: {response.status_code}")
    
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    
    # ============================================
    # 1. 分析 HTTP 响应头
    # ============================================
    print("\n" + "=" * 70)
    print("【1】HTTP 响应头分析")
    print("=" * 70)
    
    important_headers = ['server', 'x-powered-by', 'x-render', 'x-edge', 'via', 'cache-control', 'content-type']
    for key, value in response.headers.items():
        if key.lower() in important_headers or 'x-' in key.lower() or 'cf-' in key.lower():
            print(f"  {key}: {value}")
    
    # ============================================
    # 2. 分析技术栈
    # ============================================
    print("\n" + "=" * 70)
    print("【2】技术栈分析")
    print("=" * 70)
    
    tech_stack = set()
    
    # 检查 script 标签
    scripts = soup.find_all('script')
    script_srcs = [s.get('src', '') for s in scripts if s.get('src')]
    script_contents = [s.string for s in scripts if s.string]
    
    # 检查常见前端框架
    for src in script_srcs:
        if 'vue' in src.lower():
            tech_stack.add('Vue.js')
        if 'react' in src.lower():
            tech_stack.add('React')
        if 'angular' in src.lower():
            tech_stack.add('Angular')
        if 'nuxt' in src.lower():
            tech_stack.add('Nuxt.js')
        if 'next' in src.lower():
            tech_stack.add('Next.js')
        if 'tailwind' in src.lower():
            tech_stack.add('Tailwind CSS')
        if 'jquery' in src.lower():
            tech_stack.add('jQuery')
        if 'bootstrap' in src.lower():
            tech_stack.add('Bootstrap')
    
    # 检查 script 内容中的框架特征
    all_script_content = ' '.join(filter(None, script_contents))
    if '__nuxt' in all_script_content:
        tech_stack.add('Nuxt.js')
    if '_nuxt' in all_script_content:
        tech_stack.add('Nuxt.js')
    if 'createElement' in all_script_content and 'React' in all_script_content:
        tech_stack.add('React')
    if '__VUE__' in all_script_content:
        tech_stack.add('Vue.js')
    
    # 检查 meta 标签
    meta_tags = soup.find_all('meta')
    for meta in meta_tags:
        name = meta.get('name', '').lower()
        content = meta.get('content', '')
        if 'generator' in name:
            print(f"  ✅ Generator: {content}")
        if 'framework' in name:
            print(f"  ✅ Framework: {content}")
    
    # 检查 link 标签中的 CSS
    links = soup.find_all('link')
    for link in links:
        href = link.get('href', '')
        if 'tailwind' in href.lower():
            tech_stack.add('Tailwind CSS')
        if 'bootstrap' in href.lower():
            tech_stack.add('Bootstrap')
    
    # 检查 HTML 结构特征
    if soup.find(attrs={'data-v-': True}):
        tech_stack.add('Vue.js (data-v attributes)')
    if soup.find(id='app'):
        tech_stack.add('可能是 SPA (单页应用)')
    if soup.find(id='__nuxt'):
        tech_stack.add('Nuxt.js')
    
    print(f"\n  检测到的技术栈: {tech_stack if tech_stack else '未检测到明确标记'}")
    
    # 检查是否是 SSR (服务端渲染)
    print(f"\n  SSR 检测:")
    print(f"    - body 内主要内容数量: {len(soup.body.find_all()) if soup.body else 0}")
    
    # 检查是否有预加载内容
    script_tags_with_data = soup.find_all('script', type='application/json')
    script_tags_with_data += soup.find_all('script', type='application/ld+json')
    if script_tags_with_data:
        print(f"    - 发现 {len(script_tags_with_data)} 个 JSON 数据块（可能是 SSR 预加载）")
        for s in script_tags_with_data:
            print(f"      - {s.get('type')}: {str(s.string)[:100]}..." if s.string else '      - (空)')
    
    # ============================================
    # 3. SEO 分析
    # ============================================
    print("\n" + "=" * 70)
    print("【3】SEO 分析")
    print("=" * 70)
    
    # Title
    title = soup.title
    print(f"\n  Title 标签:")
    if title:
        print(f"    ✅ 存在: {title.string.strip()}")
        print(f"    长度: {len(title.string.strip())} 字符")
    else:
        print(f"    ❌ 缺失")
    
    # Meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    print(f"\n  Meta Description:")
    if meta_desc:
        print(f"    ✅ 存在: {meta_desc.get('content', '')[:150]}...")
    else:
        print(f"    ❌ 缺失")
    
    # Meta keywords
    meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
    print(f"\n  Meta Keywords:")
    if meta_keywords:
        print(f"    ✅ 存在: {meta_keywords.get('content', '')}")
    else:
        print(f"    ⚠️  未设置 (现代 SEO 中不再重要)")
    
    # Canonical URL
    canonical = soup.find('link', attrs={'rel': 'canonical'})
    print(f"\n  Canonical URL:")
    if canonical:
        print(f"    ✅ 存在: {canonical.get('href', '')}")
    else:
        print(f"    ⚠️  未设置")
    
    # Open Graph (社交分享)
    og_tags = soup.find_all('meta', attrs={'property': re.compile(r'^og:')})
    print(f"\n  Open Graph 标签:")
    if og_tags:
        print(f"    ✅ 存在 {len(og_tags)} 个 OG 标签:")
        for tag in og_tags:
            print(f"      - {tag.get('property')}: {tag.get('content', '')[:80]}")
    else:
        print(f"    ⚠️  缺失 (影响社交分享)")
    
    # Twitter Cards
    twitter_tags = soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')})
    print(f"\n  Twitter Cards:")
    if twitter_tags:
        print(f"    ✅ 存在 {len(twitter_tags)} 个 Twitter 标签")
    else:
        print(f"    ⚠️  缺失")
    
    # 结构化数据 (JSON-LD)
    json_ld = soup.find_all('script', type='application/ld+json')
    print(f"\n  结构化数据 (JSON-LD):")
    if json_ld:
        print(f"    ✅ 存在 {len(json_ld)} 个结构化数据块")
        for i, script in enumerate(json_ld):
            try:
                if script.string:
                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        print(f"      [{i+1}] 类型: {data.get('@type', 'Unknown')}")
                    elif isinstance(data, list):
                        print(f"      [{i+1}] 类型: 列表 (含 {len(data)} 项)")
            except:
                print(f"      [{i+1}] (解析失败)")
    else:
        print(f"    ⚠️  缺失")
    
    # H1 标签
    h1_tags = soup.find_all('h1')
    print(f"\n  H1 标签:")
    if h1_tags:
        print(f"    ✅ 存在 {len(h1_tags)} 个 H1:")
        for i, h1 in enumerate(h1_tags):
            text = h1.get_text(strip=True)
            print(f"      [{i+1}] '{text}'")
        if len(h1_tags) > 1:
            print(f"    ⚠️  警告: 页面应该只有一个 H1")
    else:
        print(f"    ❌ 缺失")
    
    # 图片 alt 属性检查
    img_tags = soup.find_all('img')
    print(f"\n  图片 Alt 属性:")
    if img_tags:
        alt_count = sum(1 for img in img_tags if img.get('alt'))
        print(f"    图片总数: {len(img_tags)}")
        print(f"    有 Alt 的图片: {alt_count}")
        print(f"    覆盖率: {alt_count/len(img_tags)*100:.1f}%")
        
        for i, img in enumerate(img_tags[:5]):
            src = img.get('src', '')[:50]
            alt = img.get('alt', '(无)')
            print(f"      [{i+1}] src={src}... alt={alt}")
    
    # ============================================
    # 4. 性能与其他分析
    # ============================================
    print("\n" + "=" * 70)
    print("【4】性能与结构分析")
    print("=" * 70)
    
    # HTML 大小
    print(f"\n  HTML 大小: {len(html)} 字节")
    
    # 检查是否有懒加载
    lazy_imgs = soup.find_all('img', attrs={'loading': 'lazy'})
    lazy_imgs += soup.find_all('img', attrs={'data-src': True})
    print(f"\n  懒加载图片: {len(lazy_imgs)} 张")
    
    # 检查是否有预加载
    preload_links = soup.find_all('link', attrs={'rel': 'preload'})
    prefetch_links = soup.find_all('link', attrs={'rel': 'prefetch'})
    print(f"  预加载资源: {len(preload_links)} 个 preload, {len(prefetch_links)} 个 prefetch")
    
    # 检查 viewport meta
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    print(f"\n  Viewport Meta:")
    if viewport:
        print(f"    ✅ 存在: {viewport.get('content', '')}")
    else:
        print(f"    ❌ 缺失 (移动端适配问题)")
    
    # 检查 robots
    robots = soup.find('meta', attrs={'name': 'robots'})
    print(f"\n  Robots Meta:")
    if robots:
        print(f"    ✅ 存在: {robots.get('content', '')}")
    else:
        print(f"    ⚠️  未设置 (默认允许抓取)")
    
    # ============================================
    # 5. 总结
    # ============================================
    print("\n" + "=" * 70)
    print("【5】SEO 评分总结")
    print("=" * 70)
    
    score = 0
    max_score = 10
    
    if title: score += 1.5
    if meta_desc: score += 1.5
    if canonical: score += 1
    if og_tags: score += 1
    if json_ld: score += 1
    if h1_tags: score += 1
    if img_tags and alt_count / len(img_tags) > 0.5: score += 1
    if viewport: score += 1
    if lazy_imgs: score += 0.5
    if preload_links: score += 0.5
    
    print(f"\n  SEO 综合评分: {score}/{max_score}")
    print(f"  百分比: {score/max_score*100:.1f}%")
    
    print("\n" + "-" * 70)
    print("优点:")
    if title: print("  ✅ 有 Title 标签")
    if meta_desc: print("  ✅ 有 Meta Description")
    if canonical: print("  ✅ 有 Canonical URL")
    if og_tags: print("  ✅ 有 Open Graph 标签")
    if json_ld: print("  ✅ 有结构化数据")
    if viewport: print("  ✅ 有 Viewport (移动端适配)")
    
    print("\n改进建议:")
    if not title: print("  ⚠️  添加 Title 标签")
    if not meta_desc: print("  ⚠️  添加 Meta Description")
    if not canonical: print("  ⚠️  添加 Canonical URL")
    if not og_tags: print("  ⚠️  添加 Open Graph 标签")
    if not json_ld: print("  ⚠️  添加结构化数据 (JSON-LD)")
    if not viewport: print("  ⚠️  添加 Viewport Meta")
    if img_tags and alt_count / len(img_tags) < 0.8:
        print(f"  ⚠️  提高图片 Alt 覆盖率 (当前: {alt_count/len(img_tags)*100:.1f}%)")
    
except Exception as e:
    print(f"\n❌ 错误: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("分析完成")
print("=" * 70)
