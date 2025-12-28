<?php
/**
 * =========================================================
 *  NASTV · 系统维护与规范入口（UP.PHP · 终极封板版）
 * =========================================================
 *
 *  - 永久保留
 *  - 随 Docker 镜像发布
 *  - 后续不再修改
 *
 *  GitHub：https://github.com/isddcn/nastv
 */

session_start();

/* ================= 路径 ================= */

$ROOT = dirname(__DIR__);
$WEB  = __DIR__;
$DATA = $ROOT . '/data';
$LOGS = $ROOT . '/logs';
$ENVF = $ROOT . '/.env';
$ADMIN_DIR = $WEB . '/admin';

define('NASTV_VERSION', '1.0.0-final');
define('NASTV_BUILD', getenv('NASTV_BUILD_TIME') ?: 'unknown');

/* ================= 工具 ================= */

function h($s){ return htmlspecialchars((string)$s, ENT_QUOTES, 'UTF-8'); }

function load_env($file){
    $env=[];
    if(!is_file($file)) return $env;
    foreach(file($file, FILE_IGNORE_NEW_LINES|FILE_SKIP_EMPTY_LINES) as $l){
        if($l[0]==='#' || !str_contains($l,'=')) continue;
        [$k,$v]=explode('=',$l,2);
        $env[trim($k)] = trim($v);
    }
    return $env;
}

/* ================= 环境 ================= */

$env = load_env($ENVF);
$UP_PASSWORD = $env['UP_PASSWORD'] ?? '';
$APP_PORT = $env['APP_PORT'] ?? '19841';

if($UP_PASSWORD===''){
    http_response_code(500);
    exit('UP_PASSWORD 未设置');
}

/* ================= 登录 ================= */

if(($_POST['action']??'')==='login'){
    if(hash_equals($UP_PASSWORD, $_POST['password']??'')){
        $_SESSION['up_auth']=true;
        header('Location: up.php');exit;
    }else $error='密码错误';
}
if(isset($_GET['logout'])){
    session_destroy();header('Location: up.php');exit;
}
$authed = !empty($_SESSION['up_auth']);

/* ================= admin 上传 ================= */

$msg=null;
if($authed && ($_POST['action']??'')==='upload'){
    if(!isset($_FILES['pkg']) || !str_ends_with($_FILES['pkg']['name'],'.zip')){
        $msg='仅允许上传 admin.zip';
    }else{
        if(!is_dir($ADMIN_DIR)) mkdir($ADMIN_DIR,0755,true);
        foreach(glob($ADMIN_DIR.'/*') as $f){
            is_dir($f)?exec('rm -rf '.escapeshellarg($f)):@unlink($f);
        }
        $z=new ZipArchive();
        if($z->open($_FILES['pkg']['tmp_name'])===true){
            $z->extractTo($ADMIN_DIR);$z->close();
            $msg='admin 后台已部署';
        }else $msg='ZIP 解压失败';
    }
}

/* ================= 日志 ================= */

$log_type=$_GET['log']??'';
$log='';
if($authed && in_array($log_type,['app','scheduler'])){
    $f=$LOGS.'/'.$log_type.'.log';
    $log=is_file($f)?file_get_contents($f):'日志不存在';
}

/* ================= 状态 ================= */

