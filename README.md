# zmz
自动将字幕组收藏更新同步下载至群晖nas

# 配置文件示例
{
	"zmz": {
		"account": "",
		"password": "",
		"resolution":"MP4,720P,1080P,HDTV,RMVB"
	},
	"nas": {
		"url": "https://ip:5001",
		"account": "",
		"passwd": ""
	}
}
# zmz节点
配置字幕组的用户名和密码以及下载片源的优先级

# nas节点
配置群晖nas的用户名、密码及http地址

#部署方法
我是直接在群晖上部署的，方法如下：
#1、安装python3
在群晖套件中心直接安装Python3。然后SSH登录群晖切换到root用户，然后安装pip3
参考 http://sonavox.top/blog/index.php/DSM/24.html
#2、定时任务
在群晖的控制面板-》任务计划里新增一条。

首次运行传入--init=1 参数，默认已下载所有视频。如：python3 getzmz.py --init=1