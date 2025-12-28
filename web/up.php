<?php
$UP_PASSWORD = getenv('UP_PASSWORD') ?: 'admin';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    if (($_POST['password'] ?? '') !== $UP_PASSWORD) {
        die('密码错误');
    }

    if (!empty($_FILES['upload'])) {
        $base = __DIR__ . '/admin/';
        if (!is_dir($base)) mkdir($base, 0777, true);

        $name = basename($_FILES['upload']['name']);
        move_uploaded_file($_FILES['upload']['tmp_name'], $base . $name);
        echo "上传成功：{$name}";
        exit;
    }
}
?>
<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>NASTV 管理上传</title>
<style>
body{font-family:sans-serif;background:#f5f5f5}
.box{max-width:720px;margin:40px auto;background:#fff;padding:24px;border-radius:10px}
h1{margin-top:0}
input,button{padding:8px}
.rule{background:#fafafa;border-left:4px solid #4caf50;padding:12px;margin:16px 0}
</style>
</head>
<body>
<div class="box">
<h1>NASTV 管理 / 上传</h1>

<form method="post" enctype="multipart/form-data">
<div>管理密码：</div>
<input type="password" name="password" required><br><br>

<div>上传后台文件（zip / php / 任意）：</div>
<input type="file" name="upload" required><br><br>

<button>上传</button>
</form>

<hr>

<h2>解析测试</h2>
<form target="_blank" action="/parse">
<input type="text" name="url" style="width:100%" placeholder="输入直播网页地址">
<label><input type="checkbox" name="s" checked> S 模式（缓存）</label>
<label><input type="checkbox" name="tv" checked> TV 模式</label>
<button>测试</button>
</form>

<hr>

<h2>刷新规则说明（重要）</h2>

<div class="rule">
<p>本系统支持 <b>自动刷新缓存</b>，由 scheduler.py 独立进程执行。</p>
<ul>
<li>是否开启刷新：system_settings.refresh_enabled</li>
<li>单频道是否刷新：refresh_rules.enabled</li>
<li>刷新间隔：interval_hours（小时）</li>
<li>最后刷新时间：last_refresh</li>
</ul>
<p>刷新方式为后台自动调用：</p>
<pre>/parse?url=XXX&s</pre>
<p>不会输出页面，仅更新缓存。</p>
</div>

<p>项目地址：<br>
<a href="https://github.com/isddcn/nastv" target="_blank">
https://github.com/isddcn/nastv
</a>
</p>
</div>
</body>
</html>
