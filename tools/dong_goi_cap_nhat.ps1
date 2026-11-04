# =====================================================================
#  ĐÓNG GÓI BẢN MỚI + CẬP NHẬT D:\BQHungVideo  (tạo bởi Claude 26/10/2026)
#  Làm đúng các bước của bản phát hành chính thức (.github/workflows/release.yml):
#   1) Đóng gói bằng PyInstaller 6.22.2 (môi trường .venv-build có sẵn)
#   2) Tự kiểm bản .exe mới (--self-check) — hỏng thì DỪNG, không đụng bản cũ
#   3) Thay _internal + BQHungVideo.exe trong D:\BQHungVideo; bản cũ được cất
#      nguyên vào D:\BQHungVideo\.update-backup-claude-<giờ> (hoàn tác được)
#  KHÔNG đụng dữ liệu (kênh, video, key) — dữ liệu nằm ở %LOCALAPPDATA%\BQHungVideo
#  KHÔNG đụng _credentials, _cache, _repair... trong D:\BQHungVideo.
# =====================================================================
param([string]$Viec = '')
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Goc  = Split-Path -Parent $PSScriptRoot
$App  = 'D:\BQHungVideo'
$Py   = Join-Path $Goc '.venv-build\Scripts\python.exe'
$Lam  = Join-Path $Goc '_build_moi'

function Dang-Chay {
    try {
        Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'BQHungVideo.exe' -or
            ($_.ExecutablePath -and $_.ExecutablePath.StartsWith($Goc, [System.StringComparison]::OrdinalIgnoreCase))
        }
    } catch { @() }
}

