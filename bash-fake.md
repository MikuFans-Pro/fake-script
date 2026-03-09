# FakeBash - 虚拟终端蜜罐

一个模拟真实 bash 终端的 Python 脚本，可用作蜜罐系统来监控和记录攻击者的行为。该终端看起来和真实的 bash 完全一样，但所有写操作都会被阻止，确保系统安全。

## 已知问题与警告

### ⚠️ 未知退出漏洞
存在一个**未知的可退出脚本的 BUG**，目前尚未复现，原因不明。请确保在受控环境中使用此脚本。

### ⚠️ 直接调用系统命令的风险
部分命令会直接调用系统执行，包括：
- `echo` - 可输出环境变量如 `$PATH`
- `sudo` - 在特定情况下会调用真实系统 sudo

---

## 功能特性

- **完整的终端模拟**：支持命令历史、自动补全、方向键导航等
- **权限控制**：支持普通用户和 root 权限切换（`sudo su`）
- **安全隔离**：所有写操作均被拦截，无法对系统造成实际影响
- **蜜罐模式**：攻击者无法退出脚本（除非知道暗码）

## 安装与使用

### 环境要求
- Python 3.x
- Linux 系统

### 启动方式

```bash
python3 bash.py
```

### 在 SSH 中使用作为蜜罐

将用户登录后的 shell 设置为运行此脚本：

```bash
# 在 /etc/passwd 中修改用户的 shell
user:x:1000:1000:User:/home/user:/usr/bin/python3 /path/to/bash.py
```

或在 `.bashrc` 中添加：
```bash
/usr/bin/python3 /path/to/bash.py
```

## 命令白名单

以下命令在脚本中被识别并可以执行（具体行为受权限限制）：

### 只读命令（普通用户可执行）
- `ls`, `ll` - 列出目录内容（需要 root 权限）
- `cd` - 切换目录
- `pwd` - 显示当前路径
- `cat`, `less`, `more`, `head`, `tail` - 查看文件内容
- `grep`, `find` - 搜索文件和内容
- `ps`, `top`, `htop` - 查看进程
- `df`, `du`, `free` - 系统资源查看
- `uname`, `whoami`, `id`, `groups` - 系统信息
- `w`, `who`, `date`, `cal`, `uptime`, `history`
- `echo` - 输出文本（禁止重定向）
- `man`, `help`, `which`, `whereis`, `type`, `file`, `stat`
- `wc`, `sort`, `uniq`, `cut`, `awk`, `sed`
- `clear` - 清屏

### 包管理器
- `apt`, `apt-get` - 仅支持 `search` 命令（非 root 权限）

## 命令黑名单

以下命令被识别但**永远不会真正执行**：

### 文件操作（写操作）
- `cp`, `mv`, `rm`, `mkdir`, `rmdir`, `touch`
- `chmod`, `chown`, `chgrp`

### 编辑器
- `vim`, `vi`, `nano`, `emacs`, `ed`

### 版本控制与构建
- `git`, `svn`, `hg`
- `make`, `cmake`, `gcc`, `g++`
- `python`, `python3`, `node`, `npm`, `pip`

### 包管理器（写操作）
- `apt install/remove/update/upgrade`
- `yum`, `dnf`, `pacman`, `snap`, `flatpak`

### 权限提升与用户管理
- `su`, `useradd`, `userdel`, `usermod`, `passwd`

### 系统管理
- `mount`, `umount`, `fdisk`, `mkfs`, `fsck`
- `systemctl`, `service`, `journalctl`

### 网络
- `tar`, `gzip`, `gunzip`, `zip`, `unzip`, `bzip2`, `xz`
- `ssh`, `scp`, `rsync`, `wget`, `curl`, `ping`, `traceroute`, `nslookup`, `dig`
- `ip`, `ifconfig`, `route`, `netstat`, `ss`

### 其他
- `ln`, `tee`, `xargs`, `watch`, `nohup`, `bg`, `fg`, `jobs`, `disown`
- `alias`, `unalias`, `export`, `unset`, `env`, `printenv`, `source`, `.`
- `kill`, `killall`, `pkill`, `pgrep`

## 安全机制

### 1. 重定向拦截
所有输出重定向操作都被禁止：
```bash
echo 123 > /tmp/test.txt  # 权限拒绝
echo "test" >> file.txt   # 权限拒绝
```

### 2. 写操作拒绝
任何可能修改系统文件的操作都会返回 `Permission denied`，即使在 `sudo su` 获得的伪 root 权限下也不例外。

### 3. 禁止退出
普通用户无法使用 `exit` 命令退出脚本：
```bash
$ exit
bash: exit: Permission denied
```

### 4. 强制退出机制（仅限管理员）
脚本内置了暗码机制，管理员可以使用以下命令退出：
```bash
exit --force
```

默认暗码为 `force`，可在脚本开头通过修改 `SECRET_CODE` 变量来自定义。

## 权限说明

### 普通用户模式
- 可以使用 `cd`, `pwd`, `whoami`, `uname -a` 等基本命令
- 可以使用 `echo` 输出文本，但**禁止重定向**
- `ls` 命令被阻止（需要 root 权限）
- 可以使用 `apt search` 搜索软件包
- 无法使用 `sudo` 获得写权限

### Root 用户模式（伪 root）
通过 `sudo su` 进入：
- 可以使用 `ls`, `ll` 查看文件
- 可以使用 `apt` 的只读命令（`show`, `list`, `policy`, `cache` 等）
- `whoami` 显示为 `root`
- **所有写操作仍然被阻止**

**重要限制**：虽然这些命令可以执行基本功能，但**任何写操作均无法正常操作**。例如：
```bash
$ echo $PATH          # ✓ 可以输出环境变量
/usr/local/bin:/usr/bin:/bin
$ echo 123 > /tmp/test.txt  # ✗ 权限拒绝（禁止重定向输出）
bash: echo: Permission denied
```

## 适用场景

1. **蜜罐系统**：监控攻击者行为，记录其命令
2. **沙箱环境**：允许用户探索系统但不造成破坏
3. **培训演示**：展示终端操作而不允许实际修改系统
4. **安全研究**：分析攻击者使用的工具和命令模式

## 注意事项

- 脚本只能在 Linux 系统上运行
- 所有命令执行仅限于脚本定义的范围内
- 不要在生产环境中使用此脚本保护真实系统
- 建议配合完整的日志记录系统使用
- 定期检查是否有新的安全漏洞

## 许可证

本项目仅供学习和研究使用，使用风险自负。
