import os
import json
import re
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

class RSSGenerator:
    def __init__(self, base_url="http://127.0.0.1:4590"):
        self.base_url = base_url
        self.feed_title = "桂林理工大学教务处通知"
        self.feed_description = "桂林理工大学教务处最新通知公告"
        self.feed_author = "GLUT教务处"
        self.articles_dir = "articles"
        self.favicon_url = "https://ai.glut.edu.cn/assets/logo-BT23DgsH.svg"
        
    def sanitize_filename(self, filename):
        """清理文件名中的非法字符"""
        illegal_chars = r'[<>:"/\\|?*\x00-\x1f]'
        sanitized = re.sub(illegal_chars, '_', filename)
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        return sanitized.strip('_')
    
    def find_article_markdown(self, article_title):
        """根据文章标题查找对应的Markdown文件"""
        if not os.path.exists(self.articles_dir):
            return None
            
        # 清理标题以匹配目录名
        safe_title = self.sanitize_filename(article_title)
        
        # 遍历所有文章目录
        best_match = None
        best_score = 0
        
        for dirname in os.listdir(self.articles_dir):
            dir_path = os.path.join(self.articles_dir, dirname)
            if os.path.isdir(dir_path):
                # 计算匹配分数
                score = 0
                
                # 完全匹配得最高分
                if safe_title == dirname:
                    score = 100
                # 部分匹配
                elif safe_title in dirname or dirname in safe_title:
                    score = min(len(safe_title), len(dirname)) / max(len(safe_title), len(dirname)) * 50
                
                # 如果找到更好的匹配
                if score > best_score:
                    # 查找该目录下的Markdown文件
                    for filename in os.listdir(dir_path):
                        if filename.endswith('.md'):
                            markdown_path = os.path.join(dir_path, filename)
                            # 检查文件内容是否真的包含文章标题
                            try:
                                with open(markdown_path, 'r', encoding='utf-8') as f:
                                    first_line = f.readline().strip()
                                    if article_title in first_line or first_line in article_title:
                                        best_match = markdown_path
                                        best_score = score + 50  # 内容匹配加分
                                        break
                            except:
                                continue
        
        return best_match
    
    def extract_markdown_content(self, markdown_path):
        """从Markdown文件中提取正文内容和附件信息"""
        try:
            with open(markdown_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找正文部分（在"## 正文"之后，"## 附件"之前）
            content_start = content.find('## 正文')
            attachment_start = content.find('## 附件')
            
            content_text = None
            attachments = []
            
            if content_start != -1:
                if attachment_start != -1:
                    # 提取正文到附件之间的内容
                    content_text = content[content_start + 7:attachment_start].strip()
                    # 提取附件信息
                    attachment_section = content[attachment_start:]
                    # 查找所有附件链接
                    attachment_pattern = r'\[(.*?)\]\((.*?)\)'
                    for match in re.finditer(attachment_pattern, attachment_section):
                        filename = match.group(1)
                        filepath = match.group(2)
                        attachments.append({
                            'filename': filename,
                            'filepath': filepath
                        })
                else:
                    # 没有附件部分，提取到文件末尾
                    content_text = content[content_start + 7:].strip()
                
                # 清理多余的内容
                if content_text:
                    # 移除常见的噪音文本
                    noise_patterns = [
                        r'作者：.*?发布时间：\d{4}-\d{2}-\d{2}',
                        r'点击数：\d+',
                        r'关闭上一篇：.*?下一篇：.*',
                        r'附件【.*?】已下载\d*次',
                    ]
                    
                    for pattern in noise_patterns:
                        content_text = re.sub(pattern, '', content_text)
                    
                    # 清理多余的空白行
                    content_text = re.sub(r'\n\s*\n', '\n\n', content_text)
                    content_text = content_text.strip()
                    
                    # 如果清理后内容太少，返回原始正文
                    if len(content_text) < 10:
                        content_text = content[content_start + 7:attachment_start].strip() if attachment_start != -1 else content[content_start + 7:].strip()
            
            return content_text, attachments
            
        except Exception as e:
            print(f"读取Markdown文件失败 {markdown_path}: {e}")
            return None, []
    
    def load_important_articles(self):
        """加载所有标记为重要的文章"""
        cache_dir = 'cache'
        if not os.path.exists(cache_dir):
            return []
        
        important_articles = []
        for filename in os.listdir(cache_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(cache_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        articles = json.load(f)
                        # 只选择重要文章
                        important_articles.extend([
                            article for article in articles 
                            if article.get('is_important', False)
                        ])
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        # 按日期排序，最新的在前面
        important_articles.sort(
            key=lambda x: datetime.strptime(x['date'], '%Y-%m-%d') if len(x['date']) == 10 
                         else datetime.strptime(x['date'] + '-01', '%Y-%m-%d'),
            reverse=True
        )
        
        # 返回所有重要文章
        return important_articles
    
    def generate_atom_xml(self):
        """生成ATOM格式的RSS"""
        articles = self.load_important_articles()
        
        # 创建根元素
        feed = Element('feed', {'xmlns': 'http://www.w3.org/2005/Atom'})
        
        # Feed metadata
        title = SubElement(feed, 'title')
        title.text = self.feed_title
        
        subtitle = SubElement(feed, 'subtitle')
        subtitle.text = self.feed_description
        
        link = SubElement(feed, 'link', {
            'href': f'{self.base_url}/atom.xml',
            'rel': 'self'
        })
        
        updated = SubElement(feed, 'updated')
        if articles:
            latest_date = max(
                datetime.strptime(article['scraped_at'], '%Y-%m-%d %H:%M:%S') 
                for article in articles
            )
            updated.text = latest_date.isoformat() + 'Z'
        else:
            updated.text = datetime.now().isoformat() + 'Z'
        
        author = SubElement(feed, 'author')
        name = SubElement(author, 'name')
        name.text = self.feed_author
        
        id_elem = SubElement(feed, 'id')
        id_elem.text = f'{self.base_url}/atom.xml'
        
        icon = SubElement(feed, 'icon')
        icon.text = self.favicon_url
        
        logo = SubElement(feed, 'logo')
        logo.text = self.favicon_url
        
        # 添加文章条目
        for article in articles:
            entry = SubElement(feed, 'entry')
            
            entry_title = SubElement(entry, 'title')
            entry_title.text = article['title']
            
            entry_link = SubElement(entry, 'link', {'href': article['link']})
            
            entry_id = SubElement(entry, 'id')
            entry_id.text = article['link']
            
            entry_updated = SubElement(entry, 'updated')
            scraped_time = datetime.strptime(article['scraped_at'], '%Y-%m-%d %H:%M:%S')
            entry_updated.text = scraped_time.isoformat() + 'Z'
            
            entry_published = SubElement(entry, 'published')
            if len(article['date']) == 10:
                pub_date = datetime.strptime(article['date'], '%Y-%m-%d')
            else:
                pub_date = datetime.strptime(article['date'] + '-01', '%Y-%m-%d')
            entry_published.text = pub_date.isoformat() + 'T00:00:00Z'
            
            # 获取本地Markdown内容
            markdown_path = self.find_article_markdown(article['title'])
            if markdown_path:
                content_text, attachments = self.extract_markdown_content(markdown_path)
                
                # 如果有正文内容，显示正文
                if content_text and len(content_text.strip()) > 10:
                    # 将换行符转换为HTML
                    html_content = content_text.replace('\n', '<br/>')
                    content_text = html_content
                    
                    # 如果有PDF附件，添加PDF链接
                    pdf_attachments = [att for att in attachments if att['filepath'].lower().endswith('.pdf')]
                    if pdf_attachments:
                        content_text += "<br/><br/><strong>附件:</strong><br/>"
                        for att in pdf_attachments:
                            content_text += f"<a href='{article['link']}'>{att['filename']}</a><br/>"
                    
                    # 添加原文链接
                    content_text += f"<br/><br/><strong>原文链接:</strong> <a href='{article['link']}'>{article['link']}</a>"
                else:
                    # 没有正文内容，检查是否有PDF附件
                    pdf_attachments = [att for att in attachments if att['filepath'].lower().endswith('.pdf')]
                    if pdf_attachments:
                        content_text = "<strong>附件:</strong><br/>"
                        for att in pdf_attachments:
                            content_text += f"<a href='{article['link']}'>{att['filename']}</a><br/>"
                        content_text += f"<br/><strong>原文链接:</strong> <a href='{article['link']}'>{article['link']}</a>"
                    else:
                        # 没有正文也没有PDF，只显示原文链接
                        content_text = f"<strong>原文链接:</strong> <a href='{article['link']}'>{article['link']}</a>"
            else:
                # 没有markdown文件，只显示原文链接
                content_text = f"<strong>原文链接:</strong> <a href='{article['link']}'>{article['link']}</a>"
            
            entry_summary = SubElement(entry, 'summary', {'type': 'html'})
            entry_summary.text = f"<![CDATA[{content_text}]]>"
        
        # 格式化XML
        rough_string = tostring(feed, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')
    
    def generate_rss_xml(self):
        """生成RSS 2.0格式"""
        articles = self.load_important_articles()
        
        # 创建根元素
        rss = Element('rss', {'version': '2.0'})
        channel = SubElement(rss, 'channel')
        
        # Channel metadata
        title = SubElement(channel, 'title')
        title.text = self.feed_title
        
        description = SubElement(channel, 'description')
        description.text = self.feed_description
        
        link = SubElement(channel, 'link')
        link.text = self.base_url
        
        language = SubElement(channel, 'language')
        language.text = 'zh-CN'
        
        pubDate = SubElement(channel, 'pubDate')
        if articles:
            latest_date = max(
                datetime.strptime(article['scraped_at'], '%Y-%m-%d %H:%M:%S') 
                for article in articles
            )
            pubDate.text = latest_date.strftime('%a, %d %b %Y %H:%M:%S +0000')
        else:
            pubDate.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        lastBuildDate = SubElement(channel, 'lastBuildDate')
        lastBuildDate.text = datetime.now().strftime('%a, %d %b %Y %H:%M:%S +0000')
        
        generator = SubElement(channel, 'generator')
        generator.text = 'GLUT RSS Generator'
        
        # 添加频道图标
        image = SubElement(channel, 'image')
        image_url = SubElement(image, 'url')
        image_url.text = self.favicon_url
        image_title = SubElement(image, 'title')
        image_title.text = self.feed_title
        image_link = SubElement(image, 'link')
        image_link.text = self.base_url
        
        # 添加文章条目
        for article in articles:
            item = SubElement(channel, 'item')
            
            item_title = SubElement(item, 'title')
            item_title.text = article['title']
            
            # 获取本地Markdown内容
            markdown_path = self.find_article_markdown(article['title'])
            if markdown_path:
                content_text, attachments = self.extract_markdown_content(markdown_path)
                
                # 如果有正文内容，显示正文
                if content_text and len(content_text.strip()) > 10:
                    # 将换行符转换为HTML
                    html_content = content_text.replace('\n', '<br/>')
                    content_text = html_content
                    
                    # 如果有PDF附件，添加PDF链接
                    pdf_attachments = [att for att in attachments if att['filepath'].lower().endswith('.pdf')]
                    if pdf_attachments:
                        content_text += "<br/><br/><strong>附件:</strong><br/>"
                        for att in pdf_attachments:
                            content_text += f"<a href='{article['link']}'>{att['filename']}</a><br/>"
                    
                    # 添加原文链接
                    content_text += f"<br/><br/><strong>原文链接:</strong> <a href='{article['link']}'>{article['link']}</a>"
                else:
                    # 没有正文内容，检查是否有PDF附件
                    pdf_attachments = [att for att in attachments if att['filepath'].lower().endswith('.pdf')]
                    if pdf_attachments:
                        content_text = "<strong>附件:</strong><br/>"
                        for att in pdf_attachments:
                            content_text += f"<a href='{article['link']}'>{att['filename']}</a><br/>"
                        content_text += f"<br/><strong>原文链接:</strong> <a href='{article['link']}'>{article['link']}</a>"
                    else:
                        # 没有正文也没有PDF，只显示原文链接
                        content_text = f"<strong>原文链接:</strong> <a href='{article['link']}'>{article['link']}</a>"
            else:
                # 没有markdown文件，只显示原文链接
                content_text = f"<strong>原文链接:</strong> <a href='{article['link']}'>{article['link']}</a>"
            
            item_description = SubElement(item, 'description')
            item_description.text = f"<![CDATA[{content_text}]]>"
            
            item_link = SubElement(item, 'link')
            item_link.text = article['link']
            
            item_guid = SubElement(item, 'guid')
            item_guid.text = article['link']
            item_guid.set('isPermaLink', 'true')
            
            item_pubDate = SubElement(item, 'pubDate')
            if len(article['date']) == 10:
                pub_date = datetime.strptime(article['date'], '%Y-%m-%d')
            else:
                pub_date = datetime.strptime(article['date'] + '-01', '%Y-%m-%d')
            item_pubDate.text = pub_date.strftime('%a, %d %b %Y 00:00:00 +0000')
        
        # 格式化XML
        rough_string = tostring(rss, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')

def save_rss_files():
    """生成并保存RSS文件"""
    generator = RSSGenerator()
    
    # 确保rss目录存在
    rss_dir = 'rss'
    os.makedirs(rss_dir, exist_ok=True)
    
    # 生成ATOM格式
    atom_content = generator.generate_atom_xml()
    atom_path = os.path.join(rss_dir, 'atom.xml')
    with open(atom_path, 'w', encoding='utf-8') as f:
        f.write(atom_content)
    print(f"已生成 ATOM 文件: {atom_path}")
    
    # 生成RSS格式
    rss_content = generator.generate_rss_xml()
    rss_path = os.path.join(rss_dir, 'rss.xml')
    with open(rss_path, 'w', encoding='utf-8') as f:
        f.write(rss_content)
    print(f"已生成 RSS 文件: {rss_path}")
    
    # 显示统计信息
    articles = generator.load_important_articles()
    print(f"RSS包含 {len(articles)} 篇重要文章")
    if articles:
        print("最近的文章:")
        for i, article in enumerate(articles[:5], 1):
            print(f"  {i}. {article['title'][:50]}...")
    
    return atom_path, rss_path

if __name__ == '__main__':
    save_rss_files()