from astrbot.api.all import *
from astrbot.api.message_components import Node, Plain, Record
from astrbot.api.event.filter import *
import os
import tempfile, asyncio

@register("一个本地音乐点播插件", "syuchua", "music_sender", "1.0.0")
class MusicSenderPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        # 使用相对于容器的WAV文件目录
        self.music_dir = self.config.get("music_dir", "data/music_wav")
        # 确保使用容器内的完整路径
        self.container_music_dir = os.path.join("/AstrBot", self.music_dir)
        os.makedirs(self.container_music_dir, exist_ok=True)
        self.refresh_music_cache()
        
    def refresh_music_cache(self):
        """刷新音乐文件缓存"""
        files = [f for f in os.listdir(self.container_music_dir) 
                if f.endswith(('.mp3', '.wav', '.m4a'))]
        # 建立音乐名称到文件名的映射
        self.music_info = {
            os.path.splitext(f)[0].lower(): f 
            for f in files
        }

    @command_group("music")
    def music(self):
        pass

    def find_music(self, name: str) -> tuple[str, str]:
        """模糊匹配音乐文件
        
        Args:
            name: 要搜索的音乐名称
        Returns:
            tuple[str, str]: (匹配到的音乐文件完整路径, 匹配描述)
        """
        name = name.lower().strip()
        
        # 1. 直接包含匹配
        matches = []
        for song_name, file_name in self.music_info.items():
            # 清理歌名，去掉常见前缀
            clean_name = song_name
            for prefix in ["ai", "芙宁娜", "芙宁娜翻唱", "ai芙宁娜"]:
                if clean_name.startswith(prefix):
                    clean_name = clean_name[len(prefix):].strip("-_ ").lower()
                    break
            
            # 如果搜索词在清理后的歌名中，或歌名在搜索词中
            if name in clean_name or clean_name in name:
                matches.append((song_name, file_name))
                
        if matches:
            # 选择最短的匹配结果(通常是最相关的)
            best_match = min(matches, key=lambda x: len(x[0]))
            # 使用容器内的路径
            return (os.path.join(self.container_music_dir, best_match[1]), 
                    f"找到: {best_match[0]}")
        
        # 2. 关键词匹配 (比如搜"生花"能匹配到"一路生花")
        for song_name, file_name in self.music_info.items():
            parts = set(name.split())
            song_parts = set(song_name.lower().split("-_ "))
            if parts & song_parts:  # 如果有交集
                # 使用容器内的路径
                return (os.path.join(self.container_music_dir, file_name),
                        f"关键词匹配: {song_name}")
        
        return ("", "未找到匹配歌曲")

    @music.command("help")
    async def help(self, event: AstrMessageEvent):
        """获取帮助"""
        yield event.plain_result(
            "音乐点播插件帮助:\n"
            "/music help - 显示帮助\n"
            "/music list - 显示所有音乐\n"
            "/music play <歌名> - 点播音乐\n"
            "/music dir <路径> - 设置音乐目录(管理员)"
        )

    @music.command("list") 
    async def list_music(self, event: AstrMessageEvent):
        """列出所有音乐"""
        files = [f for f in os.listdir(self.container_music_dir) 
                if f.endswith(('.mp3', '.wav', '.m4a'))]
        
        if not files:
            yield event.plain_result("没有找到音乐文件")
            return
            
        msg = "音乐列表:\n"
        for i, music in enumerate(files, 1):
            msg += f"{i}. {os.path.splitext(music)[0]}\n"
        
        yield event.plain_result(msg.strip())


    @music.command("play")
    async def play_music(self, event: AstrMessageEvent, name: str):
        """播放指定音乐"""
        music_path, description = self.find_music(name)
        if not music_path:
            yield event.plain_result(f"未找到与 '{name}' 匹配的音乐")
            return
            
        try:
            logger.info(f"准备播放音乐: {music_path}")
            
            # 使用容器内的WAV文件路径
            yield event.chain_result([
                Plain(f"即将播放: {os.path.basename(music_path)}\n"),
                Record.fromFileSystem(music_path)
            ])
            
        except Exception as e:
            logger.error(f"播放失败: {e}", exc_info=True)
            yield event.plain_result(f"播放失败: {e}")

    @permission_type(PermissionType.ADMIN)
    @music.command("dir")
    async def set_dir(self, event: AstrMessageEvent, path: str):
        """设置音乐目录"""
        if not os.path.exists(path):
            yield event.plain_result("路径不存在")
            return
            
        self.config["music_dir"] = path
        self.music_dir = path
        # 更新目录后刷新缓存
        self.refresh_music_cache()
        yield event.plain_result(f"音乐目录已设置为: {path}")

    @llm_tool(name="play_music") 
    async def play_music_tool(self, event: AstrMessageEvent, request: object):
        '''当用户说"点歌xxx"或"我想听xxx"时调用此工具播放音乐
        
        Args:
            request(object): 包含歌曲名称的请求对象
                song_name(string): 歌曲名称
        '''
        song_name = request.get("song_name", "")
        if not song_name:
            yield event.plain_result("请指定要播放的歌曲名称")
            return
            
        music_path, description = self.find_music(song_name)
        if not music_path:
            yield event.plain_result(f"抱歉,未找到与 '{song_name}' 匹配的音乐")
            return
            
        try:
            yield event.chain_result([
                Plain(f"🎵 即将播放: {os.path.basename(music_path)}\n"),
                Record.fromFileSystem(music_path)
            ])
        except Exception as e:
            yield event.plain_result(f"播放失败: {e}")