$state=[
 'env'=>is_file($ENVF),
 'data'=>is_dir($DATA)&&is_readable($DATA),
 'logs'=>is_dir($LOGS)&&is_readable($LOGS),
 'db'=>is_file($DATA.'/stream_cache.db')
];
?>
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>NASTV · 系统维护</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{margin:0;font-family:system-ui;background:#f3f4f6}
header{background:#111827;color:#fff;padding:14px 20px;font-size:18px}
.container{max-width:1100px;margin:24px auto;padding:0 16px}
.card{background:#fff;border-radius:10px;padding:20px;margin-bottom:20px;box-shadow:0 4px 12px rgba(0,0,0,.06)}
h2{margin-top:0}
button{padding:10px 14px;background:#2563eb;color:#fff;border:none;border-radius:6px}
input[type=text],input[type=password]{width:100%;padding:10px}
pre{background:#0f172a;color:#e5e7eb;padding:16px;border-radius:8px;overflow:auto;font-size:13px;line-height:1.5}
.ok{color:#16a34a}.bad{color:#dc2626}
.note{font-size:13px;color:#555}
a{color:#2563eb;text-decoration:none}
</style>
</head>
<body>
<header>
NASTV · 系统维护入口
<?php if($authed):?><a href="?logout=1" style="float:right;color:#fff">退出</a><?php endif;?>
</header>

<div class="container">

<?php if(!$authed): ?>
<div class="card">
<h2>登录</h2>
<?php if(!empty($error)):?><p class="bad"><?=h($error)?></p><?php endif;?>
<form method="post">
<input type="hidden" name="action" value="login">
<input type="password" name="password" placeholder="UP_PASSWORD" required>
<br><br><button>登录</button>
</form>
</div>

<?php else: ?>

<div class="card">
<h2>系统状态</h2>
<ul>
<li>.env：<?= $state['env']?'<span class="ok">OK</span>':'<span class="bad">缺失</span>' ?></li>
<li>data：<?= $state['data']?'<span class="ok">OK</span>':'<span class="bad">不可读</span>' ?></li>
<li>logs：<?= $state['logs']?'<span class="ok">OK</span>':'<span class="bad">不可读</span>' ?></li>
<li>数据库：<?= $state['db']?'<span class="ok">OK</span>':'<span class="bad">缺失</span>' ?></li>
</ul>
<p>端口：<?=h($APP_PORT)?> ｜ 版本：<?=NASTV_VERSION?> ｜ Build：<?=h(NASTV_BUILD)?></p>
</div>

<div class="card">
<h2>解析 / 直播测试</h2>
<form onsubmit="return openTest();">
<input type="text" id="turl" placeholder="输入直播或视频网页地址" required><br><br>
<label><input type="checkbox" id="ts"> S 模式（缓存）</label><br>
<label><input type="checkbox" id="ttv"> TV 模式（播放页面）</label><br><br>
<button>打开测试页面</button>
</form>
<p class="note">
不勾选：仅输出流地址文本<br>
S：允许缓存 ｜ TV：播放页面 ｜ S+TV：缓存+播放
</p>
</div>

<script>
function openTest(){
  let u=document.getElementById('turl').value.trim();
  if(!u)return false;
  let q='url='+encodeURIComponent(u);
  if(document.getElementById('ts').checked) q+='&s=1';
  if(document.getElementById('ttv').checked) q+='&tv=1';
  window.open('http://'+location.host+'/parse?'+q,'_blank');
  return false;
}
</script>

<div class="card">
<h2>日志查看（只读）</h2>
<a href="?log=app">应用日志</a> |
<a href="?log=scheduler">调度器日志</a>
<?php if($log):?><pre><?=h($log)?></pre><?php endif;?>
</div>

<div class="card">
<h2>后台管理上传</h2>
<?php if($msg):?><p><?=h($msg)?></p><?php endif;?>
<form method="post" enctype="multipart/form-data">
<input type="hidden" name="action" value="upload">
<input type="file" name="pkg" accept=".zip" required>
<br><br><button>上传 admin.zip</button>
</form>
</div>

<div class="card">
<h2>📜 系统规则与调度规范（最终）</h2>
<pre>
/parse：默认仅返回流地址文本
s：允许缓存
tv：播放页面
s+tv：缓存 + 播放页面

缓存：
- 不设 TTL
- 刷新失败不得覆盖旧缓存

刷新调度器：
- 独立 Python 进程
- 不提供 Web 接口

刷新方式：
1. 定时刷新（每天固定时间）
2. 间隔刷新（基于 last_open_at）
3. 手动刷新（PHP 写请求时间）

刷新开关：
- 全局刷新开关
- 单频道刷新开关

PHP 后台：
- 仅写配置和时间
- 不执行刷新
- 不清缓存

scheduler：
- 判断是否刷新
- 执行刷新
- 写缓存
- 清理手动刷新请求

时间字段：
manual_refresh_at（PHP 写）
last_open_at（parse 写）
last_refresh_at（scheduler 写）

执行：
- 顺序
- 不并发
- 失败不中断

安全：
- up.php 建议仅内网访问
- 不随 admin 更新
</pre>
</div>

<?php endif;?>
</div>
</body>
</html>
