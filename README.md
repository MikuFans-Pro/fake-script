# fake-script
一些模拟真实环境但无法执行写入操作的脚本，如模拟bash（甚至包含虚假的sudo）


## bash-fake.py
* 注意：存在未知的可退出脚本的BUG，暂未复现，原因不明 *
一个虚假的bash终端，部分命令会直接调用系统执行，比如echo，sudo
但是，任何写操作均无法正常操作。
如果你echo $PATH是可以输出的，但是如果 echo 123 > /tmp/test.txt ，则会权限拒绝（禁止重定向输出）

sudo 不带参数的情况下，是可以执行的，会直接执行系统的sudo，输出一个帮助文本。
sudo su是可以执行的，但不会传递给bash，而是脚本内部处理
sudo vi 是不可以执行的，会权限拒绝，即使是sudo su，进入了内建root，也是禁止vi等写操作的。

目前会直接执行命令的白名单：pwd / uname -a / sudo（不带参数） 
内建root的环境下可执行：exit，退出到非root用户之后，禁止执行exit（权限拒绝），但可以通过 exit --force来退出脚本。

cat 是没有权限的，避免输出文件内容。

以及更多的好玩的逻辑。

如果有BUG（如越权执行），请反馈issues。
