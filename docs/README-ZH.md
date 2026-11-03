# Make A Fire In Forest

[English](../README.md) | 简体中文

一个供休闲放松、满足好奇心的桌面小游戏：选择一座城市，加载周边地形，在森林中点燃一簇火，观察它在当地天气影响下蔓延。

游戏将真实土地覆盖数据与简单的网格火势模拟结合起来。风影响传播方向，雨雪抑制燃烧，动态天气特效则让地图更生动。

> 本项目仅用于娱乐，不用于预测真实森林火灾，也不应作为消防安全决策依据。

## 功能介绍

- **位置选择：** 自动通过 IP 定位，或手动搜索城市。
- **当地地形：** 基于 ESA WorldCover 2021 数据生成森林、水体、建成区和其他地面。
- **可调地图范围：** 支持 5 × 5、10 × 10、20 × 20 和 40 × 40 km。
- **交互式点火：** 点击或拖动点燃森林，支持暂停、调速和地图重置。
- **天气影响传播：** 顺风加快传播，逆风减缓传播，雨雪显著抑制火势。
- **地图标识：** 左上角显示风向和风速，右上角显示 N/E/S/W 方位罗盘。
- **动态降水：** 支持雨、雪及雨雪混合特效，提供 Off / Light / Full 三档。
- **燃烧统计：** 显示过火格子数，以及以公顷和平方公里表示的估算面积。
- **PNG 导出：** 保存地图、天气、方位标识和燃烧统计。

## 快速开始

### 运行打包好的 Windows 版本

如果已经获得打包版本：

1. 如果下载的是压缩包，先解压。
2. 双击 `MakeAFireInForest.exe`。
3. 等待定位和地形加载，或手动搜索城市。

对于文件夹形式的打包版本，请保持可执行文件与配套的 `_internal` 文件夹在一起。正确打包后，运行该程序的电脑无需安装 Python。

程序需要联网获取位置、天气和地形数据。打包版本不包含全球地图，也不提供离线天气服务。

### 从源码运行

建议使用 Python 3.12 作为开发和打包环境。程序需要图形桌面、Tkinter，以及 `requirements.txt` 中列出的依赖：

- NumPy
- Rasterio
- Pillow

以下命令均在项目根目录执行。

