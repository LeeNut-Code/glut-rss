import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path

def get_archive_period(date_str):
    """根据日期确定归档期间（上半年/下半年）"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m')
            # 如果只有年月，设为该月的第一天
            date_obj = date_obj.replace(day=1)
        except ValueError:
            return None
    
    year = date_obj.year
    # 1-6月为上半年，7-12月为下半年
    if date_obj.month <= 6:
        return f"{year}年上半年"
    else:
        return f"{year}年下半年"

def load_all_cached_articles():
    """加载所有缓存的文章"""
    cache_dir = 'cache'
    if not os.path.exists(cache_dir):
        print("缓存目录不存在")
        return []
    
    all_articles = []
    for filename in os.listdir(cache_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(cache_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    date_articles = json.load(f)
                    all_articles.extend(date_articles)
            except (json.JSONDecodeError, FileNotFoundError) as e:
                print(f"读取文件 {filename} 失败: {e}")
                continue
    
    return all_articles

def clean_old_cache(months=6):
    """清理指定月份以前的缓存文件"""
    cache_dir = 'cache'
    if not os.path.exists(cache_dir):
        print("缓存目录不存在")
        return 0
    
    cutoff_date = datetime.now() - timedelta(days=months * 30)
    cleaned_count = 0
    
    print(f"开始清理 {months} 个月以前的缓存文件...")
    print(f"截止日期: {cutoff_date.strftime('%Y-%m-%d')}")
    
    for filename in os.listdir(cache_dir):
        if filename.endswith('.json'):
            # 从文件名提取日期
            date_str = filename[:-5]  # 移除 .json 后缀
            try:
                file_date = datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                try:
                    # 处理只有年月的情况
                    file_date = datetime.strptime(date_str, '%Y-%m')
                except ValueError:
                    print(f"无法解析日期格式: {filename}")
                    continue
            
            # 如果文件日期早于截止日期，则删除
            if file_date < cutoff_date:
                filepath = os.path.join(cache_dir, filename)
                try:
                    os.remove(filepath)
                    print(f"已删除: {filename}")
                    cleaned_count += 1
                except OSError as e:
                    print(f"删除文件失败 {filename}: {e}")
    
    print(f"清理完成，共删除 {cleaned_count} 个缓存文件")
    return cleaned_count

def archive_old_articles(months=6):
    """归档指定月份以前的文章到年份目录"""
    # 加载所有文章
    all_articles = load_all_cached_articles()
    if not all_articles:
        print("没有找到缓存文章")
        return 0
    
    # 确定截止日期
    cutoff_date = datetime.now() - timedelta(days=months * 30)
    print(f"开始归档 {months} 个月以前的文章...")
    print(f"截止日期: {cutoff_date.strftime('%Y-%m-%d')}")
    
    # 分类文章
    old_articles = []
    recent_articles = []
    
    for article in all_articles:
        article_date = article.get('date', '')
        if not article_date:
            continue
            
        try:
            date_obj = datetime.strptime(article_date, '%Y-%m-%d')
        except ValueError:
            try:
                date_obj = datetime.strptime(article_date, '%Y-%m')
                date_obj = date_obj.replace(day=1)
            except ValueError:
                # 无法解析日期的文章放入近期
                recent_articles.append(article)
                continue
        
        if date_obj < cutoff_date:
            old_articles.append(article)
        else:
            recent_articles.append(article)
    
    if not old_articles:
        print("没有需要归档的旧文章")
        return 0
    
    print(f"找到 {len(old_articles)} 篇旧文章需要归档")
    
    # 按归档期间分组
    articles_by_period = {}
    for article in old_articles:
        period = get_archive_period(article.get('date', ''))
        if period:
            if period not in articles_by_period:
                articles_by_period[period] = []
            articles_by_period[period].append(article)
    
    # 创建归档目录并保存文章
    archive_base_dir = 'archive'
    os.makedirs(archive_base_dir, exist_ok=True)
    
    archived_count = 0
    for period, articles in articles_by_period.items():
        # 创建期间目录
        period_dir = os.path.join(archive_base_dir, period)
        os.makedirs(period_dir, exist_ok=True)
        
        # 保存文章到JSON文件
        archive_file = os.path.join(period_dir, f"{period}_articles.json")
        
        # 读取现有文件（如果存在）
        existing_articles = []
        if os.path.exists(archive_file):
            try:
                with open(archive_file, 'r', encoding='utf-8') as f:
                    existing_articles = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_articles = []
        
        # 合并并去重
        all_period_articles = existing_articles + articles
        unique_articles = []
        seen_links = set()
        
        for article in all_period_articles:
            link = article.get('link', '')
            if link not in seen_links:
                unique_articles.append(article)
                seen_links.add(link)
        
        # 保存到归档文件
        try:
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(unique_articles, f, ensure_ascii=False, indent=2)
            
            print(f"已归档 {len(unique_articles)} 篇文章到 {period}")
            archived_count += len(unique_articles)
            
        except Exception as e:
            print(f"保存归档文件失败 {period}: {e}")
    
    print(f"归档完成，共处理 {archived_count} 篇文章")
    return archived_count

def show_cache_statistics():
    """显示缓存统计信息"""
    cache_dir = 'cache'
    if not os.path.exists(cache_dir):
        print("缓存目录不存在")
        return
    
    total_files = 0
    total_articles = 0
    date_range = []
    
    for filename in os.listdir(cache_dir):
        if filename.endswith('.json'):
            total_files += 1
            filepath = os.path.join(cache_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                    total_articles += len(articles)
                    
                    # 收集日期信息
                    for article in articles:
                        date_str = article.get('date', '')
                        if date_str:
                            date_range.append(date_str)
            except (json.JSONDecodeError, FileNotFoundError):
                continue
    
    print("=== 缓存统计信息 ===")
    print(f"缓存文件数量: {total_files}")
    print(f"文章总数: {total_articles}")
    
    if date_range:
        # 简单的日期范围统计
        sorted_dates = sorted([d for d in date_range if d])
        if sorted_dates:
            print(f"日期范围: {sorted_dates[0]} 至 {sorted_dates[-1]}")
    
    # 按重要性统计
    important_count = 0
    for filename in os.listdir(cache_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(cache_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    articles = json.load(f)
                    important_count += sum(1 for article in articles if article.get('is_important', False))
            except (json.JSONDecodeError, FileNotFoundError):
                continue
    
    print(f"重要文章数量: {important_count}")
    print("==================")

def main():
    """主函数"""
    print("GLUT 文章归档管理工具")
    print("=" * 30)
    
    while True:
        print("\n请选择操作:")
        print("1. 显示缓存统计信息")
        print("2. 清理6个月以前的缓存")
        print("3. 归档6个月以前的文章")
        print("4. 执行完整清理流程（清理+归档）")
        print("5. 退出")
        
        choice = input("\n请输入选项 (1-5): ").strip()
        
        if choice == '1':
            show_cache_statistics()
            
        elif choice == '2':
            confirm = input("确认清理6个月以前的缓存吗？(y/N): ").strip().lower()
            if confirm == 'y':
                clean_old_cache(6)
            else:
                print("操作已取消")
                
        elif choice == '3':
            confirm = input("确认归档6个月以前的文章吗？(y/N): ").strip().lower()
            if confirm == 'y':
                archive_old_articles(6)
            else:
                print("操作已取消")
                
        elif choice == '4':
            confirm = input("确认执行完整清理流程吗？这将清理缓存并归档旧文章 (y/N): ").strip().lower()
            if confirm == 'y':
                print("开始执行完整清理流程...")
                # 先归档再清理，避免数据丢失
                archive_old_articles(6)
                clean_old_cache(6)
                print("完整清理流程完成")
            else:
                print("操作已取消")
                
        elif choice == '5':
            print("再见！")
            break
            
        else:
            print("无效选项，请重新选择")

if __name__ == '__main__':
    main()

