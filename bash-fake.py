#!/usr/bin/env python3

# 可以当作蜜罐来使用，比如：ssh登录之后直接启动此脚本，除非执行暗码突出，否则全部操作都是脚本限定范围内的
# 这里定义暗码 使用 exit --SECRET_CODE 来退出
SECRET_CODE = "force"

import os
import subprocess
import getpass
import readline
import atexit
import platform

class FakeBash:
    # 定义常见命令列表（只读命令）
    READ_ONLY_COMMANDS = {
        'ls', 'll', 'cd', 'pwd', 'cat', 'less', 'more', 'head', 'tail', 'grep', 'find',
        'ps', 'top', 'htop', 'df', 'du', 'free', 'uname', 'whoami', 'id', 'groups',
        'w', 'who', 'date', 'cal', 'uptime', 'history', 'echo', 'printf', 'sleep',
        'man', 'help', 'which', 'whereis', 'type', 'file', 'stat', 'wc', 'sort',
        'uniq', 'cut', 'awk', 'sed'
    }
    
    # 定义写操作命令（这些命令在非root状态下总是返回权限拒绝）
    WRITE_COMMANDS = {
        'cp', 'mv', 'rm', 'mkdir', 'rmdir', 'touch', 'chmod', 'chown', 'chgrp',
        'vim', 'vi', 'nano', 'emacs', 'ed',
        'git', 'svn', 'hg',
        'make', 'cmake', 'gcc', 'g++', 'python', 'python3', 'node', 'npm', 'pip',
        'apt', 'apt-get', 'yum', 'dnf', 'pacman', 'snap', 'flatpak',
        'sudo', 'su', 'useradd', 'userdel', 'usermod', 'passwd',
        'mount', 'umount', 'fdisk', 'mkfs', 'fsck',
        'systemctl', 'service', 'journalctl',
        'tar', 'gzip', 'gunzip', 'zip', 'unzip', 'bzip2', 'xz',
        'ssh', 'scp', 'rsync', 'wget', 'curl', 'ping', 'traceroute', 'nslookup', 'dig',
        'ip', 'ifconfig', 'route', 'netstat', 'ss',
        'ln', 'tee', 'xargs', 'watch', 'nohup', 'bg', 'fg', 'jobs', 'disown',
        'alias', 'unalias', 'export', 'unset', 'env', 'printenv', 'source', '.',
        'kill', 'killall', 'pkill', 'pgrep'
    }
    
    # 所有已知命令（用于检查命令是否存在）
    KNOWN_COMMANDS = READ_ONLY_COMMANDS | WRITE_COMMANDS

    # Shell 命令（需要模拟真实bash行为，但仍需脚本过滤）
    SHELL_COMMANDS = {'bash', 'sh', 'zsh', 'dash'}
    
    def __init__(self):
        self.current_user = getpass.getuser()
        self.is_root = False
        self.hostname = self._get_hostname()
        self.current_dir = os.getcwd()
        self.home_dir = os.path.expanduser("~")
        self.shell_depth = 0  # shell 嵌套深度

        # 设置readline历史记录
        self.history_file = os.path.expanduser("~/.fake_bash_history")
        self._setup_readline()
        
    def _setup_readline(self):
        """配置readline支持方向键和快捷键"""
        # 加载历史记录
        try:
            readline.read_history_file(self.history_file)
        except FileNotFoundError:
            pass
        
        # 保存历史记录
        atexit.register(readline.write_history_file, self.history_file)
        
        # 设置自动补全
        readline.set_completer(self._completer)
        readline.parse_and_bind("tab: complete")
        
        # 启用vi模式（可选，默认是emacs模式）
        # readline.parse_and_bind("set editing-mode vi")
    
    def _completer(self, text, state):
        """命令和路径自动补全"""
        import glob

        # 获取当前输入行的完整内容
        try:
            buffer = readline.get_line_buffer()
            cursor_pos = readline.get_begidx()

            # 如果光标在第一个词的开头，或者前面没有空格，说明是在补全命令
            if not buffer or cursor_pos == 0 or not buffer[:cursor_pos].strip():
                # 补全命令
                options = [cmd for cmd in self.KNOWN_COMMANDS if cmd.startswith(text)]
                if state < len(options):
                    return options[state]
                return None

            # 否则尝试补全路径
            # 解析路径
            if text.startswith('/'):
                # 绝对路径
                pattern = text + '*'
            else:
                # 相对路径
                pattern = text + '*'

            # 获取匹配的文件/目录
            matches = glob.glob(pattern)
            # 只返回目录
            dirs = [m for m in matches if os.path.isdir(m)]

            if state < len(dirs):
                return dirs[state]
            return None

        except Exception:
            # 如果出错，回退到命令补全
            options = [cmd for cmd in self.KNOWN_COMMANDS if cmd.startswith(text)]
            if state < len(options):
                return options[state]
            return None
        
    def _get_hostname(self):
        """获取主机名"""
        import platform
        return platform.node().split('.')[0]
    
    def _get_short_path(self):
        """获取简短路径显示，home目录显示为~"""
        if self.current_dir.startswith(self.home_dir):
            return "~" + self.current_dir[len(self.home_dir):]
        return self.current_dir
    
    def _get_short_path(self):
        """获取简短路径显示，home目录显示为~"""
        if self.current_dir.startswith(self.home_dir):
            return "~" + self.current_dir[len(self.home_dir):]
        return self.current_dir

    def _get_short_path_title(self):
        """获取简短路径显示用于标题，如果是home目录则显示~"""
        if self.current_dir == self.home_dir:
            return "~"
        if self.current_dir.startswith(self.home_dir):
            return "~" + self.current_dir[len(self.home_dir):]
        return self.current_dir

    def _set_terminal_title(self):
        """设置终端窗口标题"""
        path = self._get_short_path_title()
        # 使用OSC序列同时设置窗口标题和图标标题
        print(f"\033]2;{path}:bash\007\033]1;{path}\007", end="", flush=True)

    def _get_prompt(self):
        """生成提示符（检测是否为GUI环境）"""
        # 检测是否为GUI环境
        self.is_gui = self._check_gui()

        # ANSI颜色代码
        GREEN = "\033[32m"
        BLUE = "\033[34m"
        WHITE = "\033[0m"
        RED = "\033[31m"

        if self.is_root:
            # root用户: root@hostname:/path#
            user_info = f"root"
            path_info = self._get_short_path()
            if self.is_gui:
                return f"{WHITE}{user_info}@{self.hostname}:{path_info}#{WHITE} "
            else:
                return f"{user_info}@{self.hostname}:{path_info}# "
        else:
            # 普通用户: user@hostname:~/path$
            user_info = f"{self.current_user}"
            path_info = self._get_short_path()
            if self.is_gui:
                return f"{GREEN}{user_info}@{self.hostname}{WHITE}:{BLUE}{path_info}{WHITE}${WHITE} "
            else:
                return f"{user_info}@{self.hostname}:{path_info}$ "

    def _check_gui(self):
        """检测是否为GUI环境"""
        # 检查是否存在DISPLAY环境变量
        if os.environ.get('DISPLAY'):
            return True
        # 检查TERM是否为纯终端
        term = os.environ.get('TERM', '')
        if 'linux' in term or 'dumb' in term or term == '':
            return False
        # 检查是否在虚拟终端中
        if os.environ.get('XDG_SESSION_TYPE') == 'tty':
            return False
        # 默认认为是GUI
        return True
    
    def _execute_bash_command(self, command):
        """直接调用系统bash执行命令"""
        try:
            # 只允许ls、grep、echo通过管道执行，以及apt/apt-get search
            allowed_commands = ['ls', 'grep', 'echo', 'apt', 'apt-get']
            first_cmd = command.split('|')[0].strip().split()[0] if '|' in command else command.strip().split()[0]

            if first_cmd in allowed_commands:
                # 使用 Popen 执行命令
                process = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate()
                return stdout + stderr
            else:
                return f"bash: {command}: Permission denied"
        except Exception as e:
            return str(e)

    def _apt(self, apt_cmd, args):
        """处理apt/apt-get命令"""
        args_list = args.split() if args else []

        # 如果不是root，除了search都不允许
        if not self.is_root:
            # 检查是否是search命令
            if 'search' in args_list:
                cmd = f"{apt_cmd} {args}"
                return self._execute_bash_command(cmd).rstrip()
            else:
                return "E: Unable to acquire the admin directory (are you root?)"

        # 如果是root，直接调用系统apt（允许所有操作）
        if not args_list or not args_list[0]:
            # apt 不带参数，直接调用系统apt
            try:
                process = subprocess.Popen(
                    apt_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = process.communicate()
                return (stdout + stderr).rstrip()
            except Exception as e:
                return str(e)

        # root带参数：检查是否是允许的只读操作
        allowed_read_only = ['search', 'show', 'list', 'policy', 'cache', 'depends', 'rdepends']
        if args_list[0] in allowed_read_only:
            cmd = f"{apt_cmd} {args}"
            return self._execute_bash_command(cmd).rstrip()
        else:
            # 其他写操作命令不允许
            forbidden = ['install', 'remove', 'update', 'upgrade', 'purge', 'autoremove', 'dist-upgrade', 'full-upgrade']
            for forbidden_cmd in forbidden:
                if forbidden_cmd in args_list:
                    return self._permission_denied(f"{apt_cmd} {forbidden_cmd}")
            return self._permission_denied(f"{apt_cmd} {args_list[0] if args_list else ''}")
    
    def _cd(self, path=""):
        """实现cd命令"""
        if path == "":
            # 没有参数，切换到home目录
            path = os.path.expanduser("~")

        try:
            os.chdir(path)
            self.current_dir = os.getcwd()
            # 更新终端标题
            self._set_terminal_title()
            return ""
        except FileNotFoundError:
            return f"cd: {path}: No such file or directory"
        except PermissionError:
            return f"cd: {path}: Permission denied"
        except Exception as e:
            return f"cd: {path}: {str(e)}"
    
    def _ls(self, args):
        """实现ls命令（直接调用系统ls）"""
        try:
            if not self.is_root:
                return "ls: cannot access directory: Permission denied"

            # 直接调用系统ls命令
            cmd = f"ls {args}"
            return self._execute_bash_command(cmd).rstrip()
        except Exception as e:
            return str(e)

    def _whoami(self):
        """执行whoami命令（返回当前用户名）"""
        return self.current_user

    def _uname(self, args):
        """执行uname命令（返回模拟的系统信息）"""
        import platform
        if args == "-a":
            return f"{platform.system()} {platform.node()} {platform.release()} {platform.version()} {platform.machine()}"
        return platform.system()
    
    def _sudo_su(self):
        """执行sudo su切换到root"""
        self.is_root = True
        self.current_user = "root"
        return ""
    
    def _exit_root(self):
        """退出root状态"""
        self.is_root = False
        self.current_user = getpass.getuser()
        return ""
    
    def _permission_denied(self, command):
        """返回标准的权限拒绝信息"""
        return f"bash: {command}: Permission denied"

    def _execute_as_root(self, command):
        """以root权限执行命令（伪root）"""
        # 保存当前状态
        was_root = self.is_root

        # 临时设置为root
        self.is_root = True

        # 解析命令
        parts = command.split()
        cmd = parts[0]
        args = ' '.join(parts[1:]) if len(parts) > 1 else ""

        # 根据命令类型执行
        result = ""
        try:
            if cmd == "whoami":
                result = "root"
            elif cmd == "uname" and args == "-a":
                result = self._uname("-a")
            elif cmd == "cd":
                result = self._cd(args)
            elif cmd == "ls":
                result = self._ls(args)
            elif cmd == "ll":
                result = self._ls("-la")
            elif cmd == "pwd":
                result = self.current_dir
            elif cmd == "grep":
                result = self._execute_bash_command(command).rstrip()
            elif cmd == "apt" or cmd == "apt-get":
                result = self._apt(cmd, args)
            elif cmd == "echo":
                # 检查是否有重定向符号（输入或输出重定向）
                if '>' in command or '>>' in command or '<' in command:
                    result = self._permission_denied("echo")
                else:
                    result = self._execute_bash_command(command).rstrip()
            elif cmd == "clear":
                os.system('clear')
            else:
                # 其他命令直接执行
                if cmd in self.KNOWN_COMMANDS:
                    if cmd in self.WRITE_COMMANDS:
                        result = self._permission_denied(cmd)
                    else:
                        result = self._permission_denied(cmd)
                else:
                    result = self._command_not_found(cmd)
        finally:
            # 恢复之前的root状态
            self.is_root = was_root

        return result
    
    def _command_not_found(self, command):
        """返回命令不存在错误"""
        return f"{command}: command not found"

    def _handle_shell_command(self, shell_cmd, args):
        """
        处理 shell 命令（bash、sh等），模拟真实bash行为
        - bash (无参数): 进入子shell模式（增加shell_depth，显示新提示符）
        - bash <command>: 尝试将参数作为命令执行（仍然经过脚本过滤）
        """
        if not args or not args.strip():
            # bash 不带参数：进入子shell模式（不真正执行，只是增加深度标记）
            self.shell_depth += 1
            return ""
        else:
            # bash 带参数：尝试将参数作为命令执行（经过脚本过滤）
            # 例如：bash sudo -> 尝试执行 sudo 命令
            # 去除可能的 -c 等bash选项
            parts = args.split()
            if parts[0] == '-c' and len(parts) > 1:
                # bash -c "command" -> 执行 command
                inner_command = ' '.join(parts[1:])
                # 去除引号
                inner_command = inner_command.strip('"\'')
                return self.execute(inner_command)
            else:
                # bash command -> 执行 command
                return self.execute(args)
    
    def execute(self, command):
        """执行用户输入的命令"""
        command = command.strip()
        
        if not command:
            return ""
        
        # 解析命令
        parts = command.split()
        cmd = parts[0]
        args = ' '.join(parts[1:]) if len(parts) > 1 else ""

        # 处理 shell 命令（bash、sh等）
        if cmd in self.SHELL_COMMANDS:
            return self._handle_shell_command(cmd, args)

        # 处理 sudo su（必须在sudo处理之前）
        if command == "sudo su":
            return self._sudo_su()

        # 处理 sudo
        if cmd == "sudo":
            # 如果没有参数或参数为空，调用真实的系统sudo
            if not args or not args.strip():
                # 直接调用系统sudo
                try:
                    process = subprocess.Popen(
                        "sudo",
                        shell=True,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    stdout, stderr = process.communicate()
                    return (stdout + stderr).rstrip()
                except Exception as e:
                    return str(e)
            # 否则作为伪root执行命令
            return self._execute_as_root(args)
        
        # 处理 whoami（直接调用系统bash）
        if cmd == "whoami":
            return self._whoami()
        
        # 处理 uname -a（直接调用系统bash）
        if cmd == "uname" and args == "-a":
            return self._uname("-a")
        
        # 处理 cd
        if cmd == "cd":
            return self._cd(args)
        
        # 处理 ls
        if cmd == "ls":
            return self._ls(args)

        # 处理 ll（ls -la 的别名）
        if cmd == "ll":
            return self._ls("-la")

        # 处理 pwd
        if cmd == "pwd":
            return self.current_dir

        # 处理 grep（允许通过管道使用）
        if cmd == "grep":
            return self._execute_bash_command(command).rstrip()

        # 处理 apt（只允许search，其他需要root）
        if cmd == "apt" or cmd == "apt-get":
            return self._apt(cmd, args)

        # 处理 echo（允许执行，但禁止重定向）
        if cmd == "echo":
            # 检查是否有重定向符号（输入或输出重定向）
            if '>' in command or '>>' in command or '<' in command:
                return self._permission_denied("echo")
            # 非重定向时调用系统echo
            return self._execute_bash_command(command).rstrip()

        # 处理 clear
        if cmd == "clear":
            os.system('clear')
            return ""

        # 处理 exit --SECRET_CODE（强制退出脚本）
        if command == f"exit --{SECRET_CODE}":
            return "EXIT_FORCE"

        # 处理 exit
        if cmd == "exit":
            if self.shell_depth > 0:
                # 如果在子shell中，exit退出子shell
                self.shell_depth -= 1
                return ""
            elif self.is_root:
                # 如果是root状态，exit退出到普通用户
                return self._exit_root()
            else:
                # 普通用户状态，不允许退出
                return self._permission_denied("exit")
        
        # 检查是否是已知命令
        if cmd not in self.KNOWN_COMMANDS:
            return self._command_not_found(cmd)
        
        # 如果是写操作命令，检查权限
        if cmd in self.WRITE_COMMANDS:
            if not self.is_root:
                return self._permission_denied(cmd)
            # 即使是root也不真正执行写操作命令
            return self._permission_denied(cmd)

        # 其他所有命令都不真正执行，返回错误信息
        return self._permission_denied(cmd)
    
    def run(self):
        """启动伪bash终端"""
        # 检查是否为Linux环境
        if platform.system() != 'Linux':
            print("错误：此脚本需要Linux内核支持")
            return

        # 首先清屏
        os.system('clear')

        # 设置初始终端标题
        self._set_terminal_title()

        while True:
            try:
                # 处理多行命令（支持\续行）
                command_lines = []
                while True:
                    if not command_lines:
                        # 第一行显示提示符
                        prompt = self._get_prompt()
                    else:
                        # 续行显示空提示符
                        prompt = ""

                    user_input = input(prompt)

                    # 如果输入为空且不是续行，直接退出循环
                    if not user_input and not command_lines:
                        break

                    # 如果行尾有\，表示续行
                    if user_input.endswith('\\'):
                        command_lines.append(user_input[:-1])
                        continue
                    else:
                        command_lines.append(user_input)
                        break

                # 如果输入为空，跳过
                if not command_lines or not command_lines[0].strip():
                    continue

                # 合并多行命令
                command = ' '.join(command_lines)

                # 执行命令
                result = self.execute(command)

                # 如果返回EXIT_FORCE，退出脚本
                if result == "EXIT_FORCE":
                    break

                # 显示结果
                if result:
                    print(result)

            except KeyboardInterrupt:
                # Ctrl+C 不退出，只换行显示新提示符
                print()
                continue
            except EOFError:
                print()
                continue
            except Exception as e:
                print(f"Error: {e}")

if __name__ == "__main__":
    terminal = FakeBash()
    terminal.run()
