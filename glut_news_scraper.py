import requests
from bs4 import BeautifulSoup
import os
from datetime import datetime, timedelta
import json
import time
from urllib.parse import urljoin, urlparse
import re
import hashlib

# 重要关键词列表
IMPORTANT_KEYWORDS = ['注意事项', '选课', '公告', '毕业论文', '毕业设计', '课表', '考试', '开课信息', '学位证书', '毕业', '报名', '证书', '缓考', '重修', '答辩', '实习', '停开']

def parse_article_date(date_string):
    """解析日期字符串，返回datetime对象"""
    try:
        # 处理 "YYYY-MM-DD" 格式
        if len(date_string) == 10 and date_string[4] == '-' and date_string[7] == '-':
            return datetime.strptime(date_string, '%Y-%m-%d')
        # 处理 "YYYY-MM" 格式
        elif len(date_string) == 7 and date_string[4] == '-':
            return datetime.strptime(date_string, '%Y-%m')
        else:
            return None
    except ValueError:
        return None

def is_important_article(title):
    """判断文章是否为重要文章"""
    return any(keyword in title for keyword in IMPORTANT_KEYWORDS)

def sanitize_filename(filename):
    """清理文件名中的非法字符"""
    # 移除或替换非法字符
    illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
    sanitized = re.sub(illegal_chars, '_', filename)
    # 限制长度
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized.strip('_')

def download_attachment(url, save_path):
    """下载附件文件"""
    try:
        response = requests.get(url, timeout=30, stream=True)
        response.raise_for_status()
        
        # 创建目录
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 保存文件
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        print(f"  已下载附件: {os.path.basename(save_path)}")
        return True
    except Exception as e:
        print(f"  下载附件失败 {url}: {e}")
        return False

def extract_article_content(url):
    """提取文章全文内容并下载附件"""
    try:
        response = requests.get(url, timeout=15)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找文章内容区域
        content_div = soup.find('div', class_='content-n') or soup.find('div', id='content') or soup.find('div', class_='content')
        
        if not content_div:
            # 如果找不到标准内容区域，尝试查找其他可能的内容容器
            content_div = soup.find('div', class_='article-content') or soup.find('div', class_='news-content')
        
        if not content_div:
            print(f"  未找到文章内容区域")
            return None, []
        
        # 提取文本内容
        content_text = content_div.get_text(strip=True)
        
        # 查找附件链接
        attachments = []
        attachment_links = content_div.find_all('a', href=True)
        
        for link in attachment_links:
            href = link.get('href', '')
            if any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.rar']):
                # 处理相对链接
                if href.startswith('/'):
                    full_url = f"https://jwc.glut.edu.cn{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = urljoin(url, href)
                
                attachments.append({
                    'url': full_url,
                    'filename': link.get_text(strip=True) or os.path.basename(href)
                })
        
        # 查找iframe中的PDF等文件
        iframes = content_div.find_all('iframe', src=True)
        for iframe in iframes:
            src = iframe.get('src', '')
            if '.pdf' in src.lower():
                if src.startswith('/'):
                    full_url = f"https://jwc.glut.edu.cn{src}"
                else:
                    full_url = urljoin(url, src)
                
                attachments.append({
                    'url': full_url,
                    'filename': 'embedded_document.pdf'
                })
        
        return content_text, attachments
        
    except Exception as e:
        print(f"  提取文章内容失败: {e}")
        return None, []

def save_article_markdown(article, content_text, attachments):
    """保存文章为Markdown格式"""
    try:
        # 创建文章目录
        safe_title = sanitize_filename(article['title'])
        article_dir = os.path.join('articles', safe_title)
        os.makedirs(article_dir, exist_ok=True)
        
        # 保存Markdown文件
        md_filename = f"{safe_title}.md"
        md_filepath = os.path.join(article_dir, md_filename)
        
        # 构建Markdown内容
        md_content = f"""# {article['title']}

**发布日期**: {article['date']}  
**原文链接**: [{article['link']}]({article['link']})  
**抓取时间**: {article['scraped_at']}

---
## 正文

{content_text}

"""
        
        if attachments:
            md_content += "\n## 附件\n\n"
            for i, attachment in enumerate(attachments, 1):
                md_content += f"{i}. [{attachment['filename']}]({attachment['filename']})\n"
        
        # 写入Markdown文件
        with open(md_filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)
        
        print(f"  已保存文章: {md_filename}")
        
        # 下载附件
        downloaded_attachments = []
        for attachment in attachments:
            attachment_filename = sanitize_filename(attachment['filename'])
            attachment_path = os.path.join(article_dir, attachment_filename)
            
            if download_attachment(attachment['url'], attachment_path):
                downloaded_attachments.append(attachment_filename)
        
        return md_filepath, downloaded_attachments
        
    except Exception as e:
        print(f"  保存文章失败: {e}")
        return None, []

