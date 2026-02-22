import http.server
import socketserver
import os
import json
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import threading
import time
import socket

# 导入RSS生成功能
from rss_generator import RSSGenerator, save_rss_files

class RSSRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory='.', **kwargs)
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # RSS文件路由
        if path == '/atom.xml' or path == '/rss.xml':
            self.serve_rss_file(path[1:])  # 移除开头的 '/'
            return
        elif path == '/rss' or path == '/':
            self.serve_rss_redirect()
            return
        elif path == '/api/articles':
            self.serve_api_articles()
            return
        elif path == '/status':
            self.serve_status()
            return
        else:
            # 默认处理静态文件
            super().do_GET()
    
    def serve_rss_file(self, filename):
        """提供RSS文件服务"""
        rss_dir = 'rss'
        filepath = os.path.join(rss_dir, filename)
        
        if os.path.exists(filepath):
            # 设置正确的Content-Type
            if filename.endswith('.xml'):
                self.send_response(200)
                self.send_header('Content-Type', 'application/xml; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                with open(filepath, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
        else:
            # 如果文件不存在，先生成RSS文件
            try:
                save_rss_files()
                if os.path.exists(filepath):
                    self.serve_rss_file(filename)
                else:
                    self.send_error(404, "RSS files could not be generated")
            except Exception as e:
                self.send_error(500, f"Error generating RSS: {str(e)}")
    
    def serve_rss_redirect(self):
        """RSS根路径重定向"""
        self.send_response(302)
        self.send_header('Location', '/rss.xml')
        self.end_headers()
    
    def serve_api_articles(self):
        """提供API接口获取文章列表"""
        try:
            # 加载重要文章
            generator = RSSGenerator()
            articles = generator.load_important_articles()
            
            # 返回JSON格式
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {
                'status': 'success',
                'count': len(articles),
                'articles': articles,
                'generated_at': datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response, ensure_ascii=False, indent=2).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error loading articles: {str(e)}")
    
    def serve_status(self):
        """提供服务状态信息"""
        try:
            # 获取缓存统计
            cache_stats = self.get_cache_statistics()
            
            # 获取RSS文件信息
            rss_info = self.get_rss_info()
            
            status_data = {
                'status': 'running',
                'service': 'GLUT RSS Server',
                'version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'cache_stats': cache_stats,
                'rss_info': rss_info,
                'endpoints': {
                    'rss_feed': 'http://127.0.0.1:4590/rss.xml',
                    'atom_feed': 'http://127.0.0.1:4590/atom.xml',
                    'api_articles': 'http://127.0.0.1:4590/api/articles',
                    'status': 'http://127.0.0.1:4590/status'
                }
            }
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(status_data, ensure_ascii=False, indent=2).encode('utf-8'))
            
        except Exception as e:
            self.send_error(500, f"Error getting status: {str(e)}")
    
    def get_cache_statistics(self):
        """获取缓存统计信息"""
        cache_dir = 'cache'
        if not os.path.exists(cache_dir):
            return {'files': 0, 'articles': 0, 'important_articles': 0}
        
        total_files = 0
        total_articles = 0
        important_articles = 0
        
        for filename in os.listdir(cache_dir):
            if filename.endswith('.json'):
                total_files += 1
                filepath = os.path.join(cache_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        articles = json.load(f)
                        total_articles += len(articles)
                        important_articles += sum(1 for article in articles if article.get('is_important', False))
                except (json.JSONDecodeError, FileNotFoundError):
                    continue
        
        return {
            'files': total_files,
            'articles': total_articles,
            'important_articles': important_articles
        }
    
    def get_rss_info(self):
        """获取RSS文件信息"""
        rss_dir = 'rss'
        info = {}
        
        for filename in ['rss.xml', 'atom.xml']:
            filepath = os.path.join(rss_dir, filename)
            if os.path.exists(filepath):
                stat = os.stat(filepath)
                info[filename] = {
                    'exists': True,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            else:
                info[filename] = {'exists': False}
        
        return info
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {format % args}")

class LocalRSSServer:
    def __init__(self, port=4590):
        self.port = port
        self.server = None
        self.is_running = False
        
    def find_available_port(self, start_port=4590, max_attempts=10):
        """寻找可用端口"""
        for port in range(start_port, start_port + max_attempts):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(('localhost', port))
                    return port
                except OSError:
                    continue
        raise Exception(f"无法找到可用端口 (尝试了 {max_attempts} 个端口)")
    
    def start(self):
        """启动服务器"""
        try:
            # 检查端口是否可用，如果不可用则寻找新端口
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', self.port))
            except OSError:
                print(f"⚠️  端口 {self.port} 已被占用，正在寻找可用端口...")
                self.port = self.find_available_port()
                print(f"✅ 找到可用端口: {self.port}")
            
            # 确保RSS文件存在
            save_rss_files()
            
            # 创建服务器
            with socketserver.TCPServer(("", self.port), RSSRequestHandler) as self.server:
                self.is_running = True
                print(f"🚀 GLUT RSS Server 启动成功!")
                print(f"📡 服务地址: http://127.0.0.1:{self.port}")
                print(f"📄 RSS订阅地址:")
                print(f"   - RSS 2.0: http://127.0.0.1:{self.port}/rss.xml")
                print(f"   - Atom: http://127.0.0.1:{self.port}/atom.xml")
                print(f"🔧 API接口:")
                print(f"   - 文章列表: http://127.0.0.1:{self.port}/api/articles")
                print(f"   - 服务状态: http://127.0.0.1:{self.port}/status")
                print(f"❌ 按 Ctrl+C 停止服务")
                print("-" * 50)
                
                self.server.serve_forever()
                
        except KeyboardInterrupt:
            print("\n🛑 正在停止服务器...")
            self.stop()
        except Exception as e:
            print(f"❌ 服务器启动失败: {e}")
    
    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
        self.is_running = False
        print("✅ 服务器已停止")

def main():
    """主函数"""
    print("📡 GLUT RSS 本地服务启动器")
    print("=" * 40)
    
    # 询问用户操作
    while True:
        print("\n请选择操作:")
        print("1. 启动RSS服务 (默认端口 4590，自动切换)")
        print("2. 仅生成RSS文件")
        print("3. 查看当前状态")
        print("4. 退出")
        
        choice = input("\n请输入选项 (1-4): ").strip()
        
        if choice == '1':
            server = LocalRSSServer(4590)
            server.start()
            break
            
        elif choice == '2':
            try:
                atom_path, rss_path = save_rss_files()
                print(f"\n✅ RSS文件生成完成!")
                print(f"📁 文件位置:")
                print(f"   - {atom_path}")
                print(f"   - {rss_path}")
            except Exception as e:
                print(f"❌ 生成RSS文件失败: {e}")
                
        elif choice == '3':
            try:
                generator = RSSGenerator()
                articles = generator.load_important_articles()
                print(f"\n📊 当前状态:")
                print(f"   重要文章数量: {len(articles)}")
                if articles:
                    print(f"   最新文章: {articles[0]['title'][:50]}...")
                    print(f"   最新日期: {articles[0]['date']}")
            except Exception as e:
                print(f"❌ 获取状态失败: {e}")
                
        elif choice == '4':
            print("👋 再见!")
            break
            
        else:
            print("❌ 无效选项，请重新选择")

if __name__ == '__main__':
    main()