# EXviewer

E站的PWA客户端，于在线浏览，下载以及管理本地画廊。基于React与MaterialUI构建

[在线演示](https://driverlin.github.io/EXviewer/demo/)


## 截图

<div style="display: flex;">
<img src="https://raw.githubusercontent.com/DriverLin/EXviewer/master/Screenshot/IMG_0006.jpg" width="30%" title="home"/>
<img src="https://raw.githubusercontent.com/DriverLin/EXviewer/master/Screenshot/IMG_0012.jpg" width="30%" title="home" />
<img src="https://raw.githubusercontent.com/DriverLin/EXviewer/master/Screenshot/IMG_0007.jpg" width="30%" title="home" />
</div>
<div style="display: flex;">
<img src="https://raw.githubusercontent.com/DriverLin/EXviewer/master/Screenshot/Screenshot_20220613-210439.jpg" width="30%" title="home" />
<img src="https://raw.githubusercontent.com/DriverLin/EXviewer/master/Screenshot/Screenshot_20220613-210111.jpg" width="30%" title="detail"/>
<img src="https://raw.githubusercontent.com/DriverLin/EXviewer/master/Screenshot/Screenshot_20220613-210501.jpg" width="30%" title="detail"/>
</div>

## Docker 运行
```
docker run -d --name=exviewer --restart=unless-stopped \
-p 7964:7964 \
-v <下载路径>:/Download \
-e EH_COOKIE='<cookie字符串>' \
driverlin/exviewer:latest 
```
可选的配置项
```
-v <缓存路径>:/cache \
-e HTTP_PROXY=http://127.0.0.1:4780 \
-e EH_FAVORITE_DISABLED=true \
-e EH_DOWNLOAD_DISABLED=true \
-e EH_COMMENT_DISABLED=true \
-e EH_RATE_DISABLED=true \
-e UTC_OFFSET=8 \
```
## 本地部署

```
git clone https://github.com/DriverLin/EXviewer
cd EXviewer
pip install -r requirements.txt
```
修改server/config.json，填写cookie
```
{
    "EH_COOKIE": "ipb_member_id=***; ipb_pass_hash=***; igneous=***; sl=dm_1; sk=***; s=***"
}
```
运行
```
python server 
```

## 部署到Heroku
使用Heroku托管运行

[![Deploy](https://www.herokucdn.com/deploy/button.png)](https://dashboard.heroku.com/new?template=https://github.com/DriverLin/EXviewer) 

## 使用termux在安卓手机上运行

由于termux采用滚动更新方式，只能安装最新版本的python导致可能无法适配requirements.txt内的依赖

可先安装环境，再直接使用打包版本[exviewer-termux-aarch64](https://github.com/DriverLin/EXviewer/releases/latest/download/exviewer-termux-aarch64)
```
termux-change-repo
pkg update && pkg upgrade -y
pkg install libxslt python
curl -LJo exviewer https://github.com/DriverLin/EXviewer/releases/latest/download/exviewer-termux-aarch64 
chmod 777 ./exviewer
./exviewer
```

或者尝试手动安装requirements.txt内的依赖并根据提示报错进行相应处理


## 代理
程序会依次检测环境变量 HTTPS_PROXY,HTTP_PROXY,https_proxy,http_proxy 以使用http代理

## 环境变量

使用环境变量来指定相关配置

如果指定了环境变量 则会忽略配置文件中的项

EH_COOKIE : cookie字符串

EH_DOWNLOAD_PATH : 下载路径

EH_CACHE_PATH : 缓存路径

PORT : 端口

## 设置项

### 收藏夹
暂无在收藏时选择收藏夹功能

在这里设置默认收藏夹 

### 自定义筛选器
使用jsonpath筛选主页，相比较于watch能实现更多的自定义功能

例如 
```
$[?(
    ( 
        @.lang == "chinese"  
        || (
            (
                @.category == "Artist CG"
                || @.category == "Image Set"
                || @.category == "Cosplay"
            ) 
            && @.rank >= 4
        )
    ) 
    && @.category != "Misc"
    && @.tags.indexOf("male:males only") == -1
    && @.tags.indexOf("male:yaoi") == -1
)]
```

当需要搜索tag时，主页需要为compact或者extended

### 快捷导出格式

可快速将当前画廊导出为便于分享的格式

zip 导出为压缩包

jpg 导出长图，但是图片过大会导出失败

pdf 导出为pdf文档





## 致谢

- UI参考 [seven332/EhViewer](https://github.com/seven332/EhViewer)
- tag翻译数据 [EhTagTranslation](https://github.com/EhTagTranslation/Database)