**Windows — PowerShell**

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/main.py
```

**Linux**

```bash
python3 -m venv proj_env
./proj_env/bin/python -m pip install --upgrade pip
./proj_env/bin/python -m pip install -r requirements.txt
./proj_env/bin/python src/main.py
```

如果已有 `proj_env`，可以直接复用。在 Linux 上，可能需要通过发行版的软件包管理器单独安装 Tkinter，例如 Debian 或 Ubuntu 上的 `python3-tk`。

**项目也提供可执行程序包，请查看 Release 发布版本。**

## 游戏玩法

1. 打开 **Location & Weather（位置与天气）**。等待自动定位完成，或输入城市名称，点击 **Search（搜索）**，选中结果后点击 **Use Selected City（使用所选城市）**。
2. 等待地形地图出现。加载失败时，可点击 **Reload Terrain Map（重新加载地形地图）** 重试。
3. 在绿色森林格子上点击或拖动，点燃森林。
4. 观察火势蔓延。使用速度滑块调整播放速度，也可以暂停观察。
5. 点击 **Reset Map（重置地图）**，恢复原始地形并清除火灾损伤。

在 **Forest Settings → Map area（森林设置 → 地图范围）** 中选择不同的地理范围，默认为 10 × 10 km。

更换城市或重新加载地形会开始新场景，并清除已有火焰。**Refresh Weather（刷新天气）** 仅更新天气，不会重置地形。地形加载中或不可用时，游戏不会用随机生成的地图替代。

### 操作方式

| 操作 | 控制方式 |
| --- | --- |
| 点燃森林 | 在绿色格子上单击鼠标左键或拖动 |
| 暂停／继续 | 空格键或 Pause / Resume 按钮 |
| 恢复地形 | R 键或 Reset Map |
| 调整模拟速度 | Simulation speed 滑块 |
| 调整地图范围 | Map area 选择框 |
| 调整天气特效 | Rain / snow effects 选择框 |
| 导出图片 | Save Screenshot |

在城市搜索框或其他文本输入控件中输入内容时，不会触发快捷键。模拟暂停期间仍可以放置点火位置。

### 地图图例

| 颜色 | 含义 | 是否可燃 |
| --- | --- | --- |
| 绿色 | 森林 | 是 |
| 黄褐色 | 其他地面 | 否 |
| 蓝色 | 永久水体 | 否 |
| 银色 | 建成区 | 否 |
| 橙色／黄色 | 正在燃烧的森林 | 已在燃烧 |
| 深灰色 | 灰烬／被火烧毁的森林 | 否 |
| 蓝灰色 | 数据缺失或未知地形 | 否 |

地图上方为北，右方为东。风向箭头表示**风吹向的方向**：北风在地图上指向南方。

## 天气与火势传播

每个模拟步中，燃烧格子尝试点燃周围八个相邻森林格子。新点燃的格子从下一个模拟步开始传播。

### 风

无风、无降水时，对每个相邻森林格子的点燃概率为**每次尝试 22%**。

- 顺风风速越大，传播概率越高。
- 逆风风速越大，传播概率越低。
- 迎风分量达到 **8 m/s 或更高**时，阻止向该方向传播。
- 斜向传播使用风在尝试传播方向上的分量，而非完整风速。
- 正侧风传播使用无风时的基准概率。
- 缺少风向数据时，方向传播使用无风基准。

这些概率影响火势在网格中推进的快慢；风不会改变模拟时钟，也不会让火焰跳过格子。

### 雨雪

雨雪会降低点燃概率，并缩短燃烧格子的寿命。火势模型将降雪换算为液态水当量。

| 降水强度 | 相对于相同风况、无降水时的点燃概率 |
| --- | --- |
| 0 mm/h | 100% |
| 1 mm/h | 约 45% |
| 2 mm/h | 约 20% |
| 5 mm/h | 约 1.8% |

每个新点燃格子的初始寿命为 7 个单位。每一步，降水先扣除 `1.5 × precipitation_rate` 个寿命单位。如果格子此时熄灭，就不能继续传播；仍在燃烧的格子尝试点燃邻居，然后再扣除 1 个寿命单位。

降水强度达到 5 mm/h 时，新点燃的格子会在下一步传播前熄灭。仍然可以手动点火，熄灭后的格子变成灰烬。

模型根据 API 的降水累计时间换算每小时强度。优先使用总降水量；总量缺失时，合并雨、阵雨和降雪，避免重复计算降雪。

温度和湿度会显示在界面中，但目前不影响火势。选择位置时会获取天气，也可通过 **Refresh Weather** 更新。天气加载中或不可用时，模拟采用无风、无降水条件。

### 模型公式

设 `u` 为风在尝试传播方向上的分量，单位为 m/s：顺风为正，逆风为负。`r` 为液态水当量降水强度，单位为 mm/h。

```text
当 u >= 0 时：
    wind_factor = 1 + 0.20 * u

当 u < 0 时：
    wind_factor = max(0, 1 + u / 8) ** 2