function Dong-Goi-Va-Cap-Nhat {
    $d = @(Dang-Chay)
    if ($d.Count) {
        Write-Host '  App đang chạy. Tắt hẳn app rồi chạy lại file này.' -ForegroundColor Red
        $d | ForEach-Object { Write-Host ('    ' + $_.Name + ' (PID ' + $_.ProcessId + ')') }
        return
    }
    if (-not (Test-Path $Py)) { Write-Host '  Thiếu .venv-build — không đóng gói được.' -ForegroundColor Red; return }
    if (-not (Test-Path (Join-Path $App 'BQHungVideo.exe'))) { Write-Host "  Không thấy $App\BQHungVideo.exe" -ForegroundColor Red; return }

    # SỐ PHIÊN BẢN: mỗi lần cập nhật tại máy tăng số thứ 4 (2.50.60 -> 2.50.60.1
    # -> 2.50.60.2 ...). Dùng số thứ 4 để bản phát hành CHÍNH THỨC tiếp theo trên
    # GitHub (vd 2.50.61) vẫn được app nhận là MỚI HƠN và tự cập nhật như cũ.
    $vf = Join-Path $Goc 'app\version.py'
    $vgoc = [IO.File]::ReadAllText($vf)
    $mv = [regex]::Match($vgoc, '__version__ = "([0-9.]+)"')
    if (-not $mv.Success) { throw 'Không đọc được số phiên bản trong app\version.py' }
    $ps = [System.Collections.ArrayList]@($mv.Groups[1].Value.Split('.'))
    if ($ps.Count -ge 4) { $ps[3] = [string]([int]$ps[3] + 1) } else { [void]$ps.Add('1') }
    $vmoi = ($ps -join '.')
    [IO.File]::WriteAllText($vf, $vgoc.Replace($mv.Value, '__version__ = "' + $vmoi + '"'), (New-Object System.Text.UTF8Encoding $false))
    $script:VersionGoc = $vgoc; $script:VersionFile = $vf
    Write-Host ("  Phiên bản: " + $mv.Groups[1].Value + "  ->  " + $vmoi) -ForegroundColor Cyan

    Write-Host ''
    Write-Host '  [1/4] Đóng gói bản mới (mất khoảng 5-10 phút, cứ để chạy)...' -ForegroundColor Cyan
    if (Test-Path $Lam) { Remove-Item -LiteralPath $Lam -Recurse -Force }
    New-Item -ItemType Directory -Path $Lam | Out-Null
    Push-Location $Goc
    try {
        $a = @('-m','PyInstaller','--noconfirm','--windowed','--name','BQHungVideo',
               '--distpath', (Join-Path $Lam 'dist'), '--workpath', (Join-Path $Lam 'work'), '--specpath', $Lam,
               '--collect-all','PyQt6','--collect-submodules','app','--collect-all','google.generativeai','--collect-all','edge_tts',
               '--hidden-import','openai','--hidden-import','requests','--hidden-import','psutil','--hidden-import','dotenv',
               '--hidden-import','_nguon_song')
        # Thư viện chuẩn hay dùng: kèm sẵn để bản sửa sau (chạy thẳng mã nguồn)
        # dùng tới cũng không thiếu module.
        foreach ($m in @('difflib','statistics','fractions','decimal','csv','zipfile','tarfile','gzip','bz2','lzma',
                         'sqlite3','uuid','secrets','heapq','bisect','textwrap','unicodedata','shlex','glob','fnmatch',
                         'tempfile','shutil','urllib.request','urllib.parse','http.client','html','html.parser',
                         'xml.etree.ElementTree','concurrent.futures','queue','wave','colorsys','struct','zlib','base64',
                         'hashlib','hmac','ssl','email','calendar','locale','string','pprint','dataclasses','enum',
                         'functools','itertools','operator','copy','pickle','weakref','contextlib','traceback','inspect',
                         'ast','io','codecs','platform','ctypes','ctypes.wintypes','winreg','subprocess','signal',
                         'socket','asyncio','importlib.machinery','importlib.abc','importlib.util','mimetypes',
                         'webbrowser','random','math','cmath','array','collections','typing','threading','multiprocessing')) {
            $a += @('--hidden-import', $m)
        }
        foreach ($p in @(@('app\database\schema.sql','app/database'), @('app\assets\fonts','app/assets/fonts'),
                         @('app\assets\sfx','app/assets/sfx'), @('app\assets\music','app/assets/music'),
                         @('app\assets\hieu_ung','app/assets/hieu_ung'), @('app\core\potoken_plugins','app/core/potoken_plugins'),
                         @('.env.example','.'), @('LICENSES.txt','.'))) {
            $a += @('--add-data', ((Join-Path $Goc $p[0]) + ';' + $p[1]))
        }
        foreach ($b in @('ffmpeg.exe','ffprobe.exe','yt-dlp.exe')) { $a += @('--add-binary', ((Join-Path $Goc "bin\$b") + ';.')) }
        $a += (Join-Path $Goc 'main.py')
        & $Py @a
        if ($LASTEXITCODE -ne 0) { throw 'PyInstaller báo lỗi khi đóng gói.' }
    } finally { Pop-Location }
    $Moi = Join-Path $Lam 'dist\BQHungVideo'
    $int = Join-Path $Moi '_internal'
    Remove-Item -Recurse -Force (Join-Path $int 'googleapiclient\discovery_cache\documents') -EA SilentlyContinue
    Remove-Item -Recurse -Force (Join-Path $int 'PyQt6\Qt6\translations') -EA SilentlyContinue

    Write-Host '  [2/4] Tự kiểm bản mới...' -ForegroundColor Cyan
    $kd = Join-Path $Lam 'kiem'
    New-Item -ItemType Directory -Force $kd | Out-Null
    $env:BQ_DATA_DIR = $kd; $env:BQ_DB_PATH = (Join-Path $kd 'studio.db'); $env:BQ_QSETTINGS_INI = (Join-Path $kd 'settings.ini')
    $env:QT_QPA_PLATFORM = 'offscreen'; $env:BQ_BO_MANG = '1'
    $bc = Join-Path $kd 'result.json'
    $pr = Start-Process -FilePath (Join-Path $Moi 'BQHungVideo.exe') -ArgumentList '--self-check', ('"' + $bc + '"') -WindowStyle Hidden -PassThru -Wait
    foreach ($k in 'BQ_DATA_DIR','BQ_DB_PATH','BQ_QSETTINGS_INI','QT_QPA_PLATFORM','BQ_BO_MANG') { Remove-Item "Env:$k" -EA SilentlyContinue }
    if ($pr.ExitCode -ne 0 -or -not (Test-Path $bc)) { throw 'Bản mới TỰ KIỂM KHÔNG ĐẠT — đã dừng, bản cũ giữ nguyên.' }
    $kq = Get-Content -LiteralPath $bc -Raw | ConvertFrom-Json
    if (-not $kq.ok) { throw 'Bản mới tự kiểm báo lỗi — đã dừng, bản cũ giữ nguyên. Xem ' + $bc }

    $script:VersionGoc = $null      # bản mới đã đạt -> giữ số phiên bản mới
    Write-Host '  [3/4] Cất bản cũ...' -ForegroundColor Cyan
    $gio = Get-Date -Format 'yyyyMMdd_HHmmss'
    $Cat = Join-Path $App ('.update-backup-claude-' + $gio)
    New-Item -ItemType Directory -Path $Cat | Out-Null
    Move-Item -LiteralPath (Join-Path $App '_internal') -Destination (Join-Path $Cat '_internal')
    Move-Item -LiteralPath (Join-Path $App 'BQHungVideo.exe') -Destination (Join-Path $Cat 'BQHungVideo.exe')

    Write-Host '  [4/4] Chép bản mới vào D:\BQHungVideo...' -ForegroundColor Cyan
    try {
        Copy-Item -LiteralPath (Join-Path $Moi '_internal') -Destination (Join-Path $App '_internal') -Recurse
        Copy-Item -LiteralPath (Join-Path $Moi 'BQHungVideo.exe') -Destination (Join-Path $App 'BQHungVideo.exe')
    } catch {
        Write-Host '  Chép lỗi — đang trả bản cũ về...' -ForegroundColor Yellow
        Remove-Item -LiteralPath (Join-Path $App '_internal') -Recurse -Force -EA SilentlyContinue
        Remove-Item -LiteralPath (Join-Path $App 'BQHungVideo.exe') -Force -EA SilentlyContinue
        Move-Item -LiteralPath (Join-Path $Cat '_internal') -Destination (Join-Path $App '_internal')
        Move-Item -LiteralPath (Join-Path $Cat 'BQHungVideo.exe') -Destination (Join-Path $App 'BQHungVideo.exe')
        throw
    }
    # CHẠY THẲNG MÃ NGUỒN (27/10/2026): bản .exe đọc file này để nạp app\ +
    # config.py từ thư mục dự án -> lần sửa sau chỉ cần MỞ LẠI APP, không đóng gói.
    [IO.File]::WriteAllText((Join-Path $App 'nguon_ma.txt'), $Goc, (New-Object System.Text.UTF8Encoding $false))
    Write-Host ''
    Write-Host ('  XONG — đã lên bản v' + $vmoi + '. Mở D:\BQHungVideo\BQHungVideo.exe như mọi khi.') -ForegroundColor Green
    Write-Host '  TỪ GIỜ: Claude sửa xong, chỉ cần MỞ LẠI APP là chạy bản mới (không phải chạy file này nữa).' -ForegroundColor Green
    Write-Host '  Góc dưới thanh bên sẽ ghi "bản sửa <ngày giờ>".'
    Write-Host ('  Bản cũ cất ở: ' + $Cat)
    Write-Host '  Có vấn đề: chạy lại file này, chọn 2 để trả bản cũ.'
}

