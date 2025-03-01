from astrbot.api.all import *
from astrbot.api.message_components import Node, Plain, Record
from astrbot.api.event.filter import *
import os
from difflib import get_close_matches

@register("一个本地音乐点播插件", "syuchua", "music_sender", "1.0.0")
class MusicSenderPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        self.music_dir = self.config.get("music_dir", "data/music")
        os.makedirs(self.music_dir, exist_ok=True)
        
    @command_group("music")
    def music(self):
        pass

    def find_music(self, name: str) -> str:
        """模糊匹配音乐文件"""
        files = [f for f in os.listdir(self.music_dir) 
                if f.endswith(('.mp3', '.wav', '.m4a'))]
        # 将文件名转换为小写进行匹配
        name = name.lower()
        matches = get_close_matches(name, 
                                  [f.lower() for f in files], 
                                  n=1, 
                                  cutoff=0.6)
        if matches:
            # 找到最匹配的原始文件名
            orig_name = next(f for f in files 
                           if f.lower() == matches[0])
            return os.path.join(self.music_dir, orig_name)
        return ""

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
        files = [f for f in os.listdir(self.music_dir) 
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
        music_path = self.find_music(name)
        if not music_path:
            yield event.plain_result(f"未找到与 '{name}' 匹配的音乐")
            return
            
        try:
            yield event.chain_result([
                Plain(f"正在播放: {os.path.basename(music_path)}\n"),
                Record.fromFileSystem(music_path)
            ])
        except Exception as e:
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
            
        music_path = self.find_music(song_name)
        if not music_path:
            yield event.plain_result(f"抱歉,未找到与 '{song_name}' 匹配的音乐")
            return
            
        try:
            yield event.chain_result([
                Plain(f"🎵 正在播放: {os.path.basename(music_path)}\n"),
                Record.fromFileSystem(music_path)
            ])
        except Exception as e:
            yield event.plain_result(f"播放失败: {e}")