ignition_probability = (1 - 0.78 ** wind_factor) * exp(-0.8 * r)
```

模型输入的风速上限为 60 m/s，降水强度上限为 100 mm/h。这些是游戏规则，并非经过标定的物理火灾方程。

## 雨雪特效

雨表现为蓝色线条，雪表现为飘落的白色粒子。降水越强，粒子越密、下落越快。雨和雪可以同时出现。

在 **Forest Settings → Rain / snow effects** 中选择：

| 档位 | 视觉效果 |
| --- | --- |
| Off（关闭） | 不显示雨雪粒子 |
| Light（轻量） | 粒子数量约为完整模式的四分之一，目标帧率约 15 帧／秒 |
| Full（完整） | 完整粒子密度，目标帧率约 30 帧／秒 |

实际帧率取决于硬件和模拟负载。粒子数量设有上限，以控制渲染开销。

此设置仅影响外观：**关闭特效不会关闭天气对火势的影响**。火势模拟暂停时，天气动画仍继续播放。粒子始终位于地图范围内，并显示在风向和罗盘卡片下方。

## 燃烧统计与截图

地图操作说明下方的底部区域显示：

- 过火格子总数：**正在燃烧的格子数 + 灰烬格子数**。
- 以公顷和平方公里表示的估算过火面积。
- 单独列出的燃烧格子数和灰烬格子数。

面积根据当前已加载地图计算：

```text
cell_area_km2 = (map_side_km / grid_size) ** 2
fire_affected_area_km2 = (burning_cells + ash_cells) * cell_area_km2
```

一个格子代表一片土地，而非一棵树。重置或更换地图会清除过火面积统计。

点击 **Save Screenshot（保存截图）** 选择保存位置并导出 PNG。图片包含当前地形与火势、可见雨雪、风向与罗盘、城市与天气、地图范围以及过火统计。图像在保存对话框打开前生成。

导出通过直接绘制地图完成，不会截取其他桌面窗口。地形地图加载完成后才可使用截图功能。

## 地形数据与地图尺度

地图使用 **ESA WorldCover 2021 v200** 历史土地覆盖分类数据，源数据分辨率约为 10 m。所有地图范围均使用 **400 × 400** 模拟网格。

| 地图范围 | 格子近似宽度 |
| --- | --- |
| 5 × 5 km | 12.5 m |
| 10 × 10 km | 25 m |
| 20 × 20 km | 50 m |
| 40 × 40 km | 100 m |

源像素通过按纬度加权的地形投票聚合成游戏格子。森林包括树木覆盖区和红树林；建成区映射为城市地形；永久水体映射为水体；其他有效类别映射为普通地面。

游戏保留地形的地理分布，不会随机放置树木。聚合过程中，小片森林、狭窄河流及其他细小地物可能消失，尤其是在较大的地图范围下。

地图覆盖所选坐标周围的正方形区域，而非整个行政区域。支持的中心纬度范围为南纬 80° 至北纬 80°。有效源数据覆盖不足或源瓦片不可用时，会显示加载错误。

当前会话最多缓存 16 组位置与地图范围组合。目前尚未提供持久化离线地图缓存。

## 打包 Windows 可执行文件

请**在 Windows 上**构建 Windows 可执行文件。PyInstaller 不是交叉编译器：Linux 上的构建不会生成 Windows 可执行文件。详见 [PyInstaller 运行模式文档](https://pyinstaller.org/en/stable/operating-mode.html)。

以下命令假设前文的 Windows `.venv` 环境已经准备好，且源码程序可以正常运行。不要复用从 Linux 复制过来的虚拟环境。

### 安装打包工具

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pyinstaller-hooks-contrib
```

### 构建文件夹形式的发布版本

建议先使用此模式，便于测试和排查问题：

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onedir --windowed --name MakeAFireInForest --paths src --collect-all rasterio src/main.py
```

预期输出：

```text
dist/
└── MakeAFireInForest/
    ├── MakeAFireInForest.exe
    └── _internal/