def get_articles_from_page(url):
    """从单个页面获取文章列表"""
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        
        articles = []
        # 查找包含文章列表的div
        list_div = soup.find('div', class_='list')
        if not list_div:
            print(f"未在 {url} 找到文章列表")
            return []
        
        # 查找所有的li元素
        li_elements = list_div.find_all('li')
        
        for element in li_elements:
            # 查找文章链接
            link_element = element.find('a')
            if not link_element:
                continue
                
            title = link_element.get('title', '').strip()
            link = link_element.get('href', '')
            
            # 处理相对链接
            if link:
                if link.startswith('http'):
                    full_link = link
                elif link.startswith('../'):
                    full_link = urljoin('https://jwc.glut.edu.cn/', link[3:])
                else:
                    full_link = urljoin(url, link)
            else:
                full_link = ''
            
            # 查找日期信息
            date_element = element.find('div', class_='date')
            date_str = ''
            if date_element:
                month_element = date_element.find('p', class_='m')
                year_element = date_element.find('p', class_='y')
                if month_element and year_element:
                    month = month_element.get_text().strip()
                    year = year_element.get_text().strip()
                    date_str = f"{year}-{month}"
            
            # 只添加有标题的文章
            if title:
                # 判断是否为重要文章
                is_important = is_important_article(title)
                
                article_data = {
                    'title': title,
                    'link': full_link,
                    'date': date_str,
                    'scraped_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'is_important': is_important
                }
                
                articles.append(article_data)
        
        return articles
    except Exception as error:
        print(f'Error fetching articles from {url}: {error}')
        return []

def get_latest_articles(pages=30):
    """获取最近的文章，爬取指定页数"""
    base_url = 'https://jwc.glut.edu.cn/xwzx/tzgg.htm'
    all_articles = []
    
    print(f"开始爬取前 {pages} 页的文章...")
    
    # 首页
    print(f"正在爬取第 1 页...")
    first_page_articles = get_articles_from_page(base_url)
    all_articles.extend(first_page_articles)
    
    # 后续页面
    for page_num in range(2, min(pages + 1, 67)):  # 最多66页
        page_url = f'https://jwc.glut.edu.cn/xwzx/tzgg/{67 - page_num}.htm'
        print(f"正在爬取第 {page_num} 页: {page_url}")
        
        page_articles = get_articles_from_page(page_url)
        all_articles.extend(page_articles)
        
        # 添加延时，避免请求过于频繁
        time.sleep(1)
    
    # 按日期排序（最新的在前面）
    all_articles.sort(key=lambda x: parse_article_date(x['date']) or datetime.min, reverse=True)
    
    # 过滤最近半年的文章
    six_months_ago = datetime.now() - timedelta(days=180)
    recent_articles = [
        article for article in all_articles 
        if parse_article_date(article['date']) and 
           parse_article_date(article['date']) >= six_months_ago
    ]
    
    print(f"总共获取 {len(all_articles)} 篇文章，其中最近半年的有 {len(recent_articles)} 篇")
    return recent_articles

def create_cache_directory():
    """创建缓存目录"""
    cache_dir = 'cache'
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
        print(f"创建缓存目录: {cache_dir}")
    return cache_dir

def save_articles_by_date(articles):
    """按日期将文章保存到不同的文件中"""
    cache_dir = create_cache_directory()
    
    # 按日期分组文章
    articles_by_date = {}
    for article in articles:
        date = article['date']
        if date not in articles_by_date:
            articles_by_date[date] = []
        articles_by_date[date].append(article)
    
    # 为每个日期创建文件
    for date, date_articles in articles_by_date.items():
        # 清理日期字符串，替换非法字符
        safe_date = date.replace('/', '-').replace(':', '-')
        filename = f"{safe_date}.json"
        filepath = os.path.join(cache_dir, filename)
        
        # 读取现有文件内容（如果存在）
        existing_articles = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    existing_articles = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_articles = []
        
        # 合并新旧文章，去重
        all_articles = existing_articles + date_articles
        # 根据链接去重
        unique_articles = []
        seen_links = set()
        for article in all_articles:
            if article['link'] not in seen_links:
                unique_articles.append(article)
                seen_links.add(article['link'])
        
        # 保存到文件
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(unique_articles, f, ensure_ascii=False, indent=2)
        
        print(f"保存 {len(unique_articles)} 篇文章到 {filepath}")