function Tat-Nguon-Song {
    $f = Join-Path $App 'nguon_ma.txt'
    if (Test-Path $f) { Remove-Item -LiteralPath $f -Force; Write-Host '  Đã TẮT chạy thẳng mã nguồn — mở lại app sẽ dùng bản đóng gói.' -ForegroundColor Green }
    else { Write-Host '  Đang tắt sẵn rồi.' }
}

function Bat-Nguon-Song {
    [IO.File]::WriteAllText((Join-Path $App 'nguon_ma.txt'), $Goc, (New-Object System.Text.UTF8Encoding $false))
    Write-Host '  Đã BẬT chạy thẳng mã nguồn — mở lại app là dùng bản sửa mới nhất.' -ForegroundColor Green
}

function Tra-Ban-Cu {
    if (@(Dang-Chay).Count) { Write-Host '  Tắt app trước đã.' -ForegroundColor Red; return }
    $cat = Get-ChildItem -LiteralPath $App -Directory -Force -Filter '.update-backup-claude-*' | Sort-Object Name -Descending | Select-Object -First 1
    if (-not $cat) { Write-Host '  Không có bản cũ do công cụ này cất.'; return }
    $tam = Join-Path $App ('.ban-moi-bo-' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
    New-Item -ItemType Directory -Path $tam | Out-Null
    Move-Item -LiteralPath (Join-Path $App '_internal') -Destination (Join-Path $tam '_internal')
    Move-Item -LiteralPath (Join-Path $App 'BQHungVideo.exe') -Destination (Join-Path $tam 'BQHungVideo.exe')
    Move-Item -LiteralPath (Join-Path $cat.FullName '_internal') -Destination (Join-Path $App '_internal')
    Move-Item -LiteralPath (Join-Path $cat.FullName 'BQHungVideo.exe') -Destination (Join-Path $App 'BQHungVideo.exe')
    Remove-Item -LiteralPath $cat.FullName -Force -Recurse
    Write-Host '  Đã trả bản cũ về. Bản mới cất tạm ở ' $tam -ForegroundColor Green
}

if (-not $Viec) {
    Write-Host ''
    Write-Host '  CẬP NHẬT BQ HUNG VIDEO — chọn việc:'
    Write-Host '    1) Đóng gói bản mới và cập nhật D:\BQHungVideo'
    Write-Host '    2) Trả lại bản cũ'
    Write-Host '    3) Tắt chạy thẳng mã nguồn (dùng bản đóng gói)'
    Write-Host '    4) Bật lại chạy thẳng mã nguồn'
    $Viec = Read-Host '  Chọn 1/2/3/4'
}
try {
    switch ($Viec) { '1' { Dong-Goi-Va-Cap-Nhat } '2' { Tra-Ban-Cu } '3' { Tat-Nguon-Song } '4' { Bat-Nguon-Song } default { Write-Host '  Không làm gì.' } }
} catch {
    if ($script:VersionGoc) {          # đóng gói/tự kiểm hỏng -> trả số phiên bản cũ
        try { [IO.File]::WriteAllText($script:VersionFile, $script:VersionGoc, (New-Object System.Text.UTF8Encoding $false)) } catch { }
    }
    Write-Host ''
    Write-Host ('  LỖI: ' + $_.Exception.Message) -ForegroundColor Red
    Write-Host '  Chụp màn hình này gửi Claude.'
}