```

请分发**整个** `dist/MakeAFireInForest/` 文件夹，例如将其压缩为 ZIP。在此模式下，仅提供可执行文件是不够的。

`--collect-all rasterio` 显式收集 Rasterio 的子模块、数据和二进制文件。参数详情见 [PyInstaller 使用文档](https://pyinstaller.org/en/stable/usage.html)。

### 可选：构建单文件版本

验证文件夹版本正常后，可执行：

```powershell
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --windowed --name MakeAFireInForest --paths src --collect-all rasterio src/main.py
```

输出文件为 `dist/MakeAFireInForest.exe`。单文件版本启动时会解压依赖，因此可能启动较慢，尤其是在包含 Rasterio/GDAL 的情况下。

### 验证打包结果

在未安装 Python 的 Windows 电脑上测试：

- 启动程序并调整窗口大小。
- 搜索城市并加载地形。
- 刷新天气、更换地图范围。
- 点火、暂停、继续和重置。
- 切换天气特效档位。
- 保存截图，检查文字和地图标识。

如果程序直接退出且没有有效错误信息，可将 `--windowed` 替换为 `--console` 重新打包，再从 PowerShell 启动以查看异常堆栈。上述命令是构建起点，生成的 Windows 发布版本仍需在目标系统上验证。

## 项目结构

```text
Make_a_fire_in_forest/
├── src/
│   ├── main.py              # 应用窗口、控件与模拟循环
│   ├── forest.py            # 燃烧状态与传播规则
│   ├── weather.py           # 定位、城市搜索与天气接口
│   ├── landcover.py         # 地形获取与聚合
│   ├── location_panel.py    # 位置与天气控件
│   ├── coverage_panel.py    # 后台地形加载
│   ├── map_config.py        # 网格与地图范围设置
│   ├── map_renderer.py      # 栅格地图渲染
│   ├── weather_effects.py   # 动态雨雪效果
│   └── screenshot.py        # PNG 地图导出
├── tests/                   # 本地测试；由 Git 忽略
├── docs/                    # 补充文档
├── requirements.txt
└── README.md
```

本地 `tests/` 目录未被 Git 跟踪，新克隆的仓库中不包含该目录。

如果已有测试脚本，在项目根目录执行：

**Linux**

```bash
PYTHONPATH=src ./proj_env/bin/python -B -m unittest discover -s tests -v
```

**Windows — PowerShell**

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

## 常见问题与限制

- **自动定位不准确：** IP 定位只能提供近似位置，VPN 或代理可能影响结果。请手动搜索城市。
- **地形无法加载：** 检查网络后重试，或尝试更小的地图范围、其他位置。较大的范围需要读取更多源数据。
- **地图上没有森林：** 所选区域可能主要是建成区、水体或其他地面。可尝试其他位置或更大的地图范围。
- **天气不可用：** 点击 Refresh Weather 重试。天气不可用时使用无风、无降水条件。
- **动画卡顿：** 将雨雪特效设为 Light 或 Off，并降低模拟速度。
- **截图文字缺失或显示为方框：** 导出效果取决于可用字体。当前导出器依次尝试 Linux `fc-match`、DejaVu Sans 和 Pillow 默认字体。Windows 和非拉丁文字可能需要配置适合该平台的字体；项目未内置中文字体支持。
- **不同地图范围下，火势看起来以相似速度传播：** 规则以网格步为单位运行。改变地图范围会改变每格对应的米数，但不会重新标定传播时间。

模型未模拟地形坡度、可燃物差异、土壤湿度、积雪、城市火灾或草地火灾。土地覆盖使用历史数据，并非实时街道地图或卫星图。定位、天气和地形获取均依赖第三方服务及其可用性。

## 数据来源与署名

- **土地覆盖：** [ESA WorldCover 数据获取](https://esa-worldcover.org/en/data-access)及 [WorldCover 2021 数据集](https://doi.org/10.5281/zenodo.7254221)，依据 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 分发。
- **IP 定位：** [ipapi](https://ipapi.co/api/)。
- **城市搜索：** 通过 [Open-Meteo 地理编码 API](https://open-meteo.com/en/docs/geocoding-api) 获取 GeoNames 数据。
- **天气：** [Open-Meteo](https://open-meteo.com/en/docs)。另请参阅其[条款与使用说明](https://open-meteo.com/en/pricing)。

地形通过局部读取托管于 AWS 的公开云优化 GeoTIFF 获取，无需下载全球数据集。

© ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium.