def load_cached_articles(date=None):
    """加载缓存的文章"""
    cache_dir = 'cache'
    if not os.path.exists(cache_dir):
        return []
    
    articles = []
    if date:
        # 加载特定日期的文章
        safe_date = date.replace('/', '-').replace(':', '-')
        filename = f"{safe_date}.json"
        filepath = os.path.join(cache_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                articles = []
    else:
        # 加载所有缓存的文章
        for filename in os.listdir(cache_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(cache_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        date_articles = json.load(f)
                        articles.extend(date_articles)
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
    
    return articles

def process_important_articles(articles):
    """处理重要文章：下载全文和附件"""
    important_articles = [article for article in articles if article.get('is_important', False)]
    
    if not important_articles:
        print("没有找到标记为重要的文章")
        return
    
    print(f"\n开始处理 {len(important_articles)} 篇重要文章...")
    
    processed_count = 0
    for article in important_articles:
        print(f"\n处理文章: {article['title']}")
        
        # 提取文章内容和附件
        content_text, attachments = extract_article_content(article['link'])
        
        if content_text:
            # 保存为Markdown并下载附件
            md_path, downloaded_attachments = save_article_markdown(article, content_text, attachments)
            if md_path:
                processed_count += 1
                print(f"  完成处理，保存至: {md_path}")
                if downloaded_attachments:
                    print(f"  下载了 {len(downloaded_attachments)} 个附件")
        else:
            print("  未能提取文章内容")
        
        # 添加延时避免请求过快
        time.sleep(2)
    
    print(f"\n重要文章处理完成: {processed_count}/{len(important_articles)} 篇")

def update_rss_after_scraping():
    """在爬取完成后更新RSS文件"""
    try:
        from rss_generator import save_rss_files
        print("\n🔄 正在更新RSS订阅文件...")
        atom_path, rss_path = save_rss_files()
        print("✅ RSS文件更新完成")
        print(f"   - {atom_path}")
        print(f"   - {rss_path}")
    except ImportError:
        print("⚠️  RSS生成功能未找到，请确保rss_generator.py存在")
    except Exception as e:
        print(f"❌ 更新RSS文件失败: {e}")

# 在main函数中调用
def main():
    # 获取最近半年的文章
    articles = get_latest_articles(pages=30)  # 爬取前30页
    
    if articles:
        print(f'获取到 {len(articles)} 篇最近半年的文章')
        
        # 统计重要文章数量
        important_count = sum(1 for article in articles if article.get('is_important', False))
        print(f'其中标记为重要的文章: {important_count} 篇')
        
        # 保存到缓存文件
        save_articles_by_date(articles)
        
        # 处理重要文章（下载全文和附件）
        process_important_articles(articles)
        
        # 更新RSS文件
        update_rss_after_scraping()
        
        # 显示最近的文章
        print('\n最近半年的文章列表 (前20篇):')
        for index, article in enumerate(articles[:20], 1):
            importance_marker = " ⭐" if article.get('is_important', False) else ""
            print(f'{index}. {article["title"]}{importance_marker}')
            print(f'   日期: {article["date"]}')
            print(f'   链接: {article["link"]}')
            print('')
    else:
        print('未获取到文章')
        
        # 如果网络获取失败，尝试从缓存加载
        print('尝试从缓存加载文章...')
        cached_articles = load_cached_articles()
        if cached_articles:
            # 过滤最近半年的文章
            six_months_ago = datetime.now() - timedelta(days=180)
            recent_cached = [
                article for article in cached_articles 
                if parse_article_date(article['date']) and 
                   parse_article_date(article['date']) >= six_months_ago
            ]
            
            if recent_cached:
                print(f'从缓存加载到 {len(recent_cached)} 篇最近半年的文章')
                print('\n缓存中的最近文章:')
                for index, article in enumerate(recent_cached[:20], 1):
                    importance_marker = " ⭐" if article.get('is_important', False) else ""
                    print(f'{index}. {article["title"]}{importance_marker}')
                    print(f'   日期: {article["date"]}')
                    print(f'   链接: {article["link"]}')
                    print('')

if __name__ == '__main__':
    main()