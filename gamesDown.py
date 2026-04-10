import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import hashlib
import time
import random
import webbrowser
from bs4 import BeautifulSoup
import sys
from io import BytesIO
from PIL import Image, ImageTk
import urllib3

class GameDetailWindow:
    """游戏详情弹窗"""
    _instance = None  # 单例模式，确保只有一个详情窗口
    
    def __init__(self, parent_app):
        self.parent_app = parent_app
        self.window = None
        self.current_game_id = None
        
    def show(self, game_id, game_name):
        """显示或更新游戏详情窗口"""
        # 【关键】检查窗口是否仍然有效
        if self.window is not None:
            try:
                # 尝试访问窗口属性，如果窗口已销毁会抛出异常
                if not self.window.winfo_exists():
                    self.window = None
                    self.current_game_id = None
            except:
                # 窗口已销毁，清空引用
                self.window = None
                self.current_game_id = None
        
        # 如果窗口已存在且是同一个游戏，直接返回
        if self.window and self.current_game_id == game_id:
            try:
                self.window.lift()  # 将窗口提到最前
                self.window.focus_force()  # 强制获取焦点
                return
            except:
                # 如果 lift 失败，说明窗口有问题，重新创建
                self.window = None
                self.current_game_id = None
        
        # 如果窗口已存在但不同游戏，更新内容
        if self.window and self.current_game_id != game_id:
            self.current_game_id = game_id
            # 先清空旧内容，显示加载状态
            self.image_label.config(text="加载中...", fg="#999")
            self.detail_text.config(state=tk.NORMAL)
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(tk.END, "加载中...")
            self.detail_text.config(state=tk.DISABLED)
            
            self._load_and_update_content(game_id, game_name)
            try:
                self.window.lift()
                self.window.focus_force()
            except:
                pass
            return
        
        # 创建新窗口
        self.current_game_id = game_id
        self.window = tk.Toplevel(self.parent_app.root)
        self.window.title(f"{game_name} - 游戏详情")
        self.window.geometry("800x600")
        self.window.minsize(600, 400)
        
        # 【关键】移除模态对话框设置，允许同时操作主窗口
        # self.window.transient(self.parent_app.root)  # 注释掉
        # self.window.grab_set()  # 注释掉
        
        # 设置窗口图标和样式
        self.window.configure(bg="white")
        
        # 创建主容器
        main_frame = tk.Frame(self.window, bg="white")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # 标题
        title_label = tk.Label(main_frame, text=game_name, bg="white", 
                              font=("Microsoft YaHei", 16, "bold"), fg="#2c3e50")
        title_label.pack(anchor="w", pady=(0, 10))
        
        # 图片区域
        self.image_frame = tk.Frame(main_frame, bg="#f0f0f0", height=250)
        self.image_frame.pack(fill=tk.X, pady=(0, 15))
        self.image_frame.pack_propagate(False)
        
        # 图片占位符
        self.image_label = tk.Label(self.image_frame, text="加载中...", 
                                   bg="#e0e0e0", fg="#999", font=("Microsoft YaHei", 10))
        self.image_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        # 滚动文本区域
        text_container = tk.Frame(main_frame, bg="white")
        text_container.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(text_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.detail_text = tk.Text(text_container, wrap=tk.WORD, yscrollcommand=scrollbar.set,
                                  font=("Microsoft YaHei", 10), bg="white", fg="#333",
                                  relief=tk.FLAT, padx=5, pady=5)
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.detail_text.yview)
        
        # 设置为只读
        self.detail_text.config(state=tk.DISABLED)
        
        # 【关键】在创建所有控件后，再绑定关闭事件
        self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)
        
        print(f"✅ 详情窗口已创建，game_id={game_id}")
        
        # 异步加载详情内容
        thread = threading.Thread(target=self._load_and_update_content, args=(game_id, game_name))
        thread.daemon = True
        thread.start()
    
    def _on_window_close(self):
        """处理窗口关闭事件"""
        print("🔄 详情窗口关闭事件触发")
        
        # 销毁窗口并清理引用
        if self.window:
            try:
                print("🗑️ 正在销毁窗口...")
                self.window.destroy()
                print("✅ 窗口已销毁")
            except Exception as e:
                print(f"❌ 销毁窗口失败: {e}")
        
        self.window = None
        self.current_game_id = None
        print("✅ 引用已清理")

    def _load_and_update_content(self, game_id, game_name):
        """异步加载并更新详情内容"""
        try:
            detail_url = f"{self.parent_app.base_url}/game/{game_id}"
            
            # 【关键】禁用SSL警告
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            resp = self.parent_app.session.get(detail_url, timeout=10, verify=False)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 提取图片
            img_url = None
            img_tag = soup.find('img', class_=lambda c: c and ('capsule' in c.lower() or 'banner' in c.lower() or 'cover' in c.lower()))
            if not img_tag:
                img_tag = soup.find('img')
            if img_tag:
                img_url = img_tag.get('data-src') or img_tag.get('src')
            
            # 提取介绍文本
            description = ""
            content_div = soup.find('div', class_='content_body')
            if content_div:
                # 获取HTML内容并清理
                description = content_div.get_text(separator='\n', strip=True)
            else:
                # 尝试其他选择器
                desc_div = soup.find('div', class_=lambda c: c and ('desc' in c.lower() or 'intro' in c.lower() or 'detail' in c.lower()))
                if desc_div:
                    description = desc_div.get_text(separator='\n', strip=True)
            
            # 更新UI
            if self.window:
                # 更新图片
                if img_url:
                    if img_url.startswith('//'):
                        img_url = 'https:' + img_url
                    elif img_url.startswith('/'):
                        img_url = self.parent_app.base_url + img_url
                    
                    print(f"📥 下载详情页图片: {img_url[:60]}...")
                    
                    # 【关键】下载图片时禁用SSL验证
                    img_resp = self.parent_app.session.get(img_url, timeout=10, verify=False)
                    
                    if img_resp.status_code == 200:
                        print(f"✅ 图片下载成功，大小: {len(img_resp.content)} bytes")
                        img_data = BytesIO(img_resp.content)
                        img = Image.open(img_data)
                        print(f"📐 原始图片尺寸: {img.size}")
                        
                        # 调整图片宽度适应窗口，保持比例
                        width = 750
                        height = int(width * img.height / img.width)
                        img = img.resize((width, min(height, 250)), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        
                        self.window.after(0, lambda: self._update_image(photo))
                    else:
                        print(f"❌ 图片下载失败，状态码: {img_resp.status_code}")
                        self.window.after(0, lambda: self._update_image_error())
                else:
                    print(f"⚠️ 未找到图片URL")
                    self.window.after(0, lambda: self._update_image_error())
                
                # 更新文本
                if description:
                    print(f"📝 找到游戏介绍，长度: {len(description)} 字符")
                    self.window.after(0, lambda: self._update_text(description))
                else:
                    print(f"⚠️ 未找到游戏介绍")
                    self.window.after(0, lambda: self._update_text("暂无详细介绍"))
                    
        except Exception as e:
            print(f"❌ 加载游戏详情失败: {e}")
            import traceback
            traceback.print_exc()
            if self.window:
                self.window.after(0, lambda: self._update_text(f"加载失败: {str(e)[:200]}"))
    
    def _update_image_error(self):
        """更新图片显示为错误状态"""
        if self.window:
            self.image_label.config(text="图片加载失败", fg="#f44336")

    def _update_image(self, photo):
        """更新图片显示"""
        if self.window:  # 【关键】检查窗口是否仍然存在
            self.image_label.config(image=photo, text="")
            self.image_label.image = photo  # 保持引用
    
    def _update_text(self, text):
        """更新文本显示"""
        if self.window:  # 【关键】检查窗口是否仍然存在
            self.detail_text.config(state=tk.NORMAL)
            self.detail_text.delete(1.0, tk.END)
            self.detail_text.insert(tk.END, text)
            self.detail_text.config(state=tk.DISABLED)

class GameDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("XIA THON 游戏下载器")
        self.root.geometry("950x650")
        self.root.minsize(800, 550)

        self.COLOR_PRIMARY = "#2196F3"
        self.COLOR_SUCCESS = "#4CAF50"
        self.COLOR_BG = "#f5f5f5"
        self.COLOR_WARNING = "#FF9800"

        self.base_url = "https://koysobackup.com"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": self.base_url,
            "Origin": self.base_url,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"
        })

        # 【关键】设置 Cookie 强制使用中文
        self.session.cookies.set('language', 'schinese', domain='koysobackup.com')
        self.session.cookies.set('key', 'NBQEah#h@6qHr7T!k', domain='.koyso.com')

        # 游戏分类
        self.categories = {
            "全部游戏": "",
            "动作游戏": "action",
            "冒险游戏": "adventure",
            "射击游戏": "shooting",
            "角色扮演": "rpg",
            "策略游戏": "strategy",
            "模拟经营": "simulation",
            "体育竞速": "sports",
            "休闲游戏": "casual",
            "恐怖游戏": "horror",
            "格斗游戏": "fighting",
            "独立游戏": "indie",
            "卡牌游戏": "card",
            "即时战略": "rts",
            "局域网联机": "lan"
        }

        # 排序方式 - 只保留热门和最新
        self.sort_options = {
            "🔥 热门": "popular",
            "🆕 最新": "latest"
        }

        self.current_page = 1
        self.total_pages = None
        self.current_category = ""
        self.current_sort = "latest"
        self.game_details_cache = {}
        self.loading_details = set()
        self.image_cache = {}
        
        # 创建游戏详情窗口实例（单例）
        self.detail_window = GameDetailWindow(self)

        # 【关键】添加退出标志
        self.is_exiting = False

        # === 界面布局 ===

        # 1. 顶部标题栏
        frame_header = tk.Frame(root, bg="#2c3e50", height=45)
        frame_header.pack(fill=tk.X)
        frame_header.pack_propagate(False)

        tk.Label(frame_header, text="Koyso 游戏下载器",
                bg="#2c3e50", fg="white", font=("Microsoft YaHei", 14, "bold")).pack(pady=8)

        # 2. 搜索和控制区
        frame_control = tk.Frame(root, bg=self.COLOR_BG, padx=10, pady=8)
        frame_control.pack(fill=tk.X)

        # 第一行：分类 + 排序 + 搜索
        frame_row1 = tk.Frame(frame_control, bg=self.COLOR_BG)
        frame_row1.pack(fill=tk.X, pady=3)

        tk.Label(frame_row1, text="分类:", bg=self.COLOR_BG, font=("Microsoft YaHei", 9)).grid(row=0, column=0, sticky="w")
        self.category_var = tk.StringVar(value="全部游戏")
        self.combo_category = ttk.Combobox(frame_row1, textvariable=self.category_var,
                                           values=list(self.categories.keys()), width=10, state="readonly")
        self.combo_category.grid(row=0, column=1, sticky="w", padx=5)
        self.combo_category.bind("<<ComboboxSelected>>", lambda e: self.on_category_change())

        tk.Label(frame_row1, text="排序:", bg=self.COLOR_BG, font=("Microsoft YaHei", 9)).grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.sort_var = tk.StringVar(value="🆕 最新")
        self.combo_sort = ttk.Combobox(frame_row1, textvariable=self.sort_var,
                                       values=list(self.sort_options.keys()), width=8, state="readonly")
        self.combo_sort.grid(row=0, column=3, sticky="w", padx=5)
        self.combo_sort.bind("<<ComboboxSelected>>", lambda e: self.on_sort_change())

        tk.Label(frame_row1, text="名称:", bg=self.COLOR_BG, font=("Microsoft YaHei", 9)).grid(row=0, column=4, sticky="w", padx=(10, 0))
        self.entry_keyword = tk.Entry(frame_row1, width=12, font=("Microsoft YaHei", 9))
        self.entry_keyword.grid(row=0, column=5, sticky="w", padx=5)
        self.entry_keyword.bind("<Return>", lambda e: self.search_games())

        tk.Button(frame_row1, text="搜索", command=self.search_games,
                 bg=self.COLOR_PRIMARY, fg="white", font=("Microsoft YaHei", 9),
                 cursor="hand2", padx=12).grid(row=0, column=6, padx=5)

        # 第二行：分页控制
        frame_row2 = tk.Frame(frame_control, bg=self.COLOR_BG)
        frame_row2.pack(fill=tk.X, pady=3)

        tk.Button(frame_row2, text="◀ 上一页", command=self.prev_page,
                 font=("Microsoft YaHei", 8), cursor="hand2", state=tk.DISABLED, padx=8, pady=2).pack(side=tk.LEFT, padx=2)
        self.btn_prev = frame_row2.pack_slaves()[0]

        # 页码显示区域
        frame_page_info = tk.Frame(frame_row2, bg="white", relief=tk.SOLID, bd=1, padx=8, pady=2)
        frame_page_info.pack(side=tk.LEFT, padx=8)

        tk.Label(frame_page_info, text="第", bg="white", fg="#666", font=("Microsoft YaHei", 8)).pack(side=tk.LEFT)
        self.lbl_current_page = tk.Label(frame_page_info, text="1", bg="white", fg="#2196F3",
                                         font=("Microsoft YaHei", 9, "bold"), width=3)
        self.lbl_current_page.pack(side=tk.LEFT, padx=2)

        tk.Label(frame_page_info, text="/", bg="white", fg="#999", font=("Microsoft YaHei", 9)).pack(side=tk.LEFT)

        self.lbl_total_pages = tk.Label(frame_page_info, text="--", bg="white", fg="#4CAF50",
                                        font=("Microsoft YaHei", 9, "bold"), width=3)
        self.lbl_total_pages.pack(side=tk.LEFT, padx=2)

        tk.Label(frame_page_info, text="页", bg="white", fg="#666", font=("Microsoft YaHei", 8)).pack(side=tk.LEFT)

        tk.Button(frame_row2, text="下一页 ▶", command=self.next_page,
                 font=("Microsoft YaHei", 8), cursor="hand2", padx=8, pady=2).pack(side=tk.LEFT, padx=5)
        self.btn_next = frame_row2.pack_slaves()[-1]

        # 跳转页码
        tk.Label(frame_row2, text="跳至:", bg=self.COLOR_BG, font=("Microsoft YaHei", 8)).pack(side=tk.LEFT, padx=(10, 3))
        self.entry_jump = tk.Entry(frame_row2, width=4, font=("Microsoft YaHei", 8))
        self.entry_jump.pack(side=tk.LEFT)
        self.entry_jump.bind("<Return>", lambda e: self.jump_to_page())
        tk.Button(frame_row2, text="GO", command=self.jump_to_page,
                 bg=self.COLOR_WARNING, fg="white", font=("Microsoft YaHei", 8),
                 cursor="hand2", padx=6, pady=1).pack(side=tk.LEFT, padx=3)

        # 3. 分隔线
        ttk.Separator(root, orient='horizontal').pack(fill='x', padx=8, pady=3)

        # 4. 游戏列表标题
        frame_list_header = tk.Frame(root, bg="white")
        frame_list_header.pack(fill=tk.X, padx=10, pady=(0, 3))

        tk.Label(frame_list_header, text="📋 游戏列表",
                bg="white", fg="#333", font=("Microsoft YaHei", 11, "bold")).pack(side=tk.LEFT, padx=3)

        self.lbl_game_count = tk.Label(frame_list_header, text="（共 0 个）",
                                       bg="white", fg="#666", font=("Microsoft YaHei", 9))
        self.lbl_game_count.pack(side=tk.LEFT, padx=5)

        # 5. 游戏列表区（带滚动条）
        list_container = tk.Frame(root, bg=self.COLOR_BG, padx=8, pady=3)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(list_container, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="white")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 6. 状态栏
        frame_status = tk.Frame(root, bg="#ecf0f1", height=28)
        frame_status.pack(fill=tk.X, side=tk.BOTTOM)
        frame_status.pack_propagate(False)

        self.status_var = tk.StringVar(value="就绪 - 请选择分类或输入关键词搜索")
        tk.Label(frame_status, textvariable=self.status_var, bg="#ecf0f1",
                fg="#555", font=("Microsoft YaHei", 8), anchor=tk.W).pack(fill=tk.X, padx=8)

        # 【关键】绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # 【新增】延迟执行首次自动搜索，确保界面完全初始化
        self.root.after(200, self.auto_search_on_startup)

    def auto_search_on_startup(self):
        """程序启动时自动执行搜索"""
        if not self.is_exiting:
            print("🚀 启动时自动执行搜索...")
            self.search_games()

    def on_closing(self):
        """处理窗口关闭事件"""
        print("🔄 正在关闭程序...")
        self.is_exiting = True
        try:
            self.session.close()
        except:
            pass
        self.root.destroy()
        sys.exit(0)

    def _on_canvas_resize(self, event):
        """当 canvas 大小改变时，同步更新 scrollable_frame 的宽度"""
        canvas_width = event.width
        if self.canvas.find_withtag("all"):
            self.canvas.itemconfig(self.canvas.find_withtag("all")[0], width=canvas_width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/100)), "units")

    def on_category_change(self):
        """切换分类时重置所有状态"""
        self.current_page = 1
        self.total_pages = None
        self.search_games()

    def on_sort_change(self):
        """切换排序时重置所有状态"""
        sort_text = self.sort_var.get()
        self.current_sort = self.sort_options.get(sort_text, "latest")
        self.current_page = 1
        self.total_pages = None
        self.search_games()

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.search_games()

    def next_page(self):
        if self.total_pages is None or self.current_page < self.total_pages:
            self.current_page += 1
            self.search_games()

    def jump_to_page(self):
        try:
            page = int(self.entry_jump.get())
            if self.total_pages is not None:
                if 1 <= page <= self.total_pages:
                    self.current_page = page
                    self.search_games()
                else:
                    messagebox.showwarning("警告", f"请输入 1-{self.total_pages} 之间的页码")
            else:
                if page > 0:
                    self.current_page = page
                    self.search_games()
        except ValueError:
            messagebox.showwarning("警告", "请输入有效的页码")

    def search_games(self, keyword=None):
        if keyword is not None:
            self.entry_keyword.delete(0, tk.END)
            self.entry_keyword.insert(0, keyword)

        self.current_keyword = self.entry_keyword.get().strip()
        self.current_category = self.categories.get(self.category_var.get(), "")

        self.status_var.set("正在搜索...")
        self.btn_prev.config(state=tk.DISABLED)
        self.btn_next.config(state=tk.DISABLED)
        self.game_details_cache.clear()
        self.loading_details.clear()

        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        thread = threading.Thread(target=self._do_search, args=())
        thread.daemon = True
        thread.start()

    def _build_url(self):
        params = []
        if self.current_category:
            base_path = f"/category/{self.current_category}"
        else:
            base_path = "/"

        if self.current_sort:
            params.append(f"sort={self.current_sort}")

        if self.current_keyword:
            params.append(f"keywords={self.current_keyword}")

        params.append(f"page={self.current_page}")

        if params:
            query_string = "&".join(params)
            url = f"{self.base_url}{base_path}?{query_string}"
        else:
            url = f"{self.base_url}{base_path}"

        return url

    def _do_search(self):
        try:
            if self.is_exiting:
                return

            url = self._build_url()
            print(f"🔍 请求 URL: {url}")

            resp = self.session.get(url, timeout=10)
            resp.encoding = 'utf-8'
            
            # 【新增】检测页面实际语言
            if 'charset=' in resp.headers.get('Content-Type', ''):
                print(f"📄 服务器声明的编码: {resp.headers['Content-Type']}")
            
            # 【调试】检查页面是否包含中文
            has_chinese = any('\u4e00' <= char <= '\u9fff' for char in resp.text[:1000])
            print(f"🔤 页面包含中文: {'是' if has_chinese else '否'}")
            
            soup = BeautifulSoup(resp.text, 'html.parser')

            games = soup.find_all('a', href=lambda href: href and href.startswith('/game/'))

            total_pages = self.extract_total_pages(soup)
            self.total_pages = total_pages

            if not games:
                self.root.after(0, lambda: self.status_var.set("未找到相关游戏"))
                self.root.after(0, lambda: self.update_ui([]))
                return

            # 提取游戏基本信息（包括图片URL）
            game_list = []
            for game in games:
                game_id = game['href'].split('/')[-1]

                # 提取图片URL：优先使用 data-src，其次使用 src
                img_tag = game.find('img')
                img_url = None
                if img_tag:
                    img_url = img_tag.get('data-src') or img_tag.get('src')

                game_list.append({
                    'name': game.get_text(strip=True),
                    'id': game_id,
                    'version': '加载中...',
                    'size': '加载中...',
                    'image_url': img_url
                })
            
            # 【调试】停止执行，查看输出
            if not game_list:
                self.root.after(0, lambda: self.status_var.set("未找到相关游戏"))
                self.root.after(0, lambda: self.update_ui([]))
                return

            self.root.after(0, lambda: self.update_ui(game_list))
            
            if total_pages is not None:
                sort_name = self.sort_var.get()
                category_name = self.category_var.get()
                self.root.after(0, lambda: self.status_var.set(
                    f"{category_name} | {sort_name} - 第 {self.current_page}/{total_pages} 页，找到 {len(game_list)} 个游戏"))
            else:
                sort_name = self.sort_var.get()
                category_name = self.category_var.get()
                self.root.after(0, lambda: self.status_var.set(
                    f"{category_name} | {sort_name} - 第 {self.current_page} 页，找到 {len(game_list)} 个游戏"))

            # 异步加载游戏详情和图片
            self.root.after(100, lambda: self.load_game_details_async(game_list))

        except Exception as e:
            if not self.is_exiting:
                self.root.after(0, lambda: self.status_var.set(f"搜索失败: {e}"))
                print(f"❌ 搜索异常: {e}")
        finally:
            if not self.is_exiting:
                self.root.after(0, lambda: self.update_page_buttons())

    def extract_total_pages(self, soup):
        """从 HTML 中提取总页数"""
        try:
            pagination = soup.find('div', class_='pagination')

            if pagination:
                page_info_link = pagination.find('a', string=lambda text: text and '/' in text)

                if page_info_link:
                    page_text = page_info_link.get_text(strip=True)

                    if '/' in page_text:
                        parts = page_text.split('/')
                        if len(parts) == 2:
                            total_pages = int(parts[1])
                            print(f"✅ 成功提取总页数: {total_pages} (从 '{page_text}')")
                            return total_pages

                page_links = pagination.find_all('a', class_='page_num')
                if page_links:
                    pages = []
                    for link in page_links:
                        text = link.get_text(strip=True)
                        try:
                            page_num = int(text)
                            pages.append(page_num)
                        except ValueError:
                            pass

                    if pages:
                        max_page = max(pages)
                        print(f"⚠️ 通过页码链接估算总页数: {max_page}")
                        return max_page

            print("⚠️ 无法提取页数，使用默认值 100")
            return 100

        except Exception as e:
            print(f"❌ 提取总页数失败: {e}")
            return 100

    def load_game_details_async(self, game_list):
        """后台异步加载游戏详情和图片"""
        def _load():
            for i, game in enumerate(game_list):
                if self.is_exiting:
                    print("⚠️ 检测到退出信号，停止加载游戏详情")
                    break

                if game['id'] in self.game_details_cache:
                    cached = self.game_details_cache[game['id']]
                    if not self.is_exiting:
                        self.root.after(0, lambda g=game, c=cached: self.update_game_info(g, c))
                    continue

                if game['id'] in self.loading_details:
                    continue

                self.loading_details.add(game['id'])

                try:
                    detail_url = f"{self.base_url}/game/{game['id']}"
                    print(f"📥 正在加载游戏详情: {game['name']} (ID: {game['id']})")
                    resp = self.session.get(detail_url, timeout=10)
                    resp.encoding = 'utf-8'
                    soup = BeautifulSoup(resp.text, 'html.parser')

                    # 【调试】打印页面标题，确认请求成功
                    title_tag = soup.find('title')
                    if title_tag:
                        print(f"✅ 页面标题: {title_tag.get_text(strip=True)}")

                    # 尝试多种方式查找游戏信息
                    version = 'N/A'
                    size = 'N/A'

                    # 方法1: 查找 class='game_info' 的 div
                    info_div = soup.find('div', class_='game_info')

                    # 方法2: 如果没找到，尝试其他可能的选择器
                    if not info_div:
                        info_div = soup.find('div', class_=lambda c: c and ('info' in c.lower() or 'detail' in c.lower()))

                    if info_div:
                        print(f"✅ 找到信息容器: {info_div.get('class')}")
                        lis = info_div.find_all('li')
                        print(f"   找到 {len(lis)} 个 li 标签")

                        for li in lis:
                            spans = li.find_all('span')
                            if len(spans) >= 2:
                                label = spans[0].get_text(strip=True)
                                value = spans[1].get_text(strip=True)
                                print(f"   - {label}: {value}")
                                if '版本' in label or 'Version' in label or 'version' in label.lower():
                                    version = value
                                elif '大小' in label or 'Size' in label or 'size' in label.lower() or '文件' in label:
                                    size = value
                    else:
                        print(f"⚠️ 未找到 game_info 容器，尝试其他方式...")
                        # 尝试从整个页面查找包含版本和大小的文本
                        all_text = soup.get_text()
                        if '版本' in all_text or 'Version' in all_text:
                            version = '需查看详情页'
                        if '大小' in all_text or 'Size' in all_text or 'GB' in all_text or 'MB' in all_text:
                            size = '需查看详情页'

                    detail = {'version': version, 'size': size}
                    self.game_details_cache[game['id']] = detail
                    print(f"💾 缓存游戏信息: {game['name']} - 版本:{version}, 大小:{size}")

                    if not self.is_exiting:
                        self.root.after(0, lambda g=game, d=detail: self.update_game_info(g, d))

                    # 如果列表页没有图片，从详情页获取
                    if not game.get('image_url'):
                        print(f"🖼️  尝试从详情页获取图片...")
                        img_tag = soup.find('img', class_=lambda c: c and ('cover' in c.lower() or 'banner' in c.lower() or 'thumb' in c.lower() or 'image' in c.lower()))

                        if not img_tag:
                            # 尝试查找第一个有意义的图片
                            img_tags = soup.find_all('img')
                            print(f"   找到 {len(img_tags)} 个图片标签")
                            for img in img_tags:
                                src = img.get('data-src') or img.get('src') or ''
                                if src and ('steam' in src.lower() or 'cdn' in src.lower() or 'http' in src):
                                    img_tag = img
                                    print(f"   ✅ 选中图片: {src[:50]}...")
                                    break

                        if img_tag:
                            img_url = img_tag.get('data-src') or img_tag.get('src')
                            if img_url:
                                print(f"📸 获取到图片URL: {img_url[:60]}...")
                                game['image_url'] = img_url
                                if not self.is_exiting:
                                    self.root.after(0, lambda g=game: self.load_and_display_image(g))
                        else:
                            print(f"⚠️ 未找到合适的图片")

                except Exception as e:
                    if not self.is_exiting:
                        print(f"❌ 加载 {game['name']} 详情失败: {e}")
                        import traceback
                        traceback.print_exc()
                    detail = {'version': '错误', 'size': '错误'}
                    self.game_details_cache[game['id']] = detail
                    if not self.is_exiting:
                        self.root.after(0, lambda g=game, d=detail: self.update_game_info(g, d))
                finally:
                    self.loading_details.discard(game['id'])

                time.sleep(0.3)

        thread = threading.Thread(target=_load)
        thread.daemon = True
        thread.start()

    def load_and_display_image(self, game):
        """异步加载并显示游戏图片"""
        if not game.get('image_url'):
            print(f"⚠️ 游戏 {game['name']} 没有图片URL")
            return

        print(f"🖼️  开始加载图片: {game['name']}")

        # 检查是否已缓存
        if game['id'] in self.image_cache:
            print(f"✅ 使用缓存图片: {game['name']}")
            photo = self.image_cache[game['id']]
            self.root.after(0, lambda: self.display_image(game['id'], photo))
            return

        try:
            img_url = game['image_url']
            if img_url.startswith('//'):
                img_url = 'https:' + img_url
            elif img_url.startswith('/'):
                img_url = self.base_url + img_url

            print(f"📥 下载图片: {img_url[:60]}...")
            
            # 【关键】禁用SSL警告和验证
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            resp = self.session.get(img_url, timeout=10, verify=False)

            if resp.status_code == 200:
                print(f"✅ 图片下载成功，大小: {len(resp.content)} bytes")
                img_data = BytesIO(resp.content)
                img = Image.open(img_data)
                print(f"📐 原始图片尺寸: {img.size}")

                # 调整图片大小为 80x120
                img = img.resize((80, 120), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                # 缓存图片
                self.image_cache[game['id']] = photo
                print(f"💾 图片已缓存: {game['name']}")

                # 更新UI
                self.root.after(0, lambda: self.display_image(game['id'], photo))
            else:
                print(f"❌ 图片下载失败，状态码: {resp.status_code}")
        except Exception as e:
            print(f"❌ 加载图片失败 {game['name']}: {e}")
            import traceback
            traceback.print_exc()

    def display_image(self, game_id, photo):
        """在UI中显示图片"""
        print(f"🎨 尝试显示图片，游戏ID: {game_id}")

        found = False
        for row_frame in self.scrollable_frame.winfo_children():
            if not isinstance(row_frame, tk.Frame):
                continue

            for card_frame in row_frame.winfo_children():
                if not hasattr(card_frame, 'game_id'):
                    continue

                if card_frame.game_id == game_id:
                    print(f"✅ 找到游戏卡片: {game_id}")
                    for child in card_frame.winfo_children():
                        if isinstance(child, tk.Frame):
                            for sub_child in child.winfo_children():
                                if isinstance(sub_child, tk.Frame):
                                    for label in sub_child.winfo_children():
                                        if isinstance(label, tk.Label) and hasattr(label, 'is_image_label'):
                                            print(f"🖼️  更新图片标签")
                                            label.config(image=photo)
                                            label.image = photo
                                            found = True
                                            return

        if not found:
            print(f"⚠️ 未找到游戏 {game_id} 的图片标签")

    def update_game_info(self, game, detail):
        """更新单个游戏的版本和大小显示"""
        print(f"🔄 尝试更新游戏信息: {game['name']} - 版本:{detail['version']}, 大小:{detail['size']}")
        
        found = False
        for row_frame in self.scrollable_frame.winfo_children():
            if not isinstance(row_frame, tk.Frame):
                continue

            for card_frame in row_frame.winfo_children():
                if not hasattr(card_frame, 'game_id'):
                    continue

                if card_frame.game_id == game['id']:
                    print(f"✅ 找到游戏卡片: {game['id']}")
                    # 遍历卡片中的所有子控件
                    for child in card_frame.winfo_children():
                        if isinstance(child, tk.Frame):
                            # child 是 content_frame，继续遍历其子控件
                            for sub_child in child.winfo_children():
                                if isinstance(sub_child, tk.Frame):
                                    # sub_child 可能是 image_frame 或 info_container
                                    # 需要再深入一层查找 info_frame
                                    for deep_child in sub_child.winfo_children():
                                        if isinstance(deep_child, tk.Frame):
                                            # deep_child 是 info_frame，查找其中的标签
                                            for label in deep_child.winfo_children():
                                                if isinstance(label, tk.Label):
                                                    text = label.cget('text')
                                                    if text.startswith('版本:'):
                                                        print(f"📝 更新版本: {detail['version']}")
                                                        label.config(text=f"版本: {detail['version']}")
                                                        found = True
                                                    elif text.startswith('大小:'):
                                                        print(f"📝 更新大小: {detail['size']}")
                                                        label.config(text=f"大小: {detail['size']}")
                                                        found = True
                    
                    if not found:
                        print(f"⚠️ 未找到版本/大小标签")
                    return
        
        print(f"⚠️ 未找到游戏卡片: {game['id']}")

    def update_ui(self, games):
        """更新界面显示"""
        self.update_page_info()
        self.render_list(games)
        self.lbl_game_count.config(text=f"（共 {len(games)} 个）")

    def update_page_info(self):
        """更新页码显示"""
        self.lbl_current_page.config(text=str(self.current_page))

        if self.total_pages is not None:
            self.lbl_total_pages.config(text=str(self.total_pages))
        else:
            self.lbl_total_pages.config(text="--")

        self.entry_jump.delete(0, tk.END)

    def update_page_buttons(self):
        """更新分页按钮状态"""
        if self.current_page > 1:
            self.btn_prev.config(state=tk.NORMAL)
        else:
            self.btn_prev.config(state=tk.DISABLED)

        if self.total_pages is not None:
            if self.current_page < self.total_pages:
                self.btn_next.config(state=tk.NORMAL)
            else:
                self.btn_next.config(state=tk.DISABLED)
        else:
            self.btn_next.config(state=tk.NORMAL)

    def render_list(self, games):
        """渲染游戏列表，每行显示两个游戏，严格均分行宽"""
        for i in range(0, len(games), 2):
            row_frame = tk.Frame(self.scrollable_frame, bg="white")
            row_frame.pack(fill=tk.X, padx=10, pady=3)
            
            # 【关键】只配置两列，每列权重相等（严格50%）
            row_frame.grid_columnconfigure(0, weight=1, uniform="game_column")
            row_frame.grid_columnconfigure(1, weight=1, uniform="game_column")
            row_frame.grid_rowconfigure(0, weight=1)

            game1 = games[i]
            self.create_game_item(row_frame, game1, column=0, is_last=(i + 1 >= len(games)))

            if i + 1 < len(games):
                game2 = games[i + 1]
                self.create_game_item(row_frame, game2, column=1, is_last=True)

    def create_game_item(self, parent, game, column, is_last=False):
        """创建单个游戏项卡片，图片在左侧，信息在右侧
        
        Args:
            parent: 父容器
            game: 游戏数据
            column: 列索引（0或1）
            is_last: 是否是该行最后一个卡片（用于添加右侧分隔线）
        """
        # 【关键】计算卡片边距，实现分隔线效果
        # 第一个卡片：右边有分隔线
        # 第二个卡片：右边无分隔线
        if column == 0 and not is_last:
            # 左侧卡片，右侧添加分隔线
            padx = (2, 7)  # 左2px，右7px（包含5px分隔线空间）
        else:
            # 右侧卡片或唯一卡片
            padx = (7, 2)  # 左7px（包含5px分隔线空间），右2px
        
        # 外层容器 - 使用 grid 布局，自动填充列宽
        card_frame = tk.Frame(parent, bg="white", relief=tk.RAISED, bd=1, height=140)
        card_frame.grid(row=0, column=column, sticky="nsew", padx=padx, pady=2)
        card_frame.grid_propagate(False)  # 高度固定，宽度跟随列宽

        # 保存 game_id 用于后续更新
        card_frame.game_id = game['id']

        # 主内容容器 - 水平布局
        content_frame = tk.Frame(card_frame, bg="white")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=8)

        # ===== 左侧：游戏图片区域 =====
        image_frame = tk.Frame(content_frame, bg="#f0f0f0", width=80, height=120)
        image_frame.pack(side=tk.LEFT, fill=tk.NONE, padx=(0, 10))
        image_frame.pack_propagate(False)

        # 图片占位标签
        placeholder_label = tk.Label(image_frame, bg="#e0e0e0", text="加载中...",
                                     fg="#999", font=("Microsoft YaHei", 7))
        placeholder_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        placeholder_label.is_image_label = True

        # 如果有图片URL，异步加载
        if game.get('image_url'):
            self.root.after(100, lambda g=game: self.load_and_display_image(g))

        # ===== 右侧：游戏信息区域 =====
        info_container = tk.Frame(content_frame, bg="white")
        info_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 游戏名称 - 动态调整换行宽度
        name_label = tk.Label(info_container, text=game['name'], bg="white", anchor="w",
                font=("Microsoft YaHei", 9, "bold"), fg="#2c3e50",
                wraplength=280, justify=tk.LEFT)
        name_label.pack(anchor="w", fill=tk.X)

        # 版本和大小信息
        info_frame = tk.Frame(info_container, bg="white")
        info_frame.pack(anchor="w", pady=(5, 0), fill=tk.X)

        lbl_version = tk.Label(info_frame, text=f"版本: {game['version']}", bg="white", fg="#888",
                font=("Microsoft YaHei", 8))
        lbl_version.pack(side=tk.LEFT, padx=(0, 15))

        lbl_size = tk.Label(info_frame, text=f"大小: {game['size']}", bg="white", fg="#888",
                font=("Microsoft YaHei", 8))
        lbl_size.pack(side=tk.LEFT)

        # 按钮区域 - 查看详情 + 下载
        btn_frame = tk.Frame(info_container, bg="white")
        btn_frame.pack(fill=tk.X, expand=True, pady=(5, 0))

        # 查看详情按钮
        btn_detail = tk.Button(btn_frame, text="查看",
                              command=lambda gid=game['id'], gname=game['name']: self.detail_window.show(gid, gname),
                              bg=self.COLOR_PRIMARY, fg="white", cursor="hand2", relief=tk.FLAT,
                              font=("Microsoft YaHei", 8, "bold"), padx=12, pady=3)
        btn_detail.pack(side=tk.RIGHT, padx=(0, 5))

        # 下载按钮
        btn_download = tk.Button(btn_frame, text="下载",
                       command=lambda gid=game['id'], gname=game['name']: self.download_game(gid, gname),
                       bg=self.COLOR_SUCCESS, fg="white", cursor="hand2", relief=tk.FLAT,
                       font=("Microsoft YaHei", 8, "bold"), padx=15, pady=3)
        btn_download.pack(side=tk.RIGHT)

        # 悬停效果 - 查看详情按钮
        def on_enter_detail(e, b=btn_detail):
            b.config(bg="#1976D2")
        def on_leave_detail(e, b=btn_detail):
            b.config(bg=self.COLOR_PRIMARY)
        btn_detail.bind("<Enter>", on_enter_detail)
        btn_detail.bind("<Leave>", on_leave_detail)

        # 悬停效果 - 下载按钮
        def on_enter_download(e, b=btn_download):
            b.config(bg="#45a049")
        def on_leave_download(e, b=btn_download):
            b.config(bg=self.COLOR_SUCCESS)
        btn_download.bind("<Enter>", on_enter_download)
        btn_download.bind("<Leave>", on_leave_download)

    def download_game(self, game_id, game_name):
        self.status_var.set(f"正在获取 [{game_name}] 的下载链接...")

        thread = threading.Thread(target=self._fetch_download_link, args=(game_id, game_name))
        thread.daemon = True
        thread.start()

    def _fetch_download_link(self, game_id, game_name):
        try:
            if self.is_exiting:
                return

            timestamp = str(int(time.time()))
            secret_key = "f6i6@m29r3fwi^yqd"
            message = f"{timestamp}{game_id}{secret_key}"
            sha256_hash = hashlib.sha256(message.encode('utf-8')).hexdigest()

            data = {
                "id": game_id,
                "timestamp": timestamp,
                "secretKey": sha256_hash,
                "canvasId": str(random.randint(100000000, 9999999999))
            }

            api_url = f"{self.base_url}/api/getGamesDownloadUrl"
            resp = self.session.post(api_url, data=data, timeout=10)

            if resp.status_code == 200:
                link = resp.text.strip().strip('"').strip()

                if link and ("http" in link or link.startswith("/")):
                    if link.startswith("/"):
                        link = self.base_url + link

                    self.root.after(0, lambda: webbrowser.open(link))
                    self.root.after(0, lambda: self.status_var.set("✅ 已成功打开下载页面"))
                else:
                    self.root.after(0, lambda: self.status_var.set(f"❌ 返回内容无效"))
            else:
                self.root.after(0, lambda: self.status_var.set(f"❌ API 错误: {resp.status_code}"))

        except Exception as e:
            if not self.is_exiting:
                self.root.after(0, lambda: self.status_var.set(f"❌ 请求异常: {e}"))

if __name__ == "__main__":
    root = tk.Tk()
    app = GameDownloaderApp(root)
    root.mainloop()
